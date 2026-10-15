// 便签预设状态标签与徽标样式工具库

export const PRESET_NOTE_TAGS = [
  { label: '待看样', color: 'emerald', desc: '需实地踏勘 / 标的核查' },
  { label: '已尽调', color: 'blue', desc: '产调无抵押 / 风险排查完成' },
  { label: '重点跟进', color: 'amber', desc: '性价比极高 / 拟参拍或收购' },
  { label: '瑕疵风险', color: 'rose', desc: '存在租约 / 税费高 / 占用' },
  { label: '已弃拍', color: 'slate', desc: '标的硬伤 / 价格偏高 / 放弃' }
];

export const extractNoteTag = (notes) => {
  if (!notes) return null;
  const match = notes.match(/\[(待看样|已尽调|重点跟进|瑕疵风险|已弃拍)\]/);
  return match ? match[1] : null;
};

export const getNoteTagBadgeStyle = (tag) => {
  switch (tag) {
    case '待看样':
      return 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60';
    case '已尽调':
      return 'bg-blue-950/60 text-blue-400 border border-blue-800/60';
    case '重点跟进':
      return 'bg-amber-950/60 text-amber-400 border border-amber-800/60';
    case '瑕疵风险':
      return 'bg-rose-950/60 text-rose-400 border border-rose-800/60';
    case '已弃拍':
      return 'bg-slate-800/80 text-slate-400 border border-slate-700';
    default:
      return 'bg-slate-800/60 text-slate-300 border border-slate-700';
  }
};

// 智能时间格式化：若只有日期精度（如00:00）则展示清晰明确的YYYY-MM-DD，若有时分秒则展示具体时分
export const formatPublishTime = (timeStr) => {
  if (!timeStr) return '';
  const clean = timeStr.replace('T', ' ');
  if (clean.includes(' 00:00:00') || clean.endsWith(' 00:00')) {
    return clean.slice(0, 10);
  }
  return clean.slice(0, 16);
};

// 法拍排雷风险标签高亮样式
export const getRiskTagBadgeStyle = (tag) => {
  switch (tag) {
    case '已腾空':
    case '无租约':
    case '税费各付':
    case '有产权证':
      return 'bg-emerald-950/60 text-emerald-300 border border-emerald-700/60';
    case '未腾空':
    case '买受人全担税':
    case '无产权证':
      return 'bg-rose-950/60 text-rose-300 border border-rose-700/60 font-semibold';
    case '带租约':
    case '存在抵押':
      return 'bg-amber-950/60 text-amber-300 border border-amber-700/60';
    default:
      return 'bg-slate-800/60 text-slate-300 border border-slate-700';
  }
};
