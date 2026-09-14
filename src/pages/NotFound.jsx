import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center gap-4 px-4">
      <span className="material-symbols-outlined text-[72px] text-primary/50">gps_off</span>
      <div className="flex items-baseline gap-4">
        <span className="font-headline-xl text-on-surface text-7xl font-bold">404</span>
        <span className="hidden sm:inline-block h-14 w-px bg-outline-variant/30" />
        <span className="font-label-sm text-primary text-sm tracking-[0.4em]">PAGE NOT FOUND</span>
      </div>
      <p className="font-body-sm text-outline max-w-md">
        The requested route does not exist in the SENTINEL AI control surface. The link may be
        outdated, mistyped, or the resource may have been relocated.
      </p>
      <div className="flex items-center gap-3 mt-2">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 bg-primary text-on-primary font-label-xs text-[9px] tracking-wider px-4 py-2.5 rounded-lg hover:bg-primary/90 transition-colors"
        >
          <span className="material-symbols-outlined text-[15px]">dashboard</span>
          RETURN TO COMMAND CENTER
        </Link>
        <button
          onClick={() => window.history.back()}
          className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface font-label-xs text-[9px] tracking-wider px-4 py-2.5 rounded-lg hover:bg-surface-container-highest transition-colors"
        >
          <span className="material-symbols-outlined text-[15px]">arrow_back</span>
          GO BACK
        </button>
      </div>
      <span className="font-label-xs text-outline text-[8px] tracking-widest mt-4">
        SENTINEL AI · ROUTE CONTROLLER · HTTP 404
      </span>
    </div>
  );
}