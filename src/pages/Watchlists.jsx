import { useState, useEffect } from 'react';
import { getWatchlist, createWatchlist, updateWatchlist, deleteWatchlist } from '../services/api';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';

const CATEGORIES = ['vehicle', 'person', 'stolen_vehicle', 'wanted_person', 'missing_person', 'blacklisted_vehicle', 'suspect_vehicle', 'suspect_person', 'other'];
const PRIORITIES = ['critical', 'high', 'medium', 'low'];

function PriorityBadge({ priority }) {
  const colors = {
    critical: 'bg-error-container/60 text-on-error-container',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-50 text-yellow-700',
    low: 'bg-surface-container-low text-outline',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded font-label-xs text-[9px] tracking-wider ${colors[priority] || colors.medium}`}>
      {(priority || 'medium').toUpperCase()}
    </span>
  );
}

export default function Watchlists() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', category: 'vehicle', vehicle_registration: '', vehicle_colour: '', priority: 'medium', status: 'active' });

  const load = async () => {
    setLoading(true);
    try {
      const data = await getWatchlist();
      setItems(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...form };
      if (!payload.vehicle_registration) delete payload.vehicle_registration;
      if (!payload.vehicle_colour) delete payload.vehicle_colour;
      const created = await createWatchlist(payload);
      setItems((prev) => [created, ...prev]);
      setForm({ name: '', category: 'vehicle', vehicle_registration: '', vehicle_colour: '', priority: 'medium', status: 'active' });
      setShowForm(false);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this watchlist entity?')) return;
    try {
      await deleteWatchlist(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading) return <LoadingState message="LOADING WATCHLISTS..." />;

  return (
    <div className="space-y-5">
      <PageHeader icon="list" title="WATCHLISTS" subtitle="ENTITIES OF INTEREST">
        <button onClick={() => setShowForm(!showForm)} className="ml-4 inline-flex items-center gap-1.5 bg-primary-container text-on-primary font-label-xs text-[10px] tracking-wider px-3 py-2 rounded-lg hover:bg-primary-container/80 transition-colors">
          <span className="material-symbols-outlined text-[15px]">add</span>
          ADD ENTITY
        </button>
      </PageHeader>

      {error && (
        <div className="bg-error-container/30 border border-error/30 rounded-lg px-4 py-3 font-label-xs text-on-error-container text-[11px]">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-surface-container rounded-lg border border-outline-variant/30 p-4 grid grid-cols-1 md:grid-cols-5 gap-3">
          <input placeholder="Name *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required className="bg-surface-container-low border border-outline-variant/30 rounded px-3 py-2 font-body-sm text-on-surface text-[11px] focus:outline-none focus:border-primary" />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} className="bg-surface-container-low border border-outline-variant/30 rounded px-3 py-2 font-body-sm text-on-surface text-[11px] focus:outline-none focus:border-primary">
            {CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ').toUpperCase()}</option>)}
          </select>
          <input placeholder="Vehicle plate (e.g. MH 12 CD 5678)" value={form.vehicle_registration} onChange={e => setForm({ ...form, vehicle_registration: e.target.value })} className="bg-surface-container-low border border-outline-variant/30 rounded px-3 py-2 font-body-sm text-on-surface text-[11px] focus:outline-none focus:border-primary" />
          <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} className="bg-surface-container-low border border-outline-variant/30 rounded px-3 py-2 font-body-sm text-on-surface text-[11px] focus:outline-none focus:border-primary">
            {PRIORITIES.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
          </select>
          <button type="submit" className="bg-primary text-on-primary rounded px-4 py-2 font-label-xs text-[10px] tracking-wider hover:bg-primary/80 transition-colors">CREATE</button>
        </form>
      )}

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
        <div className="grid grid-cols-12 gap-2 px-4 py-2.5 border-b border-outline-variant/20 bg-surface-container-low">
          <span className="col-span-4 font-label-xs text-outline tracking-wider text-[9px]">NAME</span>
          <span className="col-span-2 font-label-xs text-outline tracking-wider text-[9px]">CATEGORY</span>
          <span className="col-span-2 font-label-xs text-outline tracking-wider text-[9px]">PLATE NORMALISED</span>
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">PRIORITY</span>
          <span className="col-span-1 font-label-xs text-outline tracking-wider text-[9px]">STATUS</span>
          <span className="col-span-2 font-label-xs text-outline tracking-wider text-[9px] text-right">ACTIONS</span>
        </div>
        <div className="divide-y divide-outline-variant/15 max-h-[600px] overflow-y-auto">
          {items.map(item => (
            <div key={item.id} className="grid grid-cols-12 gap-2 px-4 py-3 hover:bg-surface-container-low transition-colors items-center">
              <div className="col-span-4 min-w-0">
                <span className="font-label-xs text-on-surface text-[11px] block truncate">{item.name}</span>
                <span className="font-label-xs text-outline text-[9px]">{item.id}</span>
              </div>
              <span className="col-span-2 font-label-xs text-on-surface-variant text-[10px]">{(item.category || '').replace(/_/g, ' ')}</span>
              <span className="col-span-2 font-mono text-on-surface text-[10px]">{item.plate_normalized || '—'}</span>
              <span className="col-span-1"><PriorityBadge priority={item.priority} /></span>
              <span className="col-span-1">
                <span className={`inline-block h-1.5 w-1.5 rounded-full ${item.status === 'active' ? 'bg-secondary' : 'bg-outline/40'}`} />
              </span>
              <div className="col-span-2 flex justify-end gap-1">
                <button onClick={() => handleDelete(item.id)} className="p-1.5 rounded hover:bg-error-container/40 text-outline hover:text-error transition-colors" title="Delete">
                  <span className="material-symbols-outlined text-[14px]">delete</span>
                </button>
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <div className="px-4 py-8 text-center font-body-sm text-outline text-[11px]">No watchlist entities found.</div>
          )}
        </div>
        <div className="px-4 py-2 border-t border-outline-variant/20 bg-surface-container-low">
          <span className="font-label-xs text-outline text-[9px]">{items.length} ENTRIES</span>
        </div>
      </div>
    </div>
  );
}