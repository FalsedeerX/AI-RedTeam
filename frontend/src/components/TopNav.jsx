import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function TopNav({ username, onSignOut }) {
  const location = useLocation();
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const dropdownRef = React.useRef(null);

  const initials = username ? username.slice(0, 2).toUpperCase() : '??';

  // Close dropdown when clicking outside
  React.useEffect(() => {
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <nav
      style={{ background: '#0a0e14', borderBottom: '1px solid var(--rt-border)' }}
      className="sticky top-0 z-50 flex items-center gap-6 px-6"
      aria-label="Global navigation"
    >
      {/* Logo */}
      <Link
        to="/dashboard"
        className="py-4 font-mono font-bold text-[15px] tracking-tight whitespace-nowrap no-underline"
        style={{ color: 'var(--rt-flame)' }}
      >
        ⬡ AI RedTeam
      </Link>

      {/* Nav links */}
      <div className="flex items-center flex-1">
        <NavLink to="/dashboard" active={location.pathname === '/dashboard'}>
          Dashboard
        </NavLink>
        <NavLink to="/guide" active={location.pathname === '/guide'}>
          Guide
        </NavLink>
      </div>

      {/* User area */}
      <div className="relative flex items-center gap-3" ref={dropdownRef}>
        <span className="text-xs" style={{ color: 'var(--rt-muted)' }}>
          {username}
        </span>
        <button
          onClick={() => setDropdownOpen(o => !o)}
          className="w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs font-bold text-white flex-shrink-0 focus:outline-none"
          style={{ background: 'linear-gradient(135deg, var(--rt-flame) 0%, var(--rt-orchid) 100%)' }}
          aria-label="User menu"
        >
          {initials}
        </button>

        {/* Dropdown */}
        {dropdownOpen && (
          <div
            className="absolute right-0 top-10 w-48 rounded-lg overflow-hidden shadow-2xl z-50"
            style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
          >
            <div
              className="px-4 py-3"
              style={{ borderBottom: '1px solid var(--rt-border)' }}
            >
              <p className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>{username}</p>
              <p className="text-xs font-mono" style={{ color: 'var(--rt-muted)' }}>analyst</p>
            </div>
            <button
              className="w-full text-left px-4 py-3 text-sm transition-colors hover:bg-[var(--rt-surface2)]"
              style={{ color: 'var(--rt-muted)' }}
              onClick={() => setDropdownOpen(false)}
            >
              Account Settings
              <span className="ml-2 text-xs opacity-50">(coming soon)</span>
            </button>
            <button
              className="w-full text-left px-4 py-3 text-sm transition-colors hover:bg-[var(--rt-surface2)]"
              style={{ color: 'var(--rt-ember)', borderTop: '1px solid var(--rt-border)' }}
              onClick={() => { setDropdownOpen(false); onSignOut?.(); }}
            >
              Sign Out
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

function NavLink({ to, active, children }) {
  return (
    <Link
      to={to}
      className="px-4 py-[14px] text-xs font-semibold uppercase tracking-widest transition-colors no-underline"
      style={{
        color: active ? 'var(--rt-sky)' : 'var(--rt-muted)',
        borderBottom: active ? '2px solid var(--rt-sky)' : '2px solid transparent',
      }}
    >
      {children}
    </Link>
  );
}
