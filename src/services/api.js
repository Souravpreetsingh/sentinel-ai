const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

const delay = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

function toTime(iso) {
  if (!iso) return '--:--:--';
  return new Date(iso).toLocaleTimeString([], { hour12: false });
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** i;
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function extOf(filePath) {
  const name = String(filePath || '').split(/[\\/]/).pop() || '';
  const idx = name.lastIndexOf('.');
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : '';
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (err) {
    throw new Error(
      `Cannot reach SENTINEL backend at ${API_BASE_URL} (${err.message || 'network error'}). Is the server running?`
    );
  }
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      const detail = body?.detail;
      if (typeof detail === 'string') message = detail;
      else if (detail?.message) message = detail.message;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`API ${res.status}: ${message}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function toJSONHeader() {
  return { 'Content-Type': 'application/json' };
}

// ---------------------------------------------------------------------------
// Transforms: backend snake_case -> page camelCase
// ---------------------------------------------------------------------------

export function transformCamera(raw) {
  const detections = raw.detections || {};
  return {
    id: raw.id,
    name: raw.name,
    sector: raw.sector || '—',
    location: raw.location || '',
    status: raw.status || 'offline',
    fps: raw.fps || 0,
    resolution: raw.resolution || '—',
    type: raw.type || 'visual',
    aiEnabled: raw.ai_enabled,
    aiCapabilities: raw.ai_capabilities || [],
    detections: {
      people: detections.people || 0,
      vehicles: detections.vehicles || 0,
      motorcycles: detections.motorcycles || 0,
    },
    streamUrl: raw.stream_url || 'rtsp://sentinel.internal:554/feed',
    lastSeen: raw.last_seen || raw.updated_at,
    health: raw.health ?? 0,
    bitrate: raw.bitrate ?? 0,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export function transformIncident(raw) {
  const metadata = raw.metadata_json || {};
  const timestamp = raw.detected_at || raw.created_at;
  const confidencePct = Math.round((raw.confidence || 0) * 1000) / 10;
  const timeline = Array.isArray(metadata.timeline) && metadata.timeline.length > 0
    ? metadata.timeline
    : [
        {
          time: toTime(timestamp),
          event: raw.description || `${raw.type} automatically detected${raw.location ? ` at ${raw.location}` : ''} by the CV pipeline.`,
          type: 'system',
        },
      ];
  return {
    id: raw.id,
    type: raw.type,
    severity: raw.severity || 'medium',
    status: raw.status || 'open',
    cameraId: raw.camera_id,
    location: raw.location || '—',
    timestamp,
    duration: raw.duration,
    assignedOfficer: raw.assigned_to,
    badgeNumber: metadata.badge_number || null,
    confidence: confidencePct,
    description: raw.description || '',
    geoCoords: metadata.geo_coords || metadata.coords || null,
    hash: metadata.hash ? `SHA256: ${metadata.hash}` : null,
    timeline,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export function transformEvidence(raw) {
  const ext = extOf(raw.file_path);
  const label = ext ? { jpg: 'JPEG', jpeg: 'JPEG', png: 'PNG', webp: 'WEBP', mp4: 'MP4', mov: 'MOV', avi: 'AVI', mkv: 'MKV', wav: 'WAV', mp3: 'MP3', aac: 'AAC', json: 'JSON', txt: 'TXT' }[ext] || ext.toUpperCase() : 'FILE';
  const title = raw.title || String(raw.file_path).split(/[\\/]/).pop() || raw.id;
  return {
    id: raw.id,
    incidentId: raw.incident_id,
    cameraId: raw.camera_id,
    type: raw.type,
    title,
    duration: raw.type === 'video_clip' ? null : null,
    timestamp: raw.captured_at,
    fileSize: formatBytes(raw.file_size),
    format: `${label} / FILE`,
    hash: `SHA256: ${raw.hash}`,
    status: raw.verification_status, // verified | pending | flagged
    officer: raw.officer,
    tags: [raw.type, ext || 'file'],
    fileUrl: `${API_BASE_URL}/evidence/${raw.id}/file`,
    createdAt: raw.created_at,
  };
}

function normalizeServiceStatus(status) {
  if (status === 'active' || status === 'connected' || status === 'ok' || status === 'healthy') return 'connected';
  if (status === 'degraded' || status === 'warning') return 'degraded';
  return 'warning';
}

export function transformHealth(raw, overview = null, cameras = []) {
  const services = [];
  if (raw.ai_engine) {
    const ae = raw.ai_engine;
    const detail = ae.detail || {};
    services.push({
      name: `AI Engine · ${ae.backend || 'auto'} / ${ae.model || 'yolo'}`.toUpperCase(),
      status: normalizeServiceStatus(ae.status),
      latency: detail.inference_ms != null ? `${detail.inference_ms}ms` : (ae.yolo_status?.[0] === 'error' ? 'model missing' : '—'),
    });
  }
  if (raw.video_processing) {
    const vp = raw.video_processing;
    const detail = vp.detail || {};
    services.push({
      name: 'Video Processing',
      status: normalizeServiceStatus(vp.status),
      latency: detail.average_inference_ms != null || vp.average_inference_ms != null ? `${vp.average_inference_ms ?? detail.average_inference_ms}ms` : '—',
    });
  }
  if (raw.database) {
    const db = raw.database;
    const detail = db.detail || {};
    services.push({
      name: `Database · ${db.engine || detail.engine || raw.database }`,
      status: normalizeServiceStatus(db.status),
      latency: detail.latency_ms != null ? `${detail.latency_ms}ms` : '—',
    });
  }
  if (raw.websocket) {
    const ws = raw.websocket;
    const detail = ws.detail || {};
    const clients = ws.clients ?? detail.clients ?? 0;
    services.push({
      name: 'WebSocket Server',
      status: normalizeServiceStatus(ws.status),
      latency: `${clients} client${clients === 1 ? '' : 's'}`,
    });
  }
  if (raw.storage) {
    const st = raw.storage;
    services.push({
      name: 'Object Storage',
      status: normalizeServiceStatus(st.status),
      latency: `${st.percent ?? 0}% used`,
    });
  }
  if (raw.cpu) {
    services.push({ name: 'CPU', status: 'connected', latency: `${raw.cpu.percent ?? 0}% used` });
  }
  if (raw.memory) {
    services.push({ name: 'Memory', status: 'connected', latency: `${raw.memory.percent ?? 0}% used` });
  }

  const connectedCount = services.filter((s) => s.status === 'connected').length;
  const overall = services.length === 0
    ? 0
    : Math.max(0, Math.min(100, Math.round((connectedCount / services.length) * 90 + (raw.fps > 0 ? 8 : 0) + (raw.latency <= 40 ? 2 : 0))));

  const gpu = raw.gpu || {};
  const usedGb = raw.memory?.used_gb ?? 0;
  const totalGb = raw.memory?.total_gb ?? 0;

  const totalCameras = overview?.camerasTotal ?? cameras.length;
  const onlineCameras = overview?.camerasOnline ?? cameras.filter((c) => c.status === 'online').length;
  const offlineCameras = Math.max(totalCameras - onlineCameras, 0);

  const resolutionOf = (c) => (c.resolution || '').toLowerCase();
  const bitrateOf = (c) => c.bitrate || 0;
  const sumBitrate = (pred) => cameras.filter(pred).reduce((s, c) => s + bitrateOf(c), 0);
  const streams4k = Math.round(sumBitrate((c) => resolutionOf(c).includes('4k') || resolutionOf(c).includes('2160p')) * 10) / 10;
  const streams1080p = Math.round(sumBitrate((c) => resolutionOf(c).includes('1080p')) * 10) / 10;
  const streams720p = Math.round(sumBitrate((c) => resolutionOf(c).includes('720p')) * 10) / 10;

  const bandwidth = {
    total: Math.round(cameras.reduce((s, c) => s + bitrateOf(c), 0) * 10) / 10,
    streams1080p,
    streams4k,
    streams720p,
    alerts: 0,
    segments: [
      { label: '4K', value: streams4k },
      { label: '1080P', value: streams1080p },
      { label: '720P', value: streams720p },
      { label: 'ALERTS', value: 0 },
    ].filter((s) => s.value > 0),
  };
  if (bandwidth.segments.length === 0 && cameras.length > 0) {
    bandwidth.segments = [{ label: 'UNMAPPED', value: bandwidth.total }];
  }

  return {
    overall,
    uptime: raw.uptime || '—',
    fps: raw.fps || raw.video_processing?.fps || 0,
    latency: raw.latency || 0,
    packetLoss: raw.packet_loss || 0,
    totalCameras,
    onlineCameras,
    offlineCameras,
    services,
    networkBandwidth: bandwidth,
    gpu: {
      name: gpu.name || 'GPU',
      vram: gpu.vram || (gpu.available ? '—' : 'N/A'),
      temperature: gpu.temperature ?? 0,
      utilization: gpu.utilization ?? 0,
      power: gpu.power || '—',
    },
    storage: {
      total: `${totalGb || raw.storage?.total_gb || 0} GB`,
      used: `${usedGb || raw.storage?.used_gb || 0} GB`,
      percentage: raw.storage?.percent || 0,
    },
    raw,
  };
}

function transformAnalytics(raw) {
  const topEventTypes = (raw.topEventTypes || raw.top_event_types || []).map((e) => ({
    type: e.type || e.category || 'Unknown',
    count: e.count || 0,
  }));
  return {
    ...raw,
    peopleDetected: raw.peopleDetected ?? raw.people_detected ?? 0,
    vehiclesDetected: raw.vehiclesDetected ?? raw.vehicles_detected ?? 0,
    events: raw.events ?? 0,
    criticalIncidents: raw.criticalIncidents ?? raw.critical_incidents ?? 0,
    openIncidents: raw.openIncidents ?? raw.open_incidents ?? 0,
    camerasOnline: raw.camerasOnline ?? raw.cameras_online ?? 0,
    camerasTotal: raw.camerasTotal ?? raw.cameras_total ?? 0,
    eventCategories: raw.eventCategories || raw.event_categories || [],
    topEventTypes,
    aiModelPerformance: raw.aiModelPerformance || raw.ai_model_performance || {},
  };
}

// ---------------------------------------------------------------------------
// API service functions
// ---------------------------------------------------------------------------

export async function getCameras() {
  const list = await request('/cameras');
  return (list || []).map(transformCamera);
}

export async function getCamera(id) {
  const raw = await request(`/cameras/${encodeURIComponent(id)}`);
  return raw ? transformCamera(raw) : null;
}

export async function getIncidents(filters = {}) {
  const params = new URLSearchParams();
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.status) params.set('status', filters.status);
  if (filters.cameraId) params.set('camera_id', filters.cameraId);
  if (filters.limit) params.set('limit', String(filters.limit));
  const qs = params.toString();
  const list = await request(`/incidents${qs ? `?${qs}` : ''}`);
  return (list || []).map(transformIncident);
}

export async function getIncident(id) {
  const raw = await request(`/incidents/${encodeURIComponent(id)}`);
  return raw ? transformIncident(raw) : null;
}

export async function updateIncident(id, updates = {}) {
  const body = {};
  const mapping = {
    cameraId: 'camera_id',
    assignedOfficer: 'assigned_to',
    severity: 'severity',
    status: 'status',
    type: 'type',
    description: 'description',
    confidence: 'confidence',
    location: 'location',
  };
  Object.entries(updates).forEach(([key, value]) => {
    const wire = mapping[key] || key;
    if (value !== undefined) body[wire] = value;
  });
  const raw = await request(`/incidents/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: toJSONHeader(),
    body: JSON.stringify(body),
  });
  return raw ? transformIncident(raw) : null;
}

