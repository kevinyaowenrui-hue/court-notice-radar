import React, { useState, useEffect, useRef } from 'react';
import { 
  Inbox, Filter, CheckCheck, Loader2, X, ChevronDown
} from 'lucide-react';
import { fetchAlerts, markAlertRead, markAllAlertsRead, toggleNoticeStar } from '../api';
import { formatPublishTime } from '../tagUtils';
import NoticeItemRow from './NoticeItemRow';
import NoticeDetailPane from './NoticeDetailPane';
import Pagination from './Pagination';

const HENAN_CITIES_LIST = [
  '全部', '全省', '郑州', '洛阳', '开封', '平顶山', '安阳', '鹤壁',
  '新乡', '焦作', '濮阳', '许昌', '漯河', '三门峡', '南阳',
  '商丘', '信阳', '周口', '驻马店', '济源'
];

const PLATFORMS = [
  { id: '', label: '全部渠道' },
  { id: 'rmfysszc', label: '诉讼资产网' },
  { id: 'ali', label: '阿里法拍' },
  { id: 'jd', label: '京东拍卖' },
  { id: 'rmfyb', label: '人民法院报' },
  { id: 'local_paper', label: '地方报纸' },
  { id: 'caa', label: '中拍平台' },
  { id: 'ggzy', label: '公共资源交易' }
];

