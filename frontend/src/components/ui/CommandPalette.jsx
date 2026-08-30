import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../../store/useStore';
import './CommandPalette.css';

const COMMANDS = [
  { id: 'open-repo',    label: 'Open Repository',     icon: '📁', page: '/repository' },
  { id: 'dep-map',      label: 'Open Dependency Map',  icon: '🗺', page: '/dependency-map' },
  { id: 'impact',       label: 'Analyze Impact',       icon: '⚡', page: '/impact' },
  { id: 'risk-center',  label: 'Open Risk Center',     icon: '🛡', page: '/risk-center' },
  { id: 'test-impact',  label: 'Test Impact',          icon: '🧪', page: '/test-impact' },
  { id: 'reports',      label: 'Generate Report',      icon: '📋', page: '/reports' },
  { id: 'settings',     label: 'Settings',             icon: '⚙', page: '/settings' },
];

export default function CommandPalette() {
  const navigate = useNavigate();
  const { setCommandPaletteOpen } = useStore();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const filtered = COMMANDS.filter(
    c => c.label.toLowerCase().includes(query.toLowerCase())
  );

  const execute = (cmd) => {
    setCommandPaletteOpen(false);
    navigate(cmd.page);
  };

  const onKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected(s => Math.min(s + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected(s => Math.max(s - 1, 0));
    } else if (e.key === 'Enter' && filtered[selected]) {
      execute(filtered[selected]);
    } else if (e.key === 'Escape') {
      setCommandPaletteOpen(false);
    }
  };

  return (
    <div
      className="cmd-backdrop"
      onClick={() => setCommandPaletteOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
    >
      <div
        className="cmd-panel"
        onClick={e => e.stopPropagation()}
        role="combobox"
        aria-expanded="true"
      >
        <div className="cmd-search">
          <span className="cmd-icon">⌘</span>
          <input
            ref={inputRef}
            className="cmd-input"
            placeholder="Type a command…"
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0); }}
            onKeyDown={onKey}
            aria-label="Command input"
            aria-autocomplete="list"
          />
        </div>
        <ul className="cmd-list" role="listbox">
          {filtered.map((cmd, i) => (
            <li
              key={cmd.id}
              className={`cmd-item ${i === selected ? 'cmd-item--selected' : ''}`}
              onClick={() => execute(cmd)}
              role="option"
              aria-selected={i === selected}
            >
              <span className="cmd-item-icon">{cmd.icon}</span>
              <span>{cmd.label}</span>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="cmd-empty">No commands match</li>
          )}
        </ul>
        <div className="cmd-footer">
          <span><kbd>↑↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
