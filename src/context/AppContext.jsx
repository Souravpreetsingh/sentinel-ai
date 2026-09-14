import { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  getCameras,
  getIncidents,
  getAnalytics,
  getEvidence,
  getSystemHealth,
  updateIncident as apiUpdateIncident,
  getWatchlist,
  getAlerts,
  getTracking,
} from '../services/api';
import { sentinelWS, EVENT_TYPES } from '../services/websocket';

const AppContext = createContext(null);

function normalizeBBox(bbox, refW = 1280, refH = 720) {
  if (!bbox) return null;
  let x1, y1, x2, y2;
  if (Array.isArray(bbox)) {
    [x1, y1, x2, y2] = bbox;
  } else {
    x1 = bbox.x1 ?? 0;
    y1 = bbox.y1 ?? 0;
    x2 = bbox.x2 ?? 0;
    y2 = bbox.y2 ?? 0;
  }
  return {
    x1: Math.max(0, Math.min(100, (x1 / refW) * 100)),
    y1: Math.max(0, Math.min(100, (y1 / refH) * 100)),
    x2: Math.max(0, Math.min(100, (x2 / refW) * 100)),
    y2: Math.max(0, Math.min(100, (y2 / refH) * 100)),
  };
}

export function AppProvider({ children }) {
  const [demoMode, setDemoMode] = useState(false);
  const [cameras, setCameras] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [liveDetections, setLiveDetections] = useState({});
  const [videoProgress, setVideoProgress] = useState({});
  const [watchlists, setWatchlists] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [tracks, setTracks] = useState([]);

  const notificationId = useRef(0);
  const mountedRef = useRef(true);
  const loadedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const unreadCount = useMemo(
    () => notifications.reduce((count, n) => (n.read ? count : count + 1), 0),
    [notifications]
  );

  const addNotification = useCallback((notification) => {
    notificationId.current += 1;
    setNotifications((prev) => [
      {
        id: `NTF-${String(notificationId.current)}`,
        read: false,
        timestamp: new Date().toISOString(),
        ...notification,
      },
      ...prev,
    ]);
  }, []);

  const markAsRead = useCallback((id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => (n.read ? n : { ...n, read: true })));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const refetchCameras = useCallback(async () => {
    const data = await getCameras();
    if (mountedRef.current) setCameras(data);
  }, []);

  const refetchIncidents = useCallback(async () => {
    const data = await getIncidents();
    if (mountedRef.current) setIncidents(data);
  }, []);

  const refetchSystemHealth = useCallback(async () => {
    const data = await getSystemHealth();
    if (mountedRef.current) setSystemHealth(data);
  }, []);

  const refetchAnalytics = useCallback(async () => {
    const data = await getAnalytics();
    if (mountedRef.current) setAnalytics(data);
  }, []);

  const refetchEvidence = useCallback(async () => {
    const data = await getEvidence();
    if (mountedRef.current) setEvidence(data);
  }, []);

  const refetchWatchlists = useCallback(async () => {
    try {
      const data = await getWatchlist();
      if (mountedRef.current) setWatchlists(data);
    } catch { /* non-critical */ }
  }, []);

  const refetchAlerts = useCallback(async () => {
    try {
      const data = await getAlerts();
      if (mountedRef.current) setAlerts(data);
    } catch { /* non-critical */ }
  }, []);

  const refetchTracks = useCallback(async () => {
    try {
      const data = await getTracking();
      if (mountedRef.current) setTracks(data);
    } catch { /* non-critical */ }
  }, []);

  const updateIncident = useCallback(
    async (id, updates) => {
      const updated = await apiUpdateIncident(id, updates);
      if (updated && mountedRef.current) {
        setIncidents((prev) => prev.map((inc) => (inc.id === updated.id ? updated : inc)));
        addNotification({
          type: 'incident',
          severity: 'info',
          title: `Incident ${id} updated`,
          message: `Status changed to ${updated.status}.`,
        });
      }
      return updated;
    },
    [addNotification]
  );

  const refetchAll = useCallback(async () => {
    const results = await Promise.allSettled([
      getCameras(),
      getIncidents(),
      getSystemHealth(),
      getAnalytics(),
      getEvidence(),
      getWatchlist(),
      getAlerts(),
      getTracking(),
    ]);
    if (!mountedRef.current) return;

    if (results[0].status === 'fulfilled') setCameras(results[0].value);
    if (results[1].status === 'fulfilled') setIncidents(results[1].value);
    if (results[2].status === 'fulfilled') setSystemHealth(results[2].value);
    if (results[3].status === 'fulfilled') setAnalytics(results[3].value);
    if (results[4].status === 'fulfilled') setEvidence(results[4].value);
    if (results[5].status === 'fulfilled') setWatchlists(results[5].value);
    if (results[6].status === 'fulfilled') setAlerts(results[6].value);
    if (results[7].status === 'fulfilled') setTracks(results[7].value);

    const failures = results.filter((r) => r.status === 'rejected');
    if (failures.length === results.length) {
      setError(failures[0].reason?.message || 'Failed to load system data');
    } else if (failures.length > 0) {
      setError(`Partial load: ${failures.length} data source(s) failed. ${failures[0].reason?.message || ''}`.trim());
    }
  }, []);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    const loadInitial = async () => {
      setLoading(true);
      setError(null);
      try {
        const results = await Promise.allSettled([
          getCameras(),
          getIncidents(),
          getSystemHealth(),
          getAnalytics(),
          getEvidence(),
          getWatchlist(),
          getAlerts(),
          getTracking(),
        ]);
        if (!mountedRef.current) return;

        if (results[0].status === 'fulfilled') setCameras(results[0].value);
        if (results[1].status === 'fulfilled') setIncidents(results[1].value);
        if (results[2].status === 'fulfilled') setSystemHealth(results[2].value);
        if (results[3].status === 'fulfilled') setAnalytics(results[3].value);
        if (results[4].status === 'fulfilled') setEvidence(results[4].value);
        if (results[5].status === 'fulfilled') setWatchlists(results[5].value);
        if (results[6].status === 'fulfilled') setAlerts(results[6].value);
        if (results[7].status === 'fulfilled') setTracks(results[7].value);

        const failures = results.filter((r) => r.status === 'rejected');
        if (failures.length === results.length) {
          throw failures[0].reason;
        } else if (failures.length > 0) {
          setError(
            `Partial load: ${failures.length} data source(s) failed. ${failures[0].reason?.message || ''}`.trim()
          );
        }
      } catch (err) {
        if (mountedRef.current) setError(err.message || 'Failed to load system data');
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    };

    loadInitial();
  }, []);

  // WebSocket effect: connects when component mounts; uses real WS by default,
  // falls back to demo simulation when the Settings toggle enables it.
  useEffect(() => {
    sentinelWS.disconnect();
    sentinelWS.setDemoMode(demoMode);

    const handlers = {
      [EVENT_TYPES.CAMERA_STATUS_CHANGED]: (payload) => {
        setCameras((prev) =>
          prev.map((cam) =>
            cam.id === payload.cameraId ? { ...cam, status: payload.status } : cam
          )
        );
        addNotification({
          type: 'camera',
          severity: payload.status === 'online' ? 'success' : 'warning',
          title: `${payload.cameraName || payload.cameraId} status changed`,
          message: `${payload.cameraName || payload.cameraId} is now ${payload.status} (was ${payload.previousStatus}).`,
        });
      },
      [EVENT_TYPES.DETECTION_CREATED]: (detection) => {
        const cameraId = detection.cameraId;
        const objects = detection.objects || [];

        // Update camera detection counters
        setCameras((prev) =>
          prev.map((cam) => {
            if (cam.id !== cameraId) return cam;
            const counts = { ...cam.detections };
            if (objects.length > 0) {
              objects.forEach((o) => {
                const cls = (o.class_name || o.type || '').toLowerCase();
                if (cls === 'person') counts.people = (counts.people || 0) + 1;
                else if (cls === 'motorcycle' || cls === 'bicycle') counts.motorcycles = (counts.motorcycles || 0) + 1;
                else if (cls === 'car' || cls === 'vehicle' || cls === 'truck' || cls === 'bus') counts.vehicles = (counts.vehicles || 0) + 1;
                else counts.vehicles = (counts.vehicles || 0) + 1;
              });
            } else if (detection.type) {
              const key =
                detection.type === 'person' ? 'people' : detection.type === 'vehicle' ? 'vehicles' : detection.type === 'motorcycle' ? 'motorcycles' : null;
              if (key) counts[key] = (counts[key] || 0) + 1;
            }
            return { ...cam, detections: counts };
          })
        );

        // Store bounding-box data for CommandCenter overlay (normalised to %)
        if (objects.length > 0) {
          setLiveDetections((prev) => ({
            ...prev,
            [cameraId]: {
              objects: objects
                .map((o) => {
                  const bbox = o.bbox;
                  const norm = normalizeBBox(bbox);
                  return norm ? { ...o, bbox: norm } : null;
                })
                .filter(Boolean),
              timestamp: Date.now(),
            },
          }));
        }

        const label = detection.type || (objects[0]?.class_name) || 'object';
        addNotification({
          type: 'detection',
          level: 'info',
          title: `New detection at ${cameraId}`,
          message: `${label} detected${detection.location ? ` at ${detection.location}` : ''} (${detection.confidence ?? '--'}%).`,
        });
      },
      [EVENT_TYPES.INCIDENT_CREATED]: (payload) => {
        const incident = payload.incident;
        if (!incident) return;
        setIncidents((prev) => [incident, ...prev]);
        addNotification({
          type: 'incident',
          severity: incident.severity,
          title: `New ${incident.severity} incident created`,
          message: `${incident.type} at ${incident.location}.`,
        });
      },
      [EVENT_TYPES.INCIDENT_UPDATED]: (payload) => {
        setIncidents((prev) =>
          prev.map((inc) =>
            inc.id === payload.incidentId ? { ...inc, status: payload.status } : inc
          )
        );
        addNotification({
          type: 'incident',
          severity: 'info',
          title: `Incident ${payload.incidentId} updated`,
          message: `${payload.incidentType || payload.incidentId} status changed to ${payload.status}.`,
        });
      },
      [EVENT_TYPES.VIDEO_PROGRESS]: (payload) => {
        if (!payload.videoId) return;
        setVideoProgress((prev) => ({
          ...prev,
          [payload.videoId]: {
            progress: payload.progress ?? prev[payload.videoId]?.progress ?? 0,
            fps: payload.fps ?? prev[payload.videoId]?.fps ?? 0,
            totalFrames: payload.total_frames ?? prev[payload.videoId]?.totalFrames ?? 0,
            frame: payload.frame ?? prev[payload.videoId]?.frame ?? 0,
            status: payload.status ?? prev[payload.videoId]?.status ?? 'processing',
          },
        }));
        // Notify on completion
        if (payload.progress >= 100 || payload.status === 'completed' || payload.status === 'failed') {
          addNotification({
            type: 'video',
            severity: payload.status === 'failed' ? 'warning' : 'success',
            title: `Video ${payload.status === 'failed' ? 'failed' : 'processing complete'}`,
            message: `${payload.videoId} — ${payload.status === 'failed' ? 'error occurred' : `${payload.frame ?? ''}/${payload.totalFrames ?? ''} frames`}.`,
          });
        }
      },
      [EVENT_TYPES.SYSTEM_STATUS]: (payload) => {
        // Log but do not spam notifications for every heartbeat
        if (payload.status && payload.status !== 'healthy') {
          addNotification({
            type: 'system',
            severity: 'warning',
            title: 'System status update',
            message: `Status: ${payload.status}. FPS: ${payload.fps ?? '--'}, latency: ${payload.latency ?? '--'}ms.`,
          });
        }
      },
      [EVENT_TYPES.ALERT_CREATED]: (alert) => {
        setAlerts((prev) => [alert, ...prev].slice(0, 200));
        addNotification({
          type: 'alert',
          level: alert.severity || 'warning',
          title: `Alert: ${alert.entity_name || alert.match_type}`,
          message: `${alert.entity_category || 'entity'} seen at ${alert.camera_id || 'unknown'}`,
        });
      },
    };

    Object.entries(handlers).forEach(([eventType, handler]) => {
      sentinelWS.subscribe(eventType, handler);
    });

    sentinelWS.connect();

    return () => {
      Object.entries(handlers).forEach(([eventType, handler]) => {
        sentinelWS.unsubscribe(eventType, handler);
      });
      sentinelWS.disconnect();
    };
  }, [demoMode, addNotification]);

  const search = useCallback(
    (query) => {
      const q = String(query || '').toLowerCase().trim();
      if (!q) return { cameras: [], incidents: [] };

      const cameraResults = cameras.filter((cam) =>
        `${cam.id} ${cam.name} ${cam.sector} ${cam.location} ${cam.status}`.toLowerCase().includes(q)
      );
      const incidentResults = incidents.filter((inc) =>
        `${inc.id} ${inc.type} ${inc.location} ${inc.status} ${inc.severity}`.toLowerCase().includes(q)
      );

      return { cameras: cameraResults, incidents: incidentResults };
    },
    [cameras, incidents]
  );

  const value = {
    cameras,
    incidents,
    notifications,
    unreadCount,
    systemHealth,
    analytics,
    evidence,
    loading,
    error,
    demoMode,
    setDemoMode,
    liveDetections,
    videoProgress,
    refetchCameras,
    refetchIncidents,
    refetchSystemHealth,
    refetchAnalytics,
    refetchEvidence,
    refetchAll,
    updateIncident,
    markAsRead,
    markAllAsRead,
    clearNotifications,
    addNotification,
    search,
    watchlists,
    alerts,
    tracks,
    refetchWatchlists,
    refetchAlerts,
    refetchTracks,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}