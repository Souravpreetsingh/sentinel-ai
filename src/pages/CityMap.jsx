import { useState, useEffect, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { getGISCameras, getGISRoute, getGISSummary } from '../services/api';
import PageHeader from '../components/shared/PageHeader';

function MapButton({ icon, label, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider hover:bg-surface-container-highest transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <span className="material-symbols-outlined text-[15px] text-primary">{icon}</span>
      {label}
    </button>
  );
}

const LIFECYCLE_STYLE = {
  ACTIVE: { dot: 'bg-emerald-400', ring: 'border-emerald-400/40', label: 'ONLINE' },
  DEGRADED: { dot: 'bg-amber-400', ring: 'border-amber-400/40', label: 'DEGRADED' },
  OFFLINE: { dot: 'bg-red-500', ring: 'border-red-500/40', label: 'OFFLINE' },
  MAINTENANCE: { dot: 'bg-sky-400', ring: 'border-sky-400/40', label: 'MAINTENANCE' },
  DISABLED: { dot: 'bg-gray-400', ring: 'border-gray-400/40', label: 'DISABLED' },
};

function camToPercent(cam) {
  const lat = cam.latitude;
  const lon = cam.longitude;
  // Simple Mercator-lite projection for demo. Normalise to 5-95% range.
  const minLat = 12, maxLat = 32, minLon = 70, maxLon = 92;
  const x = ((lon - minLon) / (maxLon - minLon)) * 90 + 5;
  const y = (1 - (lat - minLat) / (maxLat - minLat)) * 90 + 5;
  return { x: Math.max(2, Math.min(98, x)), y: Math.max(2, Math.min(98, y)) };
}

export default function CityMap() {
  const { cameras = [] } = useApp();
  const [zoom, setZoom] = useState(1);
  const [activeMarker, setActiveMarker] = useState(null);
  const [gisCameras, setGisCameras] = useState([]);
  const [route, setRoute] = useState(null);
  const [summary, setSummary] = useState(null);
  const [showRoute, setShowRoute] = useState(false);

  useEffect(() => {
    getGISCameras().then(setGisCameras).catch(() => {});
    getGISSummary().then(setSummary).catch(() => {});
  }, []);

  useEffect(() => {
    if (showRoute) {
      getGISRoute('GJ01AB1234').then(setRoute).catch(() => {});
    } else {
      setRoute(null);
    }
  }, [showRoute]);

  const markers = useMemo(() => {
    if (gisCameras.length === 0) {
      return cameras.slice(0, 52).map(cam => {
        const pos = camToPercent({ latitude: 0, longitude: 0 });
        return { ...cam, x: pos.x, y: pos.y, lifecycle: cam.status === 'online' ? 'ACTIVE' : cam.status === 'warning' ? 'DEGRADED' : 'OFFLINE' };
      });
    }
    return gisCameras.map(cam => {
      const pos = camToPercent(cam);
      return { ...cam, x: pos.x, y: pos.y, lifecycle: cam.lifecycle || 'ACTIVE' };
    });
  }, [gisCameras, cameras]);

  const onlineCount = markers.filter(m => m.lifecycle === 'ACTIVE').length;
  const degradedCount = markers.filter(m => m.lifecycle === 'DEGRADED').length;
  const offlineCount = markers.filter(m => ['OFFLINE', 'DISABLED'].includes(m.lifecycle)).length;

  const routePoints = useMemo(() => {
    if (!route?.points?.length) return [];
    return route.points.map(p => ({
      ...p,
      ...camToPercent(p),
    }));
  }, [route]);

  return (
    <div className="space-y-5">
      <PageHeader icon="map" title="CITY MAP" subtitle={`${markers.length} CAMERAS · GEO-SPATIAL INTELLIGENCE`}>
        <span className="inline-flex items-center gap-1.5 bg-primary-container/20 text-primary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded border border-primary/20">
          <span className="material-symbols-outlined text-[12px]">my_location</span>
          GIS OVERLAY
        </span>
      </PageHeader>

      <div className="flex flex-col lg:flex-row gap-4">
        <div className="relative flex-1 min-h-[600px] rounded-xl border border-outline-variant/30 bg-surface-container-lowest overflow-hidden">
          <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(62,72,80,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(62,72,80,0.18) 1px, transparent 1px)', backgroundSize: '44px 44px' }} />
          <div className="absolute inset-0 transition-transform duration-300" style={{ transform: `scale(${zoom})` }}>
            {/* Route overlay */}
            {showRoute && routePoints.length > 1 && (
              <svg className="absolute inset-0 w-full h-full z-10 pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                <polyline
                  points={routePoints.map(p => `${p.x},${p.y}`).join(' ')}
                  fill="none"
                  stroke="rgb(234,179,8)"
                  strokeWidth="0.4"
                  strokeDasharray="1,0.5"
                  strokeLinecap="round"
                />
                {routePoints.map((p, i) => (
                  <g key={i}>
                    <circle cx={p.x} cy={p.y} r="0.7" fill="rgb(234,179,8)" stroke="white" strokeWidth="0.2" />
                    <text x={p.x + 1} y={p.y - 0.8} fill="white" fontSize="1.2" fontFamily="monospace">{i + 1}</text>
                  </g>
                ))}
              </svg>
            )}

            {/* Camera markers */}
            {markers.map((m) => {
              const style = LIFECYCLE_STYLE[m.lifecycle] || LIFECYCLE_STYLE.ACTIVE;
              const isActive = activeMarker === m.id;
              return (
                <div key={m.id} className="absolute group z-20" style={{ left: `${m.x}%`, top: `${m.y}%` }} onMouseEnter={() => setActiveMarker(m.id)} onMouseLeave={() => setActiveMarker(null)}>
                  <span className={`relative block h-3 w-3 rounded-full border-2 border-surface ${style.dot} shadow-lg ${m.lifecycle === 'OFFLINE' ? 'opacity-60' : ''}`} />
                  <div className={`absolute left-1/2 -translate-x-1/2 bottom-6 z-30 w-44 rounded-md bg-surface-container-high border border-outline-variant/40 px-2.5 py-2 shadow-xl transition-opacity ${isActive ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                      <span className="font-label-xs text-on-surface text-[9px]">{m.id} — {m.name}</span>
                    </div>
                    <p className="font-label-xs text-outline text-[8px] tracking-wider mt-0.5">{m.district || '—'} · {m.zone || '—'} · {m.road || '—'}</p>
                    <p className="font-label-xs text-outline text-[8px] tracking-wider mt-0.5">{style.label} · {m.vendor || '—'} {m.protocol || ''}</p>
                    {m.ai_enabled && <span className="inline-block bg-primary/80 text-on-primary font-label-xs text-[7px] px-1 py-px rounded mt-0.5">AI ENABLED</span>}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="absolute bottom-4 left-4 rounded-lg bg-surface-container/95 border border-outline-variant/30 px-4 py-3 z-10">
            <span className="font-label-xs text-outline text-[9px] tracking-wider">CAMERA LEGEND</span>
            <div className="flex flex-col gap-1.5 mt-2">
              {[
                { key: 'ACTIVE', label: 'ONLINE', count: onlineCount, dot: 'bg-emerald-400' },
                { key: 'DEGRADED', label: 'DEGRADED', count: degradedCount, dot: 'bg-amber-400' },
                { key: 'OFFLINE', label: 'OFFLINE', count: offlineCount, dot: 'bg-red-500' },
              ].map(l => (
                <div key={l.key} className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${l.dot}`} />
                  <span className="font-label-xs text-on-surface-variant text-[9px] tracking-wider">{l.label}</span>
                  <span className="font-label-xs text-outline text-[9px] ml-auto">{l.count}</span>
                </div>
              ))}
              {routePoints.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-yellow-400" />
                  <span className="font-label-xs text-on-surface-variant text-[9px] tracking-wider">TEST ROUTE</span>
                  <span className="font-label-xs text-outline text-[9px] ml-auto">{routePoints.length} hops</span>
                </div>
              )}
            </div>
          </div>

          <div className="absolute top-3 right-3 bg-surface-container/90 border border-outline-variant/30 rounded px-2 py-1 z-10">
            <span className="font-label-xs text-outline text-[8px] tracking-wider">
              {summary ? `${summary.camera_total} CAMERAS · ${summary.camera_online} ONLINE · ${summary.tracked_vehicles} TRACKED` : 'LOADING GIS...'}
            </span>
          </div>
        </div>

        <div className="w-full lg:w-60 space-y-4 flex-shrink-0">
          <div className="bg-surface-container rounded-lg border border-outline-variant/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-[16px] text-primary">control_camera</span>
              <span className="font-label-xs text-on-surface tracking-wider">MAP CONTROLS</span>
            </div>
            <div className="space-y-2">
              <MapButton icon="add" label="ZOOM +" onClick={() => setZoom(z => Math.min(z + 0.25, 2))} disabled={zoom >= 2} />
              <MapButton icon="remove" label="ZOOM -" onClick={() => setZoom(z => Math.max(z - 0.25, 0.5))} disabled={zoom <= 0.5} />
              <MapButton icon="center_focus" label="RESET VIEW" onClick={() => setZoom(1)} />
            </div>
            <div className="mt-3 pt-3 border-t border-outline-variant/20">
              <div className="flex justify-between mb-1">
                <span className="font-label-xs text-outline text-[8px] tracking-wider">CURRENT ZOOM</span>
                <span className="font-label-xs text-primary text-[8px]">{Math.round(zoom * 100)}%</span>
              </div>
              <div className="h-1 bg-surface-container-lowest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: `${((zoom - 0.5) / 1.5) * 100}%` }} />
              </div>
            </div>
          </div>

          <div className="bg-surface-container rounded-lg border border-outline-variant/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-[16px] text-secondary">layers</span>
              <span className="font-label-xs text-on-surface tracking-wider">LAYER OVERLAYS</span>
            </div>
            <div className="space-y-2.5">
              {[
                { key: 'CCTV COVERAGE', on: true },
                { key: 'TEST VEHICLE ROUTE', on: showRoute, onClick: () => setShowRoute(!showRoute) },
                { key: 'ALERT RADIUS', on: true },
                { key: 'SECTOR BOUNDARIES', on: true },
              ].map(layer => (
                <div key={layer.key} className="flex items-center justify-between cursor-pointer" onClick={layer.onClick}>
                  <span className={`font-label-xs text-[9px] tracking-wider ${layer.on ? 'text-on-surface-variant' : 'text-outline/50'}`}>{layer.key}</span>
                  <span className={`h-1.5 w-1.5 rounded-full ${layer.on ? 'bg-secondary' : 'bg-outline/40'}`} />
                </div>
              ))}
            </div>
          </div>

          {summary && (
            <div className="rounded-lg border border-outline-variant/30 bg-surface-container-low px-3 py-2.5">
              <span className="font-label-xs text-outline text-[8px] leading-relaxed block">
                TOTAL: {summary.camera_total} cameras · {summary.alert_total} alerts · {summary.tracked_vehicles} tracked vehicles
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}