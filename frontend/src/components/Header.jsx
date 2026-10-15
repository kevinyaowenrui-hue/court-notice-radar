import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, BellRing, Send } from 'lucide-react';

export default function Header({ 
  searchQuery, 
  setSearchQuery, 
  onSearchSubmit,
  onRefresh, 
  isRefreshing, 
  onRequestNotification,
  onOpenWebhookModal,
  stats
}) {
  const [notificationPerm, setNotificationPerm] = useState(
    typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default'
  );

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const input = document.getElementById('global-search-input');
        if (input) input.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleNotifyClick = async () => {
    if (onRequestNotification) {
      await onRequestNotification();
      if (typeof window !== 'undefined' && 'Notification' in window) {
        setNotificationPerm(Notification.permission);
      }
    }
  };

  return (
    <header className="h-14 bg-[#111726] border-b border-[#1e2638] px-4 flex items-center justify-between shrink-0 select-none">
      {/* 全局搜索框与今日最新指标 */}
      <div className="flex-1 max-w-xl flex items-center space-x-3">
        <form onSubmit={(e) => { e.preventDefault(); if (onSearchSubmit) onSearchSubmit(); }} className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            id="global-search-input"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="检索案号、当事人、法院、资产标的 (Ctrl + K)..."
            className="w-full pl-9 pr-12 py-1.5 text-xs rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all"
          />
          <span className="hidden sm:inline-block absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono text-[#64748b] px-1 py-0.2 bg-[#0b0f19] rounded border border-[#1e2638]">
            ⌘K
          </span>
        </form>

        {stats?.today_notices_count > 0 && (
          <span 
            className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 text-[11px] font-semibold rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shrink-0 shadow-xs cursor-default" 
            title={`当日 0 点至今全渠道收录标的 ${stats.today_notices_count} 条（其中涉豫标的 ${stats.today_henan_notices_count ?? 0} 条，全国其他 ${stats.today_notices_count - (stats.today_henan_notices_count ?? 0)} 条）；命中监控预警 ${stats.today_alerts_count ?? 0} 条`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>今日涉豫 {stats.today_henan_notices_count ?? 0} 条</span>
            <span className="text-[10px] text-emerald-400/80 font-normal">(全网 {stats.today_notices_count})</span>
            {(stats.today_alerts_count ?? 0) > 0 && (
              <span className="text-[10px] text-amber-300 pl-1 border-l border-emerald-500/30">
                预警 {stats.today_alerts_count} 条
              </span>
            )}
          </span>
        )}
      </div>

      {/* 右侧操作按钮 */}
      <div className="flex items-center space-x-2 shrink-0 ml-4">
        {/* 机器人推送配置 */}
        <button
          onClick={onOpenWebhookModal}
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-xs font-medium text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#161e31] border border-[#1e2638] transition-colors"
          title="配置企业微信/钉钉/飞书群机器人实时推送"
        >
          <Send className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden md:inline">机器人推送</span>
        </button>

        {/* 桌面通知 */}
        <button
          onClick={handleNotifyClick}
          className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors border ${
            notificationPerm === 'granted'
              ? 'text-emerald-400 bg-emerald-950/30 border-emerald-800/40'
              : 'text-amber-400 bg-amber-950/30 border-amber-800/40 hover:bg-amber-900/40'
          }`}
          title={notificationPerm === 'granted' ? '桌面预警提醒已开启' : '点击授权启用桌面推送'}
        >
          <BellRing className="w-3.5 h-3.5" />
          <span className="hidden md:inline">
            {notificationPerm === 'granted' ? '推送已开' : '开启推送'}
          </span>
        </button>

        {/* 刷新数据 */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-1.5 rounded-md text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#161e31] border border-[#1e2638] transition-colors"
          title="刷新界面统计与最新预警（系统后台每30分钟自动轮询，亦可在数据源调度一键提取全网）"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-amber-400' : ''}`} />
        </button>
      </div>
    </header>
  );
}
