# -*- coding: utf-8 -*-
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models import CourtNotice, MonitorRule, AlertEvent
from backend.engine.rule_matcher import check_match, clean_notice_content
from backend.engine.webhook import validate_webhook_response

def test_template_cleaning_and_rule_matching():
    print("=" * 60)
    print("测试 1: 爬虫模板词清洗与规则防误杀/防误报校验...")
    print("=" * 60)

    # 模拟中拍平台的公告正文（包含平台来源与网络科技股份有限公司等模板词）
    raw_content = (
        "【中拍平台信息公示】\n"
        "标的名称：郑州市金水区未来路绿地之窗写字楼一间\n"
        "处置主体/拍卖行：河南省拍卖行有限公司\n"
        "公示时间：2026-10-12 10:00:00\n"
        "平台来源：中拍平台（中国拍卖行业协会网络科技股份有限公司）\n"
        "查看原始公示：https://paimai.caa123.org.cn/notice/12345"
    )

    cleaned = clean_notice_content(raw_content)
    print(f"清洗后正文:\n{cleaned}")
    assert "中国拍卖行业协会网络科技股份有限公司" not in cleaned
    assert "平台来源：" not in cleaned
    assert "绿地之窗" in cleaned

    notice = CourtNotice(
        id=99901,
        platform="caa",
        module_type="拍卖公告",
        title="郑州市金水区未来路绿地之窗写字楼拍卖",
        content_text=raw_content,
        court_name="河南省拍卖行有限公司",
        parties="河南某投资有限公司",
        is_henan=True,
        henan_city="郑州"
    )

    # 规则 A: 用户设置排除词 ["网络科技"]（本意排除纯科技类标的）
    # 期望: 不应被模板中的“网络科技股份有限公司”误杀
    rule_a = MonitorRule(
        id=1,
        name="监控郑州房产",
        is_active=True,
        platforms=json.dumps(["caa"]),
        module_types=json.dumps(["拍卖公告"]),
        exclude_keywords=json.dumps(["网络科技"]),
        keywords=json.dumps(["绿地之窗"]),
        cities=json.dumps(["郑州"])
    )
    res_a = check_match(notice, rule_a)
    assert res_a is not None, "规则 A 应该命中，不应被模板中的'网络科技'误杀！"
    print("PASS: 规则 A 未被模板词误杀，成功命中！")

    # 规则 B: 用户设置监控关键词 ["网络科技"]
    # 期望: 不应因为模板中的“网络科技”而误报
    rule_b = MonitorRule(
        id=2,
        name="监控科技公司",
        is_active=True,
        platforms=json.dumps(["caa"]),
        module_types=json.dumps(["拍卖公告"]),
        keywords=json.dumps(["网络科技"]),
        cities=json.dumps(["郑州"])
    )
    res_b = check_match(notice, rule_b)
    assert res_b is None, "规则 B 不应命中（标的物本身不是网络科技，不应被模板污染误触发）！"
    print("PASS: 规则 B 未被模板词污染误触发！")

def test_webhook_response_validation():
    print("\n" + "=" * 60)
    print("测试 2: 第三方 Webhook 平台业务错误码深度校验...")
    print("=" * 60)

    # 企业微信 errcode
    ok, msg = validate_webhook_response("wecom", 200, '{"errcode":0,"errmsg":"ok"}')
    assert ok is True, f"企微 0 应判断为成功: {msg}"
    ok, msg = validate_webhook_response("wecom", 200, '{"errcode":93000,"errmsg":"invalid webhook url"}')
    assert ok is False and "93000" in msg, f"企微 93000 应判断为失败: {msg}"
    print("PASS: 企业微信 errcode 状态研判准确！")

    # 钉钉 errcode
    ok, msg = validate_webhook_response("dingtalk", 200, '{"errcode":0,"errmsg":"ok"}')
    assert ok is True
    ok, msg = validate_webhook_response("dingtalk", 200, '{"errcode":300001,"errmsg":"token is not exist"}')
    assert ok is False and "300001" in msg
    print("PASS: 钉钉 errcode 状态研判准确！")

    # 飞书 code
    ok, msg = validate_webhook_response("feishu", 200, '{"code":0,"msg":"success"}')
    assert ok is True
    ok, msg = validate_webhook_response("feishu", 200, '{"code":19001,"msg":"param error"}')
    assert ok is False and "19001" in msg
    print("PASS: 飞书 code 状态研判准确！")

    # HTTP 4xx/5xx 异常
    ok, msg = validate_webhook_response("generic", 500, 'Internal Server Error')
    assert ok is False and "500" in msg
    print("PASS: HTTP 异常状态码精准捕获！")

def test_alert_event_uniqueness():
    print("\n" + "=" * 60)
    print("测试 3: AlertEvent 数据库 notice_id 单标的唯一约束拦截...")
    print("=" * 60)
    from backend.database import SessionLocal
    from sqlalchemy.exc import IntegrityError
    db = SessionLocal()
    try:
        # 清理可能存在的历史测试记录
        db.query(AlertEvent).filter(AlertEvent.notice_id == 7777).delete()
        db.commit()

        # 插入第一条预警
        a1 = AlertEvent(
            rule_id=8888,
            rule_name="规则A",
            notice_id=7777,
            match_reason="首次插入规则A",
            highlight_text="测试内容"
        )
        db.add(a1)
        db.commit()
        print("PASS: 首次插入 AlertEvent 成功！")

        # 尝试为同一标的插入第二条记录 (即便是不同 rule_id)
        duplicate_caught = False
        try:
            a2 = AlertEvent(
                rule_id=9999,
                rule_name="规则B",
                notice_id=7777,
                match_reason="重复插入规则B",
                highlight_text="测试内容"
            )
            db.add(a2)
            db.commit()
        except IntegrityError:
            db.rollback()
            duplicate_caught = True

        assert duplicate_caught, "数据库应该触发 notice_id 唯一约束异常并成功回滚！"
        print("PASS: 数据库成功触发 notice_id 唯一约束拦截，从底层彻底杜绝一标多警！")
    finally:
        db.query(AlertEvent).filter(AlertEvent.notice_id == 7777).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    test_template_cleaning_and_rule_matching()
    test_webhook_response_validation()
    test_alert_event_uniqueness()
    print("\n" + "=" * 60)
    print("全部校验项目 100% 顺畅通过！")
    print("=" * 60)
