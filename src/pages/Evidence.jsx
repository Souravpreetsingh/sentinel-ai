import { useMemo, useState } from 'react';
import { useApp } from '../context/AppContext';
import PageHeader from '../components/shared/PageHeader';
import LoadingState from '../components/shared/LoadingState';
import ErrorState from '../components/shared/ErrorState';
import EmptyState from '../components/shared/EmptyState';

const TYPE_META = {
  video_clip: { label: 'VIDEO CLIP', icon: 'movie', accent: 'text-primary' },
  snapshot: { label: 'SNAPSHOT', icon: 'photo_camera', accent: 'text-secondary' },
  audio: { label: 'AUDIO', icon: 'mic', accent: 'text-tertiary' },
  sensor_log: { label: 'SENSOR LOG', icon: 'sensors', accent: 'text-secondary-fixed' },
};

const TYPE_FILTERS = [
  { key: 'all', label: 'ALL ITEMS' },
  { key: 'video_clip', label: 'VIDEO' },
  { key: 'snapshot', label: 'SNAPSHOT' },
  { key: 'audio', label: 'AUDIO' },
  { key: 'sensor_log', label: 'SENSOR LOG' },
];

function StatBar({ icon, label, value, accent }) {
  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/30 p-4">
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-label-xs text-outline tracking-wider uppercase text-[9px]">{label}</span>
        <span className={`material-symbols-outlined text-[16px] ${accent || 'text-primary'}`}>{icon}</span>
      </div>
      <span className="font-headline-md text-on-surface text-2xl font-bold">{value}</span>
    </div>
  );
}

function VerifiedBadge({ status }) {
  const isVerified = status === 'verified';
  return (
    <span
      className={`inline-flex items-center gap-1 font-label-xs text-[9px] px-2 py-0.5 rounded ${
        isVerified ? 'bg-secondary/15 text-secondary' : 'bg-tertiary/15 text-tertiary'
      }`}
    >
      <span className="material-symbols-outlined text-[11px]">
        {isVerified ? 'verified' : 'pending_actions'}
      </span>
      {isVerified ? 'VERIFIED' : 'PENDING REVIEW'}
    </span>
  );
}

