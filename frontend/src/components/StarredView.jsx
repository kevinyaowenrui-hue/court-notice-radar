import React, { useState, useEffect, useRef } from 'react';
import { Star, Loader2 } from 'lucide-react';
import { fetchNotices, toggleNoticeStar } from '../api';
import { PRESET_NOTE_TAGS, getNoteTagBadgeStyle } from '../tagUtils';
import NoticeItemRow from './NoticeItemRow';
import NoticeDetailPane from './NoticeDetailPane';
import Pagination from './Pagination';

export default function StarredView({ onStarToggled }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedModule, setSelectedModule] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [selectedNotice, setSelectedNotice] = useState(null);
  const [loading, setLoading] = useState(true);

  // 列表滚动容器 Ref，确保翻页时正常平滑翻滚置顶
  const listContainerRef = useRef(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchNotices({
        starredOnly: true,
        moduleType: selectedModule || undefined,
        noteTag: selectedTag || undefined,
        page,
        pageSize
      });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || Math.ceil((data.total || 0) / pageSize) || 1);
      
      // 翻页或筛选后联动：自动查看新一页的第 1 条标的
      if (data.items && data.items.length > 0) {
        setSelectedNotice(data.items[0]);
      } else {
        setSelectedNotice(null);
      }

      // 列表平滑翻滚置顶
      if (listContainerRef.current) {
        listContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, pageSize, selectedModule, selectedTag]);

  const handlePageChange = (newPage) => {
    setPage(newPage);
    if (listContainerRef.current) {
      listContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleToggleStar = async (id, shouldCallApi = false) => {
    setItems(prev => prev.filter(it => it.id !== id));
    setTotal(prev => Math.max(0, prev - 1));
    if (selectedNotice?.id === id) {
      setSelectedNotice(null);
    }

    if (shouldCallApi) {
      try {
        await toggleNoticeStar(id);
      } catch (err) {
        console.error('Failed to unstar notice in StarredView:', err);
        loadData();
      }
    }

    if (onStarToggled) {
      onStarToggled();
    }
  };

  const handleNotesUpdated = (id, newNotes) => {
    setItems(prev => prev.map(it => it.id === id ? { ...it, user_notes: newNotes } : it));
    if (selectedNotice?.id === id) {
      setSelectedNotice(prev => ({ ...prev, user_notes: newNotes }));
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0b0f19]">
      {/* 顶部标题与分段控件 */}
      <div className="px-5 py-3 border-b border-[#1e2638] bg-[#111726] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center space-x-2">
          <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
          <h1 className="text-sm font-bold text-[#f1f5f9]">
            我的关注标的库
          </h1>
          <span className="text-xs text-[#94a3b8] tabular-nums">({total} 件关注)</span>
        </div>

        <div className="flex items-center space-x-2 flex-wrap gap-y-2">
          {/* 尽调处置阶段漏斗 */}
          <div className="flex items-center space-x-1 bg-[#161e31] p-0.5 rounded-md border border-[#1e2638] text-xs">
            <span className="text-[10px] text-[#64748b] px-1 font-medium">尽调漏斗:</span>
            {[
              { id: '', label: '全部' },
              ...PRESET_NOTE_TAGS.map(t => ({ id: t.label, label: t.label }))
            ].map(tag => (
              <button
                key={tag.id}
                onClick={() => { setSelectedTag(tag.id); setPage(1); }}
                className={`px-2 py-0.5 rounded text-[11px] transition-all font-medium ${
                  selectedTag === tag.id
                    ? (tag.id ? `${getNoteTagBadgeStyle(tag.id)} font-bold shadow-xs` : 'bg-[#182238] text-amber-300 border border-amber-500/40 font-semibold shadow-xs')
                    : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                }`}
              >
                {tag.label}
              </button>
            ))}
          </div>

          {/* 模块筛选分段胶囊 */}
          <div className="flex items-center space-x-1 bg-[#161e31] p-0.5 rounded-md border border-[#1e2638] text-xs">
            {[
              { id: '', label: '全部标的' },
              { id: '拍卖公告', label: '司法拍卖' },
              { id: '公告', label: '法院公告' },
              { id: '债权转让', label: '债权转让' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => { setSelectedModule(tab.id); setPage(1); }}
                className={`px-2.5 py-0.5 rounded text-[11px] transition-all font-medium ${
                  selectedModule === tab.id
                    ? 'bg-[#182238] text-amber-300 border border-amber-500/30 font-semibold shadow-xs'
                    : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 主双栏区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧列表 */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#111726]">
          <div ref={listContainerRef} className="flex-1 overflow-y-auto divide-y divide-[#1e2638] scroll-smooth">
            {loading ? (
              <div className="py-20 flex flex-col items-center justify-center text-[#64748b] text-xs space-y-2">
                <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                <span>加载关注标的中...</span>
              </div>
            ) : items.length === 0 ? (
              <div className="py-20 flex flex-col items-center justify-center text-[#64748b] text-xs space-y-3">
                <Star className="w-8 h-8 text-[#334155]" />
                <p>暂无星标关注的资产或公告</p>
                <p className="text-[11px] text-[#475569]">
                  可在「工作台」或「全部公示」中点击五角星收藏，在此集中跟进处置进展。
                </p>
              </div>
            ) : (
              items.map(item => (
                <NoticeItemRow
                  key={item.id}
                  item={item}
                  isSelected={selectedNotice?.id === item.id}
                  isUnread={false}
                  onClick={() => setSelectedNotice(item)}
                  onToggleStar={(id) => handleToggleStar(id, true)}
                />
              ))
            )}
          </div>

          {/* 翻页器 */}
          {items.length > 0 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              totalItems={total}
              pageSize={pageSize}
              onPageChange={handlePageChange}
              onPageSizeChange={(newSize) => { setPageSize(newSize); setPage(1); }}
            />
          )}
        </div>

        {/* 右侧详情面板 */}
        {selectedNotice && (
          <NoticeDetailPane
            notice={selectedNotice}
            onClose={() => setSelectedNotice(null)}
            onStarChange={(id, state) => {
              if (!state) handleToggleStar(id, false);
            }}
            onNotesUpdated={handleNotesUpdated}
            onSelectNotice={(item) => setSelectedNotice(item)}
          />
        )}
      </div>
    </div>
  );
}
