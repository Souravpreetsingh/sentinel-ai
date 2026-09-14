import { useState, useMemo, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';
import SeverityBadge from '../components/shared/SeverityBadge';

const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
const severityRank = ['low', 'medium', 'high', 'critical'];

function KpiTile({ icon, label, value, sub, accent = 'text-primary' }) {
  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/30 p-3.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-label-xs text-outline tracking-wider uppercase text-[9px]">{label}</span>
        <span className={`material-symbols-outlined text-[16px] ${accent}`}>{icon}</span>
      </div>
      <div className="font-headline-md text-on-surface text-xl font-bold">{value}</div>
      {sub && <div className="font-body-sm text-outline text-[10px] mt-0.5">{sub}</div>}
    </div>
  );
}

function StatusBadgeAlt({ status, severity }) {
  const map = {
    critical: { bg: 'bg-error-container', text: 'text-on-error-container', icon: 'warning' },
    high: { bg: 'bg-secondary-container/20', text: 'text-secondary', icon: 'trending_up' },
    medium: { bg: 'bg-tertiary-container/20', text: 'text-tertiary', icon: 'schedule' },
    low: { bg: 'bg-outline-variant/20', text: 'text-outline', icon: 'info' },
    resolved: { bg: 'bg-surface-container-high', text: 'text-outline', icon: 'check_circle' },
    investigating: { bg: 'bg-primary-container/20', text: 'text-primary', icon: 'search' },
    dispatched: { bg: 'bg-tertiary-container/20', text: 'text-tertiary', icon: 'rocket_launch' },
    open: { bg: 'bg-surface-container-high', text: 'text-on-surface-variant', icon: 'unfold_more' },
  };
  const key = status === 'resolved' ? 'resolved' : status === 'investigating' ? 'investigating' : status === 'dispatched' ? 'dispatched' : status === 'open' ? 'open' : severity;
  const cfg = map[key] || map.open;
  return (
    <span className={`inline-flex items-center gap-1 font-label-xs text-[9px] px-2 py-0.5 rounded ${cfg.bg} ${cfg.text}`}>
      <span className="material-symbols-outlined text-[11px]">{cfg.icon}</span>
      {status.toUpperCase()}
    </span>
  );
}

function AuditTimelineItem({ entry, isLast }) {
  const dotColors = {
    system: 'bg-secondary',
    auto: 'bg-primary',
    dispatch: 'bg-tertiary',
    sensor: 'bg-error',
  };
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={`h-2 w-2 rounded-full ${dotColors[entry.type] || 'bg-outline'} flex-shrink-0`} />
        {!isLast && <div className="w-px flex-1 bg-outline-variant/30 my-1" />}
      </div>
      <div className="pb-4 min-w-0">
        <span className="font-label-xs text-outline text-[9px] tracking-wider">{entry.time} UTC</span>
        <p className="font-body-sm text-on-surface-variant text-[11px] mt-0.5">{entry.event}</p>
      </div>
    </div>
  );
}

