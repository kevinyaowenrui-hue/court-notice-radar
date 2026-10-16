import React from 'react';
import { Star, ShieldAlert } from 'lucide-react';
import { extractNoteTag, getNoteTagBadgeStyle, getRiskTagBadgeStyle, formatPublishTime } from '../tagUtils';

export default function NoticeItemRow({ item, isSelected, isUnread, ruleName, onClick, onToggleStar }) {
  if (!item) return null;

  const noteTag = extractNoteTag(item.user_notes);

  const getModuleBadge = (mod) => {
    switch (mod) {
      case '拍卖公告':
        return (
          <span className="px-1.5 py-0.5 text-[11px] font-semibold rounded bg-amber-950/40 text-amber-300 border border-amber-800/50 shrink-0">
            拍卖
          </span>
        );
      case '债权转让':
        return (
          <span className="px-1.5 py-0.5 text-[11px] font-semibold rounded bg-purple-950/40 text-purple-300 border border-purple-800/50 shrink-0">
            债权
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 text-[11px] font-semibold rounded bg-blue-950/40 text-blue-300 border border-blue-800/50 shrink-0">
            公告
          </span>
        );
    }
  };

  const getPlatformName = (platform) => {
    const map = {
      rmfysszc: '诉讼资产网',
      ali: '阿里',
      jd: '京东',
      rmfyb: '法院报',
      local_paper: '地方报',
      caa: '中拍',
      ggzy: '公共资源'
    };
    return map[platform] || platform;
  };

  const simplifyRuleName = (name) => {
    if (!name) return '';
    const trimmed = name.trim();
    if (trimmed.includes('重点不动产')) return '重点不动产';
    if (trimmed.includes('高优') || (trimmed.includes('一拍') && trimmed.includes('房源'))) return '【高优】一拍房源';
    if (trimmed.includes('捡漏') || (trimmed.includes('二拍') && trimmed.includes('房源'))) return '【捡漏】二拍房源';
    if (trimmed.includes('不良债权') || trimmed.includes('债权与资产包')) return '金融不良债权';
    if (trimmed.includes('破产清算') || trimmed.includes('重组预警')) return '企业破产重组';
    if (trimmed.includes('53BK') || trimmed.includes('地方报纸')) return '地方报刊雷达';
    if (trimmed.includes('法网雷达') || trimmed.includes('人民法院报') || trimmed.includes('诉讼送达')) return '【法网】送达/执行';
    if (trimmed.includes('一拍')) return '一拍精选';
    if (trimmed.includes('二拍')) return '二拍捡漏';
    if (trimmed.includes('变卖')) return '优质变卖';
    const clean = trimmed.replace(/^[【\[（(]/, '').replace(/[】\]）)]$/, '');
    return clean.length > 8 ? clean.slice(0, 8) + '...' : clean;
  };

  const timeFormatted = formatPublishTime(item.publish_time);

  return (
    <div
      onClick={onClick}
      className={`group relative px-4 py-3 border-b border-[#1e2638] cursor-pointer transition-colors duration-100 flex items-center justify-between gap-3 ${
        isSelected
          ? 'bg-[#182238] border-l-2 border-l-amber-400'
          : 'bg-[#111726] hover:bg-[#161e31]'
      }`}
    >
      {/* 左侧主要信息 */}
      <div className="flex-1 min-w-0 pr-2">
        {/* 第一行：未读点 + 模块标签 + 便签状态徽标 + 阶段 + 标题 */}
        <div className="flex items-center space-x-2">
          {isUnread && (
            <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0 shadow-xs" title="未读预警" />
          )}

          {item.is_today && (
            <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/50 shrink-0 flex items-center space-x-1 shadow-xs" title="当天最新发布标的">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>今日最新</span>
            </span>
          )}

          {/* 重点关注刚上拍房源：一拍公示期30天、二拍公示期15天，刚上拍黄金准备期 */}
          {item.is_newly_listed && (
            <span 
              className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 shrink-0 flex items-center space-x-1 shadow-xs" 
              title={
                item.days_until_bidding !== null && item.days_until_bidding !== undefined
                  ? `刚上拍标的！距开拍还剩 ${item.days_until_bidding} 天（法院公告排期，最高法规定法定公示期不少于${item.auction_stage === '二拍' ? '15' : '30'}天），独享黄金尽调看样与筹款准备期！` 
                  : "刚上拍公示标的，尽调黄金准备期！"
              }
            >
              <span>🔥 刚上拍</span>
              {item.days_until_bidding !== null && item.days_until_bidding !== undefined && item.days_until_bidding > 0 && (
                <span className="text-[9px] opacity-90 pl-0.5 font-normal">
                  (剩{item.days_until_bidding}天)
                </span>
              )}
            </span>
          )}

          {!item.is_newly_listed && item.days_until_bidding !== null && item.days_until_bidding !== undefined && item.days_until_bidding > 0 && (
            <span className="text-[10px] font-medium px-1.5 py-0.2 rounded bg-blue-950/40 text-blue-300 border border-blue-800/40 shrink-0">
              {item.auction_stage || '拍卖'}剩{item.days_until_bidding}天
            </span>
          )}

          {(item.asset_category === '房产' || item.asset_category === '住宅/商业房产') && (
            <span className="text-[10px] font-semibold px-1 py-0.2 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-800/40 shrink-0">
              房产
            </span>
          )}

          {getModuleBadge(item.module_type)}

          {noteTag && (
            <span className={`px-1.5 py-0.2 text-[10px] font-semibold rounded shrink-0 ${getNoteTagBadgeStyle(noteTag)}`}>
              {noteTag}
            </span>
          )}

          {item.auction_stage && (
            <span className="text-[10px] font-medium px-1.5 py-0.2 rounded bg-[#161e31] text-[#94a3b8] border border-[#1e2638] shrink-0">
              {item.auction_stage}
            </span>
          )}

          <h3 className={`text-xs sm:text-sm truncate text-[#f1f5f9] ${
            isUnread ? 'font-bold' : 'font-medium'
          }`}>
            {item.title}
          </h3>
        </div>

        {/* 第二行：机构法院 · 平台 · 涉豫 · 规则 · 时间 */}
        <div className="mt-1.5 flex items-center space-x-2 text-[11px] text-[#94a3b8] truncate">
          <span className="truncate max-w-[140px] sm:max-w-[200px]">
            {item.court_name || '法院/处置主体'}
          </span>
          <span>·</span>
          <span>{getPlatformName(item.platform)}</span>

          {item.henan_city && (
            <>
              <span>·</span>
              <span className="text-amber-400 font-medium">
                {item.henan_city}
              </span>
            </>
          )}

          {item.risk_tags && item.risk_tags.length > 0 && (
            <>
              <span>·</span>
              <span className="flex items-center space-x-1 shrink-0">
                {item.risk_tags.slice(0, 3).map((tag) => (
                  <span key={tag} className={`px-1 py-0.1 text-[9px] font-semibold rounded shrink-0 ${getRiskTagBadgeStyle(tag)}`}>
                    {tag}
                  </span>
                ))}
              </span>
            </>
          )}

          {ruleName && (
            <>
              <span>·</span>
              <span className="flex items-center space-x-1 shrink-0">
                {ruleName.split(' | ').map((rn, idx) => {
                  const label = simplifyRuleName(rn);
                  if (!label) return null;
                  return (
                    <span
                      key={idx}
                      className="px-1.5 py-0.2 text-[10px] font-medium rounded bg-rose-950/40 text-rose-300 border border-rose-800/40 flex items-center space-x-0.5 shrink-0"
                      title={rn.trim()}
                    >
                      <ShieldAlert className="w-2.5 h-2.5 inline shrink-0 mr-0.5 text-rose-400" />
                      <span>{label}</span>
                    </span>
                  );
                })}
              </span>
            </>
          )}

          {timeFormatted && (
            <>
              <span>·</span>
              <span className={`shrink-0 ${item.is_today ? 'text-emerald-400 font-semibold' : 'text-[#64748b]'}`}>{timeFormatted}</span>
            </>
          )}
        </div>
      </div>

      {/* 右侧价格与折扣率 (沉稳琥珀互补色) */}
      <div className="shrink-0 flex items-center space-x-3 text-right">
        {item.starting_price != null ? (
          <div>
            <div className="text-xs sm:text-sm font-bold text-amber-400 tabular-nums">
              ¥{(item.starting_price >= 10000) 
                ? `${(item.starting_price / 10000).toFixed(1)}万` 
                : item.starting_price.toLocaleString('zh-CN')}
            </div>
            {(item.area_sqm != null || item.unit_price != null) && (
              <div className="text-[10px] text-slate-400 tabular-nums font-mono">
                {item.area_sqm != null ? `${item.area_sqm}㎡` : ''}
                {item.area_sqm != null && item.unit_price != null ? ' · ' : ''}
                {item.unit_price != null ? `¥${item.unit_price.toLocaleString('zh-CN')}/㎡` : ''}
              </div>
            )}
            {item.discount_rate != null ? (
              <span className={`inline-block text-[10px] font-bold px-1.5 py-0.2 rounded mt-0.5 ${
                (item.discount_rate <= 7 || (item.discount_rate > 10 && item.discount_rate <= 70))
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'text-[#64748b]'
              }`}>
                {(item.discount_rate <= 7 || (item.discount_rate > 10 && item.discount_rate <= 70)) ? '🔥 ' : ''}{item.discount_rate}折
              </span>
            ) : (
              (!item.area_sqm && !item.unit_price) && <div className="text-[10px] text-[#64748b]">起拍价</div>
            )}
          </div>
        ) : null}

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (onToggleStar) onToggleStar(item.id, !item.is_starred);
          }}
          className={`p-1.5 rounded hover:bg-[#161e31] transition-colors ${
            item.is_starred
              ? 'text-amber-400'
              : 'text-[#475569] hover:text-[#94a3b8]'
          }`}
          title={item.is_starred ? '取消关注' : '关注标的'}
        >
          <Star className={`w-4 h-4 ${item.is_starred ? 'fill-amber-400 text-amber-400' : ''}`} />
        </button>
      </div>
    </div>
  );
}
