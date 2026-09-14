import { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { useFullscreen } from '../hooks/useFullscreen';
import { runDemoTest, resetDemo } from '../services/api';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';
import SeverityBadge from '../components/shared/SeverityBadge';
import StatusBadge from '../components/shared/StatusBadge';

function KPITile({ icon, label, value, sub, accent, children }) {
  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/30 p-4 flex flex-col gap-2 min-w-0">
      <div className="flex items-center justify-between">
        <span className="font-label-xs text-outline tracking-wider uppercase">{label}</span>
        <span className={`material-symbols-outlined text-[18px] ${accent || 'text-primary'}`}>{icon}</span>
      </div>
      <div className="font-headline-lg text-on-surface text-2xl font-bold">{value}</div>
      {sub && <span className="font-body-sm text-outline text-[11px]">{sub}</span>}
      {children}
    </div>
  );
}

function CameraFeedCard({ cam, boxes = [] }) {
  const { ref: cardRef, isFullscreen, toggleFullscreen } = useFullscreen();
  const isCritical = cam.id === 'CAM-07';
  const total = (cam.detections?.people || 0) + (cam.detections?.vehicles || 0) + (cam.detections?.motorcycles || 0);
  return (
    <div
      ref={cardRef}
      className={`border overflow-hidden flex flex-col ${
        isFullscreen ? 'fixed inset-0 z-50 w-screen h-screen rounded-none border-0' : 'rounded-lg'
      } ${isCritical ? 'border-error ring-2 ring-error/40' : 'border-outline-variant/30'}`}
    >
      {isCritical && (
        <div className="bg-error-container/80 flex items-center gap-2 px-3 py-1.5">
          <span className="material-symbols-outlined text-[14px] text-on-error-container animate-pulse">warning</span>
          <span className="font-label-xs text-on-error-container text-[10px] tracking-wider">CRITICAL ALERT — INTRUSION DETECTED</span>
        </div>
      )}
      <div className="relative aspect-video bg-surface-container-low">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-tertiary/5" />
        <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-surface-container-lowest/80 rounded px-2 py-0.5">
          <span className={`h-1.5 w-1.5 rounded-full ${cam.status === 'online' ? 'bg-secondary' : cam.status === 'warning' ? 'bg-tertiary' : 'bg-outline'}`} />
          <span className="font-label-xs text-on-surface text-[9px]">{cam.id}</span>
        </div>
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between">
          <span className="font-label-xs text-on-surface/70 text-[9px] bg-surface-container-lowest/60 rounded px-1.5 py-0.5">{cam.name}</span>
          <span className="font-label-xs text-on-surface/50 text-[9px]">{cam.fps} FPS</span>
        </div>
        {isCritical && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-24 h-24 border-2 border-error/60 rounded-lg relative">
              <div className="absolute -top-1 -left-1 w-3 h-3 border-t-2 border-l-2 border-error" />
              <div className="absolute -top-1 -right-1 w-3 h-3 border-t-2 border-r-2 border-error" />
              <div className="absolute -bottom-1 -left-1 w-3 h-3 border-b-2 border-l-2 border-error" />
              <div className="absolute -bottom-1 -right-1 w-3 h-3 border-b-2 border-r-2 border-error" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="material-symbols-outlined text-error text-[20px]">person_off</span>
              </div>
            </div>
          </div>
        )}
        {boxes.map((obj, i) => {
          const b = obj.bbox;
          if (!b) return null;
          const left = Math.min(b.x1, b.x2);
          const top = Math.min(b.y1, b.y2);
          const width = Math.abs(b.x2 - b.x1);
          const height = Math.abs(b.y2 - b.y1);
          const label = (obj.class_name || obj.type || 'obj').toUpperCase();
          const confidence =
            typeof obj.confidence === 'number'
              ? obj.confidence <= 1
                ? `${Math.round(obj.confidence * 1000) / 10}%`
                : `${Math.round(obj.confidence * 10) / 10}%`
              : '';
          return (
            <div
              key={i}
              className="absolute rounded-sm border border-primary/80"
              style={{ top: `${top}%`, left: `${left}%`, width: `${width}%`, height: `${height}%` }}
            >
              <div className="absolute -top-4 -left-1 bg-primary/90 text-on-primary font-label-xs text-[8px] px-1 py-px rounded whitespace-nowrap">
                {label} {confidence}
              </div>
              <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-primary" />
              <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-primary" />
            </div>
          );
        })}
        {!isCritical && (
          <div className="absolute top-2 right-2 flex items-center gap-1">
            <div className="w-12 h-8 border border-primary/30 rounded-sm relative">
              <div className="absolute bottom-0.5 left-1 right-1 h-1 bg-primary/20 rounded-full" />
            </div>
          </div>
        )}
      </div>
      <div className="bg-surface-container-low px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-label-xs text-on-surface text-[10px]">{total} detections</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? 'EXIT FULLSCREEN' : 'ENTER FULLSCREEN'}
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            className="p-1 rounded hover:bg-surface-container-highest transition-colors"
          >
            <span className="material-symbols-outlined text-[14px] text-outline">{isFullscreen ? 'fullscreen_exit' : 'fullscreen'}</span>
          </button>
          <button className="p-1 rounded hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[14px] text-outline">volume_up</span>
          </button>
          <button className="p-1 rounded hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[14px] text-outline">more_vert</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function IncidentFeedItem({ inc }) {
  const stamp = new Date(inc.timestamp).toLocaleTimeString([], { hour12: false });
  return (
    <div className="flex gap-3 p-3 rounded-lg bg-surface-container-low border border-outline-variant/20 hover:border-outline-variant/40 transition-colors">
      <div className="flex-shrink-0 pt-0.5">
        <SeverityBadge severity={inc.severity} size="sm" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-label-xs text-on-surface text-[10px]">{inc.id}</span>
          <StatusBadge status={inc.status} />
        </div>
        <p className="font-body-sm text-on-surface-variant text-[11px] truncate">{inc.type}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className="font-label-xs text-outline text-[9px]">{inc.location}</span>
          <span className="font-label-xs text-outline/60 text-[9px]">{stamp}</span>
        </div>
      </div>
    </div>
  );
}

