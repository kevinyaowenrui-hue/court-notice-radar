import React, { useState, useEffect } from 'react';
import { Send, Check, X, ShieldAlert, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchWebhookSettings, saveWebhookSettings, testWebhookSettings } from '../api';

const PLATFORM_OPTIONS = [
  { id: 'wecom', label: '企业微信群机器人', tip: '需以 https://qyapi.weixin.qq.com 开头' },
  { id: 'dingtalk', label: '钉钉群机器人', tip: '需以 https://oapi.dingtalk.com 开头' },
  { id: 'feishu', label: '飞书群机器人', tip: '需以 https://open.feishu.cn 开头' },
  { id: 'generic', label: '自定义 HTTP Webhook', tip: '接收标准 JSON POST 报警数据' }
];

export default function WebhookModal({ isOpen, onClose }) {
  const [enabled, setEnabled] = useState(false);
  const [platform, setPlatform] = useState('wecom');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    const loadConfig = async () => {
      setLoading(true);
      setTestResult(null);
      try {
        const cfg = await fetchWebhookSettings();
        setEnabled(cfg.enabled || false);
        setPlatform(cfg.platform || 'wecom');
        setWebhookUrl(cfg.webhook_url || '');
        setSecret(cfg.secret || '');
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadConfig();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTest = async () => {
    if (!webhookUrl.trim()) {
      setTestResult({ status: 'error', message: '请先填写 Webhook 机器人地址' });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testWebhookSettings({
        enabled,
        platform,
        webhook_url: webhookUrl.trim(),
        secret: secret.trim()
      });
      setTestResult(res);
    } catch (err) {
      setTestResult({ status: 'error', message: err.message || '请求测试失败' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await saveWebhookSettings({
        enabled,
        platform,
        webhook_url: webhookUrl.trim(),
        secret: secret.trim(),
        notify_on_new: true
      });
      onClose();
    } catch (err) {
      setTestResult({ status: 'error', message: err.message || '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
      <div className="bg-[#0f172a] border border-slate-700 rounded-xl max-w-lg w-full flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-800/80 text-cyan-400">
              <Send className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-sm">外部群机器人实时预警推送</h3>
              <p className="text-[11px] text-slate-400">增量采集命中监控规则时，无需开着网页即刻推入群聊</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs">加载配置中...</div>
        ) : (
          <form onSubmit={handleSave} className="p-5 space-y-4 text-xs">
            {/* Enable switch */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
              <div>
                <span className="font-bold text-slate-200 block">启用外部机器人推送</span>
                <span className="text-[11px] text-slate-400">调度巡检命中涉豫或关键规则时自动触发发送</span>
              </div>
              <button
                type="button"
                onClick={() => setEnabled(!enabled)}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
                  enabled ? 'bg-cyan-600 justify-end' : 'bg-slate-700 justify-start'
                }`}
              >
                <div className="bg-white w-4 h-4 rounded-full shadow-md"></div>
              </button>
            </div>

            {/* Platform selection */}
            <div>
              <label className="block text-slate-300 font-semibold mb-1">推送机器人渠道</label>
              <div className="grid grid-cols-2 gap-2">
                {PLATFORM_OPTIONS.map((p) => {
                  const isSel = platform === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setPlatform(p.id)}
                      className={`p-2.5 rounded-lg text-left border transition-all ${
                        isSel
                          ? 'bg-cyan-950/60 border-cyan-500 text-cyan-200 font-semibold'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                      }`}
                    >
                      <div className="text-xs">{p.label}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5 truncate">{p.tip}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Webhook URL */}
            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Webhook 机器人完整地址 (URL) *
              </label>
              <input
                type="url"
                required={enabled}
                placeholder={
                  platform === 'wecom'
                    ? 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...'
                    : platform === 'dingtalk'
                    ? 'https://oapi.dingtalk.com/robot/send?access_token=...'
                    : platform === 'feishu'
                    ? 'https://open.feishu.cn/open-apis/bot/v2/hook/...'
                    : 'https://your-api.com/webhook'
                }
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 font-mono text-[11px] focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Secret (Optional for DingTalk & Feishu) */}
            {(platform === 'dingtalk' || platform === 'feishu') && (
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  加签密钥 (Secret · 可选)
                </label>
                <input
                  type="password"
                  placeholder="如机器人安全设置开启了加签，请填入密钥 SEC..."
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 font-mono text-[11px] focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}

            {/* Test Feedback Area */}
            {testResult && (
              <div
                className={`p-3 rounded-lg border text-xs flex items-start space-x-2 ${
                  testResult.status === 'success'
                    ? 'bg-emerald-950/50 border-emerald-700 text-emerald-300'
                    : 'bg-rose-950/50 border-rose-700 text-rose-300'
                }`}
              >
                {testResult.status === 'success' ? (
                  <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                )}
                <div className="leading-relaxed break-all">
                  {testResult.message}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
              <button
                type="button"
                onClick={handleTest}
                disabled={testing || !webhookUrl.trim()}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs font-semibold disabled:opacity-50 transition-colors flex items-center space-x-1.5"
              >
                {testing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>{testing ? '测试发送中...' : '发送测试预警卡片'}</span>
              </button>

              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold"
                >
                  {saving ? '保存中...' : '保存配置'}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
