import React from 'react';
import { 
  Inbox, 
  Search, 
  Star, 
  SlidersHorizontal, 
  Database, 
  Send, 
  PanelLeftClose, 
  PanelLeftOpen,
  CheckCircle2,
  Scale
} from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  unreadCount = 0, 
  starredCount = 0,
  todayAlertsCount = 0,
  isCollapsed, 
  setIsCollapsed,
  onOpenWebhookModal
}) {
  const mainNav = [
    { 
      id: 'alerts', 
      label: '工作台', 
      icon: Inbox, 
      badge: unreadCount,
      badgeText: `未读 ${unreadCount}`,
      tooltip: `全库累计未读预警 ${unreadCount} 条（今日最新预警 ${todayAlertsCount} 条）`
    },
    { id: 'notices', label: '全部公示', icon: Search, tooltip: '全网司法公示与拍卖检索' },
    { 
      id: 'starred', 
      label: '我的关注', 
      icon: Star, 
      badge: starredCount,
      badgeText: `${starredCount}`,
      tooltip: `已星标收藏关注标的 ${starredCount} 条`
    },
  ];

  const settingsNav = [
    { id: 'rules', label: '监控规则', icon: SlidersHorizontal },
    { id: 'sources', label: '数据源调度', icon: Database },
    { id: 'webhook', label: '机器人推送', icon: Send, action: onOpenWebhookModal },
  ];

  return (
    <aside className={`shrink-0 bg-[#0e1320] border-r border-[#1e2638] flex flex-col justify-between transition-all duration-200 select-none ${
      isCollapsed ? 'w-[64px]' : 'w-[220px]'
    }`}>
      {/* 顶部 Logo & 折叠切换 */}
      <div>
        <div className="h-14 px-3.5 border-b border-[#1e2638] flex items-center justify-between">
          {!isCollapsed ? (
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-500/20 to-blue-500/20 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0 shadow-inner">
                <Scale className="w-4 h-4" />
              </div>
              <div className="leading-none truncate">
                <span className="font-bold text-sm tracking-tight text-[#f1f5f9]">
                  法拍雷达
                </span>
                <span className="block text-[10px] text-[#64748b] mt-0.5 font-mono">COURT RADAR</span>
              </div>
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-500/20 to-blue-500/20 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0 shadow-inner">
                <Scale className="w-4 h-4" />
              </div>
            </div>
          )}

          {!isCollapsed && (
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1 rounded text-[#64748b] hover:text-[#94a3b8] hover:bg-[#161e31] transition-colors"
              title="折叠侧边栏"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* 导航菜单列表 */}
        <div className="p-2 space-y-5">
          {/* 核心工作区 */}
          <div>
            {!isCollapsed && (
              <div className="px-2.5 mb-1.5 text-[10px] font-semibold text-[#64748b] uppercase tracking-wider">
                工作台
              </div>
            )}
            <nav className="space-y-0.5">
              {mainNav.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center rounded-md text-xs font-medium transition-all ${
                      isCollapsed ? 'justify-center p-2.5' : 'px-2.5 py-2 space-x-2.5'
                    } ${
                      isActive
                        ? 'bg-[#182238] text-[#60a5fa] font-semibold border-l-2 border-amber-400 shadow-sm'
                        : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#161e31]'
                    }`}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-amber-400' : 'text-[#64748b]'}`} />
                    {!isCollapsed && <span className="flex-1 text-left truncate">{item.label}</span>}
                    {!isCollapsed && item.badge > 0 && (
                      <span 
                        className="px-1.5 py-0.2 text-[10px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 shrink-0 tabular-nums"
                        title={item.tooltip || `${item.label} ${item.badge}`}
                      >
                        {item.badgeText || item.badge}
                      </span>
                    )}
                    {isCollapsed && item.badge > 0 && (
                      <span 
                        className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400" 
                        title={item.tooltip || `${item.label} ${item.badge}`}
                      />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* 设置与数据区 */}
          <div>
            {!isCollapsed && (
              <div className="px-2.5 mb-1.5 text-[10px] font-semibold text-[#64748b] uppercase tracking-wider">
                设置与管理
              </div>
            )}
            <nav className="space-y-0.5">
              {settingsNav.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      if (item.action) {
                        item.action();
                      } else {
                        setActiveTab(item.id);
                      }
                    }}
                    className={`w-full flex items-center rounded-md text-xs font-medium transition-all ${
                      isCollapsed ? 'justify-center p-2.5' : 'px-2.5 py-2 space-x-2.5'
                    } ${
                      isActive
                        ? 'bg-[#182238] text-[#60a5fa] font-semibold border-l-2 border-amber-400'
                        : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#161e31]'
                    }`}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-amber-400' : 'text-[#64748b]'}`} />
                    {!isCollapsed && <span className="flex-1 text-left truncate">{item.label}</span>}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* 底部折叠状态展开按钮或数据源状态 */}
      <div className="p-2 border-t border-[#1e2638] bg-[#0b0f19]">
        {isCollapsed ? (
          <div className="flex flex-col items-center py-1 space-y-2">
            <button
              onClick={() => setIsCollapsed(false)}
              className="p-1 rounded text-[#64748b] hover:text-[#94a3b8] hover:bg-[#161e31]"
              title="展开侧边栏"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
            <span className="w-2 h-2 rounded-full bg-emerald-500" title="6个数据源在线同步中" />
          </div>
        ) : (
          <div 
            onClick={() => setActiveTab('sources')} 
            className="cursor-pointer p-1.5 rounded hover:bg-[#161e31] transition-colors flex items-center space-x-2 text-[11px] text-[#94a3b8]"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="truncate">6 核心数据源在线同步</span>
          </div>
        )}
      </div>
    </aside>
  );
}