function TimelineItem({ event, isLast }) {
  const colorMap = {
    system: 'bg-secondary',
    auto: 'bg-primary',
    dispatch: 'bg-tertiary',
    sensor: 'bg-error',
  };
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={`h-2 w-2 rounded-full ${colorMap[event.type] || 'bg-outline'} flex-shrink-0`} />
        {!isLast && <div className="w-px flex-1 bg-outline-variant/30 my-1" />}
      </div>
      <div className="pb-4 min-w-0">
        <span className="font-label-xs text-outline text-[9px] tracking-wider">{event.time}</span>
        <p className="font-body-sm text-on-surface-variant text-[11px] mt-0.5">{event.event}</p>
      </div>
    </div>
  );
}

export default function CommandCenter() {
  const { cameras, incidents, systemHealth, analytics, liveDetections, watchlists, alerts, tracks, loading, error, refetchAll } = useApp();
  const [feedView, setFeedView] = useState('grid');
  const [demoResult, setDemoResult] = useState(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoResetting, setDemoResetting] = useState(false);

  const handleRunDemo = async () => {
    setDemoRunning(true);
    setDemoResult(null);
    try {
      const result = await runDemoTest();
      setDemoResult(result);
    } catch (err) {
      setDemoResult({ status: 'error', message: err.message });
    } finally {
      setDemoRunning(false);
      refetchAll();
    }
  };

  const handleResetDemo = async () => {
    setDemoResetting(true);
    try {
      await resetDemo();
      setDemoResult(null);
    } catch (err) {
      setDemoResult({ status: 'error', message: err.message });
    } finally {
      setDemoResetting(false);
      refetchAll();
    }
  };

  const liveBoxes = useMemo(() => {
    const now = Date.now();
    const map = {};
    Object.entries(liveDetections || {}).forEach(([cameraId, det]) => {
      if (det && now - det.timestamp < 15000) map[cameraId] = det.objects || [];
    });
    return map;
  }, [liveDetections]);

  if (loading) return <LoadingState message="INITIALIZING COMMAND CENTER..." />;
  if (error) return <ErrorState message={error} onRetry={refetchAll} />;
  if (!cameras.length && !incidents.length) return <EmptyState icon="dashboard" title="No Data Available" description="System data has not loaded yet." />;

  const onlineCams = cameras.filter(c => c.status === 'online').length;
  const offlineCams = cameras.filter(c => c.status === 'offline').length;
  const warningCams = cameras.filter(c => c.status === 'warning').length;

  const activeIncidents = incidents.filter(i => i.status !== 'resolved');
  const criticalIncidents = activeIncidents.filter(i => i.severity === 'critical');
  const highIncidents = activeIncidents.filter(i => i.severity === 'high');

  const totalPeople = cameras.reduce((s, c) => s + (c.detections?.people || 0), 0);
  const totalVehicles = cameras.reduce((s, c) => s + (c.detections?.vehicles || 0), 0);
  const totalMotorcycles = cameras.reduce((s, c) => s + (c.detections?.motorcycles || 0), 0);

  const displayCams = cameras.slice(0, 6);
  const feedCameras = displayCams.map((cam) => ({ cam, boxes: liveBoxes[cam.id] || [] }));

  const latestIncidents = [...incidents]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 8);

  const allTimeline = [...incidents]
    .flatMap(inc => inc.timeline.map(t => ({ ...t, incidentId: inc.id })))
    .sort((a, b) => b.time.localeCompare(a.time))
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <PageHeader icon="security" title="COMMAND CENTER" subtitle="SENTINEL AI — REAL-TIME TACTICAL OVERVIEW">
          <div className="flex items-center gap-2 ml-4">
            <span className="inline-flex items-center gap-1.5 bg-error-container/60 text-on-error-container font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
              <span className="h-1.5 w-1.5 rounded-full bg-error animate-pulse" />
              DEFCON 3
            </span>
          </div>
        </PageHeader>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[15px]">download</span>
            EXPORT SITREP
          </button>
          <button className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[15px]">filter_list</span>
            FILTER VIEW
          </button>
          <button className="inline-flex items-center gap-1.5 bg-error-container/60 border border-error/30 text-on-error-container font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-error-container transition-colors">
            <span className="material-symbols-outlined text-[15px]">add_alert</span>
            INCIDENT TRIGGER
          </button>
          <button
            onClick={handleRunDemo}
            disabled={demoRunning}
            className="inline-flex items-center gap-1.5 bg-secondary-container/60 border border-secondary/30 text-on-secondary-container font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-secondary-container transition-colors disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[15px]">play_arrow</span>
            {demoRunning ? 'RUNNING DEMO...' : 'RUN DEMO TEST'}
          </button>
          <button
            onClick={handleResetDemo}
            disabled={demoResetting}
            className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[15px]">restart_alt</span>
            {demoResetting ? 'RESETTING...' : 'RESET DEMO'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <KPITile icon="videocam" label="ACTIVE CAMERAS" value={onlineCams} sub={`${offlineCams} offline · ${warningCams} warning`} accent="text-secondary">
          <div className="flex gap-0.5 mt-1">
            {cameras.slice(0, 12).map((c, i) => (
              <div key={i} className={`h-1 flex-1 rounded-full ${c.status === 'online' ? 'bg-secondary' : c.status === 'warning' ? 'bg-tertiary' : 'bg-outline/40'}`} />
            ))}
          </div>
        </KPITile>

        <KPITile icon="report" label="ACTIVE INCIDENTS" value={activeIncidents.length} sub={`${criticalIncidents.length} critical · ${highIncidents.length} high`} accent="text-error">
          <div className="w-full bg-surface-container-lowest rounded-full h-1.5 mt-1">
            <div className="bg-error h-1.5 rounded-full" style={{ width: `${Math.min((criticalIncidents.length / Math.max(activeIncidents.length, 1)) * 100, 100)}%` }} />
          </div>
        </KPITile>

        <KPITile icon="person" label="PEOPLE DETECTED" value={(analytics?.people_detected ?? totalPeople).toLocaleString()} sub="pedestrians & cyclists" accent="text-primary">
          <div className="flex gap-2 mt-1">
            <span className="font-label-xs text-outline text-[9px]">{Math.round(totalPeople * 0.78)} ped</span>
            <span className="font-label-xs text-outline text-[9px]">{Math.round(totalPeople * 0.22)} cycle</span>
          </div>
        </KPITile>

        <KPITile icon="directions_car" label="VEHICLES" value={(analytics?.vehicles_detected ?? totalVehicles).toLocaleString()} sub={`${totalMotorcycles} motorcycles`} accent="text-tertiary">
          <div className="flex gap-2 mt-1">
            <span className="font-label-xs text-outline text-[9px]">{Math.round(totalVehicles * 0.45)} sedan</span>
            <span className="font-label-xs text-outline text-[9px]">{Math.round(totalVehicles * 0.30)} van</span>
            <span className="font-label-xs text-outline text-[9px]">{Math.round(totalVehicles * 0.25)} truck</span>
          </div>
        </KPITile>

        <KPITile icon="neurology" label="AI EVENTS TODAY" value={(analytics?.events ?? 0).toLocaleString()} sub={`${analytics?.aiModelPerformance?.accuracy ?? 0}% accuracy`} accent="text-secondary-fixed">
          <div className="flex flex-col gap-0.5 mt-1">
            {(analytics?.event_categories || []).slice(0, 2).map((cat, idx) => (
              <div key={idx} className="flex justify-between">
                <span className="font-label-xs text-outline text-[9px]">{cat.category || cat.type || 'Event'}</span>
                <span className="font-label-xs text-on-surface text-[9px]">{(cat.count ?? 0).toLocaleString()}</span>
              </div>
            ))}
            {!(analytics?.eventCategories || []).length && (
              <>
                <div className="flex justify-between"><span className="font-label-xs text-outline text-[9px]">Detection</span><span className="font-label-xs text-on-surface text-[9px]">—</span></div>
                <div className="flex justify-between"><span className="font-label-xs text-outline text-[9px]">Classification</span><span className="font-label-xs text-on-surface text-[9px]">—</span></div>
              </>
            )}
          </div>
        </KPITile>

        <KPITile icon="monitor_health" label="SYSTEM HEALTH" value={`${systemHealth?.overall || 98.7}%`} sub={`${systemHealth?.fps || 58.4} FPS · ${systemHealth?.latency || 12}ms`} accent="text-secondary">
          <div className="flex gap-2 mt-1">
            <span className="font-label-xs text-secondary text-[9px]">● NOMINAL</span>
          </div>
        </KPITile>

        <KPITile icon="list" label="WATCHLIST ENTRIES" value={(watchlists || []).length} sub={`${(alerts || []).filter(a => a.severity === 'critical').length} critical alerts`} accent="text-tertiary">
          <div className="flex gap-2 mt-1">
            <span className="font-label-xs text-outline text-[9px]">{(watchlists || []).filter(w => w.category === 'vehicle').length} vehicles</span>
            <span className="font-label-xs text-outline text-[9px]">{(watchlists || []).filter(w => w.category === 'person').length} persons</span>
          </div>
        </KPITile>

        <KPITile icon="route" label="ACTIVE TRACKS" value={(tracks || []).filter(t => t.status === 'active').length} sub={`${(alerts || []).length} total alerts`} accent="text-secondary">
          <div className="flex gap-2 mt-1">
            <span className="font-label-xs text-secondary text-[9px]">● TRACKING</span>
          </div>
        </KPITile>
      </div>

      {demoResult && (
        <div className={`rounded-lg border px-4 py-3 flex items-start gap-3 ${demoResult.status === 'completed' ? 'bg-secondary-container/20 border-secondary/30' : 'bg-error-container/20 border-error/30'}`}>
          <span className={`material-symbols-outlined text-[18px] ${demoResult.status === 'completed' ? 'text-secondary' : 'text-error'}`}>
            {demoResult.status === 'completed' ? 'check_circle' : 'error'}
          </span>
          <div className="min-w-0 flex-1">
            <span className="font-label-xs text-on-surface text-[11px] block">
              {demoResult.status === 'completed'
                ? `Demo test completed: ${demoResult.route?.length || 0} hops, ${demoResult.alerts_created} alerts, track ${demoResult.track_id || '—'}`
                : `Demo error: ${demoResult.message || 'Unknown error'}`
              }
            </span>
            {demoResult.status === 'completed' && (
              <span className="font-label-xs text-outline text-[9px] block mt-0.5">
                Plate: {demoResult.normalized} · Evidence snapshots: {demoResult.evidence_snapshots_created} · First seen: {demoResult.first_seen ? new Date(demoResult.first_seen).toLocaleTimeString([], { hour12: false }) : '—'}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-label-xs text-outline tracking-wider">CAMERA FEED MATRIX</span>
            <div className="flex items-center gap-1 bg-surface-container rounded-lg p-0.5">
              <button
                onClick={() => setFeedView('grid')}
                className={`px-2 py-1 rounded font-label-xs text-[10px] transition-colors ${feedView === 'grid' ? 'bg-surface-container-high text-on-surface' : 'text-outline hover:text-on-surface-variant'}`}
              >
                <span className="material-symbols-outlined text-[14px]">grid_view</span>
              </button>
              <button
                onClick={() => setFeedView('list')}
                className={`px-2 py-1 rounded font-label-xs text-[10px] transition-colors ${feedView === 'list' ? 'bg-surface-container-high text-on-surface' : 'text-outline hover:text-on-surface-variant'}`}
              >
                <span className="material-symbols-outlined text-[14px]">view_list</span>
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {feedCameras.map(({ cam, boxes }) => (
              <CameraFeedCard key={cam.id} cam={cam} boxes={boxes} />
            ))}
          </div>
        </div>

        <div className="lg:col-span-4 space-y-4">
          <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/20">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-error">notification_important</span>
                <span className="font-label-xs text-on-surface tracking-wider">LIVE INCIDENTS</span>
              </div>
              <span className="font-label-xs text-error bg-error-container/30 px-2 py-0.5 rounded text-[9px]">{activeIncidents.length} ACTIVE</span>
            </div>
            <div className="p-3 space-y-2 max-h-[380px] overflow-y-auto">
              {latestIncidents.length === 0 ? (
                <p className="font-body-sm text-outline text-center py-4 text-[11px]">No incidents</p>
              ) : (
                latestIncidents.map(inc => (
                  <IncidentFeedItem key={inc.id} inc={inc} />
                ))
              )}
            </div>
          </div>

          <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
              <span className="material-symbols-outlined text-[16px] text-primary">timeline</span>
              <span className="font-label-xs text-on-surface tracking-wider">ACTIVITY TIMELINE</span>
            </div>
            <div className="p-4 max-h-[280px] overflow-y-auto">
              {allTimeline.map((event, idx) => (
                <TimelineItem key={`${event.incidentId}-${idx}`} event={event} isLast={idx === allTimeline.length - 1} />
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 px-4 py-2.5 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[14px] text-outline">lock</span>
          <span className="font-label-xs text-outline text-[9px] tracking-wider">PRIVACY MODE</span>
          <span className="h-1.5 w-1.5 rounded-full bg-secondary" />
        </div>
        <div className="flex items-center gap-2">
          <span className="font-label-xs text-outline text-[9px] tracking-wider">CV PIPELINE:</span>
          <span className="font-label-xs text-on-surface-variant text-[9px]">cv.sentinel.internal:8443</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-label-xs text-outline text-[9px] tracking-wider">FASTAPI:</span>
          <span className="font-label-xs text-secondary text-[9px]">● CONNECTED</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-label-xs text-outline text-[9px] tracking-wider">LATENCY:</span>
          <span className="font-label-xs text-on-surface-variant text-[9px]">{systemHealth?.latency || 12}ms</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-label-xs text-outline text-[9px] tracking-wider">PKT LOSS:</span>
          <span className="font-label-xs text-secondary text-[9px]">{systemHealth?.packetLoss || 0.0}%</span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <span className="font-label-xs text-outline text-[9px] tracking-wider">GPU:</span>
          <span className="font-label-xs text-on-surface-variant text-[9px]">{systemHealth?.gpu?.utilization || 72}% · {systemHealth?.gpu?.temperature || 68}°C</span>
        </div>
      </div>
    </div>
  );
}
