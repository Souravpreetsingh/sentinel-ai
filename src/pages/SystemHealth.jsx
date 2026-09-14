import { useApp } from '../context/AppContext';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';

function Card({ icon, title, badge, children, className = '' }) {
  return (
    <div className={`bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden ${className}`}>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
        <span className="material-symbols-outlined text-[16px] text-primary">{icon}</span>
        <span className="font-label-xs text-on-surface tracking-wider uppercase">{title}</span>
        {badge && (
          <span className="font-label-xs text-outline text-[8px] tracking-wider ml-auto">{badge}</span>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function ServiceCard({ service }) {
  const dotColor =
    service.status === 'connected' ? 'bg-emerald-400' :
    service.status === 'degraded' ? 'bg-amber-400' : 'bg-red-500';
  const statusLabel = service.status.toUpperCase();
  return (
    <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
        <span className="font-body-sm text-on-surface text-[10px] truncate flex-1">{service.name}</span>
      </div>
      <div className="flex items-center justify-between mt-2 pl-3.5">
        <span className={`font-label-xs text-[8px] tracking-wider ${service.status === 'connected' ? 'text-secondary' : 'text-tertiary'}`}>
          {statusLabel}
        </span>
        <span className="font-label-xs text-outline text-[9px]">{service.latency}</span>
      </div>
    </div>
  );
}

function Metric({ icon, label, value, unit, accent }) {
  return (
    <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 p-3.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-label-xs text-outline tracking-wider uppercase text-[9px]">{label}</span>
        <span className={`material-symbols-outlined text-[15px] ${accent || 'text-primary'}`}>{icon}</span>
      </div>
      <span className="font-headline-lg text-on-surface text-2xl font-bold">
        {value}
        {unit && <span className="font-label-xs text-outline text-[11px] ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function SystemHealth() {
  const { systemHealth, loading, error, refetchSystemHealth } = useApp();

  if (loading) return <LoadingState message="ASSESSING SYSTEM HEALTH..." />;
  if (error) return <ErrorState message={error} onRetry={refetchSystemHealth} />;
  if (!systemHealth) return <EmptyState icon="monitor_heart" title="No Health Data" description="System health metrics have not loaded yet." />;

  const health = systemHealth;
  const [vramUsed, vramTotal = '0 GB'] = (health.gpu?.vram || 'N/A / N/A').split(' / ');
  const parseGb = (s) => parseFloat(String(s).replace(/[^\d.]/g, '')) || 0;
  const vramPercent = Math.min(Math.round((parseGb(vramUsed) / Math.max(parseGb(vramTotal), 1)) * 100), 100);
  const scorePercent = Math.min(Math.max(health.overall || 0, 0), 100);
  const bandwidth = health.networkBandwidth || {};
  const bwTotal = bandwidth.total || 1;
  const bwColors = ['bg-primary', 'bg-secondary', 'bg-tertiary', 'bg-outline-variant'];
  const bwSegments = (bandwidth.segments || [
    { label: '1080P', value: bandwidth.streams1080p || 0 },
    { label: '4K', value: bandwidth.streams4k || 0 },
    { label: 'ALERTS', value: bandwidth.alerts || 0 },
  ]).slice(0, 4).map((seg, idx) => ({
    label: seg.label,
    value: seg.value,
    cls: bwColors[idx % bwColors.length],
  }));

  return (
    <div className="space-y-5">
      <PageHeader icon="health_and_safety" title="SYSTEM HEALTH" subtitle="SENTINEL AI — INFRASTRUCTURE TELEMETRY">
        <span className="inline-flex items-center gap-1.5 bg-secondary/10 border border-secondary/25 text-secondary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          ALL SYSTEMS NOMINAL
        </span>
      </PageHeader>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-4 bg-surface-container rounded-lg border border-outline-variant/30 p-6 flex flex-col items-center justify-center gap-4">
          <div
            className="relative w-44 h-44 rounded-full"
            style={{ background: `conic-gradient(#7bd0ff ${scorePercent * 3.6}deg, #242a37 0deg)` }}
          >
            <div className="absolute inset-3 rounded-full bg-surface-container flex flex-col items-center justify-center">
              <span className="font-headline-xl text-on-surface text-4xl font-bold">{health.overall}</span>
              <span className="font-label-xs text-outline text-[9px] tracking-widest mt-1">HEALTH SCORE</span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-center">
            <div>
              <span className="font-headline-md text-on-surface text-xl font-bold">{health.onlineCameras}</span>
              <span className="font-label-xs text-outline text-[8px] block mt-0.5">ONLINE CAMS</span>
            </div>
            <div className="h-8 w-px bg-outline-variant/30" />
            <div>
              <span className="font-headline-md text-error text-xl font-bold">{health.offlineCameras}</span>
              <span className="font-label-xs text-outline text-[8px] block mt-0.5">OFFLINE CAMS</span>
            </div>
            <div className="h-8 w-px bg-outline-variant/30" />
            <div>
              <span className="font-headline-md text-on-surface text-xl font-bold">{health.totalCameras}</span>
              <span className="font-label-xs text-outline text-[8px] block mt-0.5">TOTAL NODES</span>
            </div>
          </div>
          <span className="font-label-xs text-outline text-[8px] tracking-wider">
            UPTIME {health.uptime} · LAST TELEMETRY PUSH 30S AGO
          </span>
        </div>

        <div className="xl:col-span-8 space-y-4">
          <Card icon="hub" title="Service Status" badge={`${health.services?.length || 0} SERVICES REPORTING`}>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
              {(health.services || []).map((svc) => (
                <ServiceCard key={svc.name} service={svc} />
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card icon="memory" title="GPU Monitor" badge={health.gpu?.name}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">VRAM</span>
                <span className="font-label-xs text-on-surface text-[10px]">{health.gpu?.vram}</span>
              </div>
              <div className="h-2 bg-surface-container-lowest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: `${vramPercent}%` }} />
              </div>
              <div className="grid grid-cols-3 gap-3 mt-4">
                <div>
                  <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">TEMPERATURE</span>
                  <span className={`font-label-xs text-[11px] ${health.gpu?.temperature > 80 ? 'text-error' : 'text-secondary'}`}>
                    {health.gpu?.temperature}°C
                  </span>
                </div>
                <div>
                  <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">UTILIZATION</span>
                  <span className="font-label-xs text-on-surface text-[11px]">{health.gpu?.utilization}%</span>
                </div>
                <div>
                  <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">POWER DRAW</span>
                  <span className="font-label-xs text-on-surface-variant text-[11px]">{health.gpu?.power}</span>
                </div>
              </div>
            </Card>

            <Card icon="storage" title="Storage" badge="OBJECT STORE">
              <div className="flex items-center justify-between mb-2">
                <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">CAPACITY</span>
                <span className="font-label-xs text-on-surface text-[10px]">
                  {health.storage?.used} / {health.storage?.total}
                </span>
              </div>
              <div className="h-2 bg-surface-container-lowest rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${health.storage?.percentage > 75 ? 'bg-error' : 'bg-secondary'}`}
                  style={{ width: `${health.storage?.percentage}%` }}
                />
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="font-label-xs text-outline text-[8px] tracking-wider">CONSUMED</span>
                <span className={`font-label-xs text-[10px] ${health.storage?.percentage > 75 ? 'text-error' : 'text-secondary'}`}>
                  {health.storage?.percentage}%
                </span>
              </div>
              <div className="mt-4 pt-4 border-t border-outline-variant/20">
                <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block mb-3">RECORDING ALLOCATION</span>
                <div className="flex h-2 rounded-full overflow-hidden bg-surface-container-lowest">
                  <div className="bg-primary/80" style={{ width: `${health.storage?.percentage || 0}%` }} />
                  <div className="bg-secondary/70" style={{ width: `${100 - (health.storage?.percentage || 0)}%` }} />
                </div>
                <div className="flex items-center gap-4 mt-2">
                  <span className="flex items-center gap-1 font-label-xs text-outline text-[8px]">
                    <span className="h-1.5 w-1.5 rounded-sm bg-primary/80" /> LIVE {health.storage?.percentage || 0}%
                  </span>
                  <span className="flex items-center gap-1 font-label-xs text-outline text-[8px]">
                    <span className="h-1.5 w-1.5 rounded-sm bg-secondary/70" /> FREE {100 - (health.storage?.percentage || 0)}%
                  </span>
                </div>
              </div>
            </Card>
          </div>

          <Card icon="lan" title="Network Bandwidth" badge={`${bwTotal} Mbps TOTAL`}>
            <div className="flex h-3 rounded-full overflow-hidden bg-surface-container-lowest">
              {bwSegments.map((seg) => (
                <div
                  key={seg.label}
                  className={seg.cls}
                  style={{ width: `${(seg.value / bwTotal) * 100}%` }}
                />
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-3">
              {bwSegments.map((seg) => (
                <span key={seg.label} className="flex items-center gap-1.5 font-label-xs text-outline text-[9px]">
                  <span className={`h-1.5 w-1.5 rounded-sm ${seg.cls}`} />
                  {seg.label} · {seg.value} Mbps
                </span>
              ))}
              <span className="font-label-xs text-outline text-[8px] ml-auto">INGRESS AGGREGATE</span>
            </div>
          </Card>
        </div>
      </div>

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
          <span className="material-symbols-outlined text-[16px] text-tertiary">speed</span>
          <span className="font-label-xs text-on-surface tracking-wider">SYSTEM METRICS</span>
          <span className="font-label-xs text-outline text-[8px] tracking-wider ml-auto">LIVE POLLING · 1S</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4">
          <Metric icon="videocam" label="PIPELINE FPS" value={health.fps} accent="text-secondary" />
          <Metric icon="network_check" label="LATENCY" value={health.latency} unit="ms" accent="text-primary" />
          <Metric icon="wifi_off" label="PACKET LOSS" value={health.packetLoss} unit="%" accent={health.packetLoss > 0 ? 'text-error' : 'text-secondary'} />
          <Metric icon="schedule" label="UPTIME" value={health.uptime} accent="text-tertiary" />
        </div>
      </div>
    </div>
  );
}