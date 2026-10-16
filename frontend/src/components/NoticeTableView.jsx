import React from 'react';
import { Star, ExternalLink, Share2, ShieldAlert } from 'lucide-react';
import { extractNoteTag, getNoteTagBadgeStyle, getRiskTagBadgeStyle, formatPublishTime } from '../tagUtils';

export default function NoticeTableView({
  notices = [],
  selectedNotice,
  onSelectNotice,
  onToggleStar,
  onCopyBriefing
}) {
  const getPlatformName = (platform) => {
    const map = {
      rmfysszc: '诉讼资产网',
      ali: '阿里法拍',
      jd: '京东拍卖',
      rmfyb: '法院报',
      local_paper: '地方报纸',
      caa: '中拍平台',
      ggzy: '公共资源'
    };
    return map[platform] || platform;
  };

  const getModuleBadge = (mod) => {
    switch (mod) {
      case '拍卖公告':
        return (
          <span className="px-1.5 py-0.5 text-[11px] font-semibold rounded bg-amber-950/40 text-amber-300 border border-amber-800/50">
            拍卖
          </span>
        );
      case '债权转让':
        return (
          <span className="px-1.5 py-0.5 text-[11px] font-semibold rounded bg-purple-950/40 text-purple-300 border border-purple-800/50">
            债权
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 text-[11px] font-semibold rounded bg-blue-950/40 text-blue-300 border border-blue-800/50">
            公告
          </span>
        );
    }
  };

  if (!notices || notices.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-16 text-center text-[#64748b]">
        <div className="text-3xl mb-2">📋</div>
        <div className="text-sm">暂无符合条件的公示标的数据</div>
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto min-h-full bg-[#111726]">
      <table className="w-full border-collapse text-left text-xs whitespace-nowrap">
        {/* 表头：高密度固定表头 */}
        <thead className="sticky top-0 z-10 bg-[#0e1320] border-b border-[#1e2638] text-[#94a3b8] font-semibold shadow-xs">
          <tr>
            <th className="py-2.5 px-3 w-10 text-center">关注</th>
            <th className="py-2.5 px-3 w-20 text-center">跟进状态</th>
            <th className="py-2.5 px-3 w-24">业务/阶段</th>
            <th className="py-2.5 px-3 min-w-[280px] max-w-[420px]">标的物与公示标题</th>
            <th className="py-2.5 px-3 w-36">案号</th>
            <th className="py-2.5 px-3 w-36">处置法院 / 机构</th>
            <th className="py-2.5 px-3 w-20">渠道</th>
            <th className="py-2.5 px-3 w-28 text-right">起拍价</th>
            <th className="py-2.5 px-3 w-24 text-right">建筑面积</th>
            <th className="py-2.5 px-3 w-28 text-right">折合单价</th>
            <th className="py-2.5 px-3 w-28 text-right">评估价</th>
            <th className="py-2.5 px-3 w-20 text-center">折扣率</th>
            <th className="py-2.5 px-3 w-32">发布时间</th>
            <th className="py-2.5 px-3 w-20 text-center">操作</th>
          </tr>
        </thead>

        {/* 表格内容行 */}
        <tbody className="divide-y divide-[#1e2638] text-[#cbd5e1]">
          {notices.map((item) => {
            const isSelected = selectedNotice?.id === item.id;
            const noteTag = extractNoteTag(item.user_notes);
            const timeFormatted = formatPublishTime(item.publish_time) || '--';

            return (
              <tr
                key={item.id}
                onClick={() => onSelectNotice && onSelectNotice(item)}
                onDoubleClick={() => item.source_url && window.open(item.source_url, '_blank')}
                className={`group cursor-pointer transition-colors duration-100 ${
                  isSelected
                    ? 'bg-[#182238] border-l-2 border-l-amber-400 font-medium'
                    : 'hover:bg-[#151c2e]'
                }`}
              >
                {/* 关注星标 */}
                <td className="py-2.5 px-3 text-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onToggleStar) onToggleStar(item.id, !item.is_starred);
                    }}
                    className={`p-1 rounded hover:bg-[#1e2638] transition-colors ${
                      item.is_starred
                        ? 'text-amber-400'
                        : 'text-[#475569] hover:text-[#94a3b8]'
                    }`}
                    title={item.is_starred ? '取消关注' : '加入关注'}
                  >
                    <Star className={`w-3.5 h-3.5 ${item.is_starred ? 'fill-amber-400 text-amber-400' : ''}`} />
                  </button>
                </td>

                {/* 便签状态徽标 */}
                <td className="py-2.5 px-3 text-center">
                  {noteTag ? (
                    <span className={`inline-block px-1.5 py-0.2 text-[10px] font-semibold rounded ${getNoteTagBadgeStyle(noteTag)}`}>
                      {noteTag}
                    </span>
                  ) : (
                    <span className="text-[#475569] text-[11px]">-</span>
                  )}
                </td>

                {/* 业务模块与阶段 */}
                <td className="py-2.5 px-3">
                  <div className="flex items-center space-x-1.5">
                    {getModuleBadge(item.module_type)}
                    {item.auction_stage && (
                      <span className="text-[10px] px-1 py-0.2 rounded bg-[#161e31] text-[#94a3b8] border border-[#1e2638]">
                        {item.auction_stage}
                      </span>
                    )}
                  </div>
                </td>

                {/* 标的公示标题 (带涉豫胶囊) */}
                <td className="py-2.5 px-3 max-w-[380px] truncate" title={item.title}>
                  <div className="flex items-center space-x-1.5 truncate">
                    {item.is_today && (
                      <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 flex items-center space-x-1" title="当天最新发布">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        <span>今日</span>
                      </span>
                    )}
                    {item.henan_city && (
                      <span className="shrink-0 text-[10px] font-semibold px-1 py-0.1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {item.henan_city}
                      </span>
                    )}
                    {item.risk_tags && item.risk_tags.length > 0 && (
                      <span className="flex items-center space-x-1 shrink-0">
                        {item.risk_tags.slice(0, 2).map((tag) => (
                          <span key={tag} className={`px-1 py-0.1 text-[9px] font-semibold rounded shrink-0 ${getRiskTagBadgeStyle(tag)}`}>
                            {tag}
                          </span>
                        ))}
                      </span>
                    )}
                    <span className={`truncate ${isSelected ? 'text-amber-200' : 'text-[#f1f5f9]'}`}>
                      {item.title}
                    </span>
                  </div>
                </td>

                {/* 案号 */}
                <td className="py-2.5 px-3 font-mono text-[11px] text-[#94a3b8] truncate max-w-[140px]" title={item.case_number || ''}>
                  {item.case_number || '--'}
                </td>

                {/* 处置法院/主体 */}
                <td className="py-2.5 px-3 text-[11px] text-[#94a3b8] truncate max-w-[140px]" title={item.court_name || ''}>
                  {item.court_name || '--'}
                </td>

                {/* 平台渠道 */}
                <td className="py-2.5 px-3 text-[11px] text-[#94a3b8]">
                  {getPlatformName(item.platform)}
                </td>

                {/* 起拍价 */}
                <td className="py-2.5 px-3 text-right font-bold text-amber-400 tabular-nums">
                  {item.starting_price != null 
                    ? `¥${(item.starting_price >= 10000) ? `${(item.starting_price / 10000).toFixed(1)}万` : item.starting_price.toLocaleString('zh-CN')}`
                    : '--'}
                </td>

                {/* 建筑面积 */}
                <td className="py-2.5 px-3 text-right font-mono text-[11px] text-[#cbd5e1] tabular-nums">
                  {item.area_sqm != null ? `${item.area_sqm}㎡` : '--'}
                </td>

                {/* 折合单价 */}
                <td className="py-2.5 px-3 text-right font-mono text-[11px] text-amber-300 tabular-nums">
                  {item.unit_price != null ? `¥${item.unit_price.toLocaleString('zh-CN')}/㎡` : '--'}
                </td>

                {/* 评估价 */}
                <td className="py-2.5 px-3 text-right text-[11px] text-[#64748b] tabular-nums">
                  {item.eval_price != null 
                    ? `¥${(item.eval_price >= 10000) ? `${(item.eval_price / 10000).toFixed(1)}万` : item.eval_price.toLocaleString('zh-CN')}`
                    : '--'}
                </td>

                {/* 折扣率 */}
                <td className="py-2.5 px-3 text-center">
                  {item.discount_rate != null ? (
                    <span className={`inline-block text-[10px] font-bold px-1.5 py-0.2 rounded ${
                      (item.discount_rate <= 7 || (item.discount_rate > 10 && item.discount_rate <= 70))
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'text-[#64748b]'
                    }`}>
                      {(item.discount_rate <= 7 || (item.discount_rate > 10 && item.discount_rate <= 70)) ? '🔥 ' : ''}{item.discount_rate}折
                    </span>
                  ) : (
                    <span className="text-[#475569] text-[10px]">--</span>
                  )}
                </td>

                {/* 发布时间 */}
                <td className={`py-2.5 px-3 text-[11px] ${item.is_today ? 'text-emerald-400 font-semibold' : 'text-[#64748b]'}`}>
                  {timeFormatted}
                </td>

                {/* 快捷操作 */}
                <td className="py-2.5 px-3 text-center">
                  <div className="flex items-center justify-center space-x-1.5">
                    {item.source_url && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1 rounded text-[#64748b] hover:text-[#60a5fa] hover:bg-[#1e2638] transition-colors"
                        title="打开官方原网详情"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                    {onCopyBriefing && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCopyBriefing(item);
                        }}
                        className="p-1 rounded text-[#64748b] hover:text-amber-300 hover:bg-[#1e2638] transition-colors"
                        title="生成微信简报"
                      >
                        <Share2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
