export function formatDate(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return String(dateStr);
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export function formatTimeAgo(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return String(dateStr);

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return 'just now';

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 45) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;

  return date.toLocaleDateString();
}

export function classNames(...args) {
  const classes = [];

  args.forEach((arg) => {
    if (!arg) return;

    if (typeof arg === 'string' || typeof arg === 'number') {
      const value = String(arg).trim();
      if (value) classes.push(value);
      return;
    }

    if (Array.isArray(arg)) {
      const joined = classNames(...arg);
      if (joined) classes.push(joined);
      return;
    }

    if (typeof arg === 'object') {
      Object.entries(arg).forEach(([key, enabled]) => {
        if (enabled && key) classes.push(key);
      });
    }
  });

  return classes.join(' ');
}

const STATUS_COLORS = {
  online: 'bg-green-100 text-green-700 ring-1 ring-green-600/20',
  warning: 'bg-amber-100 text-amber-700 ring-1 ring-amber-600/20',
  offline: 'bg-red-100 text-red-700 ring-1 ring-red-600/20',
  maintenance: 'bg-gray-100 text-gray-600 ring-1 ring-gray-500/20',
  degraded: 'bg-orange-100 text-orange-700 ring-1 ring-orange-600/20',
};

export function getStatusColor(status) {
  return STATUS_COLORS[status] ?? STATUS_COLORS.maintenance;
}

const SEVERITY_COLORS = {
  critical: 'bg-red-100 text-red-700 ring-1 ring-red-600/20',
  high: 'bg-orange-100 text-orange-700 ring-1 ring-orange-600/20',
  medium: 'bg-amber-100 text-amber-700 ring-1 ring-amber-600/20',
  low: 'bg-blue-100 text-blue-700 ring-1 ring-blue-600/20',
  info: 'bg-gray-100 text-gray-600 ring-1 ring-gray-500/20',
  success: 'bg-green-100 text-green-700 ring-1 ring-green-600/20',
  warning: 'bg-amber-100 text-amber-700 ring-1 ring-amber-600/20',
};

export function getSeverityColor(severity) {
  return SEVERITY_COLORS[severity] ?? SEVERITY_COLORS.info;
}

export function getSeverityLabel(severity) {
  return String(severity || 'unknown').toUpperCase();
}

export function truncate(str, max) {
  const value = String(str ?? '');
  if (value.length <= max) return value;
  return `${value.slice(0, Math.max(0, max - 1))}…`;
}