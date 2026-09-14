import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useApp } from '../../context/AppContext';

export default function Header({ onMenuToggle }) {
  const { unreadCount } = useApp();
  const [query, setQuery] = useState('');
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, '0');
      const m = String(now.getUTCMinutes()).padStart(2, '0');
      const s = String(now.getUTCSeconds()).padStart(2, '0');
      setTime(`${h}:${m}:${s} UTC`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const handleSearch = (e) => {
    if (e.key === 'Enter' && query.trim()) {
      console.log('[SENTINEL SEARCH]', query.trim());
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-30 h-16 flex items-center gap-3 px-4 pl-72 bg-surface-container-lowest/90 backdrop-blur-md border-b border-outline-variant/20">
      {/* Mobile hamburger */}
      <button
        onClick={onMenuToggle}
        className="lg:hidden flex items-center justify-center h-10 w-10 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors"
      >
        <span className="material-symbols-outlined">menu</span>
      </button>

      {/* Search */}
      <div className="flex items-center flex-1 max-w-xl gap-2 bg-surface-container rounded-lg px-3 py-2 border border-outline-variant/30 focus-within:border-primary/50 transition-colors">
        <span className="font-label-xs text-outline text-[10px] tracking-widest whitespace-nowrap select-none">
          QUERY://
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleSearch}
          placeholder="Search entities, RTSP feeds, tags..."
          className="flex-1 bg-transparent text-body-sm text-on-surface placeholder:text-outline outline-none"
        />
        <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-outline-variant/40 bg-surface-container-low px-1.5 py-0.5 font-label-xs text-outline text-[9px]">
          CTRL+K
        </kbd>
      </div>

      {/* Filter */}
      <button className="hidden sm:flex items-center gap-1.5 rounded-lg border border-outline-variant/30 bg-surface-container px-3 py-2 text-body-sm text-on-surface-variant hover:bg-surface-container-high transition-colors">
        <span className="material-symbols-outlined text-[16px]">filter_list</span>
        <span className="font-label-xs text-[10px] tracking-wider">FILTER: ALL FEEDS</span>
      </button>

      {/* Right side */}
      <div className="flex items-center gap-3 ml-auto">
        {/* Demo badge */}
        <div className="hidden md:flex items-center gap-1.5 rounded-md bg-surface-container px-2.5 py-1.5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-tertiary opacity-75"></span>
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-tertiary"></span>
          </span>
          <span className="font-label-xs text-tertiary text-[9px] tracking-wider">
            DEMO SIMULATION
          </span>
        </div>

        {/* Status badge */}
        <div className="hidden xl:flex items-center gap-1.5 rounded-md bg-surface-container px-2.5 py-1.5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-secondary"></span>
          </span>
          <span className="font-label-xs text-secondary text-[9px] tracking-wider">
            ALL SYSTEMS OPERATIONAL (99.2% UPTIME)
          </span>
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-outline-variant/30 hidden sm:block" />

        {/* Clock */}
        <div className="font-label-sm text-on-surface-variant text-[11px] tracking-widest whitespace-nowrap tabular-nums hidden sm:block">
          {time}
        </div>

        {/* Notifications */}
        <button className="relative flex items-center justify-center h-10 w-10 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors">
          <span className="material-symbols-outlined text-[22px]">notifications</span>
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-error px-1 font-label-xs text-on-error text-[8px] font-bold">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>

        {/* Avatar */}
        <div className="h-8 w-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary font-label-sm text-[10px] font-semibold cursor-pointer">
          DJ
        </div>
      </div>
    </header>
  );
}
