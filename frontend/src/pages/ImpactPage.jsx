import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { getComponents, getImpact, listRepositories } from '../services/apiService';
import ImpactPanel from '../components/impact/ImpactPanel';
import './ImpactPage.css';

const RISK_COLORS = {
  critical: 'var(--risk-critical)', high: 'var(--risk-high)',
  medium: 'var(--risk-medium)', low: 'var(--risk-low)', unknown: 'var(--risk-unknown)',
};

export default function ImpactPage() {
  const navigate = useNavigate();
  const {
    activeRepo, setActiveRepo, selectedComponent, setSelectedComponent,
    impact, setImpact, addNotification,
  } = useStore();

  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

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
    getComponents(activeRepo.id, { per_page: 100 }).then(({ data }) => {
      if (data) setComponents(data.components || []);
      setLoading(false);
    });
  }, [activeRepo]);

  const selectComponent = async (comp) => {
    setSelectedComponent(comp);
    const { data, error } = await getImpact(comp.id);
    if (data) setImpact(data);
    else addNotification(error || 'Impact load failed', 'error');
  };

  const filtered = components.filter(
    c => !search || c.name.toLowerCase().includes(search.toLowerCase()) ||
         c.path.toLowerCase().includes(search.toLowerCase())
  );

  const riskClass = r => ({ critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[r] || 'badge-unknown');

  return (
    <div className="impact-page">
      {/* Left: component selector */}
      <div className="impact-selector">
        <div className="impact-selector-header">
          <div className="section-title" style={{ margin: 0 }}>SELECT COMPONENT</div>
          <span className="text-xs muted">{filtered.length} components</span>
        </div>
        <div style={{ padding: '8px 12px' }}>
          <input
            className="input"
            placeholder="Search components…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="impact-comp-list">
          {loading && <div className="loading-container"><div className="spinner"/></div>}
          {!loading && !activeRepo && (
            <div className="empty-container text-sm">
              <p>No repository loaded.</p>
              <button className="btn btn-primary btn-sm" onClick={() => navigate('/overview')}>
                Go to Overview
              </button>
            </div>
          )}
          {filtered.filter(c => !c.metadata?.is_test).map(comp => (
            <button
              key={comp.id}
              className={`impact-comp-item ${selectedComponent?.id === comp.id ? 'impact-comp-item--active' : ''}`}
              onClick={() => selectComponent(comp)}
            >
              <div className="impact-comp-name truncate">{comp.name}</div>
              <div className="impact-comp-path truncate muted text-xs mono">{comp.path}</div>
              <div className="impact-comp-meta">
                <span className="tag">{comp.language}</span>
                <span className={`badge ${riskClass(comp.risk)}`}>{comp.risk}</span>
                {comp.risk_score > 0 && (
                  <span
                    className="text-xs mono"
                    style={{ color: RISK_COLORS[comp.risk], marginLeft: 'auto' }}
                  >
                    {Math.round(comp.risk_score)}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right: impact panel */}
      <div className="impact-main">
        {selectedComponent ? (
          <ImpactPanel onClose={() => { setSelectedComponent(null); setImpact(null); }} />
        ) : (
          <div className="empty-container" style={{ height: '100%' }}>
            <div style={{ fontSize: 32 }}>⚡</div>
            <h3 style={{ color: 'var(--text-secondary)' }}>Select a Component</h3>
            <p className="muted text-sm">Choose a file from the list to analyze its change impact.</p>
          </div>
        )}
      </div>
    </div>
  );
}
