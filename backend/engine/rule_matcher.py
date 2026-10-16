# -*- coding: utf-8 -*-
import re
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models import CourtNotice, MonitorRule, AlertEvent

def clean_notice_content(raw_content: str) -> str:
    """
    清洗公告正文中的爬虫模板字样、字段标签和系统源说明，保留纯粹的案件及标的物真实描述，
    彻底避免规则关键词或排除词被爬虫框架模板词污染/误杀。
    """
    if not raw_content:
        return ""
    text = raw_content
    # 移除爬虫系统注入的模版行和元数据标签
    patterns = [
        r'【阿里司法拍卖真实标的】',
        r'【京东拍卖】',
        r'【中拍平台信息公示】',
        r'平台来源：[^\n]+',
        r'（该数据来源于[^\n]+）',
        r'（数据来源于地方报纸官方实时网络版发布）',
        r'报纸媒体：[^\n]+',
        r'所属版面：[^\n]+',
        r'报社电子报入口：[^\n]+',
        r'原文阅读链接：[^\n]+',
        r'详情链接：[^\n]+',
        r'查看原始公示：[^\n]+',
        r'原站直达：[^\n]+',
        r'标的物：',
        r'标的名称：',
        r'当前起拍价：',
        r'拍卖阶段：',
        r'处置法院：',
        r'处置主体/拍卖行：',
        r'发布法院：',
        r'涉案当事人/受送达人：',
        r'公告类型：',
        r'刊登发布日期：',
        r'刊登标题：',
        r'公示时间：',
    ]
    for pat in patterns:
        text = re.sub(pat, ' ', text)
    return text.strip()

def check_match(notice: CourtNotice, rule: MonitorRule) -> Optional[dict]:
    """检查单条公示是否命中某条规则，支持排除词一票否决、业务模块过滤及地市定向"""
    try:
        platforms = json.loads(rule.platforms) if rule.platforms else []
    except Exception:
        platforms = []
    
    # 1. 平台过滤
    if platforms and notice.platform not in platforms:
        return None

    try:
        module_types = json.loads(rule.module_types) if getattr(rule, "module_types", None) else []
    except Exception:
        module_types = []

    # 2. 核心业务模块过滤 (公告 / 拍卖公告 / 债权转让)
    if module_types and (notice.module_type or "公告") not in module_types:
        return None

    # 2.5 拍卖阶段专属互斥校验（杜绝一拍标的误报二拍规则、二拍标的误报一拍规则）
    rule_name_str = rule.name or ""
    is_rule_first_auction = any(k in rule_name_str for k in ["一拍", "第一次拍卖", "首拍"])
    is_rule_second_auction = any(k in rule_name_str for k in ["二拍", "第二次拍卖"])

    notice_title = notice.title or ""
    notice_stage = notice.auction_stage or ""
    if not notice_stage or notice_stage == "司法拍卖":
        if "第二次拍卖" in notice_title or "二拍" in notice_title:
            notice_stage = "二拍"
        elif "第一次拍卖" in notice_title or "一拍" in notice_title or "首拍" in notice_title:
            notice_stage = "一拍"
        elif "变卖" in notice_title:
            notice_stage = "变卖"

    if is_rule_second_auction and not is_rule_first_auction:
        # 二拍专属规则：若标的为一拍或变卖，坚决拒绝匹配
        if notice_stage in ["一拍", "首拍", "变卖"] or ("第一次拍卖" in notice_title and "第二次拍卖" not in notice_title):
            return None
    elif is_rule_first_auction and not is_rule_second_auction:
        # 一拍专属规则：若标的为二拍或变卖，坚决拒绝匹配
        if notice_stage in ["二拍", "第二次拍卖", "变卖"] or ("第二次拍卖" in notice_title and "第一次拍卖" not in notice_title):
            return None

    try:
        exclude_keywords = json.loads(rule.exclude_keywords) if getattr(rule, "exclude_keywords", None) else []
    except Exception:
        exclude_keywords = []

    clean_content = clean_notice_content(notice.content_text or '')
    text_corpus = f"{notice.title or ''} {clean_content} {notice.court_name or ''} {notice.parties or ''}"

    # 3. 排除词一票否决 (命中任一排除词则彻底不报警，基于清洗后纯业务文本)
    if exclude_keywords:
        for ex in exclude_keywords:
            if ex and ex in text_corpus:
                return None

    try:
        cities = json.loads(rule.cities) if getattr(rule, "cities", None) else []
    except Exception:
        cities = []

    # 4. 涉豫地市定向过滤
    if cities:
        city_matched = False
        notice_city = notice.henan_city or ""
        if "全省" in cities and (notice.is_henan or notice_city):
            city_matched = True
        elif notice_city and notice_city in cities:
            city_matched = True
        else:
            # 兼容：如果公示内容直接包含规则指定的地市名
            for c in cities:
                if c != "全省" and c and (c in (notice.court_name or "") or c in (notice.title or "")):
                    city_matched = True
                    break
        if not city_matched:
            return None

    # 5. 价格区间过滤（若规则明确设定了价格下限或上限，无起拍价的标的一律不予匹配）
    if rule.price_min is not None or rule.price_max is not None:
        if notice.starting_price is None:
            return None
        if rule.price_min is not None and notice.starting_price < rule.price_min:
            return None
        if rule.price_max is not None and notice.starting_price > rule.price_max:
            return None

    try:
        courts = json.loads(rule.courts) if rule.courts else []
        parties = json.loads(rule.parties) if rule.parties else []
        case_numbers = json.loads(rule.case_numbers) if rule.case_numbers else []
        keywords = json.loads(rule.keywords) if rule.keywords else []
    except Exception:
        courts, parties, case_numbers, keywords = [], [], [], []

    # 命中条件判断（如果规则未配置任何具体关键词或地市，则不误报）
    if not any([courts, parties, case_numbers, keywords, cities]):
        return None

    reasons = []
    highlights = []

    # 1. 法院匹配
    if courts and notice.court_name:
        for c in courts:
            if c and c in notice.court_name:
                reasons.append(f"命中法院: {c}")
                highlights.append(f"法院: {notice.court_name}")
                break

    # 2. 当事人匹配
    if parties and notice.parties:
        for p in parties:
            if p and p in notice.parties:
                reasons.append(f"命中当事人: {p}")
                highlights.append(f"涉案当事人: {notice.parties}")
                break

    # 3. 案号匹配
    if case_numbers and notice.case_number:
        for cn in case_numbers:
            if cn and cn in notice.case_number:
                reasons.append(f"命中案号: {cn}")
                highlights.append(f"案号: {notice.case_number}")
                break

    # 4. 全文/标题关键词匹配
    if keywords:
        for kw in keywords:
            if kw and kw in text_corpus:
                reasons.append(f"命中关键词: {kw}")
                idx = text_corpus.find(kw)
                start = max(0, idx - 20)
                end = min(len(text_corpus), idx + len(kw) + 30)
                snippet = text_corpus[start:end]
                highlights.append(f"...{snippet}...")
                break

    # 5. 地市定向匹配 (仅当规则未配置任何具体法院/当事人/案号/关键词等限制时，纯属地大盘监控才以地市为由报警)
    if not any([courts, parties, case_numbers, keywords]) and cities:
        reasons.append(f"涉豫地市定向: {notice.henan_city or '属地标的'}")
        highlights.append(f"涉案地市: {notice.henan_city or '河南'}")

    if reasons:
        return {
            "match_reason": " | ".join(reasons),
            "highlight_text": " ".join(highlights)
        }
    return None

