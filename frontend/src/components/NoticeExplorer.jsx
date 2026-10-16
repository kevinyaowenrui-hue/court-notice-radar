import React, { useState, useEffect, useRef } from 'react';
import { 
  Download, Filter, Loader2, X, ChevronDown, Layers, ArrowUpDown, Command, Sparkles, LayoutList, TableProperties
} from 'lucide-react';
import { fetchNotices, fetchStats, toggleNoticeStar } from '../api';
import { formatPublishTime } from '../tagUtils';
import NoticeItemRow from './NoticeItemRow';
import NoticeTableView from './NoticeTableView';
import NoticeDetailPane from './NoticeDetailPane';
import Pagination from './Pagination';

const PLATFORMS = [
  { value: '', label: '全部平台' },
  { value: 'rmfysszc', label: '诉讼资产网' },
  { value: 'ali', label: '阿里法拍' },
  { value: 'jd', label: '京东拍卖' },
  { value: 'rmfyb', label: '人民法院报' },
  { value: 'local_paper', label: '地方报纸' },
  { value: 'caa', label: '中拍平台' },
  { value: 'ggzy', label: '公共资源交易' }
];

const HENAN_CITIES_LIST = [
  '全部', '全省', '郑州', '洛阳', '开封', '平顶山', '安阳', '鹤壁',
  '新乡', '焦作', '濮阳', '许昌', '漯河', '三门峡', '南阳',
  '商丘', '信阳', '周口', '驻马店', '济源'
];

