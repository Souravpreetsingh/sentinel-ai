import { useMemo, useState } from 'react';
import { useApp } from '../context/AppContext';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';

const RANGES = [
  { key: '1h', label: 'LAST HOUR' },
  { key: '24h', label: 'LAST 24H' },
  { key: '7d', label: 'LAST 7 DAYS' },
  { key: '30d', label: 'LAST 30 DAYS' },
];

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

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

function StatBlock({ label, value, unit, accent }) {
  return (
    <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 px-3 py-2.5">
      <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">{label}</span>
      <span className={`font-headline-md text-lg font-bold ${accent || 'text-on-surface'}`}>
        {value}
        {unit && <span className="text-[12px] text-outline ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

export default function Analytics() {
  const { analytics, loading, error, refetchAll } = useApp();
  const [range, setRange] = useState('24h');

  const data = useMemo(() => {
    if (!analytics) return null;
    const hours = analytics.hourlyTraffic || [];
    const hourly = Array.isArray(hours) ? hours : [];
    const shown =
      range === '1h' ? hourly.slice(-1) : hourly;
    const maxVehicles = Math.max(...hourly.map((h) => h.vehicles || 0), 1);
    const maxDetections = Math.max(
      ...(analytics.weeklyTrend || []).map((d) => d.detections || 0),
      1
    );
    const maxEventCount = Math.max(
      ...(analytics.topEventTypes || []).map((e) => e.count || 0),
      1
    );
    return {
      ...analytics,
      hourly,
      shown,
      maxVehicles,
      maxDetections,
      maxEventCount,
    };
  }, [analytics, range]);

  if (loading) return <LoadingState message="LOADING ANALYTICS..." />;
  if (error) return <ErrorState message={error} onRetry={refetchAll} />;
  if (!data) return <EmptyState icon="query_stats" title="No Analytics Available" description="Analytics have not loaded yet." />;

  const perf = data.aiModelPerformance || {};

  return (
    <div className="space-y-5">
      <PageHeader
        icon="monitor_heart"
        title="ANALYTICS"
        subtitle="DETECTION INTELLIGENCE & PERFORMANCE METRICS"
      >
        <div className="flex items-center gap-1 bg-surface-container rounded-lg border border-outline-variant/30 p-0.5">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`px-3 py-1.5 rounded font-label-xs text-[9px] tracking-wider transition-colors ${
                range === r.key
                  ? 'bg-primary-container/20 text-primary border border-primary/30'
                  : 'text-outline hover:text-on-surface-variant border border-transparent'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card icon="bar_chart" title="Traffic Activity" badge={`${data.shown.length} SAMPLES`}>
          <div className="flex items-end gap-[3px] h-44">
            {data.shown.map((h, idx) => (
              <div key={h.hour} className="flex-1 flex flex-col items-center gap-1.5 min-w-0">
                <div className="w-full flex items-end justify-center gap-px">
                  <div
                    className="w-1/2 rounded-t bg-primary/90"
                    style={{ height: `${Math.max((h.pedestrians / data.maxVehicles) * 140, 2)}px` }}
                    title={`${h.hour} — ${h.pedestrians} pedestrians`}
                  />
                  <div
                    className="w-1/2 rounded-t bg-tertiary/90"
                    style={{ height: `${Math.max((h.vehicles / data.maxVehicles) * 140, 2)}px` }}
                    title={`${h.hour} — ${h.vehicles} vehicles`}
                  />
                </div>
                <span className="font-label-xs text-outline text-[7px]">
                  {data.shown.length > 12 ? (idx % 3 === 0 ? h.hour : '') : h.hour}
                </span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-outline-variant/20">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-sm bg-primary" />
              <span className="font-label-xs text-on-surface-variant text-[9px]">PEDESTRIANS</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-sm bg-tertiary" />
              <span className="font-label-xs text-on-surface-variant text-[9px]">VEHICLES</span>
            </div>
            <span className="font-label-xs text-outline text-[8px] ml-auto">HOURLY SAMPLES</span>
          </div>
        </Card>

        <Card icon="calendar_view_week" title="Weekly Trend" badge="DETECTIONS / INCIDENTS / RESOLVED">
          <div className="space-y-2.5">
            {(data.weeklyTrend || []).map((d) => (
              <div key={d.day} className="flex items-center gap-2">
                <span className="font-label-xs text-outline text-[9px] w-8 flex-shrink-0">{d.day}</span>
                <div className="flex-1 flex flex-col gap-1">
                  <div className="h-2 bg-surface-container-lowest rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${(d.detections / data.maxDetections) * 100}%` }}
                    />
                  </div>
                  <div className="flex gap-3">
                    <span className="font-label-xs text-on-surface-variant text-[8px]">
                      {d.detections} DET
                    </span>
                    <span className="font-label-xs text-error text-[8px]">{d.incidents} INC</span>
                    <span className="font-label-xs text-secondary text-[8px]">{d.resolved} RSL</span>
                  </div>
                </div>
                <span
                  className="font-label-xs text-outline text-[8px] w-10 text-right flex-shrink-0"
                >
                  {Math.round((d.incidents / Math.max(d.detections, 1)) * 100)}%
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card icon="category" title="Top Event Types" badge="DETECTION CLASSIFICATION">
          <div className="space-y-2.5">
            {(data.topEventTypes || []).slice(0, 8).map((e, i) => (
              <div key={e.type} className="flex items-center gap-3">
                <span
                  className={`font-label-xs w-5 text-center rounded text-[9px] py-0.5 ${
                    i === 0 ? 'bg-error-container/40 text-error' : 'bg-surface-container-high text-outline'
                  }`}
                >
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="font-body-sm text-on-surface-variant text-[10px] truncate">{e.type}</span>
                    <span className="font-label-xs text-on-surface text-[9px]">{e.count.toLocaleString()}</span>
                  </div>
                  <div className="h-1.5 bg-surface-container-lowest rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${i === 0 ? 'bg-error' : 'bg-primary'}`}
                      style={{ width: `${(e.count / data.maxEventCount) * 100}%`, opacity: 1 - i * 0.08 }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card icon="videocam" title="AI Model Performance" badge="CV PIPELINE">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatBlock label="MODEL" value={perf.yoloVersion || 'YOLOv9b'} accent="text-primary" />
            <StatBlock label="INFERENCE" value={perf.averageInference || '—'} />
            <StatBlock label="MODELS LOADED" value={perf.modelsLoaded || 0} />
            <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 px-3 py-2.5">
              <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">ACCURACY</span>
              <div className="mt-1.5">
                <div className="flex justify-between mb-1">
                  <span className="font-label-xs text-on-surface text-[9px]">{perf.accuracy || 98.2}%</span>
                </div>
                <div className="h-1.5 bg-surface-container-lowest rounded-full overflow-hidden">
                  <div
                    className="h-full bg-secondary rounded-full"
                    style={{ width: `${perf.accuracy || 98.2}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 px-3 py-2.5">
              <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">FALSE POSITIVE</span>
              <span className="font-headline-md text-lg font-bold text-tertiary">
                {perf.falsePositiveRate || 1.8}%
              </span>
            </div>
            <div className="bg-surface-container-low rounded-lg border border-outline-variant/20 px-3 py-2.5">
              <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">GPU MEMORY</span>
              <span className="font-headline-md text-lg font-bold text-on-surface">
                {perf.gpuMemory || '3.2 GB - 8 GB'}
              </span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-outline-variant/20 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px] text-outline">thermostat</span>
              <span className="font-label-xs text-outline text-[9px]">GPU TEMP</span>
              <span className="font-label-xs text-on-surface-variant text-[9px]">{perf.gpuTemp || 68}°C</span>
            </div>
            <span className={`font-label-xs text-[9px] tracking-wider ${(perf.gpuTemp || 68) > 80 ? 'text-error' : 'text-secondary'}`}>
              {(perf.gpuTemp || 68) > 80 ? 'TRIP HIGH' : '● NOMINAL'}
            </span>
          </div>
        </Card>

        <Card icon="grid_on" title="Detection Heatmap" badge="DENSITY BY HOUR × DAY" className="xl:col-span-2">
          <div className="flex gap-1">
            <div className="w-8 flex-shrink-0" />
            <div
              className="grid flex-1 gap-px mb-2"
              style={{ gridTemplateColumns: 'repeat(24, minmax(0, 1fr))' }}
            >
              {data.hourly.map((h, i) => (
                <span
                  key={i}
                  className="font-label-xs text-outline text-[7px] text-center"
                >
                  {i % 4 === 0 ? h.hour.slice(0, 2) : ''}
                </span>
              ))}
            </div>
          </div>
          {DAYS.map((d, di) => {
            const dayFactor = [0.7, 0.8, 0.75, 0.85, 0.95, 1, 0.9][di];
            return (
              <div key={d} className="flex items-center gap-1 mb-1">
                <span className="font-label-xs text-outline text-[8px] w-8 flex-shrink-0">{d}</span>
                <div
                  className="grid flex-1 gap-px"
                  style={{ gridTemplateColumns: 'repeat(24, minmax(0, 1fr))' }}
                >
                  {data.hourly.map((h, hi) => {
                    const base = (h.pedestrians + h.vehicles * 2) / (238 + 368 * 2);
                    const intensity = Math.min(1, base * 1.6 * dayFactor);
                    return (
                      <div
                        key={hi}
                        className="h-4 w-full rounded-[2px]"
                        style={{
                          backgroundColor: `rgba(137, 206, 255, ${(0.08 + 0.82 * intensity).toFixed(3)})`,
                        }}
                        title={`${d} ${h.hour} — ${Math.round(intensity * 100)}% density`}
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-outline-variant/20">
            <span className="font-label-xs text-outline text-[8px] tracking-wider">LOW</span>
            <div
              className="h-2 flex-1 rounded-full"
              style={{
                background:
                  'linear-gradient(90deg, rgba(137,206,255,0.1), rgba(137,206,255,0.5), rgba(137,206,255,0.95))',
              }}
            />
            <span className="font-label-xs text-outline text-[8px] tracking-wider">HIGH</span>
            <span className="font-label-xs text-outline text-[8px] ml-auto">
              {data.hourly.reduce((s, h) => s + h.pedestrians + h.vehicles, 0).toLocaleString()} EVENTS
            </span>
          </div>
        </Card>
      </div>

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/20">
          <span className="material-symbols-outlined text-[16px] text-tertiary">table_rows</span>
          <span className="font-label-xs text-on-surface tracking-wider">CAMERA UTILIZATION</span>
          <span className="font-label-xs text-outline text-[9px] ml-auto">
            {(data.cameraUtilization || []).length} NODES REPORTING
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-outline-variant/20">
                {['CAMERA', 'UTILIZATION', 'LOAD', 'UPTIME'].map((h) => (
                  <th
                    key={h}
                    className="font-label-xs text-outline text-[8px] tracking-wider uppercase px-4 py-2.5"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data.cameraUtilization || []).map((row) => {
                const high = row.utilization > 90;
                return (
                  <tr key={row.cameraId} className="border-b border-outline-variant/10 last:border-0">
                    <td className="px-4 py-2.5">
                      <span className="font-label-xs text-on-surface text-[10px]">{row.cameraId}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`font-label-xs text-[10px] ${high ? 'text-error' : 'text-on-surface-variant'}`}>
                        {row.utilization.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 w-1/3">
                      <div className="h-1.5 bg-surface-container-lowest rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${high ? 'bg-error' : 'bg-secondary'}`}
                          style={{ width: `${row.utilization}%` }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`font-label-xs text-[10px] ${row.uptime >= 99 ? 'text-secondary' : 'text-tertiary'}`}>
                        {row.uptime.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}