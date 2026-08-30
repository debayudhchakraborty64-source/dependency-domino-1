import React, { useState, useEffect } from 'react';
import useStore from '../../store/useStore';
import {
  getImpact, explainImpact, getTestPlan, simulateChange, generateReport
} from '../../services/apiService';
import './ImpactPanel.css';

const RISK_COLORS = {
  critical: 'var(--risk-critical)', high: 'var(--risk-high)',
  medium: 'var(--risk-medium)', low: 'var(--risk-low)', unknown: 'var(--risk-unknown)',
};

export default function ImpactPanel({ onClose }) {
  const {
    selectedComponent, impact, setImpact,
    explanation, setExplanation,
    testPlan, setTestPlan,
    addNotification, activeRepo,
  } = useStore();

  const [loadingImpact, setLoadingImpact] = useState(false);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [loadingTests, setLoadingTests] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingSim, setLoadingSim] = useState(false);
  const [simDescription, setSimDescription] = useState('');
  const [simResult, setSimResult] = useState(null);
  const [showSim, setShowSim] = useState(false);
  const [activeTab, setActiveTab] = useState('impact'); // impact | explain | tests | simulate | report
  const [report, setReport] = useState(null);

  // Load impact on mount
  useEffect(() => {
    if (selectedComponent && !impact) {
      loadImpact();
    }
  }, [selectedComponent?.id]);

  const loadImpact = async () => {
    if (!selectedComponent) return;
    setLoadingImpact(true);
    const { data, error } = await getImpact(selectedComponent.id);
    if (data) setImpact(data);
    else addNotification(error || 'Failed to load impact.', 'error');
    setLoadingImpact(false);
  };

  const handleExplain = async () => {
    if (!selectedComponent) return;
    setLoadingExplain(true);
    setActiveTab('explain');
    const { data, error } = await explainImpact(selectedComponent.id);
    if (data) setExplanation(data);
    else addNotification(error || 'Failed to get explanation.', 'error');
    setLoadingExplain(false);
  };

  const handleTestPlan = async () => {
    if (!selectedComponent) return;
    setLoadingTests(true);
    setActiveTab('tests');
    const { data, error } = await getTestPlan(selectedComponent.id);
    if (data) setTestPlan(data);
    else addNotification(error || 'Failed to get test plan.', 'error');
    setLoadingTests(false);
  };

  const handleSimulate = async () => {
    if (!selectedComponent || !simDescription.trim()) {
      addNotification('Describe your change first.', 'warning');
      return;
    }
    setLoadingSim(true);
    const { data, error } = await simulateChange(selectedComponent.id, simDescription);
    if (data) setSimResult(data);
    else addNotification(error || 'Simulation failed.', 'error');
    setLoadingSim(false);
  };

  const handleExportReport = async () => {
    if (!selectedComponent || !activeRepo) return;
    setLoadingReport(true);
    const { data, error } = await generateReport(activeRepo.id, selectedComponent.id, true);
    if (data) {
      setReport(data);
      setActiveTab('report');
    } else addNotification(error || 'Report generation failed.', 'error');
    setLoadingReport(false);
  };

  const downloadReport = () => {
    if (!report) return;
    const text = formatReportText(report);
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `impact-report-${report.component_path?.split('/').pop() || 'report'}-${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyReport = () => {
    if (!report) return;
    navigator.clipboard.writeText(formatReportText(report));
    addNotification('Report copied to clipboard.', 'success');
  };

  if (!selectedComponent) return null;

  const riskColor = impact ? RISK_COLORS[impact.risk_level] : 'var(--risk-unknown)';

  return (
    <div className="impact-panel" role="complementary" aria-label="Impact Analysis Panel">
      {/* Header */}
      <div className="impact-panel-header">
        <div>
          <div className="impact-panel-title">IMPACT ANALYSIS</div>
          <div className="impact-panel-file mono" title={selectedComponent.path}>
            {selectedComponent.name || selectedComponent.path}
          </div>
        </div>
        <button className="btn-icon" onClick={onClose} aria-label="Close panel">✕</button>
      </div>

      {/* Score display */}
      {impact && !impact.insufficient_data && (
        <div className="impact-score-block">
          <div className="impact-score-ring">
            <ScoreRing score={impact.impact_score} riskColor={riskColor} />
          </div>
          <div className="impact-score-info">
            <div className="impact-score-value" style={{ color: riskColor }}>
              {impact.impact_score.toFixed(0)}<span className="impact-score-max">/100</span>
            </div>
            <div className={`badge badge-${impact.risk_level}`} style={{ fontSize: 11 }}>
              {impact.risk_level.toUpperCase()} IMPACT
            </div>
          </div>
        </div>
      )}

      {impact?.insufficient_data && (
        <div className="impact-insufficient">
          Insufficient evidence for a reliable risk score.
        </div>
      )}

      {/* Stats row */}
      {impact && (
        <div className="impact-stats-row">
          <StatCell label="DIRECT DEPS" value={impact.direct_dependencies?.length || 0} />
          <StatCell label="INDIRECT DEPS" value={impact.indirect_dependencies?.length || 0} />
          <StatCell label="AFFECTED" value={impact.affected_components?.length || 0} />
          <StatCell label="TESTS" value={impact.related_tests?.length || 0} />
        </div>
      )}

      {/* Action buttons */}
      <div className="impact-actions">
        <button className="btn btn-secondary btn-sm" onClick={handleExplain} disabled={loadingExplain}>
          {loadingExplain ? 'Loading…' : '🧠 Explain Impact'}
        </button>
        <button className="btn btn-secondary btn-sm" onClick={handleTestPlan} disabled={loadingTests}>
          {loadingTests ? 'Loading…' : '🧪 Test Plan'}
        </button>
        <button className="btn btn-secondary btn-sm" onClick={() => { setActiveTab('simulate'); setShowSim(true); }}>
          🎯 Simulate Change
        </button>
        <button className="btn btn-secondary btn-sm" onClick={handleExportReport} disabled={loadingReport}>
          {loadingReport ? 'Loading…' : '📋 Export Report'}
        </button>
      </div>

      {/* Tab navigation */}
      <div className="impact-tabs">
        {['impact', 'explain', 'tests', 'simulate', 'report'].map(tab => (
          <button
            key={tab}
            className={`impact-tab ${activeTab === tab ? 'impact-tab--active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="impact-tab-content">
        {activeTab === 'impact' && <ImpactTab impact={impact} loading={loadingImpact} />}
        {activeTab === 'explain' && <ExplainTab explanation={explanation} loading={loadingExplain} onLoad={handleExplain} />}
        {activeTab === 'tests' && <TestsTab testPlan={testPlan} loading={loadingTests} onLoad={handleTestPlan} />}
        {activeTab === 'simulate' && (
          <SimulateTab
            description={simDescription}
            setDescription={setSimDescription}
            result={simResult}
            loading={loadingSim}
            onSimulate={handleSimulate}
          />
        )}
        {activeTab === 'report' && (
          <ReportTab
            report={report}
            loading={loadingReport}
            onGenerate={handleExportReport}
            onDownload={downloadReport}
            onCopy={copyReport}
          />
        )}
      </div>
    </div>
  );
}

