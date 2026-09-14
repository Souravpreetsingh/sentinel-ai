export const EVENT_TYPES = Object.freeze({
  CAMERA_STATUS_CHANGED: 'camera.status_changed',
  DETECTION_CREATED: 'detection',
  INCIDENT_CREATED: 'incident_created',
  INCIDENT_UPDATED: 'incident_updated',
  VIDEO_PROGRESS: 'video_progress',
  SYSTEM_STATUS: 'system_status',
  ALERT_CREATED: 'alert.created',
  WATCHLIST_CREATED: 'watchlist.created',
  WATCHLIST_UPDATED: 'watchlist.updated',
  TRACKING_MOVEMENT: 'tracking.movement',
});

const EVENT_ALIASES = {
  'incident.created': 'incident_created',
  'incident.updated': 'incident_updated',
};

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/live`;
})();

const randomBetween = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

const DETECTION_TYPES = ['person', 'vehicle', 'motorcycle'];

const INCIDENT_TEMPLATES = [
  { type: 'Unattended Object in Corridor', severity: 'low' },
  { type: 'Moderate Crowding at South Gate', severity: 'low' },
  { type: 'Loitering Near Restricted Access', severity: 'medium' },
  { type: 'Unauthorized Vehicle Near Loading Zone', severity: 'medium' },
];

const ALERT_TEMPLATES = [
  { type: 'perimeter', level: 'warning', message: 'Unusual activity detected near North Perimeter fence.' },
  { type: 'density', level: 'warning', message: 'Crowd density approaching threshold in Market District.' },
  { type: 'anpr', level: 'info', message: 'ANPR flagged a vehicle matching watchlist criteria.' },
];

const INCIDENT_STATUSES = ['open', 'investigating', 'dispatched'];

class SentinelWebSocket {
  constructor(options = {}) {
    this.url = options.url ?? WS_BASE_URL;
    this.demoMode = options.demoMode ?? false;
    this.listeners = new Map();
    this.connectionListeners = new Set();
    this.connected = false;
    this.socket = null;
    this.demoTimers = [];
    this.counter = 0;
    this.cameraIndex = 0;
    this.incidentUpdateIndex = 0;
    this.incidentCreateIndex = 0;
    this.alertIndex = 0;
    this._preventReconnect = false;
    this._reconnectAttempt = 0;
    this._reconnectTimer = null;
    this._pendingClose = false;
  }

  connect() {
    if (this.demoMode) {
      if (this.connected && this.demoTimers.length > 0) return;
      this.connected = true;
      this._notifyConnection(true);
      this.startDemoMode();
      return;
    }

    if (this.socket && this.connected) return;
    if (this.socket) {
      // Transitional state — shut down the old socket and start fresh.
      this._teardownSocket();
    }
    this._preventReconnect = false;
    this._reconnectAttempt = 0;
    this._openSocket();
  }

  disconnect() {
    this.stopDemoMode();
    this._preventReconnect = true;
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this._teardownSocket();
    this.connected = false;
    this._notifyConnection(false);
  }

  setDemoMode(mode) {
    this.demoMode = !!mode;
    if (this.demoMode) {
      this._teardownSocket();
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer);
        this._reconnectTimer = null;
      }
    }
  }

  subscribe(eventType, callback) {
    if (typeof callback !== 'function') return () => {};

    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType).add(callback);

    return () => this.unsubscribe(eventType, callback);
  }

  unsubscribe(eventType, callback) {
    const set = this.listeners.get(eventType);
    if (!set) return;

    set.delete(callback);
    if (set.size === 0) {
      this.listeners.delete(eventType);
    }
  }

  onConnectionChange(callback) {
    this.connectionListeners.add(callback);
    return () => this.connectionListeners.delete(callback);
  }

  emit(eventType, data, envelope) {
    const set = this.listeners.get(eventType);
    if (!set || set.size === 0) return;

    const payload = envelope ?? { type: eventType, data, timestamp: new Date().toISOString() };
    set.forEach((callback) => {
      try {
        callback(data, payload);
      } catch (error) {
        console.error(`[SentinelWebSocket] listener error for "${eventType}":`, error);
      }
    });
  }

  _teardownSocket() {
    if (this.socket) {
      try {
        this.socket.onclose = null;
        this.socket.onerror = null;
        this.socket.onmessage = null;
        this.socket.onopen = null;
        this.socket.close();
      } catch {
        /* already closed */
      }
      this.socket = null;
    }
  }

  // -------------------------------------------------------------------------
  // Demo fallback
  // -------------------------------------------------------------------------

  startDemoMode() {
    if (this.demoTimers.length > 0) return;

    this.counter = 0;
    this._scheduleDetection();
    this._scheduleCameraStatusChange();
    this._scheduleIncidentUpdate();
    this._scheduleIncidentCreate();
    this._scheduleAlert();
  }

  stopDemoMode() {
    this.demoTimers.forEach((timer) => clearTimeout(timer));
    this.demoTimers = [];
  }

  _schedule(callback, min, max) {
    const timer = setTimeout(() => {
      callback();
      this._schedule(callback, min, max);
    }, randomBetween(min, max));
    this.demoTimers.push(timer);
  }

  _scheduleDetection() {
    this._schedule(this._emitDetection.bind(this), 5000, 10000);
  }

  _scheduleCameraStatusChange() {
    this._schedule(this._emitCameraStatusChange.bind(this), 55000, 90000);
  }

  _scheduleIncidentUpdate() {
    this._schedule(this._emitIncidentUpdate.bind(this), 20000, 30000);
  }

  _scheduleIncidentCreate() {
    this._schedule(this._emitIncidentCreate.bind(this), 60000, 90000);
  }

  _scheduleAlert() {
    this._schedule(this._emitAlert.bind(this), 90000, 150000);
  }

  _emitDetection() {
    this.counter += 1;
    const camera = this._demoCameras[this.counter % this._demoCameras.length] || this._demoCameras[0];
    const detectionType = DETECTION_TYPES[this.counter % DETECTION_TYPES.length];
    const detection = {
      id: `DET-${String(1000 + this.counter)}`,
      cameraId: camera.id,
      cameraName: camera.name,
      location: camera.location,
      type: detectionType,
      confidence: Math.round((85 + Math.random() * 14) * 10) / 10,
      timestamp: new Date().toISOString(),
    };
    this.emit(EVENT_TYPES.DETECTION_CREATED, detection);
  }

  _emitCameraStatusChange() {
    const candidates = this._demoCameras.filter((c) => c.status !== 'offline');
    if (candidates.length === 0) return;

    this.cameraIndex += 1;
    const camera = candidates[this.cameraIndex % candidates.length];
    const nextStatus = camera.status === 'online' ? 'warning' : 'online';

    this.emit(EVENT_TYPES.CAMERA_STATUS_CHANGED, {
      cameraId: camera.id,
      cameraName: camera.name,
      location: camera.location,
      previousStatus: camera.status,
      status: nextStatus,
      timestamp: new Date().toISOString(),
    });
  }

  _emitIncidentUpdate() {
    const active = this._demoIncidents.filter((i) => i.status !== 'resolved');
    if (active.length === 0) return;

    this.incidentUpdateIndex += 1;
    const incident = active[this.incidentUpdateIndex % active.length];
    const nextStatus = INCIDENT_STATUSES[this.incidentUpdateIndex % INCIDENT_STATUSES.length];

    this.emit(EVENT_TYPES.INCIDENT_UPDATED, {
      incidentId: incident.id,
      incidentType: incident.type,
      location: incident.location,
      previousStatus: incident.status,
      status: nextStatus,
      updatedAt: new Date().toISOString(),
      timestamp: new Date().toISOString(),
    });
  }

  _emitIncidentCreate() {
    this.incidentCreateIndex += 1;
    const camera = this._demoCameras[this.incidentCreateIndex % this._demoCameras.length] || this._demoCameras[0];
    const template = INCIDENT_TEMPLATES[this.incidentCreateIndex % INCIDENT_TEMPLATES.length];
    const now = new Date();
    const incident = {
      id: `INC-${String(1100 + this.incidentCreateIndex)}`,
      type: template.type,
      severity: template.severity,
      status: 'open',
      cameraId: camera.id,
      location: camera.location,
      timestamp: now.toISOString(),
      assignedOfficer: null,
      badgeNumber: null,
      confidence: Math.round((82 + Math.random() * 15) * 10) / 10,
      description: `${template.type} automatically detected at ${camera.name} (${camera.location}) by the CV pipeline.`,
      geoCoords: null,
      hash: null,
      timeline: [
        {
          time: now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
          event: 'Incident created by model inference.',
          type: 'system',
        },
      ],
    };

    this.emit(EVENT_TYPES.INCIDENT_CREATED, { incident });
  }

  _emitAlert() {
    this.alertIndex += 1;
    const template = ALERT_TEMPLATES[this.alertIndex % ALERT_TEMPLATES.length];

    this.emit(EVENT_TYPES.ALERT_CREATED, {
      id: `ALR-${String(4000 + this.alertIndex)}`,
      type: template.type,
      level: template.level,
      message: template.message,
      timestamp: new Date().toISOString(),
    });
  }

  // -------------------------------------------------------------------------
  // Real WebSocket connection
  // -------------------------------------------------------------------------

  _openSocket() {
    if (this.socket || this.demoMode) return;

    let ws;
    try {
      ws = new WebSocket(this.url);
    } catch (error) {
      console.error('[SentinelWebSocket] failed to open connection:', error);
      this.socket = null;
      this._scheduleReconnect();
      return;
    }

    this.socket = ws;

    ws.onopen = () => {
      this.connected = true;
      this._reconnectAttempt = 0;
      this._notifyConnection(true);
    };

    ws.onmessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        /* ignore malformed frames */
        return;
      }
      if (!message) return;

      const rawEvent = message.event || message.type;
      if (!rawEvent) return;
      const { event: canonical, data } = this._normalize(rawEvent, message.data ?? message.payload ?? message);
      this.emit(canonical, data, {
        type: canonical,
        data,
        timestamp: message.timestamp || new Date().toISOString(),
      });
    };

    ws.onclose = () => {
      this.socket = null;
      this.connected = false;
      this._notifyConnection(false);
      this._scheduleReconnect();
    };

    ws.onerror = () => {
      try {
        ws.close();
      } catch {
        /* closing anyway */
      }
    };
  }

  _scheduleReconnect() {
    if (this.demoMode || this._preventReconnect || this.socket) return;

    const attempt = this._reconnectAttempt || 0;
    const backoff = Math.min(15000, 1000 * 2 ** Math.min(attempt, 6)) + randomBetween(0, 500);
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._reconnectAttempt = (this._reconnectAttempt || 0) + 1;
      this._openSocket();
    }, backoff);
  }

  _normalize(event, data) {
    const name = EVENT_ALIASES[event] || event;
    let d = data || {};

    if (name === 'incident_created') {
      d = {
        incident: this._buildIncidentFromEvent(d),
        incidentId: d.incident_id ?? d.incidentId,
        type: d.type,
        severity: d.severity,
        status: d.status,
        cameraId: d.camera_id ?? d.cameraId,
        location: d.location,
      };
    } else if (name === 'incident_updated') {
      d = {
        incidentId: d.incidentId ?? d.incident_id,
        incidentType: d.type,
        severity: d.severity,
        status: d.status,
        location: d.location,
        cameraId: d.cameraId ?? d.camera_id,
        updatedAt: d.updatedAt ?? d.updated_at,
      };
    } else if (name === 'detection') {
      d = { ...d, cameraId: d.cameraId ?? d.camera_id };
    } else if (name === 'camera.status_changed') {
      d = {
        cameraId: d.cameraId ?? d.camera_id,
        cameraName: d.cameraName ?? d.camera_name,
        location: d.location,
        previousStatus: d.previousStatus ?? d.previous_status,
        status: d.status,
      };
    } else if (name === 'system_status') {
      d = { ...d, latency: d.latency ?? d.latency_ms };
    } else if (name === 'tracking.movement') {
      d = {
        id: d.id,
        track_id: d.track_id,
        camera_id: d.camera_id,
        entity_identifier: d.entity_identifier,
        latitude: d.latitude,
        longitude: d.longitude,
        confidence: d.confidence,
        detected_at: d.detected_at,
        alert_id: d.alert_id,
        evidence_id: d.evidence_id,
      };
    }

    return { event: name, data: d };
  }

  _buildIncidentFromEvent(payload) {
    const timestamp = new Date().toISOString();
    let confidence = payload.confidence;
    if (typeof confidence === 'number' && confidence <= 1) {
      confidence = Math.round(confidence * 1000) / 10;
    }
    return {
      id: payload.incident_id ?? payload.incidentId,
      type: payload.type,
      severity: payload.severity,
      status: payload.status,
      cameraId: payload.camera_id ?? payload.cameraId,
      location: payload.location,
      timestamp,
      assignedOfficer: null,
      badgeNumber: null,
      confidence,
      description: `${payload.type} automatically detected${payload.location ? ` at ${payload.location}` : ''} by the CV pipeline.`,
      geoCoords: null,
      hash: null,
      timeline: [
        {
          time: new Date(timestamp).toLocaleTimeString([], { hour12: false }),
          event: `Incident created by model inference${confidence != null ? ` (${confidence}% confidence)` : ''}.`,
          type: 'system',
        },
      ],
    };
  }

  _notifyConnection(connected) {
    this.connectionListeners.forEach((callback) => {
      try {
        callback(connected);
      } catch (error) {
        console.error('[SentinelWebSocket] connection listener error:', error);
      }
    });
  }
}

export { SentinelWebSocket };

// Lazy demo data so this module stays mock-free until used.
let _demoCameras = null;
let _demoIncidents = null;

Object.defineProperty(SentinelWebSocket.prototype, '_demoCameras', {
  get() {
    if (!_demoCameras) {
      // Loaded lazily — demo mode only. Real mode never touches this.
      _demoCameras = [
        { id: 'CAM-01', name: 'Main Road', location: 'Sector 14 — Main Road', status: 'online' },
        { id: 'CAM-02', name: 'North Perimeter Fence Alpha', location: 'Sector 14 — North Perimeter', status: 'online' },
        { id: 'CAM-03', name: 'Terminal 2 Plaza', location: 'Transit Hub — Terminal 2 Plaza', status: 'online' },
        { id: 'CAM-12', name: 'Market Road Center Plaza', location: 'Market District — Center Plaza', status: 'online' },
      ];
    }
    return _demoCameras;
  },
});

Object.defineProperty(SentinelWebSocket.prototype, '_demoIncidents', {
  get() {
    if (!_demoIncidents) {
      _demoIncidents = [
        { id: 'INC-DEMO-1', type: 'Restricted Zone Entry', location: 'Sector 14 — Gate B', status: 'open' },
        { id: 'INC-DEMO-2', type: 'Crowd Density Threshold Exceeded', location: 'Market District — Center Plaza', status: 'investigating' },
        { id: 'INC-DEMO-3', type: 'Unattended Object', location: 'Industrial — Cargo Bay Dock 4', status: 'open' },
      ];
    }
    return _demoIncidents;
  },
});

export const sentinelWS = new SentinelWebSocket({ demoMode: false });