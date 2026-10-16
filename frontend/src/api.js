// API client for CourtNoticeRadar

const BASE_URL = '/api';

export async function fetchStats() {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchAlerts(params = {}) {
  const query = new URLSearchParams();
  if (params.unreadOnly) query.append('unread_only', 'true');
  if (params.platform) query.append('platform', params.platform);
  if (params.moduleType) query.append('module_type', params.moduleType);
  if (params.ruleId) query.append('rule_id', params.ruleId);
  if (params.henanOnly) query.append('henan_only', 'true');
  if (params.henanCity) query.append('henan_city', params.henanCity);
  if (params.timeRange) query.append('time_range', params.timeRange);

  const pageNum = params.page || 1;
  const pageSizeNum = params.pageSize || 20;
  query.append('page', pageNum);
  query.append('page_size', pageSizeNum);
  query.append('limit', pageSizeNum);
  query.append('offset', (pageNum - 1) * pageSizeNum);

  const res = await fetch(`${BASE_URL}/alerts?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
}

export async function markAlertRead(alertId) {
  const res = await fetch(`${BASE_URL}/alerts/${alertId}/read`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to mark alert as read');
  return res.json();
}

export async function markAllAlertsRead() {
  const res = await fetch(`${BASE_URL}/alerts/read-all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to mark all alerts as read');
  return res.json();
}

export async function fetchRules() {
  const res = await fetch(`${BASE_URL}/rules`);
  if (!res.ok) throw new Error('Failed to fetch rules');
  return res.json();
}

export async function previewRule(ruleData) {
  const res = await fetch(`${BASE_URL}/rules/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ruleData)
  });
  if (!res.ok) throw new Error('Failed to preview rule matches');
  return res.json();
}

export async function createRule(ruleData) {
  const res = await fetch(`${BASE_URL}/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ruleData)
  });
  if (!res.ok) throw new Error('Failed to create rule');
  return res.json();
}

export async function updateRule(ruleId, ruleData) {
  const res = await fetch(`${BASE_URL}/rules/${ruleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ruleData)
  });
  if (!res.ok) throw new Error('Failed to update rule');
  return res.json();
}

export async function deleteRule(ruleId) {
  const res = await fetch(`${BASE_URL}/rules/${ruleId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete rule');
  return res.json();
}

export async function fetchNotices(params = {}) {
  const query = new URLSearchParams();
  if (params.query) query.append('query', params.query);
  if (params.platform) query.append('platform', params.platform);
  if (params.court) query.append('court', params.court);
  if (params.noticeType) query.append('notice_type', params.noticeType);
  if (params.moduleType) query.append('module_type', params.moduleType);
  if (params.assetCategory) query.append('asset_category', params.assetCategory);
  if (params.henanOnly) query.append('henan_only', 'true');
  if (params.henanCity) query.append('henan_city', params.henanCity);
  if (params.priceMin) query.append('price_min', params.priceMin);
  if (params.priceMax) query.append('price_max', params.priceMax);
  if (params.discountMax) query.append('discount_max', params.discountMax);
  if (params.sortBy) query.append('sort_by', params.sortBy);
  if (params.starredOnly) query.append('starred_only', 'true');
  if (params.timeRange) query.append('time_range', params.timeRange);
  if (params.noteTag) query.append('note_tag', params.noteTag);

  const pageNum = params.page || 1;
  const pageSizeNum = params.pageSize || 20;
  query.append('page', pageNum);
  query.append('page_size', pageSizeNum);
  query.append('limit', pageSizeNum);
  query.append('offset', (pageNum - 1) * pageSizeNum);

  const res = await fetch(`${BASE_URL}/notices?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch notices');
  return res.json();
}

export async function toggleNoticeStar(noticeId) {
  const res = await fetch(`${BASE_URL}/notices/${noticeId}/star`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to toggle notice star');
  return res.json();
}

export async function updateNoticeNotes(noticeId, notes) {
  const res = await fetch(`${BASE_URL}/notices/${noticeId}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes })
  });
  if (!res.ok) throw new Error('Failed to update notice notes');
  return res.json();
}

export async function fetchRelatedNotices(noticeId) {
  const res = await fetch(`${BASE_URL}/notices/${noticeId}/related`);
  if (!res.ok) throw new Error('Failed to fetch related notices');
  return res.json();
}

export async function fetchWebhookSettings() {
  const res = await fetch(`${BASE_URL}/settings/webhook`);
  if (!res.ok) throw new Error('Failed to fetch webhook settings');
  return res.json();
}

export async function saveWebhookSettings(config) {
  const res = await fetch(`${BASE_URL}/settings/webhook`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) throw new Error('Failed to save webhook settings');
  return res.json();
}

export async function testWebhookSettings(config) {
  const res = await fetch(`${BASE_URL}/settings/webhook/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) throw new Error('Failed to test webhook');
  return res.json();
}

export async function fetchPapers(params = {}) {
  const query = new URLSearchParams();
  if (params.province) query.append('province', params.province);
  if (params.monitoredOnly) query.append('monitored_only', 'true');
  if (params.query) query.append('query', params.query);
  if (params.limit) query.append('limit', params.limit);
  if (params.offset) query.append('offset', params.offset);

  const res = await fetch(`${BASE_URL}/papers?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch papers');
  return res.json();
}

export async function togglePaperMonitor(paperId) {
  const res = await fetch(`${BASE_URL}/papers/${paperId}/toggle-monitor`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to toggle paper monitor');
  return res.json();
}

export async function sync53bkPapers() {
  const res = await fetch(`${BASE_URL}/papers/sync-53bk`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to sync 53bk papers');
  return res.json();
}

export async function fetchTaskLogs() {
  const res = await fetch(`${BASE_URL}/tasks`);
  if (!res.ok) throw new Error('Failed to fetch task logs');
  return res.json();
}

export async function runCrawlTask(platform) {
  const res = await fetch(`${BASE_URL}/tasks/run?platform=${platform}`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger task');
  return res.json();
}

export async function runAllCrawlTasks() {
  const res = await fetch(`${BASE_URL}/tasks/run-all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger all tasks');
  return res.json();
}

export async function cleanHistoricalData(days = 7) {
  const res = await fetch(`${BASE_URL}/maintenance/clean-historical?days=${days}`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to clean historical data');
  return res.json();
}

export async function aliManualVerify() {
  const res = await fetch(`${BASE_URL}/crawlers/ali/manual-verify`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger Ali manual verify');
  return res.json();
}

export async function triggerCountdownCheck() {
  const res = await fetch(`${BASE_URL}/alerts/countdown/check`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger countdown check');
  return res.json();
}