export async function getAnalytics() {
  const raw = await request('/analytics/overview');
  return transformAnalytics(raw || {});
}

export async function getEvidence(filters = {}) {
  const params = new URLSearchParams();
  if (filters.incidentId) params.set('incident_id', filters.incidentId);
  if (filters.cameraId) params.set('camera_id', filters.cameraId);
  if (filters.status) params.set('status', filters.status);
  const qs = params.toString();
  const list = await request(`/evidence${qs ? `?${qs}` : ''}`);
  return (list || []).map(transformEvidence);
}

export async function getSystemHealth() {
  const [health, overview, cameras] = await Promise.allSettled([
    request('/system/health'),
    getAnalytics(),
    getCameras(),
  ]);
  const healthData = health.status === 'fulfilled' ? health.value : {};
  const overviewData = overview.status === 'fulfilled' ? overview.value : {};
  const camerasData = cameras.status === 'fulfilled' ? cameras.value : [];
  return transformHealth(healthData, overviewData, camerasData);
}

export async function uploadVideo(file, cameraId = null) {
  const form = new FormData();
  form.append('file', file);
  if (cameraId) form.append('camera_id', cameraId);
  const raw = await request('/video/upload', { method: 'POST', body: form });
  return raw
    ? { videoId: raw.video_id, filename: raw.filename, size: raw.size, status: raw.status }
    : null;
}

