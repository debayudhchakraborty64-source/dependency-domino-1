import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../../store/useStore';
import { search } from '../../services/apiService';
import './Header.css';

export default function Header() {
  const navigate = useNavigate();
  const { activeRepo, setCommandPaletteOpen, setSelectedComponent } = useStore();
  const [searchVal, setSearchVal] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const debounceRef = useRef(null);

  const handleSearch = useCallback(async (q) => {
    if (!q.trim() || q.length < 2) { setResults([]); return; }
    setSearching(true);
    const { data } = await search(q, activeRepo?.id);
    setResults(data || []);
    setSearching(false);
    setShowResults(true);
  }, [activeRepo]);

  const onInputChange = (e) => {
    const q = e.target.value;
    setSearchVal(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => handleSearch(q), 250);
    if (!q) { setResults([]); setShowResults(false); }
  };

  const selectResult = (r) => {
    setSelectedComponent(r);
    setShowResults(false);
    setSearchVal('');
    navigate('/impact');
  };

  const riskColor = (score) => {
    if (score >= 75) return 'var(--risk-critical)';
    if (score >= 50) return 'var(--risk-high)';
    if (score >= 25) return 'var(--risk-medium)';
    return 'var(--risk-low)';
  };

  return (
    <header className="app-header" role="banner">
      {/* Global search */}
      <div className="header-search-wrap" onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setShowResults(false);
      }}>
        <div className="header-search">
          <SearchIcon />
          <input
            className="header-search-input"
            type="search"
            placeholder="Search files, functions, components…"
            value={searchVal}
            onChange={onInputChange}
            onFocus={() => results.length > 0 && setShowResults(true)}
            aria-label="Global search"
          />
          <kbd className="header-search-kbd">⌘K</kbd>
        </div>
        {showResults && (
          <div className="header-search-results" role="listbox">
            {searching && (
              <div className="search-result-empty">Searching…</div>
            )}
            {!searching && results.length === 0 && (
              <div className="search-result-empty">No results found</div>
            )}
            {results.map(r => (
              <button
                key={r.id}
                className="search-result-item"
                onClick={() => selectResult(r)}
                role="option"
              >
                <span className="search-result-name">{r.name}</span>
                <span className="search-result-path muted">{r.path}</span>
                <span className="tag" style={{ color: riskColor(r.risk_score) }}>
                  {r.type}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right side */}
      <div className="header-right">
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setCommandPaletteOpen(true)}
          title="Open command palette (⌘K)"
          aria-label="Open command palette"
        >
          <span>⌘K</span>
        </button>
      </div>
    </header>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="6.5" cy="6.5" r="5"/>
      <path d="M10.5 10.5L15 15"/>
    </svg>
  );
}