// ─── Sub-tabs ─────────────────────────────────────────────────────────────────

function ImpactTab({ impact, loading }) {
  if (loading) return <div className="loading-container"><div className="spinner"/></div>;
  if (!impact) return <div className="empty-container text-sm">Loading impact analysis…</div>;

  return (
    <div className="impact-tab-body">
      {/* Score explanation */}
      {impact.score_explanation && (
        <div className="impact-why card card-sm">
          <div className="section-title">WHY?</div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            {impact.score_explanation}
          </p>
        </div>
      )}

      {/* Risk factors */}
      {impact.risk_factors?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">RISK FACTORS</div>
          {impact.risk_factors.map((rf, i) => (
            <div key={i} className="risk-factor-item">
              <span className="risk-factor-dot" />
              <span className="text-sm">{rf.description || rf.factor}</span>
            </div>
          ))}
        </div>
      )}

      {/* Affected components */}
      {impact.affected_components?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">AFFECTED COMPONENTS ({impact.affected_components.length})</div>
          <AffectedList ids={impact.affected_components.slice(0, 15)} />
        </div>
      )}

      {/* Related tests */}
      {impact.related_tests?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">RELATED TESTS ({impact.related_tests.length})</div>
          <AffectedList ids={impact.related_tests.slice(0, 10)} color="var(--green)" icon="✓" />
        </div>
      )}

      {impact.related_tests?.length === 0 && (
        <div className="impact-gap-warning">
          ⚠ No detected tests for this component.
        </div>
      )}
    </div>
  );
}