export async function analyzeVideo(videoId, cameraId = null) {
  const form = new FormData();
  if (cameraId) form.append('camera_id', cameraId);
  const raw = await request(`/video/${encodeURIComponent(videoId)}/analyze`, { method: 'POST', body: form });
  return raw ? { videoId: raw.video_id, status: raw.status } : null;
}

// ---------------------------------------------------------------------------
// Assistant — queries the live backend data.
// ---------------------------------------------------------------------------

async function getIncidentData() {
  try {
    return await getIncidents();
  } catch {
    return [];
  }
}

async function getCameraData() {
  try {
    return await getCameras();
  } catch {
    return [];
  }
}

function formatIncidentLine(incident) {
  return `${incident.id} · ${incident.type} · ${incident.location} (${incident.severity})`;
}

function buildIncidentReport(label, list) {
  if (list.length === 0) {
    return { response: `There are currently no ${label} incidents in the system.`, data: [] };
  }
  const lines = list.map(formatIncidentLine);
  return {
    response: `Found ${list.length} ${label} incident${list.length === 1 ? '' : 's'}:\n${lines.join('\n')}`,
    data: list,
  };
}

async function buildOfflineCamerasResponse() {
  const cameras = await getCameraData();
  const offline = cameras.filter((c) => c.status === 'offline');
  const warnings = cameras.filter((c) => c.status === 'warning');
  if (offline.length === 0 && warnings.length === 0) {
    return { response: 'All cameras are currently online. No connectivity issues detected.', data: [] };
  }
  const parts = [];
  if (offline.length > 0) parts.push(`Offline (${offline.length}): ${offline.map((c) => `${c.id} ${c.name}`).join(', ')}`);
  if (warnings.length > 0) parts.push(`Degraded/warning (${warnings.length}): ${warnings.map((c) => `${c.id} ${c.name}`).join(', ')}`);
  return { response: `Camera connectivity report:\n${parts.join('\n')}`, data: offline };
}

