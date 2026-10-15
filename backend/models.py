# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Index, UniqueConstraint
from backend.database import Base

class CourtNotice(Base):
    """统一司法公示与拍卖数据模型"""
    __tablename__ = "court_notices"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), index=True, nullable=False) # 'ali', 'jd', 'rmfyb', 'local_paper'
    raw_id = Column(String(128), index=True)                   # 平台原生唯一ID
    court_name = Column(String(128), index=True)               # 执行或审理法院
    case_number = Column(String(128), index=True)              # 案号
    parties = Column(Text)                                     # 涉及当事人/被执行人 (JSON或逗号分隔)
    notice_type = Column(String(64), index=True)               # 司法拍卖 / 开庭传票 / 送达裁判文书 / 破产重整等
    module_type = Column(String(32), index=True, default="公告") # 三大核心模块: 公告 / 拍卖公告 / 债权转让
    title = Column(String(512), nullable=False)                # 标的物名称 / 公示标题
    content_text = Column(Text)                                # 正文 / 竞买须知
    publish_time = Column(DateTime, index=True)                # 刊登或上架时间
    source_url = Column(String(1024), nullable=False)          # 官方详情页链接
    
    # 法拍专属扩展字段
    starting_price = Column(Float, nullable=True)              # 起拍价 (元)
    eval_price = Column(Float, nullable=True)                  # 评估价 (元)
    auction_stage = Column(String(32), nullable=True)          # 一拍 / 二拍 / 变卖 / 重新拍卖
    asset_category = Column(String(64), nullable=True)         # 房产 / 车辆 / 股权 / 机械设备
    bidding_start = Column(DateTime, nullable=True)            # 竞价开始时间
    bidding_end = Column(DateTime, nullable=True)              # 竞价结束时间

    # 河南专注模式专属字段 (覆盖河南属地法院 + 全国跨域涉豫资产/当事人)
    is_henan = Column(Boolean, default=False, index=True)      # 是否涉豫
    henan_city = Column(String(64), index=True, nullable=True) # 涉豫地市 (如: 郑州、洛阳、开封、全省等)
    henan_tag = Column(String(128), nullable=True)             # 标签描述 (如: 河南属地法院审理/执行、全国跨域涉豫标的)

    created_at = Column(DateTime, default=datetime.now, index=True)

    # 标的跟进与关注工作流
    is_starred = Column(Boolean, default=False, index=True)      # 是否标记关注/收藏
    user_notes = Column(Text, nullable=True, default="")         # 用户跟进备忘便签

    __table_args__ = (
        Index('idx_platform_rawid', 'platform', 'raw_id', unique=True),
        Index('idx_henan_city', 'is_henan', 'henan_city'),
    )

class MonitorRule(Base):
    """监控规则模型"""
    __tablename__ = "monitor_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)                 # 规则名称，如“关注某某债务人”、“西湖区法拍房”
    is_active = Column(Boolean, default=True)                  # 是否启用
    platforms = Column(Text, default="[]")                     # 监控渠道列表 JSON，如 ["ali", "jd", "rmfyb", "local_paper"]
    courts = Column(Text, default="[]")                        # 监控法院关键词 JSON
    parties = Column(Text, default="[]")                       # 监控当事人关键词 JSON
    case_numbers = Column(Text, default="[]")                  # 监控案号关键词 JSON
    keywords = Column(Text, default="[]")                      # 标的物或正文全文关键词 JSON
    exclude_keywords = Column(Text, default="[]")              # 排除关键词 JSON (命中任意词则一票否决不予预警)
    cities = Column(Text, default="[]")                        # 监控涉豫地市列表 JSON (如 ["郑州", "洛阳", "全省"])
    module_types = Column(Text, default="[]")                  # 监控业务模块列表 JSON (如 ["拍卖公告", "债权转让"])
    price_min = Column(Float, nullable=True)                   # 法拍最低价筛选
    price_max = Column(Float, nullable=True)                   # 法拍最高价筛选
    notify_browser = Column(Boolean, default=True)             # 是否触发浏览器通知
    created_at = Column(DateTime, default=datetime.now)

class AlertEvent(Base):
    """预警命中记录"""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, index=True, nullable=False)      # 命中主规则ID
    rule_name = Column(Text, nullable=False)                   # 命中规则名称（支持多规则组合合并）
    notice_id = Column(Integer, index=True, nullable=False)    # 对应的公示记录ID
    is_read = Column(Boolean, default=False, index=True)       # 是否已读
    match_reason = Column(Text, nullable=False)                # 命中原因描述
    highlight_text = Column(Text)                              # 命中的上下文高亮片段
    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        UniqueConstraint('notice_id', name='uq_alert_notice_id'),
    )

class PaperSeed(Base):
    """53BK 地方报纸入口种子库"""
    __tablename__ = "paper_seeds"

    id = Column(Integer, primary_key=True, index=True)
    province = Column(String(64), index=True, nullable=False)  # 省份
    city = Column(String(64), index=True)                      # 城市
    paper_name = Column(String(128), index=True, nullable=False)# 报纸名称，如《浙江日报》、《浙江法治报》
    epaper_url = Column(String(512), nullable=False)           # 官方电子报网址入口
    is_monitored = Column(Boolean, default=False, index=True)  # 是否加入每日定向巡检
    last_scanned_at = Column(DateTime, nullable=True)          # 最近一次巡检时间
    status = Column(String(32), default="active")              # active, error
    created_at = Column(DateTime, default=datetime.now)

class TaskLog(Base):
    """采集任务运行日志"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), index=True, nullable=False)  # 'ali', 'jd', 'rmfyb', '53bk', 'local_paper'
    task_name = Column(String(128), nullable=False)            # 任务名称
    status = Column(String(32), index=True)                    # success, warning, failed
    items_found = Column(Integer, default=0)                   # 发现条数
    new_items = Column(Integer, default=0)                     # 增量新增条数
    duration_ms = Column(Integer, default=0)                   # 耗时毫秒
    error_msg = Column(Text, nullable=True)                    # 异常信息
    created_at = Column(DateTime, default=datetime.now, index=True)

class SystemSetting(Base):
    """系统全局配置（如 Webhook 推送、通知渠道等）"""
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)                 # 配置键，如 'webhook_config'
    value = Column(Text, nullable=False)                       # 配置值（JSON 字符串）
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

