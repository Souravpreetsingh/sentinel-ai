import { useEffect, useMemo, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useFullscreen } from '../hooks/useFullscreen';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';

function BoundingBox({ label, confidence, top, left, width, height }) {
  return (
    <div
      className="absolute border-2 border-primary/80 rounded-sm"
      style={{ top: `${top}%`, left: `${left}%`, width: `${width}%`, height: `${height}%` }}
    >
      <div className="absolute -top-[22px] -left-[2px] bg-primary text-on-primary font-label-xs text-[9px] tracking-wider px-1.5 py-0.5 rounded-t whitespace-nowrap">
        {label} {confidence}%
      </div>
      <div className="absolute inset-0 pointer-events-none">
        <span className="absolute -top-1 -left-1 w-2.5 h-2.5 border-t-2 border-l-2 border-primary" />
        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 border-t-2 border-r-2 border-primary" />
        <span className="absolute -bottom-1 -left-1 w-2.5 h-2.5 border-b-2 border-l-2 border-primary" />
        <span className="absolute -bottom-1 -right-1 w-2.5 h-2.5 border-b-2 border-r-2 border-primary" />
      </div>
    </div>
  );
}

function Sparkline({ values }) {
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const pts = values
    .map((v, i) => `${(i / (values.length - 1)) * 100},${100 - ((v - min) / (max - min || 1)) * 100}`)
    .join(' ');
  return (
    <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="w-full h-10">
      <polyline
        points={pts}
        fill="none"
        stroke="#7bd0ff"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function InfoRow({ label, value, mono = true }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-outline-variant/15 last:border-0">
      <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">{label}</span>
      <span className={`text-on-surface-variant text-[11px] ${mono ? 'font-label-xs' : 'font-body-sm'} truncate ml-4 text-right`}>{value}</span>
    </div>
  );
}

export default function CameraDetail() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { cameras, loading, error, refetchCameras } = useApp();

  const cam = useMemo(
    () => cameras.find(c => c.id === String(id || '').toUpperCase()),
    [cameras, id]
  );

  const { ref: videoRef, isFullscreen, enterFullscreen, toggleFullscreen } = useFullscreen();

  const autoFullscreen = useRef(false);
  useEffect(() => {
    if (cam && searchParams.get('fs') === '1' && !autoFullscreen.current) {
      autoFullscreen.current = true;
      enterFullscreen();
    }
  }, [cam, searchParams, enterFullscreen]);

  if (loading) return <LoadingState message={`SCANNING STREAM ${id}...`} />;
  if (error) return <ErrorState message={error} onRetry={refetchCameras} />;
  if (!cam) {
    return (
      <div className="space-y-5">
        <PageHeader icon="videocam_off" title="CAMERA NOT FOUND" subtitle="SENTINEL AI — STREAM DIRECTORY" />
        <EmptyState
          icon="videocam_off"
          title={`No camera "${id}" registered`}
          description="Verify the camera ID and try again. The stream directory may have been updated since this link was created."
        />
      </div>
    );
  }

  const totalDetections = (cam.detections?.people || 0) + (cam.detections?.vehicles || 0) + (cam.detections?.motorcycles || 0);

  const detectionHistory = [
    { time: cam.lastSeen, type: 'person', confidence: 96.4 },
    { time: '2026-09-14T19:41:50Z', type: 'vehicle', confidence: 93.8 },
    { time: '2026-09-14T19:40:22Z', type: 'civilian', confidence: 91.2 },
    { time: '2026-09-14T19:38:05Z', type: 'person', confidence: 98.7 },
    { time: '2026-09-14T19:36:44Z', type: 'motorcycle', confidence: 89.5 },
    { time: '2026-09-14T19:34:18Z', type: 'person', confidence: 95.1 },
    { time: '2026-09-14T19:32:57Z', type: 'vehicle', confidence: 97.6 },
    { time: '2026-09-14T19:30:30Z', type: 'pedestrian', confidence: 94.3 },
    { time: '2026-09-14T19:28:12Z', type: 'person', confidence: 92.8 },
    { time: '2026-09-14T19:25:49Z', type: 'animal', confidence: 87.4 },
  ];

  const sparkValues = [72, 78, 75, 82, 88, 86, 92, 89, 95, 94, 97, 99];

  const ptzButtonBase = 'p-2 rounded hover:bg-surface-container-highest transition-colors text-outline hover:text-on-surface';

  return (
    <div className="space-y-5">
      <PageHeader icon="videocam" title={`CAMERA ${cam.id}`} subtitle={cam.location}>
        <PageHeaderCompat cam={cam} />
      </PageHeader>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-8 space-y-4">
          <div
            ref={videoRef}
            className={`relative overflow-hidden border border-outline-variant/30 bg-surface-container-low ${
              isFullscreen ? 'fixed inset-0 z-50 w-screen h-screen rounded-none border-0' : 'aspect-video rounded-xl'
            }`}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-tertiary/5" />

            <div className="absolute top-3 left-3 bg-surface-container-lowest/80 backdrop-blur rounded-lg px-3 py-2 border border-outline-variant/20">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${cam.status === 'online' ? 'bg-secondary animate-pulse' : cam.status === 'warning' ? 'bg-tertiary' : 'bg-outline'}`} />
                <span className="font-label-xs text-on-surface text-[10px] tracking-wider">{cam.id} — {cam.name}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="flex items-center gap-1 font-label-xs text-secondary text-[9px]">
                  <span className="material-symbols-outlined text-[10px]">radio_button_checked</span>
                  LIVE
                </span>
                <span className="flex items-center gap-1 font-label-xs text-outline text-[9px]">
                  <span className="material-symbols-outlined text-[10px]">schedule</span>
                  {new Date(cam.lastSeen).toLocaleTimeString([], { hour12: false })}
                </span>
                <span className="flex items-center gap-1 font-label-xs text-outline text-[9px]">
                  <span className="material-symbols-outlined text-[10px]">location_on</span>
                  {cam.sector}
                </span>
              </div>
            </div>

            <div className="absolute top-3 right-3 bg-surface-container-lowest/70 rounded-lg px-2.5 py-1.5 border border-outline-variant/20 text-right">
              <div className="font-label-xs text-on-surface text-[10px]">{cam.fps}.0 FPS</div>
              <div className="font-label-xs text-outline text-[9px]">{cam.bitrate} Mbps</div>
            </div>

            <div className="absolute top-3 right-3 mt-12 bg-surface-container-lowest/70 rounded-lg px-2.5 py-1.5 border border-outline-variant/20">
              <div className="font-label-xs text-tertiary text-[9px]">AI CONF 94.2%</div>
              <div className="font-label-xs text-outline text-[9px]">LAT 9.4ms · INF 12ms</div>
            </div>

            <div className="absolute inset-0 flex items-center justify-center">
              <span className="font-label-xs text-outline/40 text-[10px] tracking-[0.3em]">STREAM PREVIEW · {cam.resolution}</span>
            </div>

            <BoundingBox label={cam.type === 'thermal' ? 'HUMAN' : 'PEDESTRIAN'} confidence={96} top={30} left={18} width={22} height={38} />
            <BoundingBox label="VEHICLE" confidence={93} top={55} left={58} width={28} height={24} />
            <BoundingBox label="OBJECT" confidence={87} top={40} left={8} width={12} height={16} />

            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-surface-container-lowest/80 backdrop-blur rounded-lg px-2 py-1 flex items-center gap-3 border border-outline-variant/20">
              <button className="p-1 rounded hover:bg-surface-container-highest transition-colors text-outline hover:text-on-surface">
                <span className="material-symbols-outlined text-[14px]">volume_up</span>
              </button>
              <span className="font-label-xs text-outline text-[9px]">SENTINEL-{cam.id}</span>
              <button
                onClick={toggleFullscreen}
                aria-label={isFullscreen ? 'EXIT FULLSCREEN' : 'ENTER FULLSCREEN'}
                title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
                className="p-1 rounded hover:bg-surface-container-highest transition-colors text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[14px]">{isFullscreen ? 'fullscreen_exit' : 'fullscreen'}</span>
              </button>
              <button className="p-1 rounded hover:bg-surface-container-highest transition-colors text-outline hover:text-on-surface">
                <span className="material-symbols-outlined text-[14px]">record</span>
              </button>
            </div>
          </div>

          <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/20">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-primary">history</span>
                <span className="font-label-xs text-on-surface tracking-wider">DETECTION HISTORY — LAST 10</span>
              </div>
              <span className="font-label-xs text-outline text-[9px]">{totalDetections} TOTAL</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full font-label-xs text-[10px]">
                <thead>
                  <tr className="text-outline bg-surface-container-low border-b border-outline-variant/20">
                    <th className="text-left px-4 py-2 tracking-wider">#</th>
                    <th className="text-left px-4 py-2 tracking-wider">TIMESTAMP</th>
                    <th className="text-left px-4 py-2 tracking-wider">DETECTION TYPE</th>
                    <th className="text-right px-4 py-2 tracking-wider">CONFIDENCE</th>
                  </tr>
                </thead>
                <tbody>
                  {detectionHistory.map((det, i) => (
                    <tr key={i} className="border-b border-outline-variant/10 hover:bg-surface-container-low transition-colors">
                      <td className="px-4 py-2 text-outline">{String(i + 1).padStart(2, '0')}</td>
                      <td className="px-4 py-2 text-on-surface-variant">{new Date(det.time).toLocaleTimeString([], { hour12: false })}</td>
                      <td className="px-4 py-2 flex items-center gap-2">
                        <span className="material-symbols-outlined text-[12px] text-primary">
                          {det.type === 'person' || det.type === 'pedestrian' || det.type === 'civilian' ? 'person' : det.type === 'vehicle' ? 'directions_car' : det.type === 'motorcycle' ? 'two_wheeler' : 'pets'}
                        </span>
                        <span className="text-on-surface uppercase tracking-wider">{det.type}</span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-1 bg-surface-container-lowest rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${det.confidence > 95 ? 'bg-secondary' : det.confidence > 90 ? 'bg-primary' : 'bg-tertiary'}`} style={{ width: `${det.confidence}%` }} />
                          </div>
                          <span className="text-on-surface-variant w-12 text-right">{det.confidence.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="xl:col-span-4 space-y-4">
          <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
              <span className="material-symbols-outlined text-[16px] text-secondary">settings_input_component</span>
              <span className="font-label-xs text-on-surface tracking-wider">STREAM CONFIGURATION</span>
            </div>
            <div className="px-4 py-2">
              <InfoRow label="RTSP URL" value={cam.streamUrl} />
              <InfoRow label="Bitrate" value={`${cam.bitrate} Mbps`} />
              <InfoRow label="Codec" value="H.265 / HEVC" />
              <InfoRow label="GPU Backend" value={cam.type === 'thermal' ? 'RTX 4080 · Core 3' : 'RTX 4080 · Core 1'} />
              <InfoRow label="Neural Engine" value="TensorRT · YOLOv9b" />
              <InfoRow label="Sector" value={cam.sector} />
              <InfoRow label="Health" value={`${cam.health}%`} />
            </div>
          </div>

          <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
              <span className="material-symbols-outlined text-[16px] text-tertiary">gps_fixed</span>
              <span className="font-label-xs text-on-surface tracking-wider">PTZ CONTROL</span>
            </div>
            <div className="p-4 flex flex-col items-center gap-3">
              <div className="grid grid-cols-3 gap-1.5">
                <div />
                <button className={ptzButtonBase} aria-label="Pan up">
                  <span className="material-symbols-outlined text-[18px]">keyboard_arrow_up</span>
                </button>
                <div />
                <button className={ptzButtonBase} aria-label="Pan left">
                  <span className="material-symbols-outlined text-[18px]">keyboard_arrow_left</span>
                </button>
                <div className="p-2 rounded bg-surface-container-lowest border border-outline-variant/20 flex items-center justify-center">
                  <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                </div>
                <button className={ptzButtonBase} aria-label="Pan right">
                  <span className="material-symbols-outlined text-[18px]">keyboard_arrow_right</span>
                </button>
                <div />
                <button className={ptzButtonBase} aria-label="Pan down">
                  <span className="material-symbols-outlined text-[18px]">keyboard_arrow_down</span>
                </button>
                <div />
              </div>
              <div className="flex items-center gap-2 w-full">
                <button className="flex-1 p-2 rounded-lg bg-surface-container-high border border-outline-variant/30 hover:bg-surface-container-highest transition-colors flex items-center justify-center">
                  <span className="material-symbols-outlined text-[16px] text-outline">add</span>
                </button>
                <span className="font-label-xs text-outline text-[9px] tracking-wider">ZOOM</span>
                <button className="flex-1 p-2 rounded-lg bg-surface-container-high border border-outline-variant/30 hover:bg-surface-container-highest transition-colors flex items-center justify-center">
                  <span className="material-symbols-outlined text-[16px] text-outline">remove</span>
                </button>
              </div>
              <div className="flex items-center gap-2 w-full">
                <button className="flex-1 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant/30 hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-1">
                  <span className="material-symbols-outlined text-[12px] text-primary">center_focus</span>
                  <span className="font-label-xs text-on-surface text-[9px]">AUTO</span>
                </button>
                <button className="flex-1 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant/30 hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-1">
                  <span className="material-symbols-outlined text-[12px] text-tertiary">restart_alt</span>
                  <span className="font-label-xs text-on-surface text-[9px]">HOME</span>
                </button>
              </div>
            </div>
          </div>

          <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
              <span className="material-symbols-outlined text-[16px] text-primary">monitor_heart</span>
              <span className="font-label-xs text-on-surface tracking-wider">HEALTH METRICS</span>
            </div>
            <div className="px-4 py-3 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Uptime</span>
                <span className="font-label-xs text-secondary text-[11px]">99.{Math.round(cam.health)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Frame Rate</span>
                <span className="font-label-xs text-on-surface-variant text-[11px]">{cam.fps} FPS</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Latency</span>
                <span className="font-label-xs text-on-surface-variant text-[11px]">9.4ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Packet Loss</span>
                <span className="font-label-xs text-secondary text-[11px]">0.0%</span>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Signal Stability</span>
                  <span className="font-label-xs text-tertiary text-[10px]">12MS WINDOW</span>
                </div>
                <Sparkline values={sparkValues} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PageHeaderCompat({ cam }) {
  const statusColor =
    cam.status === 'online' ? 'bg-secondary' :
    cam.status === 'warning' ? 'bg-tertiary' : 'bg-outline';
  const statusLabel = cam.status.toUpperCase();
  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
        <span className={`h-1.5 w-1.5 rounded-full ${statusColor}`} />
        {statusLabel}
      </span>
      <span className="inline-flex items-center gap-1.5 bg-primary-container/20 text-primary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded border border-primary/20">
        <span className="material-symbols-outlined text-[12px]">dns</span>
        RTSP:554
      </span>
    </div>
  );
}