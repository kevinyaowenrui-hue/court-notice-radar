import React, { useState, useEffect } from 'react';
import { ShieldCheck, Plus, Trash2, Edit3, Check, X, Bell, Eye, Ban, MapPin, Layers, Sparkles } from 'lucide-react';
import { fetchRules, createRule, updateRule, deleteRule, previewRule } from '../api';

const ALL_PLATFORMS = [
  { id: 'ali', label: '阿里法拍' },
  { id: 'jd', label: '京东拍卖' },
  { id: 'rmfysszc', label: '人民法院诉讼资产网' },
  { id: 'rmfyb', label: '《人民法院报》公告网' },
  { id: 'local_paper', label: '53BK 地方报纸专版' },
  { id: 'caa', label: '中拍平台·信息公示' },
  { id: 'ggzy', label: '公共资源交易·全省产权交易' }
];

const ALL_MODULES = [
  { id: '公告', label: '📢 法定公告' },
  { id: '拍卖公告', label: '🔨 资产与法拍' },
  { id: '债权转让', label: '💼 债权资产包' }
];

const PRESET_CITIES = [
  '全省', '郑州', '洛阳', '开封', '平顶山', '安阳', '鹤壁',
  '新乡', '焦作', '濮阳', '许昌', '漯河', '三门峡', '南阳',
  '商丘', '信阳', '周口', '驻马店', '济源'
];

