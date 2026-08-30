import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { generateReport } from '../services/apiService';
import './ReportsPage.css';

function formatReportText(report) {
  const lines = [
    '═══════════════════════════════════════════',
    'DEPENDENCY DOMINO — IMPACT REPORT',
    '═══════════════════════════════════════════',
    `Repository:    ${report.repository_name}`,
    `Component:     ${report.component_path}`,
    `Generated:     ${new Date(report.generated_at).toLocaleString()}`,
    '',
    `Impact Score:  ${report.impact_score}/100`,
    `Risk Level:    ${report.risk_level?.toUpperCase()}`,
    '',
    '─── DIRECT DEPENDENCIES ───────────────────',
    ...(report.direct_dependencies?.map(d => `  • ${d}`) || ['  None']),
    '',
    '─── AFFECTED COMPONENTS ───────────────────',
    ...(report.affected_components?.map(d => `  • ${d}`) || ['  None']),
    '',
    '─── RELATED TESTS ─────────────────────────',
    ...(report.related_tests?.map(d => `  ✓ ${d}`) || ['  None']),
    '',
    '─── RISK FACTORS ──────────────────────────',
    ...(report.risk_factors?.map(d => `  • ${d}`) || ['  None']),
    '',
    '─── AI EXPLANATION ────────────────────────',
    report.ai_explanation?.summary || 'Not available',
    '',
    '─── RECOMMENDED ACTIONS ───────────────────',
    ...(report.recommended_actions?.map(d => `  → ${d}`) || ['  None']),
    '',
    '═══════════════════════════════════════════',
  ];
  return lines.join('\n');
}

export default function ReportsPage() {
  const navigate = useNavigate();
  const { activeRepo, selectedComponent, impact, addNotification } = useStore();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!activeRepo || !selectedComponent) {
      addNotification('Select a repository and component first.', 'warning');
      navigate('/impact');
      return;
    }
    setLoading(true);
    const { data, error } = await generateReport(activeRepo.id, selectedComponent.id, true);
    if (data) setReport(data);
    else addNotification(error || 'Report generation failed.', 'error');
    setLoading(false);
  };

  const downloadReport = () => {
    if (!report) return;
    const text = formatReportText(report);
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `impact-report-${report.component_path?.split('/').pop()}-${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyReport = () => {
    if (!report) return;
    navigator.clipboard.writeText(formatReportText(report));
    addNotification('Report copied to clipboard!', 'success');
  };

  const riskClass = r => ({ critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[r] || 'badge-unknown');

  return (
    <div className="page-container reports-page">
      <div className="reports-header">
        <h1 className="reports-title">Impact Reports</h1>
        {selectedComponent && (
          <span className="muted text-sm mono">{selectedComponent.path}</span>
        )}
      </div>

      {!selectedComponent && (
        <div className="reports-empty card">
          <div style={{ fontSize: 28, marginBottom: 8 }}>📋</div>
          <p className="muted text-sm" style={{ marginBottom: 12 }}>
            Select a component in Impact Analysis first, then generate a report here.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/impact')}>
            Go to Impact Analysis
          </button>
        </div>
      )}

      {selectedComponent && (
        <div className="reports-actions">
          <button className="btn btn-primary btn-lg" onClick={handleGenerate} disabled={loading}>
            {loading ? 'Generating…' : '📋 Generate Report'}
          </button>
          {report && (
            <>
              <button className="btn btn-secondary" onClick={copyReport}>📋 Copy</button>
              <button className="btn btn-secondary" onClick={downloadReport}>⬇ Download</button>
            </>
          )}
        </div>
      )}

      {report && (
        <div className="report-view">
          {/* Header card */}
          <div className="report-header-card card">
            <div className="report-meta-grid">
              <ReportMeta label="Repository" value={report.repository_name} />
              <ReportMeta label="Component" value={report.component_path} mono />
              <ReportMeta label="Generated" value={new Date(report.generated_at).toLocaleString()} />
              <ReportMeta label="Impact Score" value={`${report.impact_score}/100`} />
              <div>
                <div className="report-meta-label">Risk Level</div>
                <span className={`badge ${riskClass(report.risk_level)}`} style={{ fontSize: 12 }}>
                  {report.risk_level?.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          {/* Sections */}
          <div className="report-sections">
            <ReportSection title="Direct Dependencies" items={report.direct_dependencies} icon="•" />
            <ReportSection title="Affected Components" items={report.affected_components} icon="⚡" />
            <ReportSection title="Related Tests" items={report.related_tests} icon="✓" color="var(--green)" />
            <ReportSection title="Risk Factors" items={report.risk_factors} icon="⚠" color="var(--yellow)" />

            {report.ai_explanation?.summary && (
              <div className="report-ai-section card">
                <div className="section-title">
                  AI EXPLANATION
                  {report.ai_explanation.ai_available && (
                    <span className="badge badge-ai" style={{ marginLeft: 8 }}>IBM watsonx.ai</span>
                  )}
                  {!report.ai_explanation.ai_available && (
                    <span className="text-xs muted" style={{ marginLeft: 8 }}>rule-based</span>
                  )}
                </div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                  {report.ai_explanation.summary}
                </p>
                {report.ai_explanation.potential_impact && (
                  <p className="text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginTop: 8 }}>
                    {report.ai_explanation.potential_impact}
                  </p>
                )}
              </div>
            )}

            <ReportSection title="Recommended Actions" items={report.recommended_actions} icon="→" color="var(--accent)" />
          </div>
        </div>
      )}
    </div>
  );
}

function ReportMeta({ label, value, mono }) {
  return (
    <div>
      <div className="report-meta-label">{label}</div>
      <div className={`report-meta-value ${mono ? 'mono' : ''}`}>{value}</div>
    </div>
  );
}

function ReportSection({ title, items, icon, color }) {
  if (!items?.length) return null;
  return (
    <div className="report-section card">
      <div className="section-title">{title} ({items.length})</div>
      <div className="report-section-items">
        {items.map((item, i) => (
          <div key={i} className="report-section-item">
            <span style={{ color: color || 'var(--text-muted)' }}>{icon}</span>
            <span className="text-sm mono">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
