export default function EmptyState({ icon = 'inbox', title = 'Nothing here', description = '' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <span className="material-symbols-outlined text-[48px] text-outline-variant/60">
        {icon}
      </span>
      <span className="font-headline-md text-on-surface text-sm font-semibold">
        {title}
      </span>
      {description && (
        <span className="font-body-sm text-outline text-center max-w-sm">
          {description}
        </span>
      )}
    </div>
  );
}