export default function RulesManager() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);

  // Form State
  const [name, setName] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [platforms, setPlatforms] = useState(['ali', 'jd', 'rmfysszc', 'rmfyb', 'local_paper', 'caa', 'ggzy']);
  const [selectedModules, setSelectedModules] = useState([]);
  const [selectedCities, setSelectedCities] = useState([]);
  const [courtsInput, setCourtsInput] = useState('');
  const [partiesInput, setPartiesInput] = useState('');
  const [caseNosInput, setCaseNosInput] = useState('');
  const [keywordsInput, setKeywordsInput] = useState('');
  const [excludeKeywordsInput, setExcludeKeywordsInput] = useState('');
  const [priceMin, setPriceMin] = useState('');
  const [priceMax, setPriceMax] = useState('');
  const [notifyBrowser, setNotifyBrowser] = useState(true);
  const [backfill, setBackfill] = useState(false);

  // Preview State
  const [previewData, setPreviewData] = useState(null);
  const [isPreviewing, setIsPreviewing] = useState(false);

  const loadRules = async () => {
    setLoading(true);
    try {
      const data = await fetchRules();
      setRules(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  const openCreateModal = () => {
    setEditingRule(null);
    setName('');
    setIsActive(true);
    setPlatforms(['ali', 'jd', 'rmfysszc', 'rmfyb', 'local_paper', 'caa', 'ggzy']);
    setSelectedModules([]);
    setSelectedCities([]);
    setCourtsInput('');
    setPartiesInput('');
    setCaseNosInput('');
    setKeywordsInput('');
    setExcludeKeywordsInput('');
    setPriceMin('');
    setPriceMax('');
    setNotifyBrowser(true);
    setBackfill(false);
    setPreviewData(null);
    setModalOpen(true);
  };

  const openEditModal = (r) => {
    setEditingRule(r);
    setName(r.name);
    setIsActive(r.is_active);
    setPlatforms(r.platforms || []);
    setSelectedModules(r.module_types || []);
    setSelectedCities(r.cities || []);
    setCourtsInput((r.courts || []).join(', '));
    setPartiesInput((r.parties || []).join(', '));
    setCaseNosInput((r.case_numbers || []).join(', '));
    setKeywordsInput((r.keywords || []).join(', '));
    setExcludeKeywordsInput((r.exclude_keywords || []).join(', '));
    setPriceMin(r.price_min != null ? r.price_min : '');
    setPriceMax(r.price_max != null ? r.price_max : '');
    setNotifyBrowser(r.notify_browser);
    setBackfill(false);
    setPreviewData(null);
    setModalOpen(true);
  };

  const getPayload = () => ({
    name: name.trim(),
    is_active: isActive,
    platforms,
    module_types: selectedModules,
    cities: selectedCities,
    courts: courtsInput.split(/[,，\n]/).map(s => s.trim()).filter(Boolean),
    parties: partiesInput.split(/[,，\n]/).map(s => s.trim()).filter(Boolean),
    case_numbers: caseNosInput.split(/[,，\n]/).map(s => s.trim()).filter(Boolean),
    keywords: keywordsInput.split(/[,，\n]/).map(s => s.trim()).filter(Boolean),
    exclude_keywords: excludeKeywordsInput.split(/[,，\n]/).map(s => s.trim()).filter(Boolean),
    price_min: priceMin ? parseFloat(priceMin) : null,
    price_max: priceMax ? parseFloat(priceMax) : null,
    notify_browser: notifyBrowser,
    backfill
  });

  const handlePreview = async () => {
    setIsPreviewing(true);
    try {
      const data = await previewRule(getPayload());
      setPreviewData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    const payload = getPayload();

    try {
      if (editingRule) {
        await updateRule(editingRule.id, payload);
      } else {
        await createRule(payload);
      }
      setModalOpen(false);
      loadRules();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('确定要删除该监控规则吗？')) return;
    try {
      await deleteRule(id);
      loadRules();
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleActive = async (r) => {
    try {
      await updateRule(r.id, {
        name: r.name,
        is_active: !r.is_active,
        platforms: r.platforms || [],
        module_types: r.module_types || [],
        cities: r.cities || [],
        courts: r.courts || [],
        parties: r.parties || [],
        case_numbers: r.case_numbers || [],
        keywords: r.keywords || [],
        exclude_keywords: r.exclude_keywords || [],
        price_min: r.price_min,
        price_max: r.price_max,
        notify_browser: r.notify_browser,
        backfill: false
      });
      loadRules();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Add Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
            <span>智能监控与预警规则管理</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            配置关注的法院、特定债务人企业、案号前缀或标的物关键词，增量抓取时将自动触发匹配并推入预警中心
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors shadow-md shadow-blue-500/10"
        >
          <Plus className="w-4 h-4" />
          <span>新建监控规则</span>
        </button>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full py-12 text-center text-slate-400 text-sm">
            加载监控规则中...
          </div>
        ) : rules.length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-400 bg-[#0f172a] border border-slate-800 rounded-xl">
            暂无监控规则，请点击右上角新建规则
          </div>
        ) : (
          rules.map((r) => (
            <div
              key={r.id}
              className={`bg-[#0f172a] border rounded-xl p-5 flex flex-col justify-between transition-all ${
                r.is_active ? 'border-slate-800 hover:border-slate-700' : 'border-slate-800/50 opacity-60'
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-100 text-sm">{r.name}</h3>
                  <button
                    onClick={() => handleToggleActive(r)}
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                      r.is_active
                        ? 'bg-emerald-950/60 text-emerald-400 border-emerald-700/60'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    {r.is_active ? '监控中' : '已暂停'}
                  </button>
                </div>

                {/* Platforms, Modules & Cities Tags */}
                <div className="mt-3 flex flex-wrap gap-1">
                  {(r.platforms || []).map((p) => {
                    const labelMap = {
                      ali: '阿里法拍',
                      jd: '京东拍卖',
                      rmfysszc: '诉讼资产网',
                      rmfyb: '法院报',
                      local_paper: '地方报',
                      caa: '中拍平台',
                      ggzy: '公共资源'
                    };
                    return (
                      <span key={p} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                        {labelMap[p] || p}
                      </span>
                    );
                  })}
                  {(r.module_types || []).map((m) => (
                    <span key={m} className="px-1.5 py-0.5 rounded bg-indigo-950/60 border border-indigo-700/60 text-[10px] text-indigo-300">
                      {m}
                    </span>
                  ))}
                  {(r.cities || []).map((c) => (
                    <span key={c} className="px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-700/60 text-[10px] text-emerald-300">
                      📍 {c}
                    </span>
                  ))}
                </div>

                {/* Condition tags */}
                <div className="mt-3 space-y-2 text-xs">
                  {r.parties?.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">当事人/债务人:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {r.parties.map((p, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 rounded bg-blue-950/60 border border-blue-800/60 text-blue-300 text-[11px]">
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {r.courts?.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">法院关键词:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {r.courts.map((c, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 text-[11px]">
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {r.keywords?.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">全文/标的关键词:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {r.keywords.map((kw, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/60 text-amber-300 text-[11px]">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {r.exclude_keywords?.length > 0 && (
                    <div>
                      <span className="text-rose-400/90 font-medium flex items-center space-x-1">
                        <Ban className="w-3 h-3 text-rose-400 inline" />
                        <span>排除词 (一票否决):</span>
                      </span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {r.exclude_keywords.map((ex, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 rounded bg-rose-950/50 border border-rose-800/60 text-rose-300 text-[11px]">
                            {ex}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {(r.price_min != null || r.price_max != null) && (
                    <div className="text-[11px] text-slate-400">
                      价格限制: {r.price_min != null ? `≥ ¥${r.price_min.toLocaleString()}` : ''} {r.price_max != null ? `≤ ¥${r.price_max.toLocaleString()}` : ''}
                    </div>
                  )}
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>创建于 {r.created_at}</span>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => openEditModal(r)}
                    className="p-1 text-slate-400 hover:text-blue-400"
                    title="编辑规则"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(r.id)}
                    className="p-1 text-slate-400 hover:text-rose-400"
                    title="删除规则"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create / Edit Rule Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
          <div className="bg-[#0f172a] border border-slate-700 rounded-xl max-w-xl w-full max-h-[90vh] flex flex-col shadow-2xl">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <h3 className="font-bold text-slate-100 text-sm">
                {editingRule ? '编辑监控规则' : '创建新监控规则'}
              </h3>
              <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleSave} className="p-5 overflow-y-auto space-y-4 text-xs">
              {/* Henan Quick Preset Templates */}
              <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-600/40 flex flex-wrap items-center justify-between gap-1.5">
                <span className="text-[11px] text-amber-300 font-bold flex items-center space-x-1">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span>快速填入河南专属监控预设:</span>
                </span>
                <div className="flex gap-1.5 flex-wrap">
                  <button
                    type="button"
                    onClick={() => {
                      setName("郑州市金水区优质法拍房雷达");
                      setSelectedModules(["拍卖公告"]);
                      setSelectedCities(["郑州"]);
                      setCourtsInput("金水区人民法院, 郑州市中级人民法院");
                      setKeywordsInput("住宅, 公寓, 写字楼");
                      setExcludeKeywordsInput("车位, 储藏室, 废旧, 杂物间");
                      setPlatforms(["ali", "jd", "caa"]);
                    }}
                    className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700 hover:bg-slate-700 text-[10px]"
                  >
                    郑州金水房产
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setName("涉豫大额金融不良债权与资产包招商");
                      setSelectedModules(["债权转让"]);
                      setSelectedCities(["全省"]);
                      setCourtsInput("");
                      setKeywordsInput("债权, 不良资产, 抵押, 资产包");
                      setExcludeKeywordsInput("");
                      setPlatforms(["caa", "ggzy"]);
                    }}
                    className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700 hover:bg-slate-700 text-[10px]"
                  >
                    涉豫债权资产包
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setName("河南重点法院企业破产清算与重组预警");
                      setSelectedModules(["公告"]);
                      setSelectedCities(["郑州", "洛阳"]);
                      setCourtsInput("河南省高级人民法院, 郑州市中级人民法院, 洛阳市中级人民法院, 金水区人民法院");
                      setCaseNosInput("破, 清, 重");
                      setKeywordsInput("破产, 重整, 债权申报, 清算, 重组");
                      setExcludeKeywordsInput("注销公告, 减资公告");
                      setPlatforms(["rmfyb", "local_paper"]);
                    }}
                    className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700 hover:bg-slate-700 text-[10px]"
                  >
                    重点法院破产
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">规则名称 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 郑州金水区法拍住宅重点跟踪"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Module Filter */}
              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center space-x-1">
                  <Layers className="w-3.5 h-3.5 text-blue-400" />
                  <span>业务分类限定 (留空表示不限)</span>
                </label>
                <div className="grid grid-cols-3 gap-2 mt-1">
                  {ALL_MODULES.map(m => {
                    const checked = selectedModules.includes(m.id);
                    return (
                      <label key={m.id} className="flex items-center space-x-2 p-2 rounded bg-slate-900 border border-slate-800 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedModules([...selectedModules, m.id]);
                            else setSelectedModules(selectedModules.filter(x => x !== m.id));
                          }}
                          className="rounded text-blue-600"
                        />
                        <span className="text-slate-200">{m.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* City Filter */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-slate-300 font-semibold flex items-center space-x-1">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                    <span>涉豫地市定向 (留空表示全省/全国不限)</span>
                  </label>
                  <span className="text-[10px] text-slate-400">点击标签切换</span>
                </div>
                <div className="flex flex-wrap gap-1.5 p-2 rounded-lg bg-slate-900 border border-slate-800">
                  {PRESET_CITIES.map(c => {
                    const isSel = selectedCities.includes(c);
                    return (
                      <button
                        key={c}
                        type="button"
                        onClick={() => {
                          if (isSel) {
                            setSelectedCities(selectedCities.filter(x => x !== c));
                          } else {
                            if (c === '全省') setSelectedCities(['全省']);
                            else setSelectedCities([...selectedCities.filter(x => x !== '全省'), c]);
                          }
                        }}
                        className={`px-2.5 py-1 rounded text-xs transition-colors ${
                          isSel
                            ? 'bg-emerald-600 text-white font-medium shadow-sm'
                            : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                        }`}
                      >
                        {c}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Data Platforms */}
              <div>
                <label className="block text-slate-300 font-semibold mb-1">监控数据渠道</label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {ALL_PLATFORMS.map(p => {
                    const checked = platforms.includes(p.id);
                    return (
                      <label key={p.id} className="flex items-center space-x-2 p-2 rounded bg-slate-900 border border-slate-800 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            if (e.target.checked) setPlatforms([...platforms, p.id]);
                            else setPlatforms(platforms.filter(x => x !== p.id));
                          }}
                          className="rounded text-blue-600"
                        />
                        <span className="text-slate-300">{p.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Exclude Keywords */}
              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center space-x-1">
                  <Ban className="w-3.5 h-3.5 text-rose-400" />
                  <span className="text-rose-300">排除关键词 (一票否决，出现即过滤，多个逗号隔开)</span>
                </label>
                <input
                  type="text"
                  placeholder="如: 车位, 储藏室, 废旧, 注销公告"
                  value={excludeKeywordsInput}
                  onChange={(e) => setExcludeKeywordsInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-rose-950/80 focus:border-rose-500 text-slate-100 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  当事人 / 债务人姓名或企业名称 (多个用逗号隔开)
                </label>
                <input
                  type="text"
                  placeholder="如: 华盛, 创智领航, 李某某"
                  value={partiesInput}
                  onChange={(e) => setPartiesInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  执行法院关键词 (多个用逗号隔开)
                </label>
                <input
                  type="text"
                  placeholder="如: 西湖区, 郑州市中级人民法院"
                  value={courtsInput}
                  onChange={(e) => setCourtsInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  标的物名称 / 公告全文关键词 (多个用逗号隔开)
                </label>
                <input
                  type="text"
                  placeholder="如: 住宅, 股权, 采矿权, 破产清算"
                  value={keywordsInput}
                  onChange={(e) => setKeywordsInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  案号关键词 / 前缀 (如: (2026)豫01, 破申)
                </label>
                <input
                  type="text"
                  placeholder="如: 执892, 破申, 破"
                  value={caseNosInput}
                  onChange={(e) => setCaseNosInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">法拍起拍价最低 (元)</label>
                  <input
                    type="number"
                    placeholder="不限"
                    value={priceMin}
                    onChange={(e) => setPriceMin(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">法拍起拍价最高 (元)</label>
                  <input
                    type="number"
                    placeholder="不限"
                    value={priceMax}
                    onChange={(e) => setPriceMax(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Preview Panel */}
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Eye className="w-4 h-4 text-cyan-400" />
                    <span className="font-semibold text-slate-200">规则试运行命中测算</span>
                  </div>
                  <button
                    type="button"
                    onClick={handlePreview}
                    disabled={isPreviewing}
                    className="px-3 py-1 rounded bg-cyan-700/60 hover:bg-cyan-600 text-cyan-100 text-xs font-semibold flex items-center space-x-1"
                  >
                    {isPreviewing ? '测算中...' : '试运行匹配预览'}
                  </button>
                </div>
                {previewData && (
                  <div className="mt-2 text-xs border-t border-slate-800 pt-2 space-y-1.5">
                    <div className="flex items-center justify-between text-slate-300">
                      <span>全库 370+ 条存量测算结果:</span>
                      <span className="font-bold text-cyan-400">
                        预计命中 {previewData.matched_count} 条
                      </span>
                    </div>
                    {previewData.samples?.length > 0 && (
                      <div className="space-y-1 pt-1">
                        <span className="text-[10px] text-slate-400">采样命中样例:</span>
                        {previewData.samples.map(s => (
                          <div key={s.id} className="p-1.5 rounded bg-slate-950/80 border border-slate-800/80 text-[11px] text-slate-300 truncate">
                            <span className="text-blue-400 font-medium mr-1.5">[{s.module_type || '公示'}]</span>
                            {s.title}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Backfill Checkbox */}
              <label className="flex items-center space-x-2 p-2.5 rounded bg-blue-950/30 border border-blue-900/40 cursor-pointer">
                <input
                  type="checkbox"
                  checked={backfill}
                  onChange={(e) => setBackfill(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="text-slate-300 text-xs font-medium">
                  保存后立即对当前数据库 370+ 条存量数据进行回溯扫描并生成预警
                </span>
              </label>

              <div className="p-4 border-t border-slate-800 flex justify-end space-x-2 pt-4">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold"
                >
                  保存规则
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
