import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';

function LiveTile({ cam }) {
  const navigate = useNavigate();
  const total = (cam.detections?.people || 0) + (cam.detections?.vehicles || 0) + (cam.detections?.motorcycles || 0);
  const statusColor = cam.status === 'online' ? 'bg-emerald-400' : cam.status === 'warning' ? 'bg-amber-400' : 'bg-red-500';
  const lastSeen = cam.lastSeen ? new Date(cam.lastSeen).toLocaleTimeString([], { hour12: false }) : '—';

  return (
    <div
      className="rounded-lg border border-outline-variant/30 overflow-hidden flex flex-col bg-surface-container cursor-pointer hover:border-outline-variant/60"
      onClick={() => navigate(`/cameras/${cam.id}?fs=1`)}
      title={`Open ${cam.id} in fullscreen`}
    >
      <div className="relative aspect-video bg-surface-container-low">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-tertiary/5" />
        <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-surface-container-lowest/80 rounded px-2 py-0.5">
          <span className={`h-1.5 w-1.5 rounded-full ${statusColor}`} />
          <span className="font-label-xs text-on-surface text-[9px]">{cam.id}</span>
        </div>
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between">
          <span className="font-label-xs text-on-surface/70 text-[9px] bg-surface-container-lowest/60 rounded px-1.5 py-0.5 truncate max-w-[60%]">{cam.name}</span>
          <span className="font-label-xs text-on-surface/50 text-[9px]">{cam.fps} FPS</span>
        </div>
        <div className="absolute top-2 right-2 flex flex-col items-end gap-0.5">
          {cam.aiEnabled && (
            <span className="bg-primary/80 text-on-primary font-label-xs text-[7px] px-1 py-px rounded">AI</span>
          )}
        </div>
      </div>
      <div className="px-3 py-2 flex items-center justify-between bg-surface-container-low">
        <div className="flex items-center gap-2">
          <span className="font-label-xs text-on-surface-variant text-[10px]">{total} detections</span>
        </div>
        <span className="font-label-xs text-outline text-[8px]">last: {lastSeen}</span>
      </div>
    </div>
  );
}

export default function LiveWall() {
  const { cameras, loading } = useApp();

  if (loading) return <LoadingState message="LOADING LIVE WALL..." />;

  const display = cameras.slice(0, 20);
  const onlineCount = cameras.filter(c => c.status === 'online').length;

  return (
    <div className="space-y-5">
      <PageHeader icon="wallpaper" title="LIVE WALL" subtitle={`${cameras.length} CAMERAS · ${onlineCount} ONLINE`}>
        <span className="ml-4 inline-flex items-center gap-1.5 bg-primary-container/20 text-primary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded border border-primary/20">
          <span className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
          FEED ACTIVE
        </span>
      </PageHeader>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {display.map(cam => (
          <LiveTile key={cam.id} cam={cam} />
        ))}
      </div>

      {cameras.length > 20 && (
        <p className="font-label-xs text-outline text-center text-[10px]">Showing 20 of {cameras.length} cameras. Full grid in production.</p>
      )}
    </div>
  );
}