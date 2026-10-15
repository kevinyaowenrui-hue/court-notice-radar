import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

export default function Pagination({ 
  page, 
  currentPage, 
  totalPages = 1, 
  total, 
  totalItems, 
  pageSize = 20, 
  onPageChange, 
  onPageSizeChange 
}) {
  const currentP = page || currentPage || 1;
  const count = total != null ? total : (totalItems != null ? totalItems : 0);
  const totalP = Math.max(1, totalPages || Math.ceil(count / pageSize) || 1);

  if (count <= 0) return null;

  // 生成智能页码序列
  const getPageNumbers = () => {
    if (totalP <= 7) {
      return Array.from({ length: totalP }, (_, i) => i + 1);
    }
    if (currentP <= 4) {
      return [1, 2, 3, 4, 5, '...', totalP];
    }
    if (currentP >= totalP - 3) {
      return [1, '...', totalP - 4, totalP - 3, totalP - 2, totalP - 1, totalP];
    }
    return [1, '...', currentP - 1, currentP, currentP + 1, '...', totalP];
  };

  const pages = getPageNumbers();

  const handlePageClick = (p) => {
    if (typeof p !== 'number') return;
    if (p < 1 || p > totalP || p === currentP) return;
    if (onPageChange) {
      onPageChange(p);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-2.5 bg-[#111726] border-t border-[#1e2638] text-xs text-[#94a3b8] shrink-0 select-none">
      <div className="flex items-center space-x-2">
        <span>共 <strong className="text-[#f1f5f9] tabular-nums font-semibold">{count}</strong> 条标的</span>
        <span className="text-[#334155]">|</span>
        <span>第 <strong className="text-amber-400 tabular-nums font-bold">{currentP}</strong> / {totalP} 页</span>
      </div>

      <div className="flex items-center space-x-2 sm:space-x-3 flex-wrap">
        {onPageSizeChange && (
          <div className="flex items-center space-x-1.5 mr-1">
            <span className="text-[#64748b] text-[11px]">每页:</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="bg-[#161e31] border border-[#1e2638] rounded px-2 py-1 text-[#f1f5f9] text-xs focus:outline-none focus:border-amber-400/50 cursor-pointer"
            >
              <option value={20}>20 条</option>
              <option value={50}>50 条</option>
              <option value={100}>100 条</option>
            </select>
          </div>
        )}

        <div className="flex items-center space-x-1">
          {/* 首页 */}
          <button
            type="button"
            title="第一页"
            disabled={currentP <= 1}
            onClick={() => handlePageClick(1)}
            className="p-1 rounded bg-[#161e31] hover:bg-[#182238] text-[#cbd5e1] disabled:opacity-25 disabled:cursor-not-allowed border border-[#1e2638] transition-colors"
          >
            <ChevronsLeft className="w-3.5 h-3.5" />
          </button>

          {/* 上一页 */}
          <button
            type="button"
            disabled={currentP <= 1}
            onClick={() => handlePageClick(currentP - 1)}
            className="flex items-center space-x-1 px-2 py-1 rounded bg-[#161e31] hover:bg-[#182238] text-[#cbd5e1] disabled:opacity-25 disabled:cursor-not-allowed border border-[#1e2638] transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">上一页</span>
          </button>

          {/* 数字页码序列 */}
          <div className="flex items-center space-x-1 mx-1">
            {pages.map((p, idx) => {
              if (p === '...') {
                return (
                  <span key={`dots-${idx}`} className="px-1.5 py-0.5 text-[#64748b] font-mono text-xs">
                    ...
                  </span>
                );
              }
              const isActive = p === currentP;
              return (
                <button
                  key={p}
                  type="button"
                  onClick={() => handlePageClick(p)}
                  className={`min-w-[28px] h-7 px-1.5 rounded text-xs font-mono tabular-nums transition-all ${
                    isActive
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/50 font-bold shadow-xs'
                      : 'bg-[#161e31] text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#182238] border border-[#1e2638]'
                  }`}
                >
                  {p}
                </button>
              );
            })}
          </div>

          {/* 下一页 */}
          <button
            type="button"
            disabled={currentP >= totalP}
            onClick={() => handlePageClick(currentP + 1)}
            className="flex items-center space-x-1 px-2 py-1 rounded bg-[#161e31] hover:bg-[#182238] text-[#cbd5e1] disabled:opacity-25 disabled:cursor-not-allowed border border-[#1e2638] transition-colors"
          >
            <span className="hidden sm:inline">下一页</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>

          {/* 末页 */}
          <button
            type="button"
            title="最后一页"
            disabled={currentP >= totalP}
            onClick={() => handlePageClick(totalP)}
            className="p-1 rounded bg-[#161e31] hover:bg-[#182238] text-[#cbd5e1] disabled:opacity-25 disabled:cursor-not-allowed border border-[#1e2638] transition-colors"
          >
            <ChevronsRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
