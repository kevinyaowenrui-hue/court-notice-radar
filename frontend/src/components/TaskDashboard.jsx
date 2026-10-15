import React, { useState, useEffect } from 'react';
import { Activity, Play, CheckCircle2, AlertTriangle, Clock, RefreshCw, Zap, Trash2 } from 'lucide-react';
import { fetchTaskLogs, runCrawlTask, runAllCrawlTasks, cleanHistoricalData } from '../api';

const PIPELINES = [
  {
    id: 'rmfysszc',
    title: '人民法院诉讼资产网采集器',
    desc: '来源: https://www.rmfysszc.gov.cn 最高法指定平台，专注刚上拍一拍（公示期30天）与二拍（公示期15天）房产黄金期捕获',
    interval: '每 30 分钟',
    badge: '最高法法拍源',
    color: 'emerald'
  },
  {
    id: 'rmfyb',
    title: '《人民法院报》公告网采集器',
    desc: '全国法院统一开庭传票、送达裁判文书、执行公告与破产重整',
    interval: '每 30 分钟',
    badge: '官方统一源',
    color: 'indigo'
  },
  {
    id: 'jd',
    title: '京东司法拍卖高频采集器',
    desc: '监控京东司法拍卖住宅商用房、土地厂房及金融债权股权',
    interval: '每 30 分钟',
    badge: '资产法拍',
    color: 'rose'
  },
  {
    id: 'ali',
    title: '阿里资产·司法拍卖混合引擎',
    desc: 'Playwright Stealth 无头指纹伪装 + 轻量 API 降级采集',
    interval: '每 45 分钟',
    badge: '反爬加固',
    color: 'amber'
  },
  {
    id: 'local_paper',
    title: '53BK 地方报纸专版智能巡检器',
    desc: '自动轮询已监控的各省市日报/晚报第 3/4 版公告与声明专版',
    interval: '每 2 小时',
    badge: '地方下沉',
    color: 'emerald'
  },
  {
    id: 'caa',
    title: '中拍平台·信息公示采集器',
    desc: '中国拍卖行业协会官方公示、涉案财物处置结果与拍卖成交公告',
    interval: '每 30 分钟',
    badge: '行业国家级平台',
    color: 'cyan'
  },
  {
    id: 'ggzy',
    title: '公共资源交易·全省产权与债权转让采集器',
    desc: '深度接入商丘及河南省全域公共资源交易平台国有产权交易与金融债权转让大盘',
    interval: '每 30 分钟',
    badge: '产权与债权',
    color: 'amber'
  }
];

