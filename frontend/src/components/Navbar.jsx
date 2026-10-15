import React, { useState, useEffect } from 'react';
import { Bell, Search, ShieldCheck, Newspaper, Activity, RefreshCw, BellRing, Send } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, unreadCount, onRefresh, isRefreshing, onRequestNotification, onOpenWebhookModal }) {
  const [notificationPerm, setNotificationPerm] = useState(
    typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default'
  );

  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      setNotificationPerm(Notification.permission);
    }
  }, []);

  const handleNotifyClick = async () => {
    if (onRequestNotification) {
      await onRequestNotification();
      if (typeof window !== 'undefined' && 'Notification' in window) {
        setNotificationPerm(Notification.permission);
      }
    }
  };
  const tabs = [
    { id: 'alerts', label: '预警中心', icon: Bell, badge: unreadCount },
    { id: 'notices', label: '公示与法拍检索', icon: Search },
    { id: 'rules', label: '监控规则管理', icon: ShieldCheck },
    { id: 'papers', label: '53BK 地方报纸库', icon: Newspaper },
    { id: 'tasks', label: '采集调度大屏', icon: Activity },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#0f172a] border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3 shrink-0">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-600 to-blue-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-black text-xl shrink-0">
              法
            </div>
            <div className="whitespace-nowrap">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base sm:text-lg text-slate-100 tracking-tight">CourtNoticeRadar</span>
                <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-amber-950/80 text-amber-300 border border-amber-600/60 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                  <span>河南专属雷达</span>
                </span>
              </div>
              <p className="text-[11px] text-slate-400">河南省内各级法院 · 阿里京东在拍涉豫资产 · 全国跨域涉豫公告监控</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2 shrink-0 overflow-x-auto py-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative whitespace-nowrap flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-colors shrink-0 ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40 shadow-sm'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                  {tab.badge > 0 && (
                    <span className="ml-1 px-1.5 py-0.2 text-[10px] font-bold bg-rose-500 text-white rounded-full animate-pulse">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Notification & Refresh Actions */}
          <div className="flex items-center space-x-2">
            <button
              onClick={onOpenWebhookModal}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-800 text-cyan-300 border border-slate-700 hover:bg-slate-700 transition-colors"
              title="配置企业微信/钉钉/飞书群机器人实时推送"
            >
              <Send className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden sm:inline">机器人推送</span>
            </button>

            <button
              onClick={handleNotifyClick}
              className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors border ${
                notificationPerm === 'granted'
                  ? 'bg-slate-800 text-emerald-400 border-slate-700 hover:bg-slate-700'
                  : 'bg-amber-950/60 text-amber-300 border-amber-700 hover:bg-amber-900/60'
              }`}
              title={notificationPerm === 'granted' ? '桌面预警提醒已开启' : '点击启用桌面预警推送'}
            >
              <BellRing className={`w-3.5 h-3.5 ${notificationPerm === 'granted' ? 'text-emerald-400' : 'text-amber-400'}`} />
              <span className="hidden sm:inline">
                {notificationPerm === 'granted' ? '推送已开' : '开启推送'}
              </span>
            </button>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition-colors border border-slate-700"
              title="刷新全部数据"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-400' : ''}`} />
              <span>{isRefreshing ? '同步中' : '刷新'}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
