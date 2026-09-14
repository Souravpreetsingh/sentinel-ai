import { useState, useEffect } from 'react';
import { getAlerts, updateAlert } from '../services/api';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';

const SEVERITY_COLORS = {
  critical: 'bg-error-container/60 text-on-error-container',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-50 text-yellow-700',
  low: 'bg-surface-container-low text-outline',
};

const STATUS_COLORS = {
  new: 'bg-error-container/30 text-error',
  acknowledged: 'bg-surface-container-high text-on-surface-variant',
  investigating: 'bg-primary-container/40 text-primary',
  resolved: 'bg-emerald-50 text-emerald-700',
  false_positive: 'bg-outline-container text-outline',
};

function SeverityBadge({ severity }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded font-label-xs text-[9px] tracking-wider ${SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium}`}>
      {(severity || '—').toUpperCase()}
    </span>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded font-label-xs text-[9px] tracking-wider ${STATUS_COLORS[status] || STATUS_COLORS.new}`}>
      {(status || '—').toUpperCase()}
    </span>
  );
}

function timeAgo(iso) {
  if (!iso) return '—';
  const ms = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  return `${days}d ago`;
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  const load = async () => {
    setLoading(true);
    try {
      const params = filter === 'all' ? {} : { status: filter };
      const data = await getAlerts({ ...params, limit: 200 });
      setAlerts(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleStatus = async (id, status) => {
    try {
      await updateAlert(id, { status });
      setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, status } : a));
    } catch (err) {
      alert(err.message);
    }
  };

  const statusActions = (status) => {
    switch (status) {
      case 'new':
        return [
          { next: 'acknowledged', label: 'ACK' },
          { next: 'investigating', label: 'INV' },
        ];
      case 'acknowledged':
        return [
          { next: 'investigating', label: 'INV' },
          { next: 'resolved', label: 'RES' },
          { next: 'false_positive', label: 'FP' },
        ];
      case 'investigating':
        return [
          { next: 'resolved', label: 'RES' },
          { next: 'false_positive', label: 'FP' },
        ];
      default:
        return [];
    }
  };

  if (loading) return <LoadingState message="LOADING ALERTS..." />;

  return (
    <div className="space-y-5">
      <PageHeader icon="add_alert" title="ALERTS" subtitle="WATCHLIST MATCH NOTIFICATIONS">
        <div className="ml-4 flex items-center gap-1 bg-surface-container rounded-lg p-0.5">
          {['all', 'new', 'acknowledged', 'investigating', 'resolved'].map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-2 py-1 rounded font-label-xs text-[10px] transition-colors ${filter === f ? 'bg-surface-container-high text-on-surface' : 'text-outline hover:text-on-surface-variant'}`}>
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      </PageHeader>

      {error && (
        <div className="bg-error-container/30 border border-error/30 rounded-lg px-4 py-3 font-label-xs text-on-error-container text-[11px]">{error}</div>
      )}

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
        <div className="grid grid-cols-12 gap-2 px-4 py-2.5 border-b border-outline-variant/20 bg-surface-container-low">
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">SEV</span>
          <span className="col-span-3 font-label-xs text-outline tracking-wider text-[9px]">ENTITY</span>
          <span className="col-span-2 font-label-xs text-outline tracking-wider text-[9px]">CAMERA</span>
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">MATCH</span>
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">CONF</span>
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">STATUS</span>
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">WHEN</span>
          <span className="col-span-2 font-label-xs text-outline tracking-wider text-[9px] text-right">ACTIONS</span>
        </div>
        <div className="divide-y divide-outline-variant/15 max-h-[700px] overflow-y-auto">
          {alerts.map(alert => (
            <div key={alert.id} className="grid grid-cols-12 gap-2 px-4 py-3 hover:bg-surface-container-low transition-colors items-center">
              <div className="col-span-1"><SeverityBadge severity={alert.severity} /></div>
              <div className="col-span-3 min-w-0">
                <span className="font-label-xs text-on-surface text-[11px] block truncate">{alert.entity_name}</span>
                <span className="font-label-xs text-outline text-[9px]">{alert.id} · {alert.entity_identifier || 'entity'}</span>
              </div>
              <span className="col-span-2 font-label-xs text-on-surface-variant text-[10px]">{alert.camera_id || '—'}</span>
              <span className="col-span-1 font-mono text-on-surface text-[10px]">{alert.match_type || '—'}</span>
              <span className="col-span-1 font-label-xs text-on-surface text-[10px]">{alert.confidence ? `${Math.round(alert.confidence * 100)}%` : '—'}</span>
              <div className="col-span-1"><StatusBadge status={alert.status} /></div>
              <span className="col-span-1 font-label-xs text-outline text-[9px]">{timeAgo(alert.detected_at)}</span>
              <div className="col-span-2 flex justify-end gap-1">
                {statusActions(alert.status).map(action => (
                  <button key={action.label} onClick={() => handleStatus(alert.id, action.next)} className="px-2 py-1 rounded bg-surface-container-high border border-outline-variant/30 font-label-xs text-[9px] text-on-surface-variant hover:bg-surface-container-highest transition-colors">
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <div className="px-4 py-8 text-center font-body-sm text-outline text-[11px]">No alerts match the current filter.</div>
          )}
        </div>
        <div className="px-4 py-2 border-t border-outline-variant/20 bg-surface-container-low flex justify-between">
          <span className="font-label-xs text-outline text-[9px]">{alerts.length} ALERTS</span>
          <span className="font-label-xs text-outline text-[9px]">SEVERITY: {alerts.filter(a => a.severity === 'critical').length} CRIT · {alerts.filter(a => a.severity === 'high').length} HIGH</span>
        </div>
      </div>
    </div>
  );
}