function EvidenceCard({ item }) {
  const [imgError, setImgError] = useState(false);
  const meta = TYPE_META[item.type] || TYPE_META.sensor_log;
  const timestamp = new Date(item.timestamp).toLocaleString([], {
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
  const hashPreview = (item.hash.split(': ')[1] || item.hash).slice(0, 18);

  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden flex flex-col transition-all hover:border-outline-variant/50">
      <div className="px-4 py-3 flex items-center gap-3 border-b border-outline-variant/20 bg-surface-container-low">
        <span
          className={`h-9 w-9 rounded-lg bg-surface-container-lowest border border-outline-variant/30 flex items-center justify-center flex-shrink-0 ${meta.accent}`}
        >
          <span className="material-symbols-outlined text-[18px]">{meta.icon}</span>
        </span>
        <div className="min-w-0 flex-1">
          <span className="font-label-sm text-on-surface text-[11px]">{item.id}</span>
          <span className="font-label-xs text-outline text-[8px] block mt-0.5">{meta.label}</span>
        </div>
        <VerifiedBadge status={item.status} />
      </div>

      <div className="px-4 py-3 flex-1">
        {item.type === 'snapshot' && item.fileUrl && !imgError && (
          <img
            src={item.fileUrl}
            alt={item.title}
            onError={() => setImgError(true)}
            className="w-full h-36 object-cover rounded-md border border-outline-variant/20 mb-3 bg-surface-container-lowest"
          />
        )}
        <h3 className="font-body-sm text-on-surface text-[13px] font-medium leading-snug">
          {item.title}
        </h3>

        <div className="grid grid-cols-2 gap-x-3 gap-y-2 mt-3">
          <div className="min-w-0">
            <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">Incident</span>
            <span className="font-label-xs text-on-surface-variant text-[10px]">{item.incidentId}</span>
          </div>
          <div className="min-w-0">
            <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">Camera</span>
            <span className="font-label-xs text-on-surface-variant text-[10px]">{item.cameraId}</span>
          </div>
          <div className="min-w-0 col-span-2">
            <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block">Captured</span>
            <span className="font-label-xs text-on-surface-variant text-[10px]">{timestamp}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-outline-variant/15 flex-wrap">
          {item.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="font-label-xs text-primary/80 bg-surface-container-high rounded px-1.5 py-0.5 text-[8px] uppercase"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      <div className="px-4 py-3 border-t border-outline-variant/20 bg-surface-container-low space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase">Hash</span>
          <span className="font-label-xs text-on-surface-variant text-[9px] truncate" title={item.hash}>
            {hashPreview}…
          </span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase">Officer</span>
          <span className="font-label-xs text-on-surface-variant text-[9px] truncate">
            {item.officer || <span className="text-outline/60">NOT ASSIGNED</span>}
          </span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase">File</span>
          <span className="font-label-xs text-on-surface-variant text-[9px] truncate">
            {item.fileSize} · {item.format}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function Evidence() {
  const { evidence, loading, error, refetchEvidence } = useApp();
  const [typeFilter, setTypeFilter] = useState('all');
  const [query, setQuery] = useState('');

  const stats = useMemo(() => ({
    total: evidence.length,
    videoClips: evidence.filter((e) => e.type === 'video_clip').length,
    snapshots: evidence.filter((e) => e.type === 'snapshot').length,
    verified: evidence.filter((e) => e.status === 'verified').length,
  }), [evidence]);

  const filtered = useMemo(() => {
    let list = evidence;
    if (typeFilter !== 'all') list = list.filter((e) => e.type === typeFilter);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter((e) =>
        `${e.id} ${e.title} ${e.incidentId} ${e.cameraId} ${e.tags.join(' ')} ${e.officer || ''}`
          .toLowerCase()
          .includes(q)
      );
    }
    return list;
  }, [evidence, typeFilter, query]);

  if (loading) return <LoadingState message="OPENING EVIDENCE VAULT..." />;
  if (error) return <ErrorState message={error} onRetry={refetchEvidence} />;

  return (
    <div className="space-y-5">
      <PageHeader icon="folder_shared" title="EVIDENCE VAULT" subtitle="CHAIN OF CUSTODY & AUDIOVISUAL RECORDS">
        <span className="inline-flex items-center gap-1.5 bg-secondary/10 border border-secondary/25 text-secondary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
          <span className="material-symbols-outlined text-[12px]">verified_user</span>
          WORM STORAGE
        </span>
      </PageHeader>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatBar icon="inventory_2" label="TOTAL RECORDS" value={stats.total} accent="text-primary" />
        <StatBar icon="movie" label="VIDEO CLIPS" value={stats.videoClips} accent="text-secondary" />
        <StatBar icon="photo_camera" label="SNAPSHOTS" value={stats.snapshots} accent="text-tertiary" />
        <StatBar icon="verified" label="VERIFIED" value={stats.verified} accent="text-secondary" />
      </div>

      <div className="bg-surface-container rounded-lg border border-outline-variant/30 px-4 py-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 flex-wrap">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setTypeFilter(f.key)}
              className={`inline-flex items-center gap-1.5 font-label-xs text-[10px] tracking-wider px-3 py-1.5 rounded-lg transition-colors border ${
                typeFilter === f.key
                  ? 'bg-primary-container/20 text-primary border-primary/30'
                  : 'text-outline hover:text-on-surface-variant hover:bg-surface-container-high border-transparent'
              }`}
            >
              <span className="material-symbols-outlined text-[12px]">
                {f.key === 'all' ? 'apps' : TYPE_META[f.key]?.icon || 'inventory_2'}
              </span>
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex-1 min-w-[200px] max-w-xs ml-auto">
          <div className="flex items-center gap-2 bg-surface-container-low border border-outline-variant/30 rounded-lg px-3 py-1.5">
            <span className="material-symbols-outlined text-[14px] text-outline">search</span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="FIND://"
              className="bg-transparent font-label-xs text-on-surface text-[11px] outline-none w-full placeholder:text-outline/50"
            />
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-surface-container rounded-lg border border-outline-variant/30">
          <EmptyState
            icon="folder_off"
            title="No Evidence Found"
            description="No evidence records match the current filters."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((item) => (
            <EvidenceCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}