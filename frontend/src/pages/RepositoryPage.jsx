import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { getComponents, listRepositories } from '../services/apiService';
import UploadModal from '../components/repository/UploadModal';
import './RepositoryPage.css';

const LANG_COLORS = {
  javascript: '#f1e05a', jsx: '#61dafb', typescript: '#3178c6',
  tsx: '#3178c6', python: '#3572A5', css: '#563d7c',
  html: '#e34c26', json: '#666', yaml: '#cb171e', other: '#888',
};

export default function RepositoryPage() {
  const navigate = useNavigate();
  const { activeRepo, setActiveRepo, setSelectedComponent } = useStore();
  const [components, setComponents] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ language: '', type: '', risk: '', search: '' });
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [expandedDirs, setExpandedDirs] = useState(new Set(['frontend', 'backend', 'tests']));

  // Load first available repo if none set
  useEffect(() => {
    if (!activeRepo) {
      listRepositories().then(({ data }) => {
        if (data?.length) setActiveRepo(data[0]);
      });
    }
  }, []);

  useEffect(() => {
    if (!activeRepo) return;
    setLoading(true);
    setError(null);
    const params = { page, per_page: 100 };
    if (filters.language) params.language = filters.language;
    if (filters.type) params.node_type = filters.type;
    if (filters.risk) params.risk = filters.risk;
    if (filters.search) params.search = filters.search;

    getComponents(activeRepo.id, params).then(({ data, error }) => {
      if (error) { setError(error); setLoading(false); return; }
      setComponents(data.components || []);
      setTotal(data.total || 0);
      setLoading(false);
    });
  }, [activeRepo, filters, page]);

  const openComponent = (comp) => {
    setSelectedComponent(comp);
    navigate('/impact');
  };

  // Group by top-level directory
  const grouped = {};
  components.forEach(c => {
    const topDir = c.path.split('/')[0];
    if (!grouped[topDir]) grouped[topDir] = [];
    grouped[topDir].push(c);
  });

  const riskBadge = (risk) => {
    const classes = { critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low', unknown: 'badge-unknown' };
    return <span className={`badge ${classes[risk] || 'badge-unknown'}`}>{risk}</span>;
  };

  return (
    <div className="repo-page">
      {/* Sidebar: file tree */}
      <div className="repo-tree-panel">
        <div className="repo-tree-header">
          <div className="section-title" style={{ margin: 0 }}>
            {activeRepo ? activeRepo.name : 'No Repository'}
            {activeRepo?.is_demo && <span className="badge badge-demo" style={{ marginLeft: 8 }}>DEMO</span>}
          </div>
          {activeRepo && (
            <span className="text-xs muted">{total} files</span>
          )}
        </div>

        {/* Search */}
        <div style={{ padding: '8px 12px' }}>
          <input
            className="input"
            placeholder="Filter files…"
            value={filters.search}
            onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          />
        </div>

        {/* Filters */}
        <div className="repo-filters">
          <select
            className="input"
            value={filters.language}
            onChange={e => setFilters(f => ({ ...f, language: e.target.value }))}
            aria-label="Filter by language"
          >
            <option value="">All languages</option>
            {['javascript','jsx','typescript','tsx','python','css','html'].map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
          <select
            className="input"
            value={filters.type}
            onChange={e => setFilters(f => ({ ...f, type: e.target.value }))}
            aria-label="Filter by type"
          >
            <option value="">All types</option>
            {['file','service','api','test','module'].map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select
            className="input"
            value={filters.risk}
            onChange={e => setFilters(f => ({ ...f, risk: e.target.value }))}
            aria-label="Filter by risk"
          >
            <option value="">All risk levels</option>
            {['critical','high','medium','low'].map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        {/* Tree */}
        <div className="repo-tree-list">
          {loading && <div className="loading-container"><div className="spinner"/></div>}
          {error && <div className="error-container"><div className="error-title">Error</div><div>{error}</div></div>}
          {!loading && !error && !activeRepo && (
            <div className="empty-container">
              <p>No repository loaded.</p>
              <button className="btn btn-primary btn-sm" onClick={() => setShowUpload(true)}>
                Import Repository
              </button>
            </div>
          )}
          {!loading && !error && activeRepo && Object.entries(grouped).map(([dir, files]) => (
            <div key={dir} className="tree-dir">
              <button
                className="tree-dir-toggle"
                onClick={() => setExpandedDirs(s => {
                  const next = new Set(s);
                  next.has(dir) ? next.delete(dir) : next.add(dir);
                  return next;
                })}
                aria-expanded={expandedDirs.has(dir)}
              >
                <span className="tree-dir-arrow">{expandedDirs.has(dir) ? '▾' : '▸'}</span>
                <span className="tree-dir-name">{dir}/</span>
                <span className="tree-dir-count text-xs muted">{files.length}</span>
              </button>
              {expandedDirs.has(dir) && (
                <div className="tree-files">
                  {files.map(f => (
                    <button
                      key={f.id}
                      className="tree-file"
                      onClick={() => openComponent(f)}
                      title={f.path}
                    >
                      <span
                        className="tree-file-dot"
                        style={{ background: LANG_COLORS[f.language] || '#888' }}
                      />
                      <span className="tree-file-name truncate">{f.name}</span>
                      {f.risk !== 'unknown' && f.risk !== 'low' && (
                        <span className={`badge badge-${f.risk} text-xs`} style={{ padding: '1px 5px', fontSize: '9px' }}>
                          {f.risk}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main: component detail or welcome */}
      <div className="repo-main">
        {!activeRepo ? (
          <div className="empty-container" style={{ height: '100%' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>No repository loaded</h3>
            <p className="muted text-sm">Import a repository or open the demo to get started.</p>
            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
              <button className="btn btn-primary" onClick={() => setShowUpload(true)}>Import ZIP</button>
              <button className="btn btn-secondary" onClick={() => navigate('/overview')}>Open Demo</button>
            </div>
          </div>
        ) : (
          <ComponentList
            components={components}
            loading={loading}
            onSelect={openComponent}
          />
        )}
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}

function ComponentList({ components, loading, onSelect }) {
  const riskClass = r => ({ critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[r] || 'badge-unknown');

  return (
    <div className="comp-list">
      <div className="comp-list-header">
        <span className="section-title" style={{ margin: 0 }}>All Components</span>
        <span className="text-xs muted">{components.length} shown</span>
      </div>
      {loading && <div className="loading-container"><div className="spinner"/></div>}
      <div className="comp-table">
        <div className="comp-table-head">
          <span>File</span><span>Language</span><span>Type</span><span>Lines</span><span>Deps</span><span>Dependents</span><span>Risk</span>
        </div>
        {components.map(c => (
          <button key={c.id} className="comp-table-row" onClick={() => onSelect(c)}>
            <span className="mono truncate" style={{ fontSize: 12 }} title={c.path}>{c.path}</span>
            <span className="tag">{c.language}</span>
            <span className="tag">{c.type}</span>
            <span className="muted text-sm">{c.metadata?.lines ?? '—'}</span>
            <span className="muted text-sm">{c.direct_dependency_count}</span>
            <span className="muted text-sm">{c.dependent_count}</span>
            <span className={`badge ${riskClass(c.risk)}`}>{c.risk}</span>
          </button>
        ))}
        {!loading && components.length === 0 && (
          <div className="comp-empty muted text-sm">No components match the current filters.</div>
        )}
      </div>
    </div>
  );
}
