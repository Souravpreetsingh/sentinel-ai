export default function PageHeader({ icon = 'article', title = '', subtitle = '', children }) {
  return (
    <div className="flex items-center justify-between gap-4 mb-6">
      <div className="flex items-center gap-3 min-w-0">
        <span className="material-symbols-outlined text-[28px] text-primary">
          {icon}
        </span>
        <div className="min-w-0">
          <h1 className="font-headline-lg text-on-surface text-xl font-semibold truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="font-body-sm text-outline text-[12px] tracking-wider mt-0.5 truncate">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {children && (
        <div className="flex items-center gap-2 flex-shrink-0">{children}</div>
      )}
    </div>
  );
}
