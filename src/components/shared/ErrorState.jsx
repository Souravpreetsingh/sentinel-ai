export default function ErrorState({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <span className="material-symbols-outlined text-[40px] text-error">
        error
      </span>
      <span className="font-body-sm text-on-surface-variant text-center max-w-sm">
        {message}
      </span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-surface-container-high px-4 py-2 font-label-sm text-on-surface text-[11px] tracking-wider hover:bg-surface-container-highest transition-colors border border-outline-variant/30"
        >
          <span className="material-symbols-outlined text-[16px]">refresh</span>
          RETRY
        </button>
      )}
    </div>
  );
}