export default function Incidents() {
  const { incidents, evidence, loading, error, refetchIncidents, updateIncident, addNotification } = useApp();
  const [severityFilter, setSeverityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(0);
  const [busyId, setBusyId] = useState(null);

  const PAGE_SIZE = 6;

  const handleUpdate = useCallback(
    async (id, updates) => {
      setBusyId(id);
      try {
        await updateIncident(id, updates);
      } catch (err) {
        addNotification({
          type: 'alert',
          level: 'warning',
          title: 'Update failed',
          message: err.message || 'Could not update incident.',
        });
      } finally {
        setBusyId(null);
      }
    },
    [updateIncident, addNotification]
  );

  const escalateSeverity = useCallback((sev) => {
    const idx = severityRank.indexOf(sev);
    return severityRank[Math.min(idx + 1, severityRank.length - 1)];
  }, []);

  const counts = useMemo(() => ({
    all: incidents.length,
    critical: incidents.filter(i => i.severity === 'critical').length,
    high: incidents.filter(i => i.severity === 'high').length,
    medium: incidents.filter(i => i.severity === 'medium').length,
    low: incidents.filter(i => i.severity === 'low').length,
    resolved: incidents.filter(i => i.status === 'resolved').length,
  }), [incidents]);

  const kpis = useMemo(() => {
    const active = incidents.filter(i => i.status !== 'resolved');
    const critical = incidents.filter(i => i.severity === 'critical');
    const high = incidents.filter(i => i.severity === 'high');
    const medium = incidents.filter(i => i.severity === 'medium');
    const resolved = incidents.filter(i => i.status === 'resolved');
    return [
      { icon: 'inbox', label: 'ACTIVE QUEUE', value: String(active.length), sub: 'incidents in triage', accent: 'text-secondary' },
      { icon: 'priority_high', label: 'CRITICAL PRIORITY', value: String(critical.length), sub: 'immediate response', accent: 'text-error' },
      { icon: 'south_west', label: 'HIGH PRIORITY', value: String(high.length), sub: 'requires attention', accent: 'text-secondary-fixed' },
      { icon: 'swap_vert', label: 'MEDIUM PRIORITY', value: String(medium.length), sub: 'monitored queue', accent: 'text-tertiary' },
      { icon: 'check_circle', label: 'RESOLVED TODAY', value: String(resolved.length), sub: 'closed cases', accent: 'text-secondary' },
      { icon: 'timer', label: 'AVG RESPONSE', value: '3:42', sub: 'mins to assign', accent: 'text-primary' },
    ];
  }, [incidents]);

  const filtered = useMemo(() => {
    let list = incidents;
    if (severityFilter === 'critical') list = list.filter(i => i.severity === 'critical');
    else if (severityFilter === 'high') list = list.filter(i => i.severity === 'high');
    else if (severityFilter === 'medium') list = list.filter(i => i.severity === 'medium');
    else if (severityFilter === 'low') list = list.filter(i => i.severity === 'low');
    else if (severityFilter === 'resolved') list = list.filter(i => i.status === 'resolved');

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(i =>
        `${i.id} ${i.type} ${i.location} ${i.status} ${i.assignedOfficer || ''}`.toLowerCase().includes(q)
      );
    }
    return [...list].sort((a, b) => {
      const sa = severityOrder[a.severity] ?? 4;
      const sb = severityOrder[b.severity] ?? 4;
      if (sa !== sb) return sa - sb;
      return new Date(b.timestamp) - new Date(a.timestamp);
    });
  }, [incidents, severityFilter, searchQuery]);

  if (loading) return <LoadingState message="LOADING INCIDENT RESPONSE CENTER..." />;
  if (error) return <ErrorState message={error} onRetry={refetchIncidents} />;

  const pageCount = Math.max(Math.ceil(filtered.length / PAGE_SIZE), 1);
  const safePage = Math.min(page, pageCount - 1);
  const paged = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  const defaultSelected = incidents.find(i => i.severity === 'critical')?.id
    ?? incidents.find(i => i.status === 'open')?.id
    ?? incidents[0]?.id
    ?? null;
  const selectedIncident = incidents.find(i => i.id === selectedId) ?? incidents.find(i => i.id === defaultSelected) ?? null;
  const incidentEvidence = selectedIncident ? evidence.filter((e) => e.incidentId === selectedIncident.id) : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-[26px] text-error">emergency</span>
          <div>
            <h1 className="font-headline-lg text-on-surface text-xl font-semibold">INCIDENT RESPONSE CENTER</h1>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 bg-error-container/40 text-on-error-container font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
            <span className="h-1.5 w-1.5 rounded-full bg-error animate-pulse" />
            {incidents.filter(i => i.status !== 'resolved').length} QUEUED
          </span>
          <span className="font-body-sm text-outline text-[11px]">SENTINEL AI — LIVE INCIDENT TRIAGE & RESPONSE COORDINATION</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors">
          <span className="material-symbols-outlined text-[15px]">download</span>
          EXPORT LOG
        </button>
        <button className="inline-flex items-center gap-1.5 bg-error-container/50 border border-error/30 text-on-error-container font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-error-container transition-colors">
          <span className="material-symbols-outlined text-[15px]">add_circle</span>
          CREATE MANUAL INCIDENT
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {kpis.map(kpi => (
          <KpiTile key={kpi.label} {...kpi} />
        ))}
      </div>

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 px-4 py-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 flex-wrap">
          {[
            { key: 'all', label: 'ALL', count: counts.all },
            { key: 'critical', label: 'CRITICAL', count: counts.critical },
            { key: 'high', label: 'HIGH', count: counts.high },
            { key: 'medium', label: 'MEDIUM', count: counts.medium },
            { key: 'low', label: 'LOW', count: counts.low },
            { key: 'resolved', label: 'RESOLVED', count: counts.resolved },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => { setSeverityFilter(tab.key); setPage(0); }}
              className={`inline-flex items-center gap-1.5 font-label-xs text-[10px] tracking-wider px-3 py-1.5 rounded-lg transition-colors border ${
                severityFilter === tab.key
                  ? tab.key === 'critical'
                    ? 'bg-error-container/40 text-error border-error/40'
                    : tab.key === 'high'
                      ? 'bg-secondary-container/20 text-secondary border-secondary/30'
                      : 'bg-primary-container/20 text-primary border-primary/30'
                  : 'text-outline hover:text-on-surface-variant hover:bg-surface-container-high border-transparent'
              }`}
            >
              {tab.label}
              <span className={`text-[9px] px-1.5 py-0 rounded ${severityFilter === tab.key ? 'bg-surface-container-lowest/40' : 'bg-surface-container-high'}`}>{tab.count}</span>
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

        <button className="flex items-center gap-1 bg-surface-container-high border border-outline-variant/30 text-on-surface-variant font-label-xs text-[10px] px-2.5 py-1.5 rounded-lg hover:bg-surface-container-highest transition-colors">
          <span className="material-symbols-outlined text-[14px]">calendar_month</span>
          DATE
          <span className="material-symbols-outlined text-[12px] text-outline">expand_more</span>
        </button>

        <button className="inline-flex items-center gap-1.5 bg-primary-container/20 border border-primary/30 text-primary font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-primary-container/30 transition-colors">
          <span className="material-symbols-outlined text-[15px]">refresh</span>
          REFRESH
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/20">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] text-secondary">format_list_bulleted</span>
              <span className="font-label-xs text-on-surface tracking-wider">INCIDENT LEDGER</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-label-xs text-outline text-[9px]">{filtered.length} RECORDS</span>
              <button className="p-1 rounded hover:bg-surface-container-highest transition-colors">
                <span className="material-symbols-outlined text-[14px] text-outline">download</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full font-label-xs text-[10px] min-w-[900px]">
              <thead>
                <tr className="text-outline bg-surface-container-low border-b border-outline-variant/20">
                  <th className="text-left px-3 py-2 tracking-wider">INCIDENT ID</th>
                  <th className="text-left px-3 py-2 tracking-wider">EVENT TYPE</th>
                  <th className="text-left px-3 py-2 tracking-wider">SEVERITY</th>
                  <th className="text-left px-3 py-2 tracking-wider">NODE</th>
                  <th className="text-left px-3 py-2 tracking-wider">LOCATION</th>
                  <th className="text-left px-3 py-2 tracking-wider">DETECTED AT</th>
                  <th className="text-left px-3 py-2 tracking-wider">STATUS</th>
                  <th className="text-left px-3 py-2 tracking-wider">ASSIGNED</th>
                  <th className="text-right px-3 py-2 tracking-wider">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {paged.map(inc => (
                  <tr
                    key={inc.id}
                    onClick={() => setSelectedId(inc.id)}
                    className={`border-b border-outline-variant/10 transition-colors cursor-pointer ${
                      inc.severity === 'critical'
                        ? 'bg-error-container/15 hover:bg-error-container/25'
                        : inc.severity === 'high'
                          ? 'bg-secondary-container/5 hover:bg-surface-container-low'
                          : 'hover:bg-surface-container-low'
                    } ${selectedId === inc.id || (selectedIncident && selectedIncident.id === inc.id) ? 'ring-1 ring-inset ring-primary/40' : ''}`}
                  >
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        {inc.severity === 'critical' && (
                          <span className="relative flex h-1.5 w-1.5">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-error opacity-75" />
                            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-error" />
                          </span>
                        )}
                        <span className="text-on-surface">{inc.id}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-on-surface-variant max-w-[160px] truncate">{inc.type}</td>
                    <td className="px-3 py-2.5"><SeverityBadge severity={inc.severity} size="sm" /></td>
                    <td className="px-3 py-2.5 text-outline">{inc.cameraId}</td>
                    <td className="px-3 py-2.5 text-on-surface-variant max-w-[140px] truncate">{inc.location}</td>
                    <td className="px-3 py-2.5 text-outline">
                      {new Date(inc.timestamp).toLocaleString([], { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadgeAlt status={inc.status} severity={inc.severity} /></td>
                    <td className="px-3 py-2.5 text-on-surface-variant">{inc.assignedOfficer || <span className="text-outline">—</span>}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          disabled={busyId === inc.id}
                          onClick={(e) => { e.stopPropagation(); handleUpdate(inc.id, { status: 'investigating' }); }}
                          className="p-1 rounded hover:bg-surface-container-highest transition-colors text-primary disabled:opacity-40"
                          title="Investigate"
                        >
                          <span className="material-symbols-outlined text-[13px]">search</span>
                        </button>
                        <button
                          disabled={busyId === inc.id}
                          onClick={(e) => { e.stopPropagation(); handleUpdate(inc.id, { status: 'resolved' }); }}
                          className="p-1 rounded hover:bg-surface-container-highest transition-colors text-secondary disabled:opacity-40"
                          title="Resolve"
                        >
                          <span className="material-symbols-outlined text-[13px]">check</span>
                        </button>
                        <button
                          className="p-1 rounded hover:bg-surface-container-highest transition-colors text-tertiary"
                          title="Share"
                        >
                          <span className="material-symbols-outlined text-[13px]">ios_share</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {paged.length === 0 && (
              <EmptyState icon="report_off" title="No Incidents" description="No incidents match the current filters." />
            )}
          </div>

          <div className="flex items-center justify-between px-4 py-3 border-t border-outline-variant/20 bg-surface-container-low">
            <span className="font-label-xs text-outline text-[9px] tracking-wider">
              SHOWING {(safePage * PAGE_SIZE) + 1}–{Math.min((safePage + 1) * PAGE_SIZE, filtered.length)} OF {filtered.length}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(Math.max(0, safePage - 1))}
                disabled={safePage === 0}
                className="p-1.5 rounded bg-surface-container-high border border-outline-variant/30 hover:bg-surface-container-highest transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className="material-symbols-outlined text-[13px] text-outline">chevron_left</span>
              </button>
              {Array.from({ length: pageCount }, (_, i) => (
                <button
                  key={i}
                  onClick={() => setPage(i)}
                  className={`w-7 h-7 rounded font-label-xs text-[10px] transition-colors ${
                    safePage === i
                      ? 'bg-primary-container/30 text-primary border border-primary/30'
                      : 'text-outline hover:bg-surface-container-high border border-transparent'
                  }`}
                >
                  {i + 1}
                </button>
              ))}
              <button
                onClick={() => setPage(Math.min(pageCount - 1, safePage + 1))}
                disabled={safePage >= pageCount - 1}
                className="p-1.5 rounded bg-surface-container-high border border-outline-variant/30 hover:bg-surface-container-highest transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className="material-symbols-outlined text-[13px] text-outline">chevron_right</span>
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-4">
          {selectedIncident ? (
            <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden sticky top-4 space-y-0">
              <div className={`px-4 py-3 border-b border-outline-variant/20 flex items-start justify-between gap-2 ${selectedIncident.severity === 'critical' ? 'bg-error-container/20' : 'bg-surface-container-low'}`}>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-label-xs text-on-surface text-[11px] tracking-wider">{selectedIncident.id}</span>
                    <SeverityBadge severity={selectedIncident.severity} size="sm" />
                  </div>
                  <p className="font-body-sm text-on-surface-variant text-[11px]">{selectedIncident.type}</p>
                  <p className="font-body-sm text-outline text-[10px] mt-0.5">{selectedIncident.location}</p>
                </div>
                <span className="material-symbols-outlined text-[16px] text-outline cursor-pointer hover:text-on-surface transition-colors flex-shrink-0">close</span>
              </div>

              <div className="relative aspect-video bg-surface-container-low border-b border-outline-variant/20">
                <div className="absolute inset-0 bg-gradient-to-br from-secondary/5 via-transparent to-error/10" />
                <div className="absolute top-2 left-2 bg-surface-container-lowest/80 rounded px-2 py-1 border border-outline-variant/20">
                  <span className="font-label-xs text-on-surface text-[9px] tracking-wider">CV OVERLAY · {selectedIncident.cameraId}</span>
                </div>
                <div className="absolute top-2 right-2 bg-surface-container-lowest/80 rounded px-2 py-1 border border-outline-variant/20">
                  <span className="font-label-xs text-secondary text-[9px]">{selectedIncident.confidence.toFixed(1)}% CONF</span>
                </div>
                <div className="absolute inset-y-[30%] left-[12%] right-[55%] border-2 border-secondary/70 rounded-sm">
                  <div className="absolute -top-[18px] -left-[2px] bg-secondary text-on-secondary font-label-xs text-[8px] px-1 py-px rounded-t">TRACK-01</div>
                  <div className="absolute inset-0">
                    <span className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-secondary" />
                    <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-secondary" />
                  </div>
                </div>
                <div className="absolute inset-y-[20%] left-[48%] right-[18%] border border-error/50 rounded-sm">
                  <div className="absolute -top-[18px] -left-[2px] bg-error-container text-on-error-container font-label-xs text-[8px] px-1 py-px rounded-t">SUSPECT</div>
                </div>
                <div className="absolute bottom-0 inset-x-0 px-3 py-2 bg-surface-container-lowest/70 backdrop-blur flex items-center justify-between border-t border-outline-variant/20">
                  <span className="font-label-xs text-outline text-[9px]">REC · {new Date(selectedIncident.timestamp).toLocaleTimeString([], { hour12: false })}</span>
                  <div className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px] text-error animate-pulse">fiber_manual_record</span>
                    <span className="font-label-xs text-error text-[9px]">LIVE</span>
                  </div>
                </div>
              </div>

              <div className="px-4 py-3 border-b border-outline-variant/20 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Detection Type</span>
                  <span className="font-label-xs text-on-surface text-[10px]">{selectedIncident.type}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Sensor Trigger</span>
                  <span className="font-label-xs text-on-surface text-[10px]">YOLOv9b · Inference 9.4ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Sector Unit</span>
                  <span className="font-label-xs text-on-surface text-[10px]">{selectedIncident.cameraId} / {selectedIncident.geoCoords}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-label-xs text-outline text-[9px] tracking-wider uppercase">Chain of Custody</span>
                  <span className="font-label-xs text-tertiary text-[9px] truncate ml-3">{selectedIncident.hash.split(': ')[1]?.slice(0, 20)}…</span>
                </div>
              </div>

              <div className="px-4 py-3 border-b border-outline-variant/20 space-y-2">
                <div className="flex flex-col sm:flex-row gap-2">
                  <button
                    disabled={busyId === selectedIncident.id}
                    onClick={() => handleUpdate(selectedIncident.id, { severity: escalateSeverity(selectedIncident.severity) })}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-error-container/50 border border-error/30 text-on-error-container font-label-xs text-[9px] tracking-wider px-3 py-2 rounded-lg hover:bg-error-container transition-colors disabled:opacity-40"
                  >
                    <span className="material-symbols-outlined text-[13px]">south_west</span>
                    ESCALATE
                  </button>
                  <button
                    disabled={busyId === selectedIncident.id}
                    onClick={() => handleUpdate(selectedIncident.id, { status: 'investigating' })}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-secondary-container/20 border border-secondary/30 text-secondary font-label-xs text-[9px] tracking-wider px-3 py-2 rounded-lg hover:bg-secondary-container/30 transition-colors disabled:opacity-40"
                  >
                    <span className="material-symbols-outlined text-[13px]">local_police</span>
                    DISPATCH PATROL
                  </button>
                </div>
                <button
                  disabled={busyId === selectedIncident.id}
                  onClick={() => handleUpdate(selectedIncident.id, { status: 'resolved' })}
                  className="w-full flex items-center justify-center gap-1.5 bg-surface-container-low border border-outline-variant/30 text-outline font-label-xs text-[9px] tracking-wider px-3 py-2 rounded-lg hover:bg-surface-container-high hover:text-on-surface-variant transition-colors disabled:opacity-40"
                >
                  <span className="material-symbols-outlined text-[13px]">block</span>
                  FALSE POSITIVE
                </button>
              </div>

              <div className="px-4 py-3">
                <div className="flex items-center gap-2 mb-3">
                  <span className="material-symbols-outlined text-[14px] text-tertiary">history</span>
                  <span className="font-label-xs text-on-surface tracking-wider">AUDIT TRAIL</span>
                </div>
<div className="max-h-[200px] overflow-y-auto pr-1">
                {selectedIncident.timeline.map((entry, idx) => (
                  <AuditTimelineItem key={idx} entry={entry} isLast={idx === selectedIncident.timeline.length - 1} />
                ))}
              </div>
            </div>

            <div className="px-4 py-3 border-t border-outline-variant/20 bg-surface-container-low">
              <div className="flex items-center gap-2 mb-3">
                <span className="material-symbols-outlined text-[14px] text-secondary">folder_shared</span>
                <span className="font-label-xs text-on-surface tracking-wider">ASSOCIATED EVIDENCE</span>
              </div>
              {incidentEvidence.length === 0 ? (
                <p className="font-body-sm text-outline text-[10px]">No evidence records for this incident.</p>
              ) : (
                <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1">
                  {incidentEvidence.map((ev) => (
                    <div key={ev.id} className="flex items-center gap-2 bg-surface-container-low rounded px-2 py-1.5">
                      <span className="material-symbols-outlined text-[12px] text-tertiary">{ev.type === 'video_clip' ? 'movie' : ev.type === 'snapshot' ? 'photo_camera' : ev.type === 'audio' ? 'mic' : 'sensors'}</span>
                      <span className="font-label-xs text-on-surface-variant text-[9px] truncate flex-1" title={ev.title}>{ev.title}</span>
                      <span className="font-label-xs text-outline text-[8px]">{ev.fileSize}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
            <div className="bg-surface-container rounded-lg border border-outline-variant/30">
              <EmptyState icon="article" title="No Incident Selected" description="Select an incident from the ledger to inspect its details." />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}