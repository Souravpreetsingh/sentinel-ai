const severityStyles = {
  critical: 'bg-error-container text-on-error-container font-bold',
  high: 'bg-surface-container-high text-secondary font-semibold',
  medium: 'bg-surface-container-high text-tertiary font-medium',
  low: 'bg-surface-container text-outline',
};

const sizeStyles = {
  sm: 'text-[8px] px-1.5 py-px',
  md: 'text-[9px] px-2 py-0.5',
};

export default function SeverityBadge({ severity = 'medium', size = 'md' }) {
  return (
    <span
      className={`inline-flex items-center font-label-xs uppercase tracking-wider rounded ${severityStyles[severity] || severityStyles.medium} ${sizeStyles[size] || sizeStyles.md}`}
    >
      {severity}
    </span>
  );
}
