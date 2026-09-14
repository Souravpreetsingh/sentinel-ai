import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';

function CameraCard({ cam }) {
  const navigate = useNavigate();
  const isCritical = cam.id === 'CAM-07';
  const isWarning = cam.id === 'CAM-09';
  const isOffline = cam.status === 'offline';
  const total = (cam.detections?.people || 0) + (cam.detections?.vehicles || 0) + (cam.detections?.motorcycles || 0);

  const gradients = {
    'CAM-01': 'from-blue-900/30 to-slate-900/40',
    'CAM-02': 'from-orange-900/30 to-red-950/40',
    'CAM-03': 'from-indigo-900/30 to-slate-900/40',
    'CAM-04': 'from-cyan-900/30 to-slate-900/40',
    'CAM-05': 'from-emerald-900/30 to-slate-900/40',
    'CAM-06': 'from-teal-900/30 to-slate-900/40',
    'CAM-07': 'from-red-900/40 to-slate-900/40',
    'CAM-08': 'from-purple-900/30 to-slate-900/40',
    'CAM-09': 'from-amber-900/30 to-slate-900/40',
    'CAM-10': 'from-sky-900/30 to-slate-900/40',
    'CAM-12': 'from-violet-900/30 to-slate-900/40',
    'CAM-15': 'from-rose-900/30 to-slate-900/40',
  };

  return (
    <div
      className={`rounded-xl border overflow-hidden flex flex-col transition-all cursor-pointer ${
        isCritical ? 'border-error ring-2 ring-error/30' :
        isWarning ? 'border-tertiary/60 ring-1 ring-tertiary/30' :
        isOffline ? 'border-outline/30 opacity-60' :
        'border-outline-variant/30 hover:border-outline-variant/50'
      }`}
      onClick={() => navigate(`/cameras/${cam.id}?fs=1`)}
      title={`Open ${cam.id} in fullscreen`}
    >
      <div className="px-4 py-3 flex items-center justify-between border-b border-outline-variant/20 bg-surface-container">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`h-2 w-2 rounded-full flex-shrink-0 ${
            cam.status === 'online' ? 'bg-secondary' :
            cam.status === 'warning' ? 'bg-tertiary' : 'bg-outline'
          }`} />
          <div className="min-w-0">
            <div className="font-label-sm text-on-surface text-[11px]">{cam.id}</div>
            <div className="font-body-sm text-outline text-[10px] truncate">{cam.name}</div>
          </div>
        </div>
        <span className="font-label-xs text-outline bg-surface-container-high px-2 py-0.5 rounded text-[9px]">{cam.resolution}</span>
      </div>

      <div className={`relative aspect-video bg-gradient-to-br ${gradients[cam.id] || 'from-slate-900/40 to-surface-container-low'} ${isOffline ? 'flex items-center justify-center' : ''}`}>
        {isOffline ? (
          <div className="flex flex-col items-center gap-2">
            <span className="material-symbols-outlined text-[40px] text-outline/60">videocam_off</span>
            <span className="font-label-xs text-outline text-[10px] tracking-wider">FEED UNAVAILABLE</span>
            <span className="font-body-sm text-outline/60 text-[10px]">Camera disconnected at 18:42:11</span>
          </div>
        ) : (
          <>
            <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-surface-container-lowest/80 rounded px-2 py-1">
              <span className="material-symbols-outlined text-[12px] text-primary">radio_button_checked</span>
              <span className="font-label-xs text-on-surface text-[9px] tracking-wider">LIVE</span>
            </div>
            <div className="absolute top-2 right-2">
              <span className="font-label-xs text-on-surface/50 bg-surface-container-lowest/60 rounded px-1.5 py-0.5 text-[9px]">{cam.fps} FPS</span>
            </div>
            <div className="absolute bottom-2 left-2 right-2 flex items-center gap-1.5">
              {cam.aiCapabilities.slice(0, 3).map(cap => (
                <span key={cap} className="font-label-xs text-primary/80 bg-surface-container-lowest/70 rounded px-1.5 py-0.5 text-[8px] uppercase">{cap}</span>
              ))}
              {cam.aiCapabilities.length > 3 && (
                <span className="font-label-xs text-outline bg-surface-container-lowest/70 rounded px-1.5 py-0.5 text-[8px]">+{cam.aiCapabilities.length - 3}</span>
              )}
            </div>
            {isCritical && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="bg-error-container/90 rounded-lg px-3 py-2 flex items-center gap-2 animate-pulse">
                  <span className="material-symbols-outlined text-[16px] text-on-error-container">warning</span>
                  <span className="font-label-xs text-on-error-container text-[10px] tracking-wider">INTRUSION ALERT</span>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="bg-surface-container px-4 py-3 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px] text-outline">person</span>
              <span className="font-label-xs text-on-surface-variant text-[10px]">{cam.detections?.people || 0}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px] text-outline">directions_car</span>
              <span className="font-label-xs text-on-surface-variant text-[10px]">{cam.detections?.vehicles || 0}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px] text-outline">two_wheeler</span>
              <span className="font-label-xs text-on-surface-variant text-[10px]">{cam.detections?.motorcycles || 0}</span>
            </div>
          </div>
          <span className="font-label-xs text-outline text-[9px]">{total} total</span>
        </div>
        <div className="flex items-center gap-2 pt-1 border-t border-outline-variant/20">
          <div className="flex items-center gap-1 min-w-0 flex-1">
            <span className="font-label-xs text-outline text-[9px] truncate">{cam.location}</span>
          </div>
          <div className="flex items-center gap-1">
            <button aria-label={`Open ${cam.id} fullscreen`} className="p-1 rounded hover:bg-surface-container-highest transition-colors" onClick={() => navigate(`/cameras/${cam.id}?fs=1`)}>
              <span className="material-symbols-outlined text-[14px] text-outline">fullscreen</span>
            </button>
            <button className="p-1 rounded hover:bg-surface-container-highest transition-colors">
              <span className="material-symbols-outlined text-[14px] text-outline">settings</span>
            </button>
            <button className="p-1 rounded hover:bg-surface-container-highest transition-colors">
              <span className="material-symbols-outlined text-[14px] text-outline">more_vert</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Cameras() {
  const { cameras, loading, error, refetchCameras } = useApp();
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('grid');

  const onlineCount = cameras.filter(c => c.status === 'online').length;
  const warningCount = cameras.filter(c => c.status === 'warning').length;
  const offlineCount = cameras.filter(c => c.status === 'offline').length;

  const filtered = useMemo(() => {
    let list = cameras;
    if (statusFilter === 'online') list = list.filter(c => c.status === 'online');
    else if (statusFilter === 'warning') list = list.filter(c => c.status === 'warning');
    else if (statusFilter === 'offline') list = list.filter(c => c.status === 'offline');
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(c =>
        `${c.id} ${c.name} ${c.sector} ${c.location}`.toLowerCase().includes(q)
      );
    }
    return list;
  }, [cameras, statusFilter, searchQuery]);

  if (loading) return <LoadingState message="LOADING CAMERA DIRECTORY..." />;
  if (error) return <ErrorState message={error} onRetry={refetchCameras} />;

  return (
    <div className="space-y-5">
      <PageHeader icon="videocam" title="LIVE CAMERAS MANAGEMENT & STREAM DIRECTORY" subtitle="SENTINEL AI — RTSP STREAM INFRASTRUCTURE">
        <span className="inline-flex items-center gap-1.5 bg-primary-container/20 text-primary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded border border-primary/20">
          <span className="material-symbols-outlined text-[12px]">dns</span>
          RTSP CORE
        </span>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        <button className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors">
          <span className="material-symbols-outlined text-[15px]">tune</span>
          BATCH CALIBRATE
        </button>
        <button className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors">
          <span className="material-symbols-outlined text-[15px]">upload_file</span>
          EXPORT MANIFEST
        </button>
        <button className="inline-flex items-center gap-1.5 bg-primary-container/20 border border-primary/30 text-primary font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-primary-container/30 transition-colors">
          <span className="material-symbols-outlined text-[15px]">add</span>
          ADD NODE
        </button>
      </div>

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 px-4 py-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 flex-wrap">
          {[
            { key: 'all', label: 'ALL CAMERAS', count: cameras.length },
            { key: 'online', label: 'ONLINE', count: onlineCount },
            { key: 'warning', label: 'ALERT', count: warningCount },
            { key: 'offline', label: 'OFFLINE', count: offlineCount },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`inline-flex items-center gap-1.5 font-label-xs text-[10px] tracking-wider px-3 py-1.5 rounded-lg transition-colors ${
                statusFilter === f.key
                  ? 'bg-primary-container/20 text-primary border border-primary/30'
                  : 'text-outline hover:text-on-surface-variant hover:bg-surface-container-high border border-transparent'
              }`}
            >
              {f.label}
              <span className={`text-[9px] px-1.5 py-0 rounded ${statusFilter === f.key ? 'bg-primary/20' : 'bg-surface-container-high'}`}>{f.count}</span>
            </button>
          ))}
        </div>

        <div className="flex-1 min-w-[200px] max-w-xs">
          <div className="flex items-center gap-2 bg-surface-container-low border border-outline-variant/30 rounded-lg px-3 py-1.5">
            <span className="material-symbols-outlined text-[14px] text-outline">search</span>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="FIND://"
              className="bg-transparent font-label-xs text-on-surface text-[11px] outline-none w-full placeholder:text-outline/50"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1 bg-surface-container-high border border-outline-variant/30 text-on-surface-variant font-label-xs text-[10px] px-2.5 py-1.5 rounded-lg hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[14px]">apartment</span>
            SECTOR
            <span className="material-symbols-outlined text-[12px] text-outline">expand_more</span>
          </button>
          <button className="flex items-center gap-1 bg-surface-container-high border border-outline-variant/30 text-on-surface-variant font-label-xs text-[10px] px-2.5 py-1.5 rounded-lg hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[14px]">neurology</span>
            AI CAPABILITY
            <span className="material-symbols-outlined text-[12px] text-outline">expand_more</span>
          </button>
          <button className="flex items-center gap-1 bg-surface-container-high border border-outline-variant/30 text-on-surface-variant font-label-xs text-[10px] px-2.5 py-1.5 rounded-lg hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined text-[14px]">aspect_ratio</span>
            RESOLUTION
            <span className="material-symbols-outlined text-[12px] text-outline">expand_more</span>
          </button>
        </div>

        <div className="flex items-center gap-1 ml-auto">
          <div className="flex items-center bg-surface-container-high rounded-lg p-0.5 border border-outline-variant/30">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded transition-colors ${viewMode === 'grid' ? 'bg-surface-container-highest text-on-surface' : 'text-outline hover:text-on-surface-variant'}`}
            >
              <span className="material-symbols-outlined text-[14px]">grid_view</span>
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded transition-colors ${viewMode === 'table' ? 'bg-surface-container-highest text-on-surface' : 'text-outline hover:text-on-surface-variant'}`}
            >
              <span className="material-symbols-outlined text-[14px]">view_list</span>
            </button>
          </div>
          <div className="flex items-center gap-1 bg-secondary/10 border border-secondary/20 rounded-lg px-2.5 py-1.5 ml-2">
            <span className="material-symbols-outlined text-[12px] text-secondary">speed</span>
            <span className="font-label-xs text-secondary text-[10px]">60 FPS</span>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon="videocam_off" title="No Cameras Found" description="No cameras match the current filter criteria." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(cam => (
            <CameraCard key={cam.id} cam={cam} />
          ))}
        </div>
      )}
    </div>
  );
}