function ExplainTab({ explanation, loading, onLoad }) {
  if (loading) return <div className="loading-container"><div className="spinner"/><span>Getting AI explanation…</span></div>;
  if (!explanation) return (
    <div className="empty-container">
      <p className="muted text-sm">Click "Explain Impact" to get an AI-powered analysis.</p>
      <button className="btn btn-primary btn-sm" onClick={onLoad}>Get Explanation</button>
    </div>
  );

  const isAI = explanation.ai_available && explanation.ai_source === 'watsonx';
  const fallbackReason = explanation.fallback_reason;

  return (
    <div className="impact-tab-body">
      {/* Source badge */}
      {isAI ? (
        <div className="ai-active-notice">
          <span className="badge badge-ai">IBM watsonx.ai</span>
          {explanation.model_used && (
            <span className="text-xs muted"> {explanation.model_used}</span>
          )}
        </div>
      ) : (
        <div className="ai-fallback-notice">
          {fallbackReason
            ? `Rule-based analysis: ${fallbackReason}`
            : 'IBM watsonx.ai is not configured. Showing rule-based analysis.'}
        </div>
      )}

      {explanation.summary && (
        <ExplainSection title="SUMMARY" text={explanation.summary} />
      )}
      {explanation.why_it_matters && (
        <ExplainSection title="WHY IT MATTERS" text={explanation.why_it_matters} />
      )}
      {explanation.potential_impact && (
        <ExplainSection title="POTENTIAL IMPACT" text={explanation.potential_impact} />
      )}
      {explanation.risk_factors?.length > 0 && (
        <BulletSection title="RISK FACTORS" items={explanation.risk_factors} icon="•" />
      )}
      {explanation.recommended_actions?.length > 0 && (
        <BulletSection title="RECOMMENDED ACTIONS" items={explanation.recommended_actions} icon="→" color="var(--accent)" />
      )}
      {explanation.test_recommendations?.length > 0 && (
        <BulletSection title="TEST RECOMMENDATIONS" items={explanation.test_recommendations} icon="✓" color="var(--green)" />
      )}

      {/* Evidence classification — only shown when present */}
      {(explanation.detected_dependencies?.length > 0 || explanation.inferred_relationships?.length > 0) && (
        <div className="impact-section">
          <div className="section-title">EVIDENCE CLASSIFICATION</div>
          {explanation.detected_dependencies?.length > 0 && (
            <div className="evidence-group">
              <span className="evidence-label evidence-label--detected">DETECTED</span>
              <div className="evidence-items">
                {explanation.detected_dependencies.map((d, i) => (
                  <span key={i} className="evidence-item mono text-xs">{d}</span>
                ))}
              </div>
            </div>
          )}
          {explanation.inferred_relationships?.length > 0 && (
            <div className="evidence-group">
              <span className="evidence-label evidence-label--inferred">INFERRED</span>
              <div className="evidence-items">
                {explanation.inferred_relationships.map((d, i) => (
                  <span key={i} className="evidence-item mono text-xs">{d}</span>
                ))}
              </div>
            </div>
          )}
          {explanation.possible_impacts?.length > 0 && (
            <div className="evidence-group">
              <span className="evidence-label evidence-label--possible">POSSIBLE</span>
              <div className="evidence-items">
                {explanation.possible_impacts.map((d, i) => (
                  <span key={i} className="evidence-item text-xs">{d}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Uncertainties */}
      {explanation.uncertainties?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">UNCERTAINTIES</div>
          <div className="uncertainties-box">
            {explanation.uncertainties.map((u, i) => (
              <div key={i} className="uncertainty-item">
                <span className="uncertainty-icon">?</span>
                <span className="text-xs">{u}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TestsTab({ testPlan, loading, onLoad }) {
  if (loading) return <div className="loading-container"><div className="spinner"/><span>Generating test plan…</span></div>;
  if (!testPlan) return (
    <div className="empty-container">
      <p className="muted text-sm">Click "Test Plan" to generate recommendations.</p>
      <button className="btn btn-primary btn-sm" onClick={onLoad}>Generate Test Plan</button>
    </div>
  );

  return (
    <div className="impact-tab-body">
      {testPlan.ai_generated ? (
        <div className="ai-active-notice"><span className="badge badge-ai">AI Generated</span></div>
      ) : (
        <div className="ai-fallback-notice">Rule-based test plan (watsonx.ai not configured)</div>
      )}
      <div className="test-plan-notice text-xs muted">
        ⚠ These are recommendations only — not proof of complete test coverage.
      </div>

      {testPlan.existing_tests?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">EXISTING TESTS ({testPlan.existing_tests.length})</div>
          {testPlan.existing_tests.map((t, i) => (
            <div key={i} className="test-item test-item--exists">
              <span style={{ color: 'var(--green)' }}>✓</span>
              <span className="mono text-xs">{t}</span>
            </div>
          ))}
        </div>
      )}

      {testPlan.recommended_tests?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">RECOMMENDED TESTS</div>
          {testPlan.recommended_tests.map((t, i) => (
            <div key={i} className="test-item">
              <span style={{ color: 'var(--accent)' }}>→</span>
              <span className="text-sm">{t}</span>
            </div>
          ))}
        </div>
      )}

      {testPlan.coverage_gaps?.length > 0 && (
        <div className="impact-section">
          <div className="section-title">COVERAGE GAPS</div>
          {testPlan.coverage_gaps.map((g, i) => (
            <div key={i} className="test-item">
              <span style={{ color: 'var(--yellow)' }}>⚠</span>
              <span className="text-sm">{g}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SimulateTab({ description, setDescription, result, loading, onSimulate }) {
  return (
    <div className="impact-tab-body">
      <div className="impact-section">
        <div className="section-title">DESCRIBE YOUR CHANGE</div>
        <textarea
          className="input"
          placeholder="e.g. Change authentication token validation logic"
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={3}
        />
        <button
          className="btn btn-primary btn-sm"
          onClick={onSimulate}
          disabled={loading || !description.trim()}
          style={{ marginTop: 8 }}
        >
          {loading ? 'Simulating…' : '🎯 Simulate Change'}
        </button>
      </div>

      {result && (
        <>
          <div className="impact-section">
            <div className="section-title">CONSEQUENCE ANALYSIS</div>
            <div className="sim-consequence card card-sm">
              {!result.ai_available && (
                <div className="ai-fallback-notice" style={{ marginBottom: 8 }}>
                  Rule-based analysis (watsonx.ai not configured)
                </div>
              )}
              <p className="text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {result.ai_consequence_summary}
              </p>
            </div>
          </div>

          {result.affected_components?.length > 0 && (
            <div className="impact-section">
              <div className="section-title">AFFECTED COMPONENTS ({result.affected_components.length})</div>
              {result.affected_components.slice(0, 10).map((c, i) => (
                <div key={i} className="test-item">
                  <span style={{ color: 'var(--orange)' }}>⚡</span>
                  <span className="mono text-xs">{c}</span>
                </div>
              ))}
            </div>
          )}

          {result.recommended_tests?.length > 0 && (
            <div className="impact-section">
              <div className="section-title">RUN THESE TESTS</div>
              {result.recommended_tests.slice(0, 8).map((t, i) => (
                <div key={i} className="test-item">
                  <span style={{ color: 'var(--green)' }}>✓</span>
                  <span className="mono text-xs">{t}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ReportTab({ report, loading, onGenerate, onDownload, onCopy }) {
  if (loading) return <div className="loading-container"><div className="spinner"/><span>Generating report…</span></div>;
  if (!report) return (
    <div className="empty-container">
      <p className="muted text-sm">Generate an impact report for this component.</p>
      <button className="btn btn-primary btn-sm" onClick={onGenerate}>Generate Report</button>
    </div>
  );

  return (
    <div className="impact-tab-body">
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button className="btn btn-secondary btn-sm" onClick={onCopy}>📋 Copy</button>
        <button className="btn btn-primary btn-sm" onClick={onDownload}>⬇ Download</button>
      </div>
      <div className="report-preview card card-sm">
        <pre className="report-text mono text-xs">{formatReportText(report)}</pre>
      </div>
    </div>
  );
}

// ─── Helper components ────────────────────────────────────────────────────────

function ScoreRing({ score, riskColor }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (score / 100) * circumference;

  return (
    <svg width="72" height="72" viewBox="0 0 72 72" aria-label={`Impact score: ${score}`}>
      <circle cx="36" cy="36" r={radius} fill="none" stroke="var(--bg-overlay)" strokeWidth="5"/>
      <circle
        cx="36" cy="36" r={radius} fill="none"
        stroke={riskColor} strokeWidth="5"
        strokeDasharray={`${strokeDash} ${circumference}`}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
        style={{ transition: 'stroke-dasharray 600ms ease' }}
      />
    </svg>
  );
}

function StatCell({ label, value }) {
  return (
    <div className="impact-stat-cell">
      <div className="impact-stat-value">{value}</div>
      <div className="impact-stat-label">{label}</div>
    </div>
  );
}

function AffectedList({ ids, color, icon = '→' }) {
  if (!ids || ids.length === 0) {
    return <div className="text-xs muted" style={{ padding: '8px 0' }}>No items</div>;
  }

  return (
    <div className="affected-list">
      {ids.map((id, i) => (
        <div key={id || `item-${i}`} className="affected-item">
          <span style={{ color: color || 'var(--text-muted)' }}>{icon}</span>
          <span className="mono text-xs">{id || '(unknown)'}</span>
        </div>
      ))}
    </div>
  );
}

function ExplainSection({ title, text }) {
  return (
    <div className="impact-section">
      <div className="section-title">{title}</div>
      <p className="text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>{text}</p>
    </div>
  );
}

function BulletSection({ title, items, icon, color }) {
  return (
    <div className="impact-section">
      <div className="section-title">{title}</div>
      {items.map((item, i) => (
        <div key={i} className="bullet-item">
          <span style={{ color: color || 'var(--text-muted)' }}>{icon}</span>
          <span className="text-sm">{item}</span>
        </div>
      ))}
    </div>
  );
}

function formatReportText(report) {
  const lines = [
    '═══════════════════════════════════════════',
    'DEPENDENCY DOMINO — IMPACT REPORT',
    '═══════════════════════════════════════════',
    '',
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
    '─── INDIRECT DEPENDENCIES ─────────────────',
    ...(report.indirect_dependencies?.map(d => `  • ${d}`) || ['  None']),
    '',
    '─── AFFECTED COMPONENTS ───────────────────',
    ...(report.affected_components?.map(d => `  • ${d}`) || ['  None']),
    '',
    '─── RELATED TESTS ─────────────────────────',
    ...(report.related_tests?.map(d => `  ✓ ${d}`) || ['  None detected']),
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
    'Generated by Dependency Domino',
    '═══════════════════════════════════════════',
  ];
  return lines.join('\n');
}