export default function NoticeExplorer({ externalSearchQuery = '', onStarToggled, refreshTrigger, stats }) {
  const [notices, setNotices] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Pagination states
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);

  // Sort and quick presets
  const [sortBy, setSortBy] = useState('publish_time_desc');
  const [discountMax, setDiscountMax] = useState(null);

  // 视图模式: 'card' 卡片流 或 'table' 密集表格
  const [viewMode, setViewMode] = useState(() => {
    return localStorage.getItem('radar_view_mode') || 'card';
  });

  // Filter states
  const [timeRange, setTimeRange] = useState('all');
  const [selectedModule, setSelectedModule] = useState('');
  const [tabCounts, setTabCounts] = useState({ total: 0, '公告': 0, '拍卖公告': 0, '债权转让': 0 });
  const [platformCounts, setPlatformCounts] = useState({});
  const [assetCategory, setAssetCategory] = useState('');
  const [henanOnly, setHenanOnly] = useState(true);
  const [selectedCity, setSelectedCity] = useState('');
  const [platform, setPlatform] = useState('');
  const [court, setCourt] = useState('');
  const [priceMin, setPriceMin] = useState('');
  const [priceMax, setPriceMax] = useState('');
  const [searchQuery, setSearchQuery] = useState(externalSearchQuery);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  // Selected notice for detail pane
  const [selectedNotice, setSelectedNotice] = useState(null);

  // 列表滚动容器 Ref，确保翻页时正常平滑翻滚置顶
  const listContainerRef = useRef(null);

  // 监听筛选条件切换，同步重置分页 page 为 1
  const prevFiltersRef = useRef({ timeRange, platform, selectedModule, selectedCity, assetCategory, henanOnly });
  useEffect(() => {
    const prev = prevFiltersRef.current;
    if (
      prev.timeRange !== timeRange ||
      prev.platform !== platform ||
      prev.selectedModule !== selectedModule ||
      prev.selectedCity !== selectedCity ||
      prev.assetCategory !== assetCategory ||
      prev.henanOnly !== henanOnly
    ) {
      prevFiltersRef.current = { timeRange, platform, selectedModule, selectedCity, assetCategory, henanOnly };
      if (page !== 1) {
        setPage(1);
      }
    }
  }, [timeRange, platform, selectedModule, selectedCity, assetCategory, henanOnly, page]);

  useEffect(() => {
    if (externalSearchQuery !== undefined) {
      setSearchQuery(externalSearchQuery);
    }
  }, [externalSearchQuery]);

  const loadData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const noticeData = await fetchNotices({
        query: searchQuery || undefined,
        platform: platform || undefined,
        court: court || undefined,
        moduleType: selectedModule || undefined,
        assetCategory: assetCategory || undefined,
        henanOnly: henanOnly ? true : false,
        henanCity: (henanOnly && selectedCity && selectedCity !== '全部') ? selectedCity : undefined,
        priceMin: priceMin ? parseFloat(priceMin) : undefined,
        priceMax: priceMax ? parseFloat(priceMax) : undefined,
        discountMax: discountMax || undefined,
        sortBy: sortBy || undefined,
        timeRange: timeRange === 'all' ? undefined : timeRange,
        page,
        pageSize
      });

      setNotices(noticeData.items || []);
      setTotal(noticeData.total || 0);
      setTotalPages(noticeData.total_pages || Math.ceil((noticeData.total || 0) / pageSize) || 1);
      if (noticeData.tab_counts) {
        setTabCounts(noticeData.tab_counts);
      }
      if (noticeData.platform_counts) {
        setPlatformCounts(noticeData.platform_counts);
      }

      // 翻页或筛选后联动更新详情面板
      if (!silent) {
        if (noticeData.items && noticeData.items.length > 0) {
          setSelectedNotice(noticeData.items[0]);
        } else {
          setSelectedNotice(null);
        }

        // 列表平滑翻滚置顶
        if (listContainerRef.current) {
          listContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
        }
      } else {
        if (selectedNotice && noticeData.items) {
          const fresh = noticeData.items.find(i => i.id === selectedNotice.id);
          if (fresh) setSelectedNotice(fresh);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadData(false);
  }, [page, pageSize, selectedModule, assetCategory, henanOnly, selectedCity, platform, searchQuery, sortBy, discountMax, timeRange]);

  useEffect(() => {
    if (refreshTrigger) {
      loadData(true);
    }
  }, [refreshTrigger]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        return;
      }
      loadData(true);
    }, 10000);
    return () => clearInterval(timer);
  }, [page, pageSize, selectedModule, assetCategory, henanOnly, selectedCity, platform, searchQuery, sortBy, discountMax, timeRange]);

  // 键盘极速漫游流: J/K 上下选择, S 标星关注, O 打开原网, C 复制微信简报
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tagName = e.target.tagName?.toLowerCase();
      if (tagName === 'input' || tagName === 'textarea' || e.target.isContentEditable) {
        return;
      }

      if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (!notices.length) return;
        const currentIndex = selectedNotice ? notices.findIndex(n => n.id === selectedNotice.id) : -1;
        const nextIndex = Math.min(notices.length - 1, currentIndex + 1);
        setSelectedNotice(notices[nextIndex]);
      } else if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!notices.length) return;
        const currentIndex = selectedNotice ? notices.findIndex(n => n.id === selectedNotice.id) : 0;
        const prevIndex = Math.max(0, currentIndex - 1);
        setSelectedNotice(notices[prevIndex]);
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
  }, [notices, selectedNotice]);

  const handlePageChange = (newPage) => {
    setPage(newPage);
    if (listContainerRef.current) {
      listContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleExportCsv = () => {
    const params = new URLSearchParams();
    if (searchQuery) params.append('query', searchQuery);
    if (platform) params.append('platform', platform);
    if (court) params.append('court', court);
    if (selectedModule) params.append('module_type', selectedModule);
    if (henanOnly) params.append('henan_only', 'true');
    if (henanOnly && selectedCity && selectedCity !== '全部') params.append('henan_city', selectedCity);
    if (priceMin) params.append('price_min', priceMin);
    if (priceMax) params.append('price_max', priceMax);
    if (assetCategory) params.append('asset_category', assetCategory);
    if (discountMax) params.append('discount_max', discountMax);
    if (sortBy) params.append('sort_by', sortBy);
    if (timeRange && timeRange !== 'all') params.append('time_range', timeRange);

    window.open(`/api/notices/export?${params.toString()}`, '_blank');
  };

  const handleStarChange = async (id, nextState, shouldCallApi = false) => {
    let targetState = nextState;
    if (targetState === undefined) {
      const current = notices.find(n => n.id === id);
      targetState = current ? !current.is_starred : true;
    }

    setNotices(prev => prev.map(n => n.id === id ? { ...n, is_starred: targetState } : n));
    if (selectedNotice?.id === id) {
      setSelectedNotice(prev => ({ ...prev, is_starred: targetState }));
    }

    if (shouldCallApi) {
      try {
        const res = await toggleNoticeStar(id);
        const actualState = res?.is_starred !== undefined ? res.is_starred : targetState;
        if (actualState !== targetState) {
          setNotices(prev => prev.map(n => n.id === id ? { ...n, is_starred: actualState } : n));
          if (selectedNotice?.id === id) {
            setSelectedNotice(prev => ({ ...prev, is_starred: actualState }));
          }
        }
      } catch (err) {
        console.error('Failed to toggle notice star:', err);
        setNotices(prev => prev.map(n => n.id === id ? { ...n, is_starred: !targetState } : n));
        if (selectedNotice?.id === id) {
          setSelectedNotice(prev => ({ ...prev, is_starred: !targetState }));
        }
      }
    }

    if (onStarToggled) {
      onStarToggled();
    }
  };

  const handleNotesUpdated = (id, newNotes) => {
    setNotices(prev => prev.map(n => n.id === id ? { ...n, user_notes: newNotes } : n));
    if (selectedNotice?.id === id) {
      setSelectedNotice(prev => ({ ...prev, user_notes: newNotes }));
    }
  };

  const handleCopyBriefingDirect = (item) => {
    if (!item) return;
    const priceInfo = item.starting_price 
      ? `¥${Number(item.starting_price).toLocaleString('zh-CN')} ${item.discount_rate ? `(${item.discount_rate}折捡漏)` : ''}`
      : '以公告为准';
    const evalInfo = item.eval_price 
      ? `¥${Number(item.eval_price).toLocaleString('zh-CN')}`
      : '无评估价/参考公文';
    const lines = [
      `【法拍资产 · 投资尽调简报】`,
      `📍 标的名称：${item.title}`,
      `💰 起拍价格：${priceInfo}`,
      `📊 评估价格：${evalInfo}`,
      `⚖️ 处置主体：${item.court_name || '法院/处置机构'}`,
      `📑 模块阶段：${item.module_type || '公告'}${item.auction_stage ? ` · ${item.auction_stage}` : ''}`,
      `🗺️ 属地涉豫：${item.is_henan ? (item.henan_city ? `涉豫 · ${item.henan_city}` : '涉豫重点') : '全国标的'}`,
      `📅 发布时间：${formatPublishTime(item.publish_time) || '最新'}`,
      `🔗 官方直达：${item.source_url}`
    ];
    if (item.user_notes) {
      lines.push(`📝 处置便签：${item.user_notes}`);
    }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(lines.join('\n'));
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0b0f19]">
      {/* 顶部控制栏 */}
      <div className="px-4 py-2.5 border-b border-[#1e2638] bg-[#111726] flex flex-wrap items-center justify-between gap-3 shrink-0">
        {/* 左侧业务模块分段控件 */}
        <div className="flex items-center space-x-1 bg-[#161e31] p-0.5 rounded-md border border-[#1e2638] text-xs">
          {[
            { id: '', label: '全量公示', count: tabCounts.total ?? (stats?.total_notices || 0) },
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

          {/* 快捷场景胶囊 */}
          <span className="w-px h-4 bg-[#1e2638] mx-1 shrink-0" />
          <button
            onClick={() => {
              if (discountMax === 70) {
                setDiscountMax(null);
                setSortBy('publish_time_desc');
              } else {
                setDiscountMax(70);
                setSortBy('discount_asc');
                setSelectedModule('');
              }
              setPage(1);
            }}
            className={`px-2 py-1 rounded text-[11px] font-medium transition-colors flex items-center space-x-1 ${
              discountMax === 70
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                : 'text-[#94a3b8] hover:text-[#f1f5f9]'
            }`}
            title="一键筛选折扣率 ≤70% 的司法拍卖超值资产"
          >
            <span>🔥 ≤7折捡漏</span>
          </button>

          {/* 重点关注：一拍/二拍刚上拍房源快捷场景 */}
          <button
            onClick={() => {
              if (assetCategory === '住宅/商业房产' && selectedModule === '拍卖公告') {
                setAssetCategory('');
              } else {
                setAssetCategory('住宅/商业房产');
                setSelectedModule('拍卖公告');
                setSortBy('publish_time_desc');
              }
              setPage(1);
            }}
            className={`px-2 py-1 rounded text-[11px] font-medium transition-colors flex items-center space-x-1 ${
              assetCategory === '住宅/商业房产' && selectedModule === '拍卖公告'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                : 'text-[#94a3b8] hover:text-[#f1f5f9]'
            }`}
            title="一键筛选刚上拍的一拍（公示期30天）与二拍（公示期15天）法拍房源"
          >
            <span>🏠 刚上拍房源</span>
          </button>

          {/* 当开启涉豫且在今日时，明确提示涉豫与全网的关系，消除数字割裂 */}
          {henanOnly && timeRange === 'today' && stats?.today_notices_count > 0 && (
            <button
              onClick={() => { setHenanOnly(false); setPage(1); }}
              className="hidden xl:flex items-center space-x-1 text-[11px] text-amber-300/90 ml-1.5 px-2 py-0.5 rounded bg-amber-950/30 border border-amber-500/30 hover:bg-amber-900/30 transition-colors"
              title="当前列表已筛选涉豫标的。全网今日共有标的，点击此标签可快速切换至全国全域查看所有标的"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              <span>已筛涉豫 {tabCounts.total} 条</span>
              <span className="text-[10px] text-[#94a3b8]">(全网 {stats.today_notices_count} 条 · 点击看全网)</span>
            </button>
          )}
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

        {/* 右侧工具组 */}
        <div className="flex items-center space-x-2">
          {/* 排序下拉 */}
          <div className="flex items-center space-x-1.5 bg-[#161e31] px-2.5 py-1 rounded-md border border-[#1e2638] text-xs">
            <ArrowUpDown className="w-3 h-3 text-amber-400 shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
              className="bg-transparent text-[#cbd5e1] text-xs focus:outline-none cursor-pointer"
            >
              <option value="publish_time_desc" className="bg-[#111726]">最新发布时间</option>
              <option value="bidding_start_asc" className="bg-[#111726]">⏰ 即将开拍/截标</option>
              <option value="discount_asc" className="bg-[#111726]">🔥 捡漏折扣 (低到高)</option>
              <option value="price_asc" className="bg-[#111726]">起拍价格 (低到高)</option>
              <option value="price_desc" className="bg-[#111726]">起拍价格 (高到低)</option>
            </select>
          </div>

          {/* 涉豫切换 */}
          <button
            onClick={() => { setHenanOnly(!henanOnly); setSelectedCity(''); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors border ${
              henanOnly
                ? 'bg-amber-950/40 text-amber-300 border-amber-800/60 font-semibold'
                : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9]'
            }`}
            title={henanOnly ? "当前仅筛选河南属地与涉豫标的，点击可切换为全国全域视角" : "当前为全国全域大盘，点击开启河南属地专注筛选"}
          >
            {henanOnly ? '涉豫资产' : '全国全域'}
          </button>

          {/* 筛选抽屉开关 */}
          <button
            onClick={() => setFilterDrawerOpen(!filterDrawerOpen)}
            className={`flex items-center space-x-1 px-2.5 py-1 text-xs rounded-md font-medium transition-colors border ${
              filterDrawerOpen || platform || selectedCity || court || priceMin || priceMax || discountMax
                ? 'bg-[#182238] text-[#60a5fa] border-blue-500/40'
                : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9]'
            }`}
          >
            <Filter className="w-3 h-3" />
            <span>高级筛选</span>
            {(platform || selectedCity || court || priceMin || priceMax || discountMax || assetCategory) && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            )}
            <ChevronDown className={`w-3 h-3 transition-transform ${filterDrawerOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* 导出 CSV */}
          <button
            onClick={handleExportCsv}
            className="flex items-center space-x-1 px-2.5 py-1 text-xs rounded-md font-medium text-[#94a3b8] hover:text-[#f1f5f9] bg-[#161e31] border border-[#1e2638] hover:bg-[#182238] transition-colors"
            title="导出当前筛选结果为 CSV 报表"
          >
            <Download className="w-3 h-3" />
            <span className="hidden sm:inline">导出CSV</span>
          </button>

          {/* 视图模式切换 (卡片流 / 密集表格) */}
          <div className="flex items-center rounded-md bg-[#161e31] border border-[#1e2638] p-0.5 ml-1">
            <button
              onClick={() => { setViewMode('card'); localStorage.setItem('radar_view_mode', 'card'); }}
              className={`flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors ${
                viewMode === 'card'
                  ? 'bg-[#182238] text-amber-300 font-semibold shadow-xs'
                  : 'text-[#64748b] hover:text-[#94a3b8]'
              }`}
              title="切换为卡片流视图"
            >
              <LayoutList className="w-3.5 h-3.5" />
              <span className="hidden lg:inline text-[11px]">卡片流</span>
            </button>
            <button
              onClick={() => { setViewMode('table'); localStorage.setItem('radar_view_mode', 'table'); }}
              className={`flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors ${
                viewMode === 'table'
                  ? 'bg-[#182238] text-amber-300 font-semibold shadow-xs'
                  : 'text-[#64748b] hover:text-[#94a3b8]'
              }`}
              title="切换为高密度大屏表格视图"
            >
              <TableProperties className="w-3.5 h-3.5" />
              <span className="hidden lg:inline text-[11px]">密集表格</span>
            </button>
          </div>
        </div>
      </div>

      {/* 7 大信息源渠道专属全景切换栏 */}
      <div className="px-4 py-2 border-b border-[#1e2638] bg-[#0e1424] flex items-center justify-between gap-2 overflow-x-auto no-scrollbar shrink-0 text-xs">
        <div className="flex items-center space-x-1.5 shrink-0">
          <span className="text-[#64748b] text-[11px] font-semibold shrink-0 mr-1">
            7大数据源:
          </span>
          {[
            { id: '', label: '全部平台', count: platformCounts.total ?? (tabCounts.total ?? total) },
            { id: 'rmfysszc', label: '诉讼资产网', count: platformCounts.rmfysszc ?? 0 },
            { id: 'ali', label: '阿里法拍', count: platformCounts.ali ?? 0 },
            { id: 'jd', label: '京东拍卖', count: platformCounts.jd ?? 0 },
            { id: 'rmfyb', label: '人民法院报', count: platformCounts.rmfyb ?? 0 },
            { id: 'local_paper', label: '地方报纸', count: platformCounts.local_paper ?? 0 },
            { id: 'ggzy', label: '公共资源交易', count: platformCounts.ggzy ?? 0 },
            { id: 'caa', label: '中拍平台', count: platformCounts.caa ?? 0 },
          ].map(p => {
            const isActive = platform === p.id;
            return (
              <button
                key={p.id}
                onClick={() => { setPlatform(p.id); setPage(1); }}
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

        {/* 当某个平台在当前时间段无公示但在其他时间段有时提供一键快捷提示 */}
        {platform && (platformCounts[platform] === 0 || total === 0) && stats?.platform_counts?.[platform] > 0 && timeRange !== 'all' && (
          <button
            onClick={() => { setTimeRange('all'); setPage(1); }}
            className="flex items-center space-x-1 px-2.5 py-1 text-[11px] rounded bg-amber-950/40 text-amber-300 border border-amber-500/40 hover:bg-amber-900/40 transition-colors shrink-0"
            title={`该渠道在当前时间段暂无新标的，全库累计共有 ${stats.platform_counts[platform]} 条。点击切换为全部时间`}
          >
            <span>当前为0 · 全库累计 {stats.platform_counts[platform]} 条 (点击查看)</span>
          </button>
        )}
      </div>

      {/* 高级过滤抽屉面板 */}
      {filterDrawerOpen && (
        <div className="px-5 py-3.5 border-b border-[#1e2638] bg-[#0e1320] space-y-3 shrink-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 text-xs">
            {/* 平台下拉 */}
            <div>
              <label className="block text-[11px] font-semibold text-[#64748b] mb-1">渠道来源</label>
              <select
                value={platform}
                onChange={(e) => { setPlatform(e.target.value); setPage(1); }}
                className="w-full p-1.5 rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] text-xs focus:outline-none focus:border-amber-400/50"
              >
                {PLATFORMS.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            {/* 标的类别 (大宗资产) */}
            <div>
              <label className="block text-[11px] font-semibold text-[#64748b] mb-1">标的类别</label>
              <select
                value={assetCategory}
                onChange={(e) => { setAssetCategory(e.target.value); setPage(1); }}
                className="w-full p-1.5 rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] text-xs focus:outline-none focus:border-amber-400/50"
              >
                <option value="">全部标的资产</option>
                <option value="住宅/商业房产">🏠 住宅/商业房产</option>
                <option value="金融债权与股权">📑 金融债权与股权</option>
                <option value="工业厂房与土地">🏭 工业厂房与土地</option>
                <option value="其他资产">📦 其他资产</option>
              </select>
            </div>

            {/* 法院输入 */}
            <div>
              <label className="block text-[11px] font-semibold text-[#64748b] mb-1">法院/处置主体</label>
              <input
                type="text"
                value={court}
                onChange={(e) => setCourt(e.target.value)}
                onBlur={() => setPage(1)}
                placeholder="例如：郑州市中级人民法院"
                className="w-full p-1.5 rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] text-xs focus:outline-none focus:border-amber-400/50"
              />
            </div>

            {/* 起拍价区间 */}
            <div className="sm:col-span-2">
              <label className="block text-[11px] font-semibold text-[#64748b] mb-1">起拍价区间 (元)</label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  placeholder="最低价格"
                  value={priceMin}
                  onChange={(e) => setPriceMin(e.target.value)}
                  className="w-full p-1.5 rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] text-xs tabular-nums focus:outline-none focus:border-amber-400/50"
                />
                <span className="text-[#64748b]">-</span>
                <input
                  type="number"
                  placeholder="最高价格"
                  value={priceMax}
                  onChange={(e) => setPriceMax(e.target.value)}
                  className="w-full p-1.5 rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] text-xs tabular-nums focus:outline-none focus:border-amber-400/50"
                />
                <button
                  onClick={() => { setPage(1); loadData(); }}
                  className="px-3 py-1.5 rounded-md bg-[#182238] text-amber-300 border border-amber-500/40 font-medium hover:bg-[#1d2a45] transition-colors shrink-0"
                >
                  确定
                </button>
              </div>
            </div>
          </div>

          {/* 涉豫地市细分 */}
          {henanOnly && (
            <div className="flex items-center space-x-1.5 text-xs flex-wrap gap-y-1.5 pt-2 border-t border-[#1e2638]">
              <span className="text-[#64748b] font-semibold shrink-0">涉豫地市:</span>
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

      {/* 激活条件 Chips 条 */}
      {(platform || selectedCity || court || priceMin || priceMax || !henanOnly || searchQuery) && (
        <div className="px-5 py-1.5 bg-[#0e1320] border-b border-[#1e2638] flex items-center space-x-2 text-xs shrink-0 flex-wrap gap-y-1">
          <span className="text-[#64748b] text-[11px]">当前搜索与过滤:</span>
          {searchQuery && (
            <span className="px-1.5 py-0.2 rounded bg-[#182238] text-amber-300 border border-amber-500/30 flex items-center space-x-1 text-[11px]">
              <span>关键词: "{searchQuery}"</span>
              <button onClick={() => { setSearchQuery(''); setPage(1); }}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {!henanOnly && (
            <span className="px-1.5 py-0.2 rounded bg-[#161e31] text-[#cbd5e1] border border-[#1e2638] flex items-center space-x-1 text-[11px]">
              <span>全国全域</span>
              <button onClick={() => { setHenanOnly(true); setPage(1); }}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {platform && (
            <span className="px-1.5 py-0.2 rounded bg-[#182238] text-amber-300 border border-amber-500/30 flex items-center space-x-1 text-[11px]">
              <span>平台: {PLATFORMS.find(p => p.value === platform)?.label}</span>
              <button onClick={() => { setPlatform(''); setPage(1); }}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {selectedCity && (
            <span className="px-1.5 py-0.2 rounded bg-amber-950/40 text-amber-300 border border-amber-800/40 flex items-center space-x-1 text-[11px]">
              <span>地市: {selectedCity}</span>
              <button onClick={() => { setSelectedCity(''); setPage(1); }}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          {court && (
            <span className="px-1.5 py-0.2 rounded bg-[#161e31] text-[#cbd5e1] border border-[#1e2638] flex items-center space-x-1 text-[11px]">
              <span>法院: {court}</span>
              <button onClick={() => { setCourt(''); setPage(1); }}><X className="w-3 h-3 hover:text-rose-400" /></button>
            </span>
          )}
          <button 
            onClick={() => { setPlatform(''); setSelectedCity(''); setCourt(''); setPriceMin(''); setPriceMax(''); setHenanOnly(true); setSearchQuery(''); setPage(1); }}
            className="text-[11px] text-[#60a5fa] hover:underline ml-2"
          >
            重置全部
          </button>
        </div>
      )}

      {/* 双栏区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧列表 */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#111726]">
          <div ref={listContainerRef} className="flex-1 overflow-y-auto divide-y divide-[#1e2638] scroll-smooth">
            {loading ? (
              <div className="py-20 flex flex-col items-center justify-center text-[#64748b] text-xs space-y-2">
                <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                <span>检索全量司法与法拍数据中...</span>
              </div>
            ) : notices.length === 0 ? (
              <div className="py-20 flex flex-col items-center justify-center text-[#64748b] text-xs space-y-3">
                <Layers className="w-8 h-8 text-[#334155]" />
                <p>未找到符合条件的公示或法拍标的</p>
                <p className="text-[11px] text-[#475569]">
                  请尝试清空筛选条件或调整检索关键词。
                </p>
              </div>
            ) : viewMode === 'table' ? (
              <NoticeTableView
                notices={notices}
                selectedNotice={selectedNotice}
                onSelectNotice={(item) => setSelectedNotice(item)}
                onToggleStar={(id, nextState) => handleStarChange(id, nextState, true)}
                onCopyBriefing={handleCopyBriefingDirect}
              />
            ) : (
              notices.map(item => (
                <NoticeItemRow
                  key={item.id}
                  item={item}
                  isSelected={selectedNotice?.id === item.id}
                  isUnread={false}
                  onClick={() => setSelectedNotice(item)}
                  onToggleStar={(id, nextState) => handleStarChange(id, nextState, true)}
                />
              ))
            )}
          </div>

          {/* 翻页器与极速快捷键提示 */}
          {notices.length > 0 && (
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
                {discountMax && (
                  <span className="text-amber-300 text-[10px] font-medium">🔥 捡漏模式 (≤{discountMax}折)</span>
                )}
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

        {/* 右侧详情面板 */}
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
