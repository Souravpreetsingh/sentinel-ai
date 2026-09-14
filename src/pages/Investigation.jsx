import { useState } from 'react';
import { searchInvestigation } from '../services/api';
import PageHeader from '../components/shared/PageHeader';

const KIND_STYLES = {
  camera: 'bg-blue-50 text-blue-700',
  alert: 'bg-error-container/30 text-error',
  track: 'bg-purple-50 text-purple-700',
  watchlist: 'bg-primary-container/30 text-primary',
  detection: 'bg-surface-container-high text-on-surface-variant',
  evidence: 'bg-amber-50 text-amber-700',
};

function KindBadge({ kind }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded font-label-xs text-[9px] tracking-wider ${KIND_STYLES[kind] || KIND_STYLES.detection}`}>
      {(kind || '—').toUpperCase()}
    </span>
  );
}

function timeStr(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString([], { hour12: false, month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function Investigation() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [facets, setFacets] = useState({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeKind, setActiveKind] = useState('all');

  const doSearch = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchInvestigation({ query: query.trim(), limit: 100 });
      setResults(data.results || []);
      setFacets(data.facets || {});
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filtered = activeKind === 'all' ? results : results.filter(r => r.kind === activeKind);

  return (
    <div className="space-y-5">
      <PageHeader icon="search" title="INVESTIGATION" subtitle="UNIFIED SEARCH ACROSS ALL DATA" />

      <form onSubmit={doSearch} className="flex gap-3">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search plate, entity name, camera ID, alert ID, location..."
          className="flex-1 bg-surface-container border border-outline-variant/30 rounded-lg px-4 py-2.5 font-body-sm text-on-surface text-[12px] focus:outline-none focus:border-primary"
        />
        <button type="submit" disabled={loading} className="bg-primary text-on-primary px-5 py-2.5 rounded-lg font-label-xs text-[10px] tracking-wider hover:bg-primary/80 transition-colors disabled:opacity-50">
          {loading ? 'SEARCHING...' : 'SEARCH'}
        </button>
      </form>

      {error && (
        <div className="bg-error-container/30 border border-error/30 rounded-lg px-4 py-3 font-label-xs text-on-error-container text-[11px]">{error}</div>
      )}

      {total > 0 && (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-label-xs text-outline text-[9px] tracking-wider">{total} RESULTS</span>
          {['all', 'camera', 'alert', 'track', 'watchlist', 'detection', 'evidence'].map(kind => (
            <button
              key={kind}
              onClick={() => setActiveKind(kind)}
              className={`px-2 py-1 rounded font-label-xs text-[9px] tracking-wider transition-colors ${
                activeKind === kind
                  ? 'bg-primary-container text-on-primary'
                  : 'bg-surface-container-high text-outline hover:text-on-surface-variant'
              }`}
            >
              {kind.toUpperCase()} {kind !== 'all' ? `(${facets[kind] || 0})` : ''}
            </button>
          ))}
        </div>
      )}

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
        <div className="divide-y divide-outline-variant/15 max-h-[700px] overflow-y-auto">
          {filtered.map((item, idx) => (
            <div key={`${item.id}-${idx}`} className="flex items-start gap-3 px-4 py-3 hover:bg-surface-container-low transition-colors">
              <div className="pt-0.5"><KindBadge kind={item.kind} /></div>
              <div className="min-w-0 flex-1">
                <span className="font-label-xs text-on-surface text-[11px] block truncate">{item.title}</span>
                <span className="font-body-sm text-on-surface-variant text-[10px] block mt-0.5">{item.subtitle}</span>
                <div className="flex items-center gap-3 mt-1">
                  {item.camera_name && <span className="font-label-xs text-outline text-[9px]">{item.camera_name}</span>}
                  {item.severity && <span className="font-label-xs text-error text-[9px]">{item.severity.toUpperCase()}</span>}
                  {item.confidence != null && <span className="font-label-xs text-outline text-[9px]">{Math.round(item.confidence * 100)}%</span>}
                  {item.timestamp && <span className="font-label-xs text-outline/70 text-[9px]">{timeStr(item.timestamp)}</span>}
                </div>
              </div>
              {item.location && (
                <span className="font-label-xs text-outline text-[9px] text-right flex-shrink-0 max-w-[200px] truncate hidden md:block">{item.location}</span>
              )}
            </div>
          ))}
          {results.length > 0 && filtered.length === 0 && (
            <div className="px-4 py-6 text-center font-body-sm text-outline text-[11px]">No results of type "{activeKind}".</div>
          )}
          {results.length === 0 && !loading && query.trim() && (
            <div className="px-4 py-8 text-center font-body-sm text-outline text-[11px]">No results found for "{query}".</div>
          )}
        </div>
      </div>
    </div>
  );
}