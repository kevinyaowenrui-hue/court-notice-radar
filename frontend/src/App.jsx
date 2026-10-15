import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import AlertCenter from './components/AlertCenter';
import NoticeExplorer from './components/NoticeExplorer';
import StarredView from './components/StarredView';
import RulesManager from './components/RulesManager';
import SourcesView from './components/SourcesView';
import WebhookModal from './components/WebhookModal';
import { fetchStats } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('alerts');
  const [stats, setStats] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [webhookModalOpen, setWebhookModalOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Global search state
  const [globalSearch, setGlobalSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');

  const prevUnreadRef = useRef(null);

  const requestNotificationPermission = async () => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      const perm = await Notification.requestPermission();
      if (perm === 'granted') {
        new Notification('CourtNoticeRadar', {
          body: '桌面预警通知已成功启用！'
        });
      }
    }
  };

  const loadStats = async () => {
    try {
      const data = await fetchStats();
      if (prevUnreadRef.current !== null && data.unread_alerts > prevUnreadRef.current) {
        const diff = data.unread_alerts - prevUnreadRef.current;
        if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
          new Notification('CourtNoticeRadar 新预警提醒', {
            body: `雷达捕获到 ${diff} 条新增涉豫或法拍预警，请及时查阅！`
          });
        }
      }
      prevUnreadRef.current = data.unread_alerts;
      setStats(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadStats();
    // 轮询未读预警（页面隐藏时暂停轮询，杜绝无谓锁竞争）
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        return;
      }
      loadStats();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    setRefreshTrigger(Date.now());
    await loadStats();
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const handleGlobalSearchSubmit = () => {
    if (globalSearch.trim()) {
      setSubmittedSearch(globalSearch.trim());
      setActiveTab('notices');
    }
  };

  return (
    <div className="h-screen w-screen flex flex-row overflow-hidden bg-[#0b0f19] text-[#f1f5f9] font-sans selection:bg-amber-500/30 selection:text-amber-200">
      {/* 极简左侧导航栏 */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unreadCount={stats?.unread_alerts || 0}
        todayAlertsCount={stats?.today_alerts_count || 0}
        starredCount={stats?.starred_count || 0}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        onOpenWebhookModal={() => setWebhookModalOpen(true)}
      />

      {/* 右侧主工作区容器 */}
      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden bg-[#0b0f19]">
        {/* 顶部全局控制条 */}
        <Header
          searchQuery={globalSearch}
          setSearchQuery={setGlobalSearch}
          onSearchSubmit={handleGlobalSearchSubmit}
          onRefresh={handleManualRefresh}
          isRefreshing={isRefreshing}
          onRequestNotification={requestNotificationPermission}
          onOpenWebhookModal={() => setWebhookModalOpen(true)}
          stats={stats}
        />

        {/* 主视图内容区域 */}
        <main className="flex-1 flex overflow-hidden bg-[#0b0f19]">
          {activeTab === 'alerts' && (
            <AlertCenter 
              stats={stats} 
              refreshTrigger={refreshTrigger}
              onAlertCountChange={() => { loadStats(); setRefreshTrigger(Date.now()); }} 
            />
          )}

          {activeTab === 'notices' && (
            <NoticeExplorer 
              stats={stats}
              externalSearchQuery={submittedSearch} 
              refreshTrigger={refreshTrigger}
              onStarToggled={() => { loadStats(); setRefreshTrigger(Date.now()); }} 
            />
          )}

          {activeTab === 'starred' && (
            <StarredView onStarToggled={() => { loadStats(); setRefreshTrigger(Date.now()); }} />
          )}

          {activeTab === 'rules' && (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#0b0f19]">
              <div className="max-w-6xl mx-auto">
                <RulesManager />
              </div>
            </div>
          )}

          {activeTab === 'sources' && (
            <SourcesView onTriggerCompleted={() => { loadStats(); setRefreshTrigger(Date.now()); }} />
          )}
        </main>
      </div>

      {/* 全局 Webhook 配置弹窗 */}
      <WebhookModal
        isOpen={webhookModalOpen}
        onClose={() => setWebhookModalOpen(false)}
      />
    </div>
  );
}