async function buildCameraSummaryResponse() {
  const cameras = await getCameraData();
  const counts = cameras.reduce((acc, c) => {
    acc[c.status] = (acc[c.status] || 0) + 1;
    return acc;
  }, {});
  const lines = cameras.map((c) => `${c.id} ${c.name} — ${c.status}`);
  return {
    response: `System has ${cameras.length} cameras (${counts.online || 0} online, ${counts.warning || 0} warning, ${counts.offline || 0} offline):\n${lines.join('\n')}`,
    data: cameras,
  };
}

async function buildTrafficResponse() {
  let analytics;
  try {
    analytics = await getAnalytics();
  } catch {
    analytics = {};
  }
  const hourly = analytics.hourlyTraffic || [];
  const weekly = analytics.weeklyTrend || [];
  if (hourly.length === 0) {
    return { response: 'No traffic analytics are available yet.', data: [] };
  }
  const totalPedestrians = hourly.reduce((s, h) => s + (h.pedestrians || 0), 0);
  const totalVehicles = hourly.reduce((s, h) => s + (h.vehicles || 0), 0);
  const totalIncidents = hourly.reduce((s, h) => s + (h.incidents || 0), 0);
  const peakHour = hourly.reduce((best, h) => ((h.vehicles || 0) > (best.vehicles || 0) ? h : best), hourly[0]);
  const peakDay = weekly.reduce((best, d) => ((d.detections || 0) > (best.detections || 0) ? d : best), weekly[0]);
  return {
    response:
      `Today: ${totalPedestrians} pedestrians, ${totalVehicles} vehicles, and ${totalIncidents} traffic-related incidents across 24 monitored hours.\n` +
      `Peak vehicle hour: ${peakHour.hour} (${peakHour.vehicles} vehicles). ` +
      `Weekly peak detections: ${peakDay.day} (${peakDay.detections} detections).`,
    data: hourly,
  };
}

