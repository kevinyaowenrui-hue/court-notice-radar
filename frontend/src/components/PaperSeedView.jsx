import React, { useState, useEffect } from 'react';
import { Newspaper, ExternalLink, RefreshCw, CheckCircle, Search, Filter } from 'lucide-react';
import { fetchPapers, togglePaperMonitor, sync53bkPapers } from '../api';

export default function PaperSeedView() {
  const [papers, setPapers] = useState([]);
  const [provinces, setProvinces] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedProvince, setSelectedProvince] = useState('');
  const [monitoredOnly, setMonitoredOnly] = useState(false);
  const [query, setQuery] = useState('');
  const [syncing, setSyncing] = useState(false);

  const loadPapers = async () => {
    setLoading(true);
    try {
      const data = await fetchPapers({
        province: selectedProvince || undefined,
        monitoredOnly,
        query: query.trim() || undefined,
        limit: 100
      });
      setPapers(data.items || []);
      setTotal(data.total || 0);
      if (data.provinces) setProvinces(data.provinces);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPapers();
  }, [selectedProvince, monitoredOnly]);

  const handleToggle = async (paperId) => {
    try {
      const res = await togglePaperMonitor(paperId);
      setPapers(prev => prev.map(p => p.id === paperId ? { ...p, is_monitored: res.is_monitored } : p));
    } catch (err) {
      console.error(err);
    }
  };

  const handleSync53bk = async () => {
    setSyncing(true);
    try {
      await sync53bkPapers();
      alert('已触发 53BK 全国报纸目录同步，后台正在自动拉取中...');
      setTimeout(() => {
        loadPapers();
        setSyncing(false);
      }, 3000);
    } catch (err) {
      console.error(err);
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Intro Banner */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Newspaper className="w-5 h-5 text-emerald-400" />
              <h2 className="text-base font-bold text-slate-100">
                53BK 全国数字报纸入口种子库 (地方公示雷达)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              基于 <strong>www.53bk.com</strong> 全国报纸汇集导航系统深度抽取。
              已建立全国各省市主流《日报》《晚报》《法治报》的官方最新电子版入口字典。
              勾选“开启巡检”后，系统将在每日排程中定向嗅探该报纸的<strong>第 3/4 版公告与声明专版</strong>，高效捕获下沉基层案件。
            </p>
          </div>

          <button
            onClick={handleSync53bk}
            disabled={syncing}
            className="flex items-center justify-center space-x-1.5 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-xs font-semibold text-white transition-colors border border-emerald-600 whitespace-nowrap self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            <span>{syncing ? '同步中...' : '从 53BK 增量同步'}</span>
          </button>
        </div>
      </div>

      {/* Filter Row */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-3 flex-wrap gap-y-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="搜索报纸名称或城市..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadPapers()}
              className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 w-48 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center space-x-1.5">
            <span className="text-slate-400">省份:</span>
            <select
              value={selectedProvince}
              onChange={(e) => setSelectedProvince(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none"
            >
              <option value="">全部省份</option>
              {provinces.map((prov) => (
                <option key={prov} value={prov}>{prov}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setSelectedProvince(selectedProvince === '河南' ? '' : '河南')}
            className={`px-3 py-1.5 rounded-lg border font-semibold transition-colors ${
              selectedProvince === '河南'
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/60'
                : 'bg-slate-800/80 text-amber-400 border-amber-700/40 hover:bg-slate-700'
            }`}
          >
            🌟 河南全省电子报专区 (40家)
          </button>

          <button
            onClick={() => setMonitoredOnly(!monitoredOnly)}
            className={`px-3 py-1.5 rounded-lg border font-medium transition-colors ${
              monitoredOnly
                ? 'bg-emerald-950/60 text-emerald-400 border-emerald-700'
                : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
            }`}
          >
            仅看已开启巡检报刊
          </button>
        </div>

        <div className="text-slate-400">
          共收录 <strong className="text-slate-200 font-bold">{total}</strong> 份官方电子报纸入口
        </div>
      </div>

      {/* Paper Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5">
        {loading ? (
          <div className="col-span-full py-12 text-center text-slate-400 text-sm">
            加载报纸种子库中...
          </div>
        ) : papers.length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-400 bg-[#0f172a] border border-slate-800 rounded-xl">
            未匹配到对应的报纸信息
          </div>
        ) : (
          papers.map((p) => (
            <div
              key={p.id}
              className={`bg-[#0f172a] border rounded-xl p-4 flex flex-col justify-between transition-all ${
                p.is_monitored
                  ? 'border-emerald-500/40 shadow-sm'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between text-xs">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                    {p.province} · {p.city}
                  </span>
                  <button
                    onClick={() => handleToggle(p.id)}
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition-colors ${
                      p.is_monitored
                        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-600'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                    }`}
                  >
                    {p.is_monitored ? '已巡检' : '未开启'}
                  </button>
                </div>

                <h3 className="font-bold text-slate-100 text-sm mt-3 line-clamp-1" title={p.paper_name}>
                  {p.paper_name}
                </h3>

                <p className="text-[11px] text-slate-400 mt-1 truncate font-mono" title={p.epaper_url}>
                  {p.epaper_url}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span className="truncate">上次巡检: {p.last_scanned_at}</span>
                <a
                  href={p.epaper_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-1 text-blue-400 hover:text-blue-300 shrink-0 ml-1"
                  title="在新窗口打开数字报官网"
                >
                  <span>阅读</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