export default function TaskDashboard({ onTriggerCompleted }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runningPlatforms, setRunningPlatforms] = useState({});
  const [syncingAll, setSyncingAll] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await fetchTaskLogs();
      if (Array.isArray(data)) {
        setLogs(data);
      } else {
        setLogs(data.logs || []);
        if (data.running_platforms) {
          const rpMap = {};
          data.running_platforms.forEach(p => { rpMap[p] = true; });
          setRunningPlatforms(rpMap);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const handleRunNow = async (platform) => {
    setRunningPlatforms(prev => ({ ...prev, [platform]: true }));
    try {
      await runCrawlTask(platform);
      await loadLogs();
      if (onTriggerCompleted) onTriggerCompleted();
    } catch (err) {
      console.error(err);
    } finally {
      setRunningPlatforms(prev => ({ ...prev, [platform]: false }));
    }
  };

  const handleRunAllNow = async () => {
    setSyncingAll(true);
    setSyncMsg('已启动全网 7 大渠道受控并发采集...');
    try {
      const res = await runAllCrawlTasks();
      setSyncMsg(res.message || '全部 7 大数据源已启动后台并发采集');
      // 动态根据 running_platforms 轮询，移除硬编码 24 秒截断
      let pollCount = 0;
      const timer = setInterval(async () => {
        pollCount += 1;
        try {
          const data = await fetchTaskLogs();
          const logsList = Array.isArray(data) ? data : (data.logs || []);
          const activeList = Array.isArray(data) ? [] : (data.running_platforms || []);
          setLogs(logsList);
          const rpMap = {};
          activeList.forEach(p => { rpMap[p] = true; });
          setRunningPlatforms(rpMap);

          if (onTriggerCompleted) onTriggerCompleted();

          // 至少轮询 2 次确认任务已调度；之后若当前运行渠道为空，代表全部渠道采集完成
          if (pollCount >= 2 && activeList.length === 0) {
            clearInterval(timer);
            setSyncingAll(false);
            setSyncMsg('全网 7 大渠道采集与预警匹配已全部完成！');
            setTimeout(() => setSyncMsg(''), 4000);
          }
          // 最大超时保底 (180秒 = 60次)
          if (pollCount > 60) {
            clearInterval(timer);
            setSyncingAll(false);
            setSyncMsg('');
          }
        } catch (pollErr) {
          console.error(pollErr);
        }
      }, 3000);
    } catch (err) {
      console.error(err);
      setSyncMsg('启动失败，请检查服务状态');
      setSyncingAll(false);
    }
  };

  const [cleaning, setCleaning] = useState(false);
  const handleCleanHistorical = async () => {
    if (!window.confirm('确认清理 7 天前的陈旧历史数据吗？这将彻底释放库容，保留近 7 天与今日最新数据（已关注标的会保留）。')) return;
    setCleaning(true);
    try {
      const res = await cleanHistoricalData(7);
      alert(res.message || '清理完成！');
      if (onTriggerCompleted) onTriggerCompleted();
    } catch (err) {
      alert('清理失败: ' + err.message);
    } finally {
      setCleaning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-[#0e1424] p-4 rounded-xl border border-[#1e2638]">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
            <Activity className="w-4 h-4 text-amber-400" />
            <span>采集管道与调度监控中心</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            系统默认后台全自动定时轮询抓取（无需手动点）。若需立即同步，可点击右侧按钮一键提取全部数据源。
          </p>
        </div>
        <div className="flex items-center space-x-2 shrink-0">
          {syncMsg && (
            <span className="text-xs text-amber-300 bg-amber-950/40 border border-amber-800/60 px-2.5 py-1 rounded">
              {syncMsg}
            </span>
          )}
          <button
            onClick={handleRunAllNow}
            disabled={syncingAll}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold shadow-sm transition-all border ${
              syncingAll
                ? 'bg-amber-950/50 text-amber-300 border-amber-800/60 cursor-not-allowed'
                : 'bg-amber-500 hover:bg-amber-400 text-slate-950 border-amber-400 font-bold active:scale-95'
            }`}
            title="一键同时唤醒人民法院报、京东、阿里、地方报、中拍平台、公共资源 6 大渠道后台并发采集"
          >
            <Zap className={`w-3.5 h-3.5 ${syncingAll ? 'animate-bounce text-amber-300' : 'fill-slate-950'}`} />
            <span>{syncingAll ? '全网并发采集中...' : '⚡ 一键提取全部数据源'}</span>
          </button>
          <button
            onClick={handleCleanHistorical}
            disabled={cleaning}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-300 bg-[#161e31] hover:bg-rose-950/40 hover:text-rose-300 border border-[#1e2638] hover:border-rose-800/60 transition-colors"
            title="一键清理 7 天前发布的陈旧历史数据，保持库容极简与最新发布时效（已关注标的会保留）"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-400" />
            <span>{cleaning ? '清理中...' : '清理7天前旧数据'}</span>
          </button>
        </div>
      </div>

      {/* 6 Pipeline Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {PIPELINES.map((p) => {
          const isRunning = runningPlatforms[p.id];
          const latestLog = logs.find(l => l.platform === p.id);

          return (
            <div
              key={p.id}
              className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-950 text-blue-400 border border-blue-800">
                    {p.badge}
                  </span>
                  {latestLog?.status === 'failed' ? (
                    <div className="flex items-center space-x-1.5 text-xs text-rose-400 font-semibold" title={latestLog?.error_msg || '任务执行异常'}>
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
                      <span>异常告警</span>
                    </div>
                  ) : latestLog?.status === 'warning' ? (
                    <div className="flex items-center space-x-1.5 text-xs text-amber-400 font-semibold">
                      <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                      <span>注意</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-semibold">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                      <span>运行正常</span>
                    </div>
                  )}
                </div>

                <h3 className="font-bold text-slate-100 text-sm mt-3">{p.title}</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{p.desc}</p>

                <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span>轮询周期:</span>
                    <span className="text-slate-200 font-medium">{p.interval}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>最近执行:</span>
                    <span className="text-slate-200">{latestLog?.created_at || '待执行'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>上次新增:</span>
                    <span className="text-emerald-400 font-bold">{latestLog?.new_items || 0} 条新数据</span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800">
                <button
                  onClick={() => handleRunNow(p.id)}
                  disabled={isRunning}
                  className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-xs font-semibold text-white transition-colors"
                >
                  {isRunning ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>正在抓取中...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>立即执行抓取</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Task Execution Log Table */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-slate-400" />
            <h3 className="font-bold text-slate-100 text-xs">最近任务执行流水日志</h3>
          </div>
          <button
            onClick={loadLogs}
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white"
          >
            <RefreshCw className="w-3 h-3" />
            <span>刷新日志</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4 font-semibold">任务名称</th>
                <th className="py-3 px-4 font-semibold">渠道平台</th>
                <th className="py-3 px-4 font-semibold">执行状态</th>
                <th className="py-3 px-4 font-semibold">发现条数</th>
                <th className="py-3 px-4 font-semibold">增量入库</th>
                <th className="py-3 px-4 font-semibold">耗时</th>
                <th className="py-3 px-4 font-semibold">触发时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-400">加载日志中...</td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-400">暂无日志记录</td>
                </tr>
              ) : (
                logs.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-200">{l.task_name}</td>
                    <td className="py-3 px-4 uppercase text-slate-400 font-mono text-[11px]">{l.platform}</td>
                    <td className="py-3 px-4">
                      {l.status === 'success' ? (
                        <span className="flex items-center space-x-1 text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>成功</span>
                        </span>
                      ) : l.status === 'warning' ? (
                        <span className="flex items-center space-x-1 text-amber-400 font-semibold cursor-help" title={l.error_msg || '巡检发现0条或存在反爬拦截'}>
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>注意</span>
                        </span>
                      ) : (
                        <span className="flex items-center space-x-1 text-rose-400 font-semibold cursor-help" title={l.error_msg || '任务执行失败'}>
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>失败</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{l.items_found}</td>
                    <td className="py-3 px-4 font-bold text-emerald-400">+{l.new_items}</td>
                    <td className="py-3 px-4 text-slate-400">{l.duration_ms} ms</td>
                    <td className="py-3 px-4 text-slate-400">{l.created_at}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