export default function AlertCenter({ stats, onAlertCountChange, refreshTrigger }) {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [timeRange, setTimeRange] = useState('today');
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [selectedModule, setSelectedModule] = useState('');
  const [henanOnly, setHenanOnly] = useState(true);
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedNotice, setSelectedNotice] = useState(null);
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const [tabCounts, setTabCounts] = useState({ total: 0, '公告': 0, '拍卖公告': 0, '债权转让': 0 });
  const [platformCounts, setPlatformCounts] = useState({});

  // Pagination states
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);

  // 列表滚动容器 Ref，确保翻页时正常平滑翻滚置顶
  const listContainerRef = useRef(null);

  const loadAlerts = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await fetchAlerts({
        unreadOnly,
        platform: selectedPlatform || undefined,
        moduleType: selectedModule || undefined,
        henanOnly: henanOnly ? true : false,
        henanCity: (henanOnly && selectedCity && selectedCity !== '全部') ? selectedCity : undefined,
        timeRange: timeRange === 'all' ? undefined : timeRange,
        page,
        pageSize
      });
      setAlerts(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || Math.ceil((data.total || 0) / pageSize) || 1);
      if (data.tab_counts) {
        setTabCounts(data.tab_counts);
      }
      if (data.platform_counts) {
        setPlatformCounts(data.platform_counts);
      }

      // 静默轮询时保持当前选中的标的不变；初次加载或手动筛选时查看第一条
      if (!silent) {
        if (data.items && data.items.length > 0) {
          setSelectedNotice(data.items[0].notice);
          if (!data.items[0].is_read) {
            handleMarkRead(data.items[0].id);
          }
        } else {
          setSelectedNotice(null);
        }

        if (listContainerRef.current) {
          listContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
        }
      } else {
        // 静默同步时：如果当前选中标的在列表中有更新，静默更新属性
        if (selectedNotice && data.items) {
          const fresh = data.items.find(i => i.notice?.id === selectedNotice.id);
          if (fresh?.notice) {
            setSelectedNotice(fresh.notice);
          }
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts(false);
  }, [unreadOnly, timeRange, selectedPlatform, selectedModule, henanOnly, selectedCity, page, pageSize]);

  // 全局刷新触发与 10 秒定时自动静默轮询：确保抓取入库或状态变更时全板块实时更新
  useEffect(() => {
    if (refreshTrigger) {
      loadAlerts(true);
    }
  }, [refreshTrigger]);

  useEffect(() => {
    const timer = setInterval(() => {
      loadAlerts(true);
    }, 10000);
    return () => clearInterval(timer);
  }, [unreadOnly, timeRange, selectedPlatform, selectedModule, henanOnly, selectedCity, page, pageSize]);

  const handleMarkRead = async (alertId) => {
    try {
      await markAlertRead(alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a));
      if (onAlertCountChange) onAlertCountChange();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    if (listContainerRef.current) {
      listContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const selectAlertItem = (item) => {
    setSelectedNotice(item.notice);
    if (!item.is_read) {
      handleMarkRead(item.id);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllAlertsRead();
      setAlerts(prev => prev.map(a => ({ ...a, is_read: true })));
      if (onAlertCountChange) onAlertCountChange();
    } catch (err) {
      console.error(err);
    }
  };

  // 键盘极速漫游流: J/K 上下选择预警, S 关注, O 原网, C 复制简报
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tagName = e.target.tagName?.toLowerCase();
      if (tagName === 'input' || tagName === 'textarea' || e.target.isContentEditable) {
        return;
      }

      if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (!alerts.length) return;
        const currentIndex = selectedNotice ? alerts.findIndex(a => a.notice?.id === selectedNotice.id) : -1;
        const nextIndex = Math.min(alerts.length - 1, currentIndex + 1);
        selectAlertItem(alerts[nextIndex]);
      } else if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!alerts.length) return;
        const currentIndex = selectedNotice ? alerts.findIndex(a => a.notice?.id === selectedNotice.id) : 0;
        const prevIndex = Math.max(0, currentIndex - 1);
        selectAlertItem(alerts[prevIndex]);
      } else if (e.key === 's' || e.key === 'S') {
        if (selectedNotice) {
          e.preventDefault();
          handleStarChange(selectedNotice.id, !selectedNotice.is_starred, true);
        }
      } else if (e.key === 'o' || e.key === 'O') {
        if (selectedNotice?.source_url) {
          e.preventDefault();
          window.open(selectedNotice.source_url, '_blank');
        }
      } else if (e.key === 'c' || e.key === 'C') {
        if (selectedNotice && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          const priceInfo = selectedNotice.starting_price 
            ? `¥${Number(selectedNotice.starting_price).toLocaleString('zh-CN')} ${selectedNotice.discount_rate ? `(${selectedNotice.discount_rate}折捡漏)` : ''}`
            : '以公告为准';
          const evalInfo = selectedNotice.eval_price 
            ? `¥${Number(selectedNotice.eval_price).toLocaleString('zh-CN')}`
            : '无评估价/参考公文';
          const lines = [
            `【法拍资产 · 投资尽调简报】`,
            `📍 标的名称：${selectedNotice.title}`,
            `💰 起拍价格：${priceInfo}`,
            `📊 评估价格：${evalInfo}`,
            `⚖️ 处置主体：${selectedNotice.court_name || '法院/处置机构'}`,
            `📑 模块阶段：${selectedNotice.module_type || '公告'}${selectedNotice.auction_stage ? ` · ${selectedNotice.auction_stage}` : ''}`,
            `🗺️ 属地涉豫：${selectedNotice.is_henan ? (selectedNotice.henan_city ? `涉豫 · ${selectedNotice.henan_city}` : '涉豫重点') : '全国标的'}`,
            `📅 发布时间：${formatPublishTime(selectedNotice.publish_time) || '最新'}`,
            `🔗 官方直达：${selectedNotice.source_url}`
          ];
          if (selectedNotice.user_notes) {
            lines.push(`📝 处置便签：${selectedNotice.user_notes}`);
          }
          navigator.clipboard.writeText(lines.join('\n'));
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [alerts, selectedNotice]);

  const handleStarChange = async (noticeId, nextState, shouldCallApi = false) => {
    let targetState = nextState;
    if (targetState === undefined) {
      const current = alerts.find(a => a.notice?.id === noticeId);
      targetState = current?.notice ? !current.notice.is_starred : true;
    }

    setAlerts(prev => prev.map(a => {
      if (a.notice && a.notice.id === noticeId) {
        return { ...a, notice: { ...a.notice, is_starred: targetState } };
      }
      return a;
    }));

    if (selectedNotice?.id === noticeId) {
      setSelectedNotice(prev => ({ ...prev, is_starred: targetState }));
    }

    if (shouldCallApi) {
      try {
        const res = await toggleNoticeStar(noticeId);
        const actualState = res?.is_starred !== undefined ? res.is_starred : targetState;
        if (actualState !== targetState) {
          setAlerts(prev => prev.map(a => {
            if (a.notice && a.notice.id === noticeId) {
              return { ...a, notice: { ...a.notice, is_starred: actualState } };
            }
            return a;
          }));
          if (selectedNotice?.id === noticeId) {
            setSelectedNotice(prev => ({ ...prev, is_starred: actualState }));
          }
        }
      } catch (err) {
        console.error('Failed to toggle notice star:', err);
        setAlerts(prev => prev.map(a => {
          if (a.notice && a.notice.id === noticeId) {
            return { ...a, notice: { ...a.notice, is_starred: !targetState } };
          }
          return a;
        }));
        if (selectedNotice?.id === noticeId) {
          setSelectedNotice(prev => ({ ...prev, is_starred: !targetState }));
        }
      }
    }

    if (onAlertCountChange) {
      onAlertCountChange();
    }
  };

  const handleNotesUpdated = (noticeId, notes) => {
    setAlerts(prev => prev.map(a => {
      if (a.notice && a.notice.id === noticeId) {
        return { ...a, notice: { ...a.notice, user_notes: notes } };
      }
      return a;
    }));
    if (selectedNotice && selectedNotice.id === noticeId) {
      setSelectedNotice(prev => ({ ...prev, user_notes: notes }));
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0b0f19]">
      {/* 顶部控制栏：分段控件 + 状态标签 + 筛选入口 */}
      <div className="px-4 py-2.5 border-b border-[#1e2638] bg-[#111726] flex flex-wrap items-center justify-between gap-3 shrink-0">
        {/* 左侧：业务模块分段统计切换 */}
        <div className="flex items-center space-x-1 bg-[#161e31] p-0.5 rounded-md border border-[#1e2638] text-xs">
          {[
            { id: '', label: '全部预警', count: tabCounts.total ?? (stats?.total_alerts || 0) },
            { id: '公告', label: '法院公告', count: tabCounts['公告'] ?? 0 },
            { id: '拍卖公告', label: '司法拍卖', count: tabCounts['拍卖公告'] ?? 0 },
            { id: '债权转让', label: '债权转让', count: tabCounts['债权转让'] ?? 0 },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => { setSelectedModule(tab.id); setPage(1); }}
              className={`px-3 py-1 rounded transition-all font-medium flex items-center space-x-1.5 ${
                selectedModule === tab.id
                  ? 'bg-[#182238] text-amber-300 border border-amber-500/30 font-semibold shadow-xs'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9]'
              }`}
            >
              <span>{tab.label}</span>
              <span className="text-[11px] opacity-80 tabular-nums">({tab.count})</span>
            </button>
          ))}
        </div>

        {/* 时效筛选胶囊：以当天最新发布为主 */}
        <div className="flex items-center space-x-1 bg-[#161e31] p-0.5 rounded-md border border-[#1e2638] text-xs">
          {[
            { id: 'today', label: '🟢 今日最新' },
            { id: '3days', label: '近3天' },
            { id: '7days', label: '近7天' },
            { id: 'all', label: '全部' },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => { setTimeRange(t.id); setPage(1); }}
              className={`px-2.5 py-1 rounded transition-all font-medium ${
                timeRange === t.id
                  ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/50 font-bold shadow-xs'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* 右侧：快速过滤与全部已读 */}
        <div className="flex items-center space-x-2">
          {/* 涉豫切换 */}
          <button
            onClick={() => { setHenanOnly(!henanOnly); setSelectedCity(''); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors border ${
              henanOnly
                ? 'bg-amber-950/40 text-amber-300 border-amber-800/60 font-semibold'
                : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9]'
            }`}
            title={henanOnly ? "当前仅筛选涉豫重点预警，点击切换为全国大盘" : "当前为全国大盘，点击开启河南属地专注筛选"}
          >
            {henanOnly ? '涉豫重点' : '全国大盘'}
          </button>

          {/* 仅未读按钮：与当前时间维度动态对齐 */}
          <button
            onClick={() => { setUnreadOnly(!unreadOnly); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors border ${
              unreadOnly
                ? 'bg-rose-950/40 text-rose-300 border-rose-800/60 font-semibold'
                : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9]'
            }`}
            title={
              unreadOnly 
                ? "当前已过滤未读预警，点击显示全部预警" 
                : timeRange === 'today'
                  ? `点击仅查看今日未读预警 (${stats?.today_unread_alerts ?? '今日'} 条)`
                  : `点击仅查看未读预警 (全库累计 ${stats?.unread_alerts || 0} 条)`
            }
          >
            {unreadOnly 
              ? `已筛未读 (${total})` 
              : timeRange === 'today'
                ? `仅未读 (${stats?.today_unread_alerts ?? 0})`
                : timeRange === 'all'
                  ? `仅未读 (${stats?.unread_alerts ?? 0})`
                  : '仅看未读'
            }
          </button>

          {/* 全库历史未读一键直达入口：明确 211 条是历史上未读预警，点击即可一网打尽 */}
          {timeRange !== 'all' && stats?.unread_alerts > 0 && (
            <button
              onClick={() => { setTimeRange('all'); setUnreadOnly(true); setPage(1); }}
              className="hidden 2xl:flex items-center space-x-1 px-2 py-1 text-[11px] rounded font-medium bg-amber-950/30 text-amber-300 border border-amber-500/30 hover:bg-amber-900/40 transition-colors"
              title={`全库历史各时间段累计未读共 ${stats.unread_alerts} 条。点击将时间切换为【全部】并一键筛选出这 ${stats.unread_alerts} 条未读预警`}
            >
              <span>历史累计未读 {stats.unread_alerts} 条</span>
              <span className="text-[10px] text-[#94a3b8]">· 一键看全部</span>
            </button>
          )}

          {/* 更多筛选展开 */}
          <button
            onClick={() => setFilterPanelOpen(!filterPanelOpen)}
            className={`flex items-center space-x-1 px-2.5 py-1 text-xs rounded-md font-medium transition-colors border ${
              filterPanelOpen || selectedPlatform || selectedCity
                ? 'bg-[#182238] text-[#60a5fa] border-blue-500/40'
                : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9]'
            }`}
          >
            <Filter className="w-3 h-3" />
            <span>筛选</span>
            {(selectedPlatform || selectedCity) && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            )}
            <ChevronDown className={`w-3 h-3 transition-transform ${filterPanelOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* 全部标记已读 */}
          {stats?.unread_alerts > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="flex items-center space-x-1 px-2.5 py-1 text-xs rounded-md font-medium text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#161e31] border border-[#1e2638] transition-colors"
              title="将全部预警标记为已读"
            >
              <CheckCheck className="w-3.5 h-3.5 text-[#64748b]" />
              <span className="hidden sm:inline">全部已读</span>
            </button>
          )}
        </div>
      </div>

      {/* 7 大信息源渠道专属全景切换栏 */}
      <div className="px-4 py-2 border-b border-[#1e2638] bg-[#0e1424] flex items-center justify-between gap-2 overflow-x-auto no-scrollbar shrink-0 text-xs">
        <div className="flex items-center space-x-1.5 shrink-0">
          <span className="text-[#64748b] text-[11px] font-semibold shrink-0 mr-1">
            7大数据源:
          </span>
          {[
            { id: '', label: '全部渠道', count: platformCounts.total ?? (tabCounts.total ?? total) },
            { id: 'rmfysszc', label: '诉讼资产网', count: platformCounts.rmfysszc ?? 0 },
            { id: 'ali', label: '阿里法拍', count: platformCounts.ali ?? 0 },
            { id: 'jd', label: '京东拍卖', count: platformCounts.jd ?? 0 },
            { id: 'rmfyb', label: '人民法院报', count: platformCounts.rmfyb ?? 0 },
            { id: 'local_paper', label: '地方报纸', count: platformCounts.local_paper ?? 0 },
            { id: 'ggzy', label: '公共资源交易', count: platformCounts.ggzy ?? 0 },
            { id: 'caa', label: '中拍平台', count: platformCounts.caa ?? 0 },
          ].map(p => {
            const isActive = selectedPlatform === p.id;
            return (
              <button
                key={p.id}
                onClick={() => { setSelectedPlatform(p.id); setPage(1); }}
                className={`px-2.5 py-1 rounded-md transition-all font-medium flex items-center space-x-1.5 shrink-0 border ${
                  isActive
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/60 font-bold shadow-xs'
                    : 'bg-[#141b2d] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9] hover:border-[#2d3748]'
                }`}
              >
                <span>{p.label}</span>
                <span className={`text-[11px] tabular-nums px-1.5 py-0.2 rounded-full ${
                  isActive 
                    ? 'bg-amber-400/20 text-amber-300 font-semibold' 
                    : p.count > 0 
                      ? 'bg-[#1e293b] text-[#cbd5e1]' 
                      : 'text-[#475569]'
                }`}>
                  {p.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* 当某个平台在当前时间段无预警但在其他时间段有预警时的智能快捷提示 */}
        {selectedPlatform && (platformCounts[selectedPlatform] === 0 || total === 0) && stats?.platform_counts?.[selectedPlatform] > 0 && timeRange !== 'all' && (
          <button
            onClick={() => { setTimeRange('all'); setPage(1); }}
            className="flex items-center space-x-1 px-2.5 py-1 text-[11px] rounded bg-amber-950/40 text-amber-300 border border-amber-500/40 hover:bg-amber-900/40 transition-colors shrink-0"
            title={`该渠道在当前时间段暂无新标的，全库累计共有 ${stats.platform_counts[selectedPlatform]} 条。点击切换为全部时间`}
          >
            <span>当前为0 · 全库累计 {stats.platform_counts[selectedPlatform]} 条 (点击查看)</span>
          </button>
        )}
      </div>

      {/* 展开的轻量高级筛选抽屉面板 */}
      {filterPanelOpen && (
        <div className="px-5 py-3 border-b border-[#1e2638] bg-[#0e1320] space-y-3 shrink-0">
          {/* 渠道平台选择 */}
          <div className="flex items-center space-x-2 text-xs flex-wrap gap-y-1.5">
            <span className="text-[#64748b] font-semibold shrink-0">渠道来源:</span>
            {PLATFORMS.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelectedPlatform(p.id); setPage(1); }}
                className={`px-2 py-0.5 rounded text-[11px] transition-colors border ${
                  selectedPlatform === p.id
                    ? 'bg-[#182238] text-amber-300 border-amber-500/40 font-semibold'
                    : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9]'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* 涉豫地市细分 */}
          {henanOnly && (
            <div className="flex items-center space-x-1.5 text-xs flex-wrap gap-y-1.5 pt-1.5 border-t border-[#1e2638]">
              <span className="text-[#64748b] font-semibold shrink-0">地市限定:</span>
              {HENAN_CITIES_LIST.map(c => {
                const isSelected = (!selectedCity && c === '全部') || selectedCity === c;
                return (
                  <button
                    key={c}
                    onClick={() => { setSelectedCity(c === '全部' ? '' : c); setPage(1); }}
                    className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                      isSelected
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                        : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#161e31]'
                    }`}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 激活过滤条件的 Chips 提示条 */}
      {(selectedPlatform || selectedCity || unreadOnly || !henanOnly) && (
        <div className="px-5 py-1.5 bg-[#0e1320] border-b border-[#1e2638] flex items-center space-x-2 text-xs shrink-0 flex-wrap gap-y-1">
          <span className="text-[#64748b] text-[11px]">当前激活条件:</span>
          {!henanOnly && (
            <span className="px-1.5 py-0.2 rounded bg-[#161e31] text-[#cbd5e1] border border-[#1e2638] flex items-center space-x-1 text-[11px]">
              <span>全国大盘</span>
              <button onClick={() => setHenanOnly(true)}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {unreadOnly && (
            <span className="px-1.5 py-0.2 rounded bg-rose-950/40 text-rose-300 border border-rose-800/40 flex items-center space-x-1 text-[11px]">
              <span>仅看未读</span>
              <button onClick={() => setUnreadOnly(false)}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {selectedPlatform && (
            <span className="px-1.5 py-0.2 rounded bg-[#182238] text-amber-300 border border-amber-500/30 flex items-center space-x-1 text-[11px]">
              <span>渠道: {PLATFORMS.find(p => p.id === selectedPlatform)?.label}</span>
              <button onClick={() => setSelectedPlatform('')}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {selectedCity && (
            <span className="px-1.5 py-0.2 rounded bg-amber-950/40 text-amber-300 border border-amber-800/40 flex items-center space-x-1 text-[11px]">
              <span>地市: {selectedCity}</span>
              <button onClick={() => setSelectedCity('')}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          <button 
            onClick={() => { setSelectedPlatform(''); setSelectedCity(''); setUnreadOnly(false); setHenanOnly(true); }}
            className="text-[11px] text-[#60a5fa] hover:underline ml-2"
          >
            重置全部
          </button>
        </div>
      )}

      {/* 主双栏区域：左侧列表 + 右侧常驻详情 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧预警列表 */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#111726]">
          <div ref={listContainerRef} className="flex-1 overflow-y-auto divide-y divide-[#1e2638] scroll-smooth">
            {loading ? (
              <div className="py-20 flex flex-col items-center justify-center text-[#64748b] text-xs space-y-2">
                <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                <span>检索实时预警事件中...</span>
              </div>
            ) : alerts.length === 0 ? (
              <div className="py-20 flex flex-col items-center justify-center text-[#64748b] text-xs space-y-3">
                <Inbox className="w-8 h-8 text-[#334155]" />
                <p>当前筛选条件下无预警事件</p>
                <p className="text-[11px] text-[#475569]">
                  后台调度巡检持续运行中，命中监控规则时将实时呈现在此工作台。
                </p>
              </div>
            ) : (
              alerts.map(item => (
                <NoticeItemRow
                  key={item.id}
                  item={item.notice}
                  isSelected={selectedNotice?.id === item.notice?.id}
                  isUnread={!item.is_read}
                  ruleName={item.rule_name}
                  onClick={() => selectAlertItem(item)}
                  onToggleStar={(id, nextState) => handleStarChange(id, nextState, true)}
                />
              ))
            )}
          </div>

          {/* 分页导航与快捷键提示 */}
          {alerts.length > 0 && (
            <div className="shrink-0 border-t border-[#1e2638] bg-[#0e1320]">
              <div className="px-3.5 py-1.5 flex items-center justify-between text-[11px] text-[#64748b] border-b border-[#161e31] select-none">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-amber-400/90">⌨️ 极速漫游:</span>
                  <span><kbd className="px-1 py-0.2 bg-[#161e31] rounded text-[#cbd5e1] border border-[#1e2638]">J / ↓</kbd> 下一条</span>
                  <span><kbd className="px-1 py-0.2 bg-[#161e31] rounded text-[#cbd5e1] border border-[#1e2638]">K / ↑</kbd> 上一条</span>
                  <span><kbd className="px-1 py-0.2 bg-[#161e31] rounded text-[#cbd5e1] border border-[#1e2638]">S</kbd> 关注</span>
                  <span><kbd className="px-1 py-0.2 bg-[#161e31] rounded text-[#cbd5e1] border border-[#1e2638]">O</kbd> 原网</span>
                  <span><kbd className="px-1 py-0.2 bg-[#161e31] rounded text-[#cbd5e1] border border-[#1e2638]">C</kbd> 复制简报</span>
                </div>
                <span className="text-[#64748b] text-[10px]">实时预警初筛</span>
              </div>
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                totalItems={total}
                pageSize={pageSize}
                onPageChange={handlePageChange}
                onPageSizeChange={(newSize) => { setPageSize(newSize); setPage(1); }}
              />
            </div>
          )}
        </div>

        {/* 右侧常驻详情面板 */}
        {selectedNotice && (
          <NoticeDetailPane
            notice={selectedNotice}
            onClose={() => setSelectedNotice(null)}
            onStarChange={(id, nextState) => handleStarChange(id, nextState, false)}
            onNotesUpdated={handleNotesUpdated}
            onSelectNotice={(item) => setSelectedNotice(item)}
          />
        )}
      </div>
    </div>
  );
}