async function buildSystemHealthResponse() {
  let health;
  try {
    health = await getSystemHealth();
  } catch {
    health = null;
  }
  if (!health) {
    return { response: 'System health metrics are currently unavailable.', data: [] };
  }
  const degraded = (health.services || []).filter((s) => s.status !== 'connected');
  const parts = [
    `Overall health ${health.overall}/100 with ${health.uptime} uptime.`,
    `Cameras: ${health.onlineCameras} online, ${health.offlineCameras} offline of ${health.totalCameras}.`,
    `Network: latency ${health.latency}ms, packet loss ${health.packetLoss}%.`,
    degraded.length > 0
      ? `Degraded services: ${degraded.map((s) => s.name).join(', ')}`
      : `All ${health.services.length} core services operational.`,
  ];
  return { response: parts.join('\n'), data: health.services };
}

async function buildRecentIncidentsResponse() {
  const incidents = await getIncidentData();
  const recent = incidents.slice(0, 5);
  if (recent.length === 0) return { response: 'There are no recorded incidents.', data: [] };
  const lines = recent.map(formatIncidentLine);
  return {
    response: `Latest ${recent.length} incident${recent.length === 1 ? '' : 's'}:\n${lines.join('\n')}`,
    data: recent,
  };
}

export async function askAssistant(message) {
  await delay(150);
  const input = String(message || '').toLowerCase().trim();

  if (input.includes('critical')) return buildIncidentReport('critical', (await getIncidentData()).filter((i) => i.severity === 'critical'));
  if (input.includes('high')) return buildIncidentReport('high', (await getIncidentData()).filter((i) => i.severity === 'high'));
  if (input.includes('offline')) return buildOfflineCamerasResponse();
  if (input.includes('camera')) return buildCameraSummaryResponse();
  if (input.includes('traffic')) return buildTrafficResponse();
  if (input.includes('health') || input.includes('status')) return buildSystemHealthResponse();
  if (input.includes('recent')) return buildRecentIncidentsResponse();
  if (input.includes('open')) return buildIncidentReport('open', (await getIncidentData()).filter((i) => i.status === 'open'));
  if (input.includes('resolved')) return buildIncidentReport('resolved', (await getIncidentData()).filter((i) => i.status === 'resolved'));

  if (input.includes('help')) {
    return {
      response:
        'I can help you query the SENTINEL AI system. Available commands:\n' +
        '• "critical incidents" or "show critical" — report critical incidents\n' +
        '• "high incidents" — report high-severity incidents\n' +
        '• "offline cameras" — list offline cameras\n' +
        '• "which cameras" or "camera status" — camera status summary\n' +
        '• "traffic" — traffic analytics summary\n' +
        '• "system health" or "status" — system health report\n' +
        '• "recent incidents" — last 5 incidents\n' +
        '• "open incidents" / "resolved incidents" — filter by status\n' +
        '• "help" — show this list',
      data: null,
    };
  }

  return {
    response:
      'I can help you query the SENTINEL AI system. Try asking about: critical incidents, camera status, traffic activity, system health, or recent incidents.',
    data: null,
  };
}

