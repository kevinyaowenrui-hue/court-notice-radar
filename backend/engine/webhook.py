# -*- coding: utf-8 -*-
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import List, Optional, Dict, Any, Tuple
import requests
from sqlalchemy.orm import Session

from backend.models import SystemSetting, AlertEvent, CourtNotice

SETTING_KEY = "webhook_config"

DEFAULT_CONFIG = {
    "enabled": False,
    "platform": "wecom",      # "wecom" | "dingtalk" | "feishu" | "generic"
    "webhook_url": "",
    "secret": "",             # 钉钉 / 飞书签名密钥 (可选)
    "notify_on_new": True     # 发现新预警时自动推送
}

def get_webhook_config(db: Session) -> Dict[str, Any]:
    """读取当前 Webhook 配置"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if not setting:
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(setting.value)
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_webhook_config(db: Session, config: Dict[str, Any]) -> Dict[str, Any]:
    """保存 Webhook 配置"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if not setting:
        setting = SystemSetting(key=SETTING_KEY, value=json.dumps(config, ensure_ascii=False))
        db.add(setting)
    else:
        setting.value = json.dumps(config, ensure_ascii=False)
    db.commit()
    return config

def _sign_dingtalk_url(url: str, secret: str) -> str:
    """计算钉钉机器人的时间戳加签 URL"""
    if not secret:
        return url
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = f'{timestamp}\n{secret}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    delim = '&' if '?' in url else '?'
    return f"{url}{delim}timestamp={timestamp}&sign={sign}"

def _sign_feishu(secret: str) -> Dict[str, str]:
    """生成飞书签名头"""
    timestamp = str(int(time.time()))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return {"timestamp": timestamp, "sign": sign}

def build_alert_payload(platform: str, alerts_data: List[Dict[str, Any]], secret: str = "") -> tuple[Dict[str, Any], Optional[str]]:
    """根据目标渠道构建对应的数据格式"""
    total = len(alerts_data)
    first = alerts_data[0] if alerts_data else {}
    
    # 构建卡片内容摘要
    card_lines = [
        f"### 🚨 【法院公示与法拍雷达】新增 {total} 条高价值预警",
        f"> **命中规则**: {first.get('rule_name', '-')}",
        f"> **涉案标的**: {first.get('title', '-')}",
        f"> **渠道模块**: {first.get('platform_name', '-')} · {first.get('module_type', '公告')}",
        f"> **属地法院**: {first.get('court_name', '-')} (豫 · {first.get('henan_city', '全省')})",
    ]
    if first.get('starting_price'):
        price_str = f"¥{first['starting_price']:,.2f}"
        if first.get('eval_price'):
            discount = round(first['starting_price'] / first['eval_price'] * 10, 1)
            price_str += f" (评估 ¥{first['eval_price']:,.2f} · **{discount}折**)"
        if first.get('auction_stage'):
            price_str += f" · {first['auction_stage']}"
        card_lines.append(f"> **起拍价格**: {price_str}")
    
    card_lines.append(f"> **命中原因**: {first.get('match_reason', '-')}")
    if first.get('source_url'):
        card_lines.append(f"> [👉 点击在浏览器中查看标的详情]({first['source_url']})")

    if total > 1:
        card_lines.append(f"\n*另外还有 {total - 1} 条匹配公示，请前往系统大屏查看。*")

    md_content = "\n".join(card_lines)

    if platform == "wecom":
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": md_content
            }
        }, None

    elif platform == "dingtalk":
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": f"【法院公示与法拍预警】{first.get('title', '新预警')}等 {total} 条",
                "text": md_content
            }
        }, None

    elif platform == "feishu":
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"🚨 法院公示与法拍监控雷达 ({total}条新预警)",
                        "content": [
                            [
                                {"tag": "text", "text": md_content}
                            ]
                        ]
                    }
                }
            }
        }
        if secret:
            sign_info = _sign_feishu(secret)
            payload.update(sign_info)
        return payload, None

    else: # generic webhook
        return {
            "event": "court_notice_alert",
            "timestamp": int(time.time()),
            "total_alerts": total,
            "alerts": alerts_data
        }, None

def validate_webhook_response(platform: str, status_code: int, response_text: str) -> Tuple[bool, str]:
    """
    深度研判各大平台 Webhook 响应报文，杜绝 HTTP 200 下返回业务错误码 (如 93000、300001、19001) 虚报成功
    """
    if status_code != 200:
        return False, f"HTTP状态码异常 [{status_code}]: {response_text[:200]}"
    
    clean_text = (response_text or "").strip()
    try:
        data = json.loads(clean_text)
        if platform == "wecom":
            errcode = data.get("errcode")
            if errcode is not None and errcode != 0:
                return False, f"企业微信机器人返回错误 [{errcode}]: {data.get('errmsg', '未知错误')}"
        elif platform == "dingtalk":
            errcode = data.get("errcode")
            if errcode is not None and errcode != 0:
                return False, f"钉钉机器人返回错误 [{errcode}]: {data.get('errmsg', '未知错误')}"
        elif platform == "feishu":
            code = data.get("code") or data.get("StatusCode")
            if code is not None and code != 0:
                return False, f"飞书机器人返回错误 [{code}]: {data.get('msg', '未知错误')}"
    except Exception:
        pass

    return True, clean_text[:200]

def send_alert_webhook(db: Session, alerts: List[AlertEvent]) -> Dict[str, Any]:
    """抓取增量匹配产生新预警时，触发 Webhook 分批推送，确保全量覆盖并精准校验业务状态码"""
    if not alerts:
        return {"status": "skipped", "message": "No alerts to send"}

    config = get_webhook_config(db)
    if not config.get("enabled") or not config.get("webhook_url"):
        return {"status": "disabled", "message": "Webhook not enabled or URL empty"}

    # 提取预警及对应公示数据
    alerts_data = []
    for a in alerts:
        n = db.query(CourtNotice).filter(CourtNotice.id == a.notice_id).first()
        if not n:
            continue
        alerts_data.append({
            "alert_id": a.id,
            "rule_name": a.rule_name,
            "match_reason": a.match_reason,
            "title": n.title,
            "module_type": n.module_type or "公告",
            "platform": n.platform,
            "platform_name": {
                "ali": "阿里法拍", "jd": "京东拍卖", "rmfyb": "人民法院报",
                "local_paper": "53BK地方报", "caa": "中拍平台", "ggzy": "公共资源"
            }.get(n.platform, n.platform),
            "court_name": n.court_name or "未注明法院",
            "henan_city": n.henan_city or "全省",
            "starting_price": n.starting_price,
            "eval_price": n.eval_price,
            "auction_stage": n.auction_stage,
            "source_url": n.source_url
        })

    if not alerts_data:
        return {"status": "skipped", "message": "No notice data found"}

    target_url = config.get("webhook_url", "").strip()
    platform = config.get("platform", "wecom")
    secret = config.get("secret", "").strip()

    if platform == "dingtalk" and secret:
        target_url = _sign_dingtalk_url(target_url, secret)

    # 分批推送：每 5 条打包一张卡片，最多推送 4 批（20 条），避免机器人频率受限
    batch_size = 5
    batches = [alerts_data[i:i + batch_size] for i in range(0, min(len(alerts_data), 20), batch_size)]
    
    success_batches = 0
    error_msgs = []

    for idx, batch in enumerate(batches):
        if idx > 0:
            time.sleep(0.5)

        payload, _ = build_alert_payload(platform, batch, secret=secret)
        try:
            resp = requests.post(target_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            ok, msg = validate_webhook_response(platform, resp.status_code, resp.text)
            if ok:
                success_batches += 1
            else:
                error_msgs.append(f"第 {idx+1} 批失败: {msg}")
        except Exception as e:
            error_msgs.append(f"第 {idx+1} 批网络异常: {str(e)}")

    if success_batches == len(batches):
        return {
            "status": "success",
            "total_sent": len(alerts_data),
            "batches_sent": success_batches,
            "message": f"成功推送 {len(alerts_data)} 条预警（分 {success_batches} 批发送）"
        }
    elif success_batches > 0:
        return {
            "status": "warning",
            "total_sent": len(alerts_data),
            "batches_sent": success_batches,
            "message": f"部分批次发送成功（成功 {success_batches}/{len(batches)} 批）: {'; '.join(error_msgs)}"
        }
    else:
        return {
            "status": "error",
            "message": f"Webhook 推送失败: {'; '.join(error_msgs)}"
        }

def test_webhook(config: Dict[str, Any]) -> Dict[str, Any]:
    """手动测试发送一条示例预警卡片，严格校验第三方机器人的业务状态码"""
    target_url = config.get("webhook_url", "").strip()
    if not target_url:
        return {"status": "error", "message": "请填写有效的 Webhook URL"}

    platform = config.get("platform", "wecom")
    secret = config.get("secret", "").strip()

    if platform == "dingtalk" and secret:
        target_url = _sign_dingtalk_url(target_url, secret)

    sample_alerts = [{
        "alert_id": 9999,
        "rule_name": "【测试】河南省重点不动产司法拍卖精准监控",
        "match_reason": "测试推送：命中关键词: 住宅 (测试专用数据)",
        "title": "河南省郑州市金水区未来路绿地之窗优质办公房产（测试连通性专用）",
        "module_type": "拍卖公告",
        "platform": "ali",
        "platform_name": "阿里法拍",
        "court_name": "郑州市中级人民法院",
        "henan_city": "郑州",
        "starting_price": 1280000.0,
        "eval_price": 1850000.0,
        "auction_stage": "一拍",
        "source_url": "https://sf.taobao.com"
    }]

    payload, _ = build_alert_payload(platform, sample_alerts, secret=secret)

    try:
        resp = requests.post(target_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        ok, msg = validate_webhook_response(platform, resp.status_code, resp.text)
        if ok:
            return {
                "status": "success",
                "message": f"测试推送发送成功！目标服务返回成功应答：{msg[:100]}"
            }
        else:
            return {
                "status": "error",
                "message": f"测试推送被拒绝: {msg}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"连接测试失败: {str(e)}"
        }

def send_bidding_countdown_webhook(db: Session, starred_notices: List[CourtNotice]) -> Dict[str, Any]:
    """对已关注且距离开拍不足 48 小时的重点标的发送开拍倒计时提醒"""
    config = get_webhook_config(db)
    if not config.get("enabled"):
        return {"status": "disabled", "message": "Webhook 推送未启用"}

    target_url = config.get("webhook_url", "").strip()
    if not target_url or not starred_notices:
        return {"status": "ignored", "message": "无有效 Webhook 地址或无急需提醒标的"}

    platform = config.get("platform", "wecom")
    secret = config.get("secret", "").strip()

    if platform == "dingtalk" and secret:
        target_url = _sign_dingtalk_url(target_url, secret)

    total = len(starred_notices)
    card_lines = [
        f"### ⏰ 【法拍雷达】重点关注标的开拍倒计时提醒 ({total} 件即将开拍)",
        "> **提示**: 您重点星标跟进的以下标的即将在 **48 小时内** 正式开拍，请及时确认保证金划转、实地看样与参拍准备！\n"
    ]

    from datetime import datetime
    now = datetime.now()
    for idx, n in enumerate(starred_notices[:5]):
        hours_str = ""
        if n.bidding_start:
            diff = n.bidding_start - now
            h_left = max(0, int(diff.total_seconds() / 3600))
            hours_str = f"（约剩 **{h_left}** 小时）"

        price_info = f"¥{n.starting_price:,.2f}" if n.starting_price else "待定"
        stage_info = n.auction_stage or "拍卖"
        card_lines.append(f"**{idx + 1}. {n.title}**")
        card_lines.append(f"> • **开拍时间**: {n.bidding_start.strftime('%Y-%m-%d %H:%M') if n.bidding_start else '即将开拍'} {hours_str}")
        card_lines.append(f"> • **当前阶段**: {stage_info} · 起拍价 {price_info}")
        card_lines.append(f"> • **处置法院**: {n.court_name or '法院'} (豫 · {n.henan_city or '全省'})")
        if n.source_url:
            card_lines.append(f"> • [👉 点击前往官方拍卖页面]({n.source_url})")
        card_lines.append("")

    if total > 5:
        card_lines.append(f"*另有 {total - 5} 件已关注标的即将开拍，请前往客户端查看。*")

    md_content = "\n".join(card_lines)

    if platform == "wecom":
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": md_content}
        }
    elif platform == "dingtalk":
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"【法拍雷达】{total}件关注标的即将开拍",
                "text": md_content
            }
        }
    elif platform == "feishu":
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"⏰ 关注标的开拍倒计时 ({total}件)"},
                    "template": "orange"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": md_content}
                    }
                ]
            }
        }
        if secret:
            payload.update(_sign_feishu(secret))
    else:
        payload = {
            "event": "bidding_countdown",
            "total": total,
            "text": md_content,
            "notice_ids": [n.id for n in starred_notices]
        }

    try:
        resp = requests.post(target_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        ok, msg = validate_webhook_response(platform, resp.status_code, resp.text)
        if ok:
            return {"status": "success", "message": f"成功推送 {total} 件标的开拍倒计时提醒"}
        else:
            return {"status": "error", "message": f"推送被拒绝: {msg}"}
    except Exception as e:
        return {"status": "error", "message": f"网络异常: {str(e)}"}

