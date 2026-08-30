import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { getRisks, listRepositories, getImpact } from '../services/apiService';
import './RiskCenterPage.css';

const RISK_COLORS = {
  critical: 'var(--risk-critical)', high: 'var(--risk-high)',
  medium: 'var(--risk-medium)', low: 'var(--risk-low)', unknown: 'var(--risk-unknown)',
};

export default function RiskCenterPage() {
  const navigate = useNavigate();
  const { activeRepo, setActiveRepo, setSelectedComponent, setImpact, addNotification } = useStore();
  const [risks, setRisks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState('risk_score');
  const [search, setSearch] = useState('');
  const [filterRisk, setFilterRisk] = useState('');

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
    getRisks(activeRepo.id).then(({ data, error }) => {
      if (data) setRisks(data);
      setLoading(false);
    });
  }, [activeRepo]);

  const handleSelectComponent = async (comp) => {
    setSelectedComponent(comp);
    const { data } = await getImpact(comp.id);
    if (data) setImpact(data);
    navigate('/impact');
  };

  const sorted = risks?.top_risk_components
    ? [...risks.top_risk_components]
        .filter(c => {
          const q = search.toLowerCase();
          const matchSearch = !q || c.path.toLowerCase().includes(q) || c.name?.toLowerCase().includes(q);
          const matchRisk = !filterRisk || c.risk === filterRisk;
          return matchSearch && matchRisk;
        })
        .sort((a, b) => b.risk_score - a.risk_score)
    : [];

  const riskClass = r => ({ critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[r] || 'badge-unknown');

  return (
    <div className="page-container risk-page">
      <div className="risk-page-header">
        <h1 className="risk-page-title">Codebase Risk Center</h1>
        {activeRepo && <span className="muted text-sm">{activeRepo.name}</span>}
      </div>

      {/* Summary cards */}
      {risks && (
        <div className="risk-summary-grid">
          <RiskSummaryCard label="Total Components" value={risks.total_components} color="var(--text-primary)" />
          <RiskSummaryCard label="Critical" value={risks.critical_count} color="var(--risk-critical)" />
          <RiskSummaryCard label="High Risk" value={risks.high_count} color="var(--risk-high)" />
          <RiskSummaryCard label="Medium Risk" value={risks.medium_count} color="var(--risk-medium)" />
          <RiskSummaryCard label="Low Risk" value={risks.low_count} color="var(--risk-low)" />
          <RiskSummaryCard label="Weak Test Coverage" value={risks.weak_test_coverage_count} color="var(--yellow)" />
        </div>
      )}

      {/* Risk bar visualization */}
      {risks && risks.total_components > 0 && (
        <div className="risk-bar-section card">
          <div className="section-title">RISK DISTRIBUTION</div>
          <div className="risk-bar-track">
            {[
              { key: 'critical_count', color: 'var(--risk-critical)' },
              { key: 'high_count', color: 'var(--risk-high)' },
              { key: 'medium_count', color: 'var(--risk-medium)' },
              { key: 'low_count', color: 'var(--risk-low)' },
              { key: 'unknown_count', color: 'var(--risk-unknown)' },
            ].map(({ key, color }) => {
              const count = risks[key] || 0;
              const pct = (count / risks.total_components) * 100;
              return pct > 0 ? (
                <div
                  key={key}
                  className="risk-bar-segment"
                  style={{ width: `${pct}%`, background: color }}
                  title={`${key.replace('_count','')}: ${count} (${pct.toFixed(1)}%)`}
                />
              ) : null;
            })}
          </div>
        </div>
      )}

      {/* Component table */}
      <div className="risk-table-section">
        <div className="risk-table-header">
          <span className="section-title" style={{ margin: 0 }}>HIGH-RISK COMPONENTS</span>
          <div className="risk-table-controls">
            <div className="risk-search-wrap">
              <input
                className="input risk-search-input"
                type="text"
                placeholder="Search components…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                aria-label="Search components"
              />
              {search && (
                <button
                  className="risk-search-clear"
                  onClick={() => setSearch('')}
                  aria-label="Clear search"
                >✕</button>
              )}
            </div>
            <select
              className="input"
              value={filterRisk}
              onChange={e => setFilterRisk(e.target.value)}
              style={{ maxWidth: 110, height: 30, fontSize: 12 }}
              aria-label="Filter by risk"
            >
              <option value="">All risk</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <span className="text-xs muted">{sorted.length} shown</span>
          </div>
        </div>

        {loading && <div className="loading-container"><div className="spinner"/></div>}

        {!loading && !activeRepo && (
          <div className="empty-container">No repository loaded.</div>
        )}

        {!loading && activeRepo && sorted.length === 0 && (
          <div className="empty-container">No risk data available.</div>
        )}

        {!loading && sorted.length > 0 && (
          <div className="risk-table">
            <div className="risk-table-head">
              <span>Component</span>
              <span>Type</span>
              <span>Language</span>
              <span>Score</span>
              <span>Deps</span>
              <span>Dependents</span>
              <span>Tests</span>
              <span>Risk</span>
            </div>
            {sorted.map(comp => (
              <button
                key={comp.id}
                className="risk-table-row"
                onClick={() => handleSelectComponent(comp)}
                title={`Click to analyze ${comp.path}`}
              >
                <span className="mono text-xs truncate" title={comp.path}>{comp.path}</span>
                <span className="tag">{comp.type}</span>
                <span className="tag">{comp.language}</span>
                <span
                  className="risk-score-cell mono"
                  style={{ color: RISK_COLORS[comp.risk] }}
                >
                  {Math.round(comp.risk_score)}
                </span>
                <span className="muted text-sm">{comp.direct_dependency_count}</span>
                <span className="muted text-sm">{comp.dependent_count}</span>
                <span className={comp.test_count === 0 ? 'text-yellow' : 'text-green'} style={{ fontSize: 12 }}>
                  {comp.test_count === 0 ? '⚠' : `✓ ${comp.test_count}`}
                </span>
                <span className={`badge ${riskClass(comp.risk)}`}>{comp.risk}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RiskSummaryCard({ label, value, color }) {
  return (
    <div className="risk-summary-card card card-sm">
      <div className="risk-summary-value" style={{ color }}>{value ?? 0}</div>
      <div className="risk-summary-label">{label}</div>
    </div>
  );
}