// ---------------------------------------------------------------------------
// Phase 6 — Watchlist / Alerts / Tracking / GIS / Search / Scale / Demo APIs
// ---------------------------------------------------------------------------

export async function getWatchlist(filters = {}) {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.status) params.set('status', filters.status);
  if (filters.priority) params.set('priority', filters.priority);
  if (filters.query) params.set('query', filters.query);
  if (filters.limit) params.set('limit', String(filters.limit));
  const qs = params.toString();
  return request(`/watchlists${qs ? `?${qs}` : ''}`);
}

export async function createWatchlist(payload) {
  return request('/watchlists', {
    method: 'POST',
    headers: toJSONHeader(),
    body: JSON.stringify(payload),
  });
}

export async function updateWatchlist(id, payload) {
  return request(`/watchlists/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: toJSONHeader(),
    body: JSON.stringify(payload),
  });
}

export async function deleteWatchlist(id) {
  return request(`/watchlists/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export async function getAlerts(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.camera_id) params.set('camera_id', filters.camera_id);
  if (filters.watchlist_id) params.set('watchlist_id', filters.watchlist_id);
  if (filters.limit) params.set('limit', String(filters.limit));
  const qs = params.toString();
  return request(`/alerts${qs ? `?${qs}` : ''}`);
}

export async function updateAlert(id, payload) {
  return request(`/alerts/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: toJSONHeader(),
    body: JSON.stringify(payload),
  });
}

export async function getTracking(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.watchlist_id) params.set('watchlist_id', filters.watchlist_id);
  if (filters.entity_identifier) params.set('entity_identifier', filters.entity_identifier);
  if (filters.limit) params.set('limit', String(filters.limit));
  const qs = params.toString();
  return request(`/tracking${qs ? `?${qs}` : ''}`);
}

export async function getTrack(id) {
  return request(`/tracking/${encodeURIComponent(id)}`);
}

export async function getEntityMovements(entityId, limit = 500) {
  return request(`/tracking/entity/${encodeURIComponent(entityId)}?limit=${limit}`);
}

export async function getGISCameras() {
  return request('/gis/cameras');
}

export async function getGISEvents(limit = 500) {
  return request(`/gis/events?limit=${limit}`);
}

export async function getGISRoute(entityIdentifier) {
  return request(`/gis/route/${encodeURIComponent(entityIdentifier)}`);
}

export async function getGISSummary() {
  return request('/gis/summary');
}

export async function searchInvestigation(params = {}) {
  const p = new URLSearchParams();
  if (params.query) p.set('query', params.query);
  if (params.camera_id) p.set('camera_id', params.camera_id);
  if (params.severity) p.set('severity', params.severity);
  if (params.tracking_id) p.set('tracking_id', params.tracking_id);
  if (params.watchlist_id) p.set('watchlist_id', params.watchlist_id);
  if (params.start) p.set('start', params.start);
  if (params.end) p.set('end', params.end);
  if (params.limit) p.set('limit', String(params.limit));
  const qs = p.toString();
  return request(`/search${qs ? `?${qs}` : ''}`);
}

export async function getScalePresets() {
  return request('/scale/presets');
}

export async function getScalePreset(name) {
  return request(`/scale/preset/${encodeURIComponent(name)}`);
}

export async function runScaleSimulation(payload = {}) {
  return request('/scale/run', {
    method: 'POST',
    headers: toJSONHeader(),
    body: JSON.stringify(payload),
  });
}

export async function getDemoStatus() {
  return request('/demo/status');
}

export async function runDemoTest() {
  return request('/demo/run-test', { method: 'POST' });
}

export async function resetDemo() {
  return request('/demo/reset', { method: 'POST' });
}

export { API_BASE_URL };