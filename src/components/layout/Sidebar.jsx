import { NavLink } from 'react-router-dom';

const navItems = [
  { num: '01', label: 'Command Center', icon: 'dashboard', path: '/' },
  { num: '02', label: 'Live Cameras', icon: 'videocam', path: '/cameras' },
  { num: '03', label: 'Live Wall', icon: 'wallpaper', path: '/live-wall' },
  { num: '04', label: 'Watchlists', icon: 'list', path: '/watchlists' },
  { num: '05', label: 'Alerts', icon: 'add_alert', path: '/alerts' },
  { num: '06', label: 'Investigation', icon: 'search', path: '/investigation' },
  { num: '07', label: 'Incidents', icon: 'warning', path: '/incidents' },
  { num: '08', label: 'City Map', icon: 'map', path: '/map' },
  { num: '09', label: 'Analytics', icon: 'monitoring', path: '/analytics' },
  { num: '10', label: 'AI Assistant', icon: 'smart_toy', path: '/assistant' },
  { num: '11', label: 'Evidence', icon: 'folder_shared', path: '/evidence' },
  { num: '12', label: 'System Health', icon: 'health_and_safety', path: '/system' },
];

export default function Sidebar({ isOpen, onClose }) {
  const baseLinkClasses =
    'flex items-center gap-3 px-4 py-2.5 text-body-sm text-on-surface-variant rounded-r-lg transition-all duration-150 hover:bg-surface-container-low hover:text-on-surface';
  const activeLinkClasses =
    'bg-primary-container text-on-primary font-semibold border-l-2 border-primary';

  const sidebarContent = (
    <div className="flex h-full flex-col bg-surface-container-lowest border-r border-outline-variant/30 w-72">
      {/* Brand */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-3">
          <svg
            width="32"
            height="32"
            viewBox="0 0 100 100"
            className="text-primary flex-shrink-0"
          >
            <polygon
              points="50,2 93,27 93,73 50,98 7,73 7,27"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
            />
            <polygon
              points="50,18 78,35 78,65 50,82 22,65 22,35"
              fill="currentColor"
              fillOpacity="0.15"
              stroke="currentColor"
              strokeWidth="2"
            />
            <circle cx="50" cy="50" r="8" fill="currentColor" />
          </svg>
          <div>
            <div className="font-headline-md text-base font-semibold text-on-surface tracking-wide">
              SENTINEL AI
            </div>
            <div className="font-label-xs text-outline text-[9px] tracking-widest mt-0.5">
              AI CCTV INTELLIGENCE // SEC-OPS
            </div>
          </div>
        </div>
      </div>

      {/* Privacy badge */}
      <div className="mx-5 mb-5 flex items-center gap-2 rounded-md bg-surface-container-low px-3 py-2">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-secondary opacity-75"></span>
          <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary"></span>
        </span>
        <div className="flex flex-col">
          <span className="font-label-xs text-secondary text-[9px] tracking-widest">
            PRIVACY MODE: ACTIVE
          </span>
          <span className="font-label-xs text-outline text-[8px] tracking-wider">
            ISO-27701
          </span>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-3 space-y-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            onClick={onClose}
            className={({ isActive }) =>
              `${baseLinkClasses} ${isActive ? activeLinkClasses : ''}`
            }
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            <span className="flex-1">
              <span className="font-label-xs text-outline text-[9px] mr-2">{item.num}</span>
              {item.label}
            </span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-outline-variant/20 px-3 py-4 space-y-3">
        <NavLink
          to="/settings"
          onClick={onClose}
          className={({ isActive }) =>
            `${baseLinkClasses} ${isActive ? activeLinkClasses : ''}`
          }
        >
          <span className="material-symbols-outlined text-[20px]">tune</span>
          <span>Settings</span>
        </NavLink>

        {/* User profile */}
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-container-low mx-1">
          <div className="h-8 w-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary font-label-sm text-[10px] font-semibold">
            DJ
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-label-sm text-on-surface text-[11px] truncate">
              Officer D. Jenkins
            </span>
            <span className="font-label-xs text-outline text-[9px] tracking-wider">
              BADGE #4829
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 z-40">
        {sidebarContent}
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <aside className="absolute inset-y-0 left-0 z-50">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}
