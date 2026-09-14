const statusConfig = {
  open: {
    className: 'bg-surface-container text-error',
    dot: false,
    icon: null,
  },
  investigating: {
    className: 'text-secondary-container',
    dot: true,
    dotColor: 'bg-secondary-container',
    icon: null,
  },
  dispatched: {
    className: 'bg-surface-container text-primary font-semibold',
    dot: false,
    icon: null,
  },
  resolved: {
    className: 'text-outline',
    dot: false,
    icon: 'check_circle',
  },
  online: {
    className: 'bg-surface-container text-secondary',
    dot: false,
    icon: null,
  },
  offline: {
    className: 'bg-surface-container text-outline',
    dot: false,
    icon: null,
  },
  warning: {
    className: 'bg-tertiary-container/20 text-tertiary',
    dot: false,
    icon: null,
  },
};

export default function StatusBadge({ status = 'open' }) {
  const config = statusConfig[status] || statusConfig.open;

  return (
    <span
      className={`inline-flex items-center gap-1 font-label-xs px-2 py-0.5 rounded ${config.className}`}
    >
      {config.dot && (
        <span className="relative flex h-1.5 w-1.5">
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full ${config.dotColor} opacity-75`}
          ></span>
          <span
            className={`relative inline-flex h-1.5 w-1.5 rounded-full ${config.dotColor}`}
          ></span>
        </span>
      )}
      {config.icon && (
        <span className="material-symbols-outlined text-[12px]">{config.icon}</span>
      )}
      {status}
    </span>
  );
}
