import React from 'react';
import { NavLink } from 'react-router-dom';
import useStore from '../../store/useStore';
import './Sidebar.css';

const NAV_ITEMS = [
  { path: '/overview',       label: 'Overview',        icon: HomeIcon },
  { path: '/repository',     label: 'Repository',      icon: RepoIcon },
  { path: '/dependency-map', label: 'Dependency Map',  icon: GraphIcon },
  { path: '/impact',         label: 'Impact Analysis', icon: BlastIcon },
  { path: '/risk-center',    label: 'Risk Center',     icon: ShieldIcon },
  { path: '/test-impact',    label: 'Test Impact',     icon: TestIcon },
  { path: '/reports',        label: 'Reports',         icon: ReportIcon },
];

const BOTTOM_ITEMS = [
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
];

export default function Sidebar() {
  const { activeRepo, backendStatus, watsonxConfigured } = useStore();

  return (
    <aside className="sidebar" aria-label="Main navigation">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon" aria-hidden="true">
          <DominoIcon />
        </div>
        <div>
          <div className="sidebar-logo-name">Dependency</div>
          <div className="sidebar-logo-sub">DOMINO</div>
        </div>
      </div>

      {/* Active repo indicator */}
      {activeRepo && (
        <div className="sidebar-repo-indicator">
          <div className="sidebar-repo-dot" />
          <span className="truncate" title={activeRepo.name}>{activeRepo.name}</span>
          {activeRepo.is_demo && (
            <span className="badge badge-demo badge-label" style={{ fontSize: '9px', padding: '1px 6px' }}>DEMO</span>
          )}
        </div>
      )}

      {/* Nav links */}
      <nav className="sidebar-nav" role="navigation">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link--active' : ''}`
            }
            aria-label={label}
          >
            <span className="sidebar-link-icon">
              <Icon />
            </span>
            <span className="sidebar-link-label">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="sidebar-bottom">
        <div className="sidebar-status-row">
          <div className={`status-dot ${backendStatus === 'ok' ? 'status-dot--ok' : 'status-dot--err'}`} />
          <span className="text-xs muted sidebar-status-label">
            {backendStatus === 'ok' ? 'Backend connected' : 'Backend offline'}
          </span>
        </div>
        {watsonxConfigured && (
          <div className="sidebar-status-row">
            <div className="status-dot status-dot--ai" />
            <span className="text-xs muted sidebar-status-label">watsonx.ai active</span>
          </div>
        )}
        {BOTTOM_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `sidebar-link sidebar-link-sm ${isActive ? 'sidebar-link--active' : ''}`
            }
          >
            <span className="sidebar-link-icon">
              <Icon />
            </span>
            <span className="sidebar-link-label">{label}</span>
          </NavLink>
        ))}
      </div>
    </aside>
  );
}

// ─── Icons — 20px crisp outline SVGs ─────────────────────────────────────────

function DominoIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <rect x="2.5" y="2" width="8" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none" opacity="0.9"/>
      <rect x="12.5" y="7" width="7" height="13" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none" opacity="0.6"/>
      <circle cx="6.5" cy="7" r="1" fill="currentColor"/>
      <circle cx="6.5" cy="11" r="1" fill="currentColor"/>
      <circle cx="6.5" cy="15" r="1" fill="currentColor"/>
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 9.5L12 3l9 6.5V21a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/>
      <path d="M9 22V12h6v10"/>
    </svg>
  );
}

function RepoIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
    </svg>
  );
}

function GraphIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="5" cy="12" r="2.5"/>
      <circle cx="19" cy="5" r="2.5"/>
      <circle cx="19" cy="19" r="2.5"/>
      <path d="M7.5 12l9-6.5M7.5 12l9 6.5"/>
    </svg>
  );
}

function BlastIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  );
}

function TestIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="9" y1="15" x2="15" y2="15"/>
      <line x1="9" y1="11" x2="11" y2="11"/>
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 20V10M12 20V4M6 20v-6"/>
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
    </svg>
  );
}
