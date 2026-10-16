import React, { useState, useEffect } from 'react';
import { ExternalLink, Star, X, Check, Copy, Share2, GitCommit, Layers, ArrowUpRight, Calculator, CheckSquare, ChevronDown, ChevronUp } from 'lucide-react';
import { updateNoticeNotes, toggleNoticeStar, fetchRelatedNotices } from '../api';
import { PRESET_NOTE_TAGS, extractNoteTag, getNoteTagBadgeStyle, getRiskTagBadgeStyle, formatPublishTime } from '../tagUtils';

// 🧮 拿房真实总成本 & 举牌红线测算器
function InvestorRoiCalculator({ notice, onAppendNotes }) {
  const [expanded, setExpanded] = useState(false);
  const [bidPrice, setBidPrice] = useState('');
  const [marketPrice, setMarketPrice] = useState('');
  const [deedRate, setDeedRate] = useState(1.5);
  const [includeSellerTax, setIncludeSellerTax] = useState(false);
  const [sellerRate, setSellerRate] = useState(6.3);
  const [arrears, setArrears] = useState('0.5'); // 5000元
  const [clearance, setClearance] = useState('1.5'); // 15000元
  const [targetMargin, setTargetMargin] = useState(15); // 15%

  // 初始化或切换标的时重置默认测算数值
  useEffect(() => {
    if (notice) {
      const defaultBid = notice.starting_price ? (notice.starting_price / 10000).toFixed(1) : '';
      const defaultMarket = notice.eval_price
        ? (notice.eval_price / 10000).toFixed(1)
        : (notice.starting_price ? (notice.starting_price * 1.3 / 10000).toFixed(1) : '');
      setBidPrice(defaultBid);
      setMarketPrice(defaultMarket);
      const isSellerTax = Boolean(notice.risk_tags?.some(t => t.includes('全担税') || t.includes('垫付税费')));
      setIncludeSellerTax(isSellerTax);
    }
  }, [notice?.id]);

  const bidNum = parseFloat(bidPrice) || 0;
  const marketNum = parseFloat(marketPrice) || 0;
  const arrearsNum = parseFloat(arrears) || 0;
  const clearanceNum = parseFloat(clearance) || 0;
  const deedTaxWan = bidNum * (deedRate / 100);
  const sellerTaxWan = includeSellerTax ? (bidNum * (sellerRate / 100)) : 0;
  const totalCostWan = bidNum + deedTaxWan + sellerTaxWan + arrearsNum + clearanceNum;

  const area = notice?.area_sqm || 0;
  const actualUnitPrice = area > 0 ? Math.round((totalCostWan * 10000) / area) : 0;
  const grossProfitWan = marketNum - totalCostWan;
  const roiPercent = totalCostWan > 0 ? ((grossProfitWan / totalCostWan) * 100).toFixed(1) : 0;

  // 举牌红线封顶计算
  const taxMultiplier = 1 + (deedRate + (includeSellerTax ? sellerRate : 0)) / 100;
  const totalCostCap = marketNum / (1 + targetMargin / 100);
  const maxBidWan = Math.max(0, (totalCostCap - arrearsNum - clearanceNum) / taxMultiplier).toFixed(1);

  const handleSyncToNotes = () => {
    const summary = `【举牌红线测算】拿房总成本¥${totalCostWan.toFixed(1)}万(契税¥${deedTaxWan.toFixed(2)}万${includeSellerTax ? `+转嫁税¥${sellerTaxWan.toFixed(2)}万` : ''}+杂费¥${(arrearsNum+clearanceNum).toFixed(1)}万)${actualUnitPrice > 0 ? ` 折合到手¥${actualUnitPrice.toLocaleString()}/㎡` : ''}，在预期去化¥${marketNum}万下保${targetMargin}%收益举牌上限【¥${maxBidWan}万】`;
    if (onAppendNotes) {
      onAppendNotes(summary);
    }
  };

  return (
    <div className="bg-[#121827] rounded-lg border border-[#1e2638] overflow-hidden">
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-3 flex items-center justify-between cursor-pointer hover:bg-[#161e31] transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Calculator className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-xs font-bold text-[#f1f5f9]">
            🧮 拿房真实总成本 & 举牌红线测算器
          </span>
          {bidNum > 0 && totalCostWan > 0 && !expanded && (
            <span className="text-[10px] text-amber-300 font-mono">
              (成本¥{totalCostWan.toFixed(1)}万 · 上限¥{maxBidWan}万)
            </span>
          )}
        </div>
        <div className="flex items-center space-x-1 text-[#64748b]">
          <span className="text-[10px]">{expanded ? '收起' : '展开测算'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </div>

      {expanded && (
        <div className="p-3.5 pt-1 border-t border-[#1e2638] space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="text-[11px] text-[#94a3b8] block mb-1">拟出价/举牌价 (万元)</label>
              <input
                type="number"
                step="0.1"
                value={bidPrice}
                onChange={(e) => setBidPrice(e.target.value)}
                placeholder="起拍价"
                className="w-full bg-[#161e31] border border-[#1e2638] rounded px-2.5 py-1 text-xs text-[#f1f5f9] font-mono focus:border-amber-400/60 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] text-[#94a3b8] block mb-1">同小区二手去化价 (万元)</label>
              <input
                type="number"
                step="0.1"
                value={marketPrice}
                onChange={(e) => setMarketPrice(e.target.value)}
                placeholder="参考评估/挂牌价"
                className="w-full bg-[#161e31] border border-[#1e2638] rounded px-2.5 py-1 text-xs text-[#f1f5f9] font-mono focus:border-amber-400/60 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[11px] text-[#94a3b8] block mb-1">契税费率</label>
              <select
                value={deedRate}
                onChange={(e) => setDeedRate(parseFloat(e.target.value))}
                className="w-full bg-[#161e31] border border-[#1e2638] rounded px-2 py-1 text-xs text-[#cbd5e1] focus:border-amber-400/60 focus:outline-none"
              >
                <option value={1}>1.0% (首套/二套 ≤140㎡)</option>
                <option value={1.5}>1.5% (首套 &gt;140㎡)</option>
                <option value={2}>2.0% (二套 &gt;140㎡)</option>
                <option value={3}>3.0% (三套及以上/商办)</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[#94a3b8] block mb-1">目标净收益率</label>
              <select
                value={targetMargin}
                onChange={(e) => setTargetMargin(parseFloat(e.target.value))}
                className="w-full bg-[#161e31] border border-[#1e2638] rounded px-2 py-1 text-xs text-[#cbd5e1] focus:border-amber-400/60 focus:outline-none"
              >
                <option value={10}>10% 安全垫 (保本微利)</option>
                <option value={15}>15% 目标收益 (稳健投资)</option>
                <option value={20}>20% 激进收益 (高性价比)</option>
                <option value={25}>25% 暴利安全垫</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[#94a3b8] block mb-1">物业/采暖欠费预估 (万)</label>
              <input
                type="number"
                step="0.1"
                value={arrears}
                onChange={(e) => setArrears(e.target.value)}
                className="w-full bg-[#161e31] border border-[#1e2638] rounded px-2.5 py-1 text-xs text-[#cbd5e1] font-mono focus:border-amber-400/60 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[11px] text-[#94a3b8] block mb-1">清场安置备用金 (万)</label>
              <input
                type="number"
                step="0.1"
                value={clearance}
                onChange={(e) => setClearance(e.target.value)}
                className="w-full bg-[#161e31] border border-[#1e2638] rounded px-2.5 py-1 text-xs text-[#cbd5e1] font-mono focus:border-amber-400/60 focus:outline-none"
              />
            </div>
          </div>

          <div className="p-2 rounded bg-[#161e31] border border-[#1e2638] flex items-center justify-between">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeSellerTax}
                onChange={(e) => setIncludeSellerTax(e.target.checked)}
                className="rounded border-[#1e2638] text-amber-500 focus:ring-0 cursor-pointer"
              />
              <span className="text-xs text-[#cbd5e1] font-medium">
                买受人全担税费 (转嫁上家增值税/个税)
              </span>
            </label>
            {includeSellerTax && (
              <div className="flex items-center space-x-1 text-[11px] text-rose-300">
                <span>预估费率:</span>
                <input
                  type="number"
                  step="0.1"
                  value={sellerRate}
                  onChange={(e) => setSellerRate(parseFloat(e.target.value) || 0)}
                  className="w-12 bg-[#121827] border border-rose-800/60 rounded px-1 text-center font-mono text-xs text-rose-300"
                />
                <span>%</span>
              </div>
            )}
          </div>

          <div className="bg-[#161e31] rounded-lg p-3 border border-amber-500/30 space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-[#94a3b8] block text-[11px]">拿房真实总成本</span>
                <span className="text-base font-bold text-amber-400 font-mono">
                  ¥{totalCostWan.toFixed(2)}万
                </span>
                {actualUnitPrice > 0 && (
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    实得单价: ¥{actualUnitPrice.toLocaleString()}/㎡
                  </div>
                )}
              </div>
              <div>
                <span className="text-[#94a3b8] block text-[11px]">预期投资毛利 / ROI</span>
                <div className={`text-base font-bold font-mono ${grossProfitWan >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {grossProfitWan >= 0 ? `+¥${grossProfitWan.toFixed(2)}万` : `-¥${Math.abs(grossProfitWan).toFixed(2)}万`}
                  <span className="text-xs ml-1 font-normal opacity-90">({roiPercent}%)</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  税费杂费占: ¥{(deedTaxWan + sellerTaxWan + arrearsNum + clearanceNum).toFixed(2)}万
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-[#1e2638] flex items-center justify-between">
              <div>
                <span className="text-[11px] text-slate-400">🛡️ {targetMargin}% 收益举牌上限红线: </span>
                <span className="text-sm font-bold text-amber-300 font-mono ml-1">
                  ¥{maxBidWan} 万元
                </span>
              </div>
              <button
                type="button"
                onClick={handleSyncToNotes}
                className="px-2 py-1 text-[11px] font-semibold rounded bg-[#182238] text-amber-300 border border-amber-500/40 hover:bg-[#1d2a45] transition-colors"
                title="将当前投资红线结论快速追加到便签备忘中"
              >
                + 记入便签
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// 📋 职业法拍 5 步尽调 Checklist
const DD_CHECKLIST_TEMPLATE = [
  { id: 'title', title: '1. 产调与司法查封排查', hint: '不动产登记中心调取产调证明，核实首封法院、查封轮次、是否有多次抵押及破产程序介入' },
  { id: 'site', title: '2. 现场实地勘验与占用', hint: '现场上门核实是否有人居住、是否有老人/重病人员阻挠、水电表走动、门锁及内部结构完好度' },
  { id: 'lease', title: '3. 租赁及居住权穿透', hint: '核查是否存在长租合同（买卖不破租赁）、租金是否在抵押前一次性付清、是否登记居住权' },
  { id: 'tax', title: '4. 综合税费与历史欠费', hint: '核实原购房价/增值税原值发票，确认上家增值税/个税是否转嫁买受人；向物业核查欠费及滞纳金' },
  { id: 'school', title: '5. 户口学区与协同交付', hint: '向派出所核查户口沉淀情况；向教育局核验学区学位占用周期；评估法院协助执行清场交付力度' },
];

function DueDiligenceChecklist({ notice, onAppendNotes }) {
  const [expanded, setExpanded] = useState(false);
  const [checkedMap, setCheckedMap] = useState({});

  useEffect(() => {
    if (notice?.id) {
      try {
        const saved = localStorage.getItem(`court_dd_checks_${notice.id}`);
        setCheckedMap(saved ? JSON.parse(saved) : {});
      } catch {
        setCheckedMap({});
      }
    }
  }, [notice?.id]);

  const toggleItem = (id) => {
    const next = { ...checkedMap, [id]: !checkedMap[id] };
    setCheckedMap(next);
    try {
      localStorage.setItem(`court_dd_checks_${notice.id}`, JSON.stringify(next));
    } catch (e) {
      console.error(e);
    }
  };

  const doneCount = DD_CHECKLIST_TEMPLATE.filter(it => checkedMap[it.id]).length;

  const handleSyncToNotes = () => {
    const doneTitles = DD_CHECKLIST_TEMPLATE
      .filter(it => checkedMap[it.id])
      .map(it => it.title.slice(3, 7))
      .join('/');
    const noteContent = `[${doneCount === 5 ? '已尽调' : '待看样'}] 已排查${doneCount}/5项尽调清单(${doneTitles || '暂无'})`;
    if (onAppendNotes) {
      onAppendNotes(noteContent);
    }
  };

  return (
    <div className="bg-[#121827] rounded-lg border border-[#1e2638] overflow-hidden">
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-3 flex items-center justify-between cursor-pointer hover:bg-[#161e31] transition-colors"
      >
        <div className="flex items-center space-x-2">
          <CheckSquare className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-bold text-[#f1f5f9]">
            📋 职业法拍 5 步尽调 Checklist
          </span>
          <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
            doneCount === 5
              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-700/60'
              : 'bg-[#161e31] text-[#94a3b8] border border-[#1e2638]'
          }`}>
            {doneCount}/5 项已排查
          </span>
        </div>
        <div className="flex items-center space-x-1 text-[#64748b]">
          <span className="text-[10px]">{expanded ? '收起' : '展开清单'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </div>

      {expanded && (
        <div className="p-3.5 pt-1 border-t border-[#1e2638] space-y-2.5 text-xs">
          <div className="space-y-2">
            {DD_CHECKLIST_TEMPLATE.map((item) => {
              const isChecked = !!checkedMap[item.id];
              return (
                <div
                  key={item.id}
                  onClick={() => toggleItem(item.id)}
                  className={`p-2.5 rounded border cursor-pointer transition-colors ${
                    isChecked
                      ? 'bg-emerald-950/20 border-emerald-700/40 text-emerald-200'
                      : 'bg-[#161e31] border-[#1e2638] text-[#cbd5e1] hover:bg-[#182238]'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="rounded border-[#1e2638] text-emerald-500 focus:ring-0 cursor-pointer shrink-0"
                    />
                    <span className={`font-semibold text-xs ${isChecked ? 'text-emerald-300 line-through opacity-90' : 'text-[#f1f5f9]'}`}>
                      {item.title}
                    </span>
                  </div>
                  <p className="mt-1 pl-5 text-[11px] text-[#94a3b8] leading-relaxed">
                    {item.hint}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="pt-2 border-t border-[#1e2638] flex items-center justify-between">
            <span className="text-[11px] text-[#64748b]">
              排查进度自动存盘，防丢抗重置
            </span>
            <button
              type="button"
              onClick={handleSyncToNotes}
              className="px-2.5 py-1 text-[11px] font-semibold rounded bg-[#182238] text-emerald-300 border border-emerald-500/40 hover:bg-[#1d2a45] transition-colors"
            >
              同步排查结论至便签
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function NoticeDetailPane({ notice, onClose, onStarChange, onNotesUpdated, onSelectNotice }) {
  const [notes, setNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isStarred, setIsStarred] = useState(false);
  const [copied, setCopied] = useState(false);
  const [briefingCopied, setBriefingCopied] = useState(false);

  const handleAppendNotes = (textToAppend) => {
    let current = notes || '';
    let updated = current ? `${current}\n${textToAppend}` : textToAppend;
    setNotes(updated);
    handleSaveNotes(updated);
  };

  // 跨平台全流程关联与时间线
  const [relatedData, setRelatedData] = useState(null);
  const [loadingRelated, setLoadingRelated] = useState(false);

  useEffect(() => {
    if (notice) {
      setNotes(notice.user_notes || '');
      setIsStarred(!!notice.is_starred);
      setSaveSuccess(false);

      setLoadingRelated(true);
      fetchRelatedNotices(notice.id)
        .then((data) => setRelatedData(data))
        .catch((err) => {
          console.error('Failed to load related notices:', err);
          setRelatedData(null);
        })
        .finally(() => setLoadingRelated(false));
    }
  }, [notice?.id]);

  if (!notice) return null;

  const handleSaveNotes = async (overrideNotes) => {
    const val = overrideNotes !== undefined ? overrideNotes : notes;
    setSavingNotes(true);
    setSaveSuccess(false);
    try {
      await updateNoticeNotes(notice.id, val);
      setSaveSuccess(true);
      if (onNotesUpdated) {
        onNotesUpdated(notice.id, val);
      }
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      console.error('Failed to save notes:', err);
    } finally {
      setSavingNotes(false);
    }
  };

  const handleQuickTagClick = (tagLabel) => {
    let current = notes || '';
    const currentTag = extractNoteTag(current);
    let updated = '';
    if (currentTag === tagLabel) {
      updated = current.replace(`[${tagLabel}]`, '').trim();
    } else if (currentTag) {
      updated = current.replace(`[${currentTag}]`, `[${tagLabel}]`);
    } else {
      updated = `[${tagLabel}] ${current}`.trim();
    }
    setNotes(updated);
    handleSaveNotes(updated);
  };

  const handleToggleStar = async () => {
    const nextState = !isStarred;
    setIsStarred(nextState);
    try {
      const res = await toggleNoticeStar(notice.id);
      const actualState = res?.is_starred !== undefined ? res.is_starred : nextState;
      setIsStarred(actualState);
      if (onStarChange) {
        onStarChange(notice.id, actualState);
      }
    } catch (err) {
      setIsStarred(!nextState);
      console.error('Failed to toggle star:', err);
    }
  };

  const getPlatformLabel = (p) => {
    const map = {
      rmfysszc: '人民法院诉讼资产网',
      ali: '阿里司法拍卖',
      jd: '京东拍卖',
      rmfyb: '人民法院报公告网',
      local_paper: '地方报纸专版',
      caa: '中拍平台',
      ggzy: '公共资源交易中心'
    };
    return map[p] || p;
  };

  const copyTextToClipboard = async (text) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      // fallback below
    }
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const res = document.execCommand('copy');
      document.body.removeChild(textarea);
      return res;
    } catch {
      return false;
    }
  };

  const handleCopyNotice = async () => {
    if (!notice) return;
    const fullContent = `${notice.title}\n\n${notice.content_text || ''}\n\n【来源渠道】：${getPlatformLabel(notice.platform)}\n【官方链接】：${notice.source_url}`;
    await copyTextToClipboard(fullContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyBriefing = async () => {
    if (!notice) return;
    const priceInfo = notice.starting_price 
      ? `¥${Number(notice.starting_price).toLocaleString('zh-CN')} ${notice.discount_rate ? `(${notice.discount_rate}折捡漏)` : ''}`
      : '以公告为准';
    const evalInfo = notice.eval_price 
      ? `¥${Number(notice.eval_price).toLocaleString('zh-CN')}`
      : '无评估价/参考公文';
    
    const lines = [
      `【法拍资产 · 投资尽调简报】`,
      `📍 标的名称：${notice.title}`,
      `💰 起拍价格：${priceInfo}`,
      `📊 评估价格：${evalInfo}`,
      `⚖️ 处置主体：${notice.court_name || '法院/处置机构'}`,
      `📑 模块阶段：${notice.module_type || '公告'}${notice.auction_stage ? ` · ${notice.auction_stage}` : ''}`,
      `🗺️ 属地涉豫：${notice.is_henan ? (notice.henan_city ? `涉豫 · ${notice.henan_city}` : '涉豫重点') : '全国标的'}`,
      `📅 发布时间：${formatPublishTime(notice.publish_time) || '最新'}`,
      `🔗 官方直达：${notice.source_url}`
    ];
    if (notice.user_notes) {
      lines.push(`📝 处置便签：${notice.user_notes}`);
    }

    await copyTextToClipboard(lines.join('\n'));
    setBriefingCopied(true);
    setTimeout(() => setBriefingCopied(false), 2000);
  };

  return (
    <aside className="w-full lg:w-[440px] xl:w-[480px] shrink-0 border-l border-[#1e2638] bg-[#111726] flex flex-col h-full overflow-hidden transition-all duration-150">
      {/* 顶部标题与快捷操作栏 */}
      <div className="p-4 border-b border-[#1e2638] flex items-center justify-between shrink-0 bg-[#0e1320]">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-950/40 text-blue-300 border border-blue-800/50">
            {notice.module_type || '公告'}
          </span>
          {notice.auction_stage && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/50">
              {notice.auction_stage}
            </span>
          )}
          {notice.is_henan && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/50">
              {notice.henan_city ? `涉豫 · ${notice.henan_city}` : '涉豫重点'}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            onClick={handleToggleStar}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-medium transition-colors border ${
              isStarred
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-xs'
                : 'bg-[#161e31] text-[#94a3b8] border-[#1e2638] hover:text-[#f1f5f9] hover:bg-[#182238]'
            }`}
            title={isStarred ? '点击取消关注' : '点击加入我的关注标的'}
          >
            <Star className={`w-3.5 h-3.5 ${isStarred ? 'fill-amber-400 text-amber-400' : 'text-[#64748b]'}`} />
            <span>{isStarred ? '已关注' : '关注标的'}</span>
          </button>

          <a
            href={notice.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded text-[#64748b] hover:text-[#60a5fa] hover:bg-[#161e31] transition-colors"
            title="新窗口打开官方原网详情"
          >
            <ExternalLink className="w-4 h-4" />
          </a>

          <button
            onClick={onClose}
            className="p-1.5 rounded text-[#64748b] hover:text-[#f1f5f9] hover:bg-[#161e31] transition-colors"
            title="关闭详情面板"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 滚动内容区 */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* 标的/公告标题 */}
        <div>
          <h2 className="text-base font-bold text-[#f1f5f9] leading-snug">
            {notice.title}
          </h2>
          <div className="mt-1.5 flex items-center space-x-2 text-xs text-[#94a3b8]">
            <span>{getPlatformLabel(notice.platform)}</span>
            <span>·</span>
            <span className="text-[#64748b]">{formatPublishTime(notice.publish_time) || '未知发布时间'}</span>
          </div>
        </div>

        {/* 法拍核心指标网格 (琥珀金互补色系统) */}
        {(notice.starting_price != null || notice.eval_price != null || notice.area_sqm != null) && (
          <div className="bg-[#161e31] rounded-lg p-3.5 border border-[#1e2638] grid grid-cols-2 gap-3">
            <div>
              <div className="text-[11px] text-[#94a3b8]">起拍价 (元)</div>
              <div className="text-lg font-bold text-amber-400 tabular-nums mt-0.5">
                ¥{notice.starting_price ? Number(notice.starting_price).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '--'}
              </div>
            </div>
            <div>
              <div className="text-[11px] text-[#94a3b8]">评估价 (元)</div>
              <div className="text-sm font-semibold text-[#cbd5e1] tabular-nums mt-1">
                {notice.eval_price ? `¥${Number(notice.eval_price).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}` : '--'}
              </div>
            </div>

            {(notice.area_sqm != null || notice.unit_price != null) && (
              <>
                <div className="pt-2 border-t border-[#1e2638]">
                  <div className="text-[11px] text-[#94a3b8]">建筑面积 (㎡)</div>
                  <div className="text-sm font-semibold text-[#cbd5e1] tabular-nums mt-0.5 font-mono">
                    {notice.area_sqm != null ? `${notice.area_sqm} ㎡` : '--'}
                  </div>
                </div>
                <div className="pt-2 border-t border-[#1e2638]">
                  <div className="text-[11px] text-[#94a3b8]">折合起拍单价</div>
                  <div className="text-sm font-bold text-amber-300 tabular-nums mt-0.5 font-mono">
                    {notice.unit_price != null ? `¥${notice.unit_price.toLocaleString('zh-CN')} / ㎡` : '--'}
                  </div>
                </div>
              </>
            )}

            {notice.discount_rate != null && (
              <div className="col-span-2 pt-2 border-t border-[#1e2638] flex items-center justify-between">
                <span className="text-xs text-[#94a3b8]">折扣评估</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  (notice.discount_rate <= 7 || (notice.discount_rate > 10 && notice.discount_rate <= 70))
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    : 'bg-[#111726] text-[#94a3b8] border border-[#1e2638]'
                }`}>
                  {(notice.discount_rate <= 7 || (notice.discount_rate > 10 && notice.discount_rate <= 70)) ? '🔥 捡漏 ' : ''}{notice.discount_rate}折
                </span>
              </div>
            )}
          </div>
        )}

        {/* 一拍公示期不少于30天/二拍公示期不少于15天 刚上拍尽调指示卡 */}
        {(notice.auction_stage || notice.bidding_start || notice.is_newly_listed) && (
          <div className="bg-[#131c2e] rounded-lg p-3 border border-amber-500/30 flex items-start space-x-3">
            <div className="w-8 h-8 rounded-md bg-amber-500/20 text-amber-300 flex items-center justify-center shrink-0 font-bold text-xs">
              {notice.auction_stage || '法拍'}
            </div>
            <div className="flex-1 text-xs">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-[#f1f5f9]">
                  {notice.auction_stage === '一拍' ? '一拍公示中 · 法定公示期不少于 30 天' : (notice.auction_stage === '二拍' ? '二拍公示中 · 法定公示期不少于 15 天' : '司法拍卖进行中')}
                </span>
                {notice.is_newly_listed && (
                  <span className="px-1.5 py-0.2 rounded bg-amber-500/30 text-amber-200 text-[10px] font-bold">
                    🔥 刚上拍
                  </span>
                )}
              </div>
              <div className="mt-1 text-[#94a3b8] leading-relaxed">
                {notice.bidding_start ? (
                  <>开拍时间：<span className="text-amber-300 font-mono font-medium">{notice.bidding_start.replace('T', ' ').slice(0, 16)}</span>{notice.days_until_bidding !== null && notice.days_until_bidding !== undefined && notice.days_until_bidding > 0 ? `（距开拍还剩 ${notice.days_until_bidding} 天，法定公示不少于${notice.auction_stage === '二拍' ? '15' : '30'}天）` : ''}</>
                ) : (
                  <>刚发布公示，法定准备期内，建议立即展开现场勘验、不动产产权查册、税费核算与信贷资金准备。</>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 法拍标的排雷自检标签 */}
        {notice.risk_tags && notice.risk_tags.length > 0 && (
          <div className="bg-[#121827] rounded-lg p-3.5 border border-[#1e2638] space-y-2">
            <div className="text-xs font-bold text-slate-200 flex items-center justify-between">
              <span className="flex items-center space-x-1.5">
                <span>🛡️</span>
                <span>标的排雷自检标签</span>
              </span>
              <span className="text-[10px] text-slate-400 font-normal">基于公告正文与尽调文书自动排查</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {notice.risk_tags.map((tag) => (
                <span key={tag} className={`px-2 py-0.5 text-xs font-semibold rounded ${getRiskTagBadgeStyle(tag)}`}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 🧮 拿房真实总成本 & 举牌红线测算器 */}
        <InvestorRoiCalculator notice={notice} onAppendNotes={handleAppendNotes} />

        {/* 📋 职业法拍 5 步尽调 Checklist */}
        <DueDiligenceChecklist notice={notice} onAppendNotes={handleAppendNotes} />

        {/* 关键元数据列表 */}
        <div className="space-y-2 text-xs">
          {notice.court_name && (
            <div className="flex items-start">
              <span className="w-16 text-[#64748b] shrink-0">法院/机构</span>
              <span className="text-[#e2e8f0] font-medium">{notice.court_name}</span>
            </div>
          )}
          {notice.case_number && (
            <div className="flex items-start">
              <span className="w-16 text-[#64748b] shrink-0">执行案号</span>
              <span className="text-[#e2e8f0] font-mono">{notice.case_number}</span>
            </div>
          )}
          {notice.parties && (
            <div className="flex items-start">
              <span className="w-16 text-[#64748b] shrink-0">当事人</span>
              <span className="text-[#e2e8f0]">{notice.parties}</span>
            </div>
          )}
          {notice.notice_type && (
            <div className="flex items-start">
              <span className="w-16 text-[#64748b] shrink-0">公告类型</span>
              <span className="text-[#e2e8f0]">{notice.notice_type}</span>
            </div>
          )}
          {notice.henan_tag && (
            <div className="flex items-start">
              <span className="w-16 text-[#64748b] shrink-0">涉豫认定</span>
              <span className="text-amber-400 font-medium">{notice.henan_tag}</span>
            </div>
          )}
        </div>

        {/* 同案号 / 跨平台案件全流程时间线 */}
        <div className="pt-2 border-t border-[#1e2638] space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <GitCommit className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs font-bold text-[#f1f5f9]">
                同案号历史 & 跨平台流转时间线
              </span>
            </div>
            {relatedData && relatedData.related_count > 0 ? (
              <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                关联 {relatedData.related_count} 处流转
              </span>
            ) : (
              <span className="text-[10px] text-[#64748b]">单阶段公示</span>
            )}
          </div>

          {loadingRelated ? (
            <div className="py-2 text-[11px] text-[#64748b]">检索关联历史公告中...</div>
          ) : relatedData && relatedData.items && relatedData.items.length > 1 ? (
            <div className="relative pl-3 space-y-2.5 before:absolute before:left-1 before:top-2 before:bottom-2 before:w-[2px] before:bg-[#1e2638]">
              {relatedData.items.map((it) => (
                <div
                  key={it.id}
                  onClick={() => onSelectNotice && onSelectNotice(it)}
                  className={`group relative pl-3 cursor-pointer p-2 rounded transition-colors duration-100 ${
                    it.is_current
                      ? 'bg-[#182238] border border-amber-500/40'
                      : 'bg-[#141b2b] hover:bg-[#192338] border border-transparent'
                  }`}
                  title={it.is_current ? '当前正在查看的标的' : '点击切换查看此关联历史公示'}
                >
                  <div
                    className={`absolute -left-[17px] top-3 w-2.5 h-2.5 rounded-full border-2 ${
                      it.is_current
                        ? 'bg-amber-400 border-[#0e1320]'
                        : 'bg-[#475569] border-[#0e1320] group-hover:bg-amber-400/80'
                    }`}
                  />

                  <div className="flex items-center justify-between text-[11px] text-[#94a3b8] mb-1">
                    <div className="flex items-center space-x-1.5">
                      <span className="font-semibold text-[#cbd5e1]">{getPlatformLabel(it.platform)}</span>
                      {it.auction_stage && (
                        <span className="px-1 py-0.1 rounded bg-[#0e1320] text-amber-300 text-[10px] border border-[#1e2638]">
                          {it.auction_stage}
                        </span>
                      )}
                      <span className="text-[10px] text-[#64748b]">{it.publish_time}</span>
                    </div>
                    {it.is_current && (
                      <span className="text-[10px] font-bold text-amber-400">
                        当前公示
                      </span>
                    )}
                  </div>

                  <div className="text-xs text-[#f1f5f9] font-medium line-clamp-1 group-hover:text-amber-300 transition-colors">
                    {it.title}
                  </div>

                  <div className="mt-1 flex items-center justify-between text-[11px]">
                    <span className="text-[10px] text-slate-500">
                      {it.match_reason}
                    </span>
                    {it.starting_price != null && (
                      <span className="font-semibold text-amber-400 tabular-nums">
                        ¥{(it.starting_price >= 10000)
                          ? `${(it.starting_price / 10000).toFixed(1)}万`
                          : it.starting_price.toLocaleString('zh-CN')}
                        {it.discount_rate != null ? ` (${it.discount_rate}折)` : ''}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-2.5 rounded bg-[#161e31] border border-[#1e2638] text-[11px] text-[#64748b]">
              暂未检索到同案号的其他跨平台拍卖或送达流转记录
            </div>
          )}
        </div>

        {/* 业务跟进便签 / 处置备忘录 */}
        <div className="pt-2 border-t border-[#1e2638] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#f1f5f9]">
              标的跟进便签 / 处置备忘录
            </span>
            {saveSuccess && (
              <span className="text-xs text-emerald-400 flex items-center space-x-1">
                <Check className="w-3.5 h-3.5" />
                <span>已保存</span>
              </span>
            )}
          </div>

          {/* 预设状态胶囊快捷栏 */}
          <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
            <span className="text-[11px] text-[#64748b] mr-0.5">快捷标记:</span>
            {PRESET_NOTE_TAGS.map((t) => {
              const active = extractNoteTag(notes) === t.label;
              return (
                <button
                  key={t.label}
                  type="button"
                  onClick={() => handleQuickTagClick(t.label)}
                  title={t.desc}
                  className={`text-[11px] px-2 py-0.5 rounded transition-all duration-100 ${
                    active 
                      ? `${getNoteTagBadgeStyle(t.label)} shadow-xs font-bold` 
                      : 'bg-[#161e31] text-[#94a3b8] border border-[#1e2638] hover:text-[#f1f5f9] hover:bg-[#182238]'
                  }`}
                >
                  {active ? `✓ ${t.label}` : t.label}
                </button>
              );
            })}
          </div>

          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="填写产调情况、评估分析、竞买策略、联系人等跟踪备忘..."
            rows={3}
            className="w-full text-xs p-2.5 rounded-md border border-[#1e2638] bg-[#161e31] text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-amber-400/50 focus:border-amber-400/50 resize-none transition-colors"
          />
          <div className="flex justify-end">
            <button
              onClick={() => handleSaveNotes()}
              disabled={savingNotes}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-[#182238] text-amber-300 border border-amber-500/40 hover:bg-[#1d2a45] disabled:opacity-50 transition-colors"
            >
              {savingNotes ? '保存中...' : '保存备忘'}
            </button>
          </div>
        </div>

        {/* 正文或竞买须知 */}
        <div className="pt-2 border-t border-[#1e2638] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#f1f5f9]">
              {notice.platform === 'local_paper' ? '报刊法治专版刊登全文' : '公告正文 / 标的概况'}
            </span>
            <div className="flex items-center space-x-1.5">
              <button
                onClick={handleCopyBriefing}
                className="flex items-center space-x-1 text-[11px] text-amber-300 hover:text-amber-200 transition-colors px-2 py-0.5 rounded bg-[#182238] border border-amber-500/40"
                title="一键复制微信/钉钉/飞书格式化推荐简报 (快捷键: C)"
              >
                {briefingCopied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400 font-medium">已复制简报</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3 h-3 text-amber-400" />
                    <span>微信简报</span>
                  </>
                )}
              </button>

              <button
                onClick={handleCopyNotice}
                className="flex items-center space-x-1 text-[11px] text-[#94a3b8] hover:text-[#f1f5f9] transition-colors px-2 py-0.5 rounded bg-[#161e31] border border-[#1e2638]"
                title="一键复制公告公文全文"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400 font-medium">已复制全文</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>复制全文</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {notice.platform === 'local_paper' && (
            <div className="p-2.5 rounded bg-blue-950/30 border border-blue-900/50 text-[11px] text-blue-200/90 leading-relaxed flex items-start space-x-2">
              <span className="shrink-0 text-sm">📰</span>
              <div>
                <span>本条公告已由雷达系统从官方数字报全版面解析入库。如需核验排版原件，点击下方直达<strong>【{notice.title.match(/《(.*?)》/)?.[1] || '地方报社'}】官方电子报专版</strong>。</span>
              </div>
            </div>
          )}

          <div className="text-xs text-[#cbd5e1] leading-relaxed whitespace-pre-wrap bg-[#161e31] p-3 rounded-md border border-[#1e2638] max-h-80 overflow-y-auto font-sans selection:bg-amber-500/30">
            {notice.content_text || '暂无详细公告正文'}
          </div>
        </div>

        {/* 底部查看原网大按钮 */}
        <div className="pt-2 space-y-2">
          <a
            href={notice.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`w-full py-2.5 px-4 rounded-md flex items-center justify-center space-x-2 text-xs font-semibold transition-colors ${
              notice.platform === 'local_paper'
                ? 'bg-[#182848] text-amber-300 hover:bg-[#1f345e] border border-amber-500/40 shadow-xs'
                : 'bg-[#1d283f] text-[#60a5fa] hover:bg-[#23324e] border border-[#2b3d60]'
            }`}
          >
            <span>
              {notice.platform === 'local_paper'
                ? `前往《${notice.title.match(/《(.*?)》/)?.[1] || '报社'}》官方电子报专版`
                : '在官方平台查看标的详情与竞买须知'}
            </span>
            <ArrowUpRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    </aside>
  );
}