def match_new_notices(db: Session, new_notices: List[CourtNotice]) -> List[AlertEvent]:
    """批量匹配新入库公示与活跃规则，实行源头一标一警写入合并"""
    if not new_notices:
        return []

    active_rules = db.query(MonitorRule).filter(MonitorRule.is_active == True).all()
    if not active_rules:
        return []

    alerts_created = []
    seen_notice_ids = set()

    for notice in new_notices:
        if not notice or not notice.id:
            continue
        if notice.id in seen_notice_ids:
            continue
        seen_notice_ids.add(notice.id)

        matched_rules = []
        for rule in active_rules:
            match_res = check_match(notice, rule)
            if match_res:
                matched_rules.append((rule, match_res))

        if not matched_rules:
            continue

        hit_rule_names = [rule.name for rule, _ in matched_rules if rule.name]
        hit_reasons = [m.get("match_reason") for _, m in matched_rules if m.get("match_reason")]
        hit_highlights = [m.get("highlight_text") for _, m in matched_rules if m.get("highlight_text")]

        # 在 alert_events 表中按 notice_id 唯一查重（每个 notice_id 全局只生成唯一 1 条 AlertEvent）
        existing = db.query(AlertEvent).filter(AlertEvent.notice_id == notice.id).first()
        if existing:
            # 仅合并追加新规则名与原因，绝不插入第 2 行，且绝不重置已有的 is_read 状态
            curr_rules = [r.strip() for r in (existing.rule_name or "").split(" | ") if r.strip()]
            added_any = False
            for rn in hit_rule_names:
                if rn not in curr_rules:
                    curr_rules.append(rn)
                    added_any = True

            curr_reasons = [re.strip() for re in (existing.match_reason or "").split(" ；") if re.strip()]
            for hr in hit_reasons:
                if hr not in curr_reasons:
                    curr_reasons.append(hr)
                    added_any = True

            if added_any:
                existing.rule_name = " | ".join(curr_rules)
                existing.match_reason = " ；".join(curr_reasons)
                alerts_created.append(existing)
        else:
            primary_rule = matched_rules[0][0]
            dedup_rules = list(dict.fromkeys(hit_rule_names))
            dedup_reasons = list(dict.fromkeys(hit_reasons))

            alert = AlertEvent(
                rule_id=primary_rule.id,
                rule_name=" | ".join(dedup_rules),
                notice_id=notice.id,
                is_read=False,
                match_reason=" ；".join(dedup_reasons),
                highlight_text=hit_highlights[0] if hit_highlights else ""
            )
            db.add(alert)
            alerts_created.append(alert)

    if alerts_created:
        db.commit()
    return alerts_created

