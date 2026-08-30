import React, { useEffect, useState } from 'react';
import useStore from '../store/useStore';
import { getComponents, getImpact, getTestPlan, listRepositories } from '../services/apiService';
import './TestImpactPage.css';

export default function TestImpactPage() {
  const { activeRepo, setActiveRepo, setSelectedComponent, setImpact, addNotification } = useStore();
  const [tests, setTests] = useState([]);
  const [nonTests, setNonTests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTest, setSelectedTest] = useState(null);
  const [testPlan, setTestPlan] = useState(null);
  const [loadingPlan, setLoadingPlan] = useState(false);

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
    getComponents(activeRepo.id, { per_page: 200 }).then(({ data }) => {
      if (data) {
        setTests(data.components.filter(c => c.metadata?.is_test));
        setNonTests(data.components.filter(c => !c.metadata?.is_test));
      }
      setLoading(false);
    });
  }, [activeRepo]);

  const selectTest = async (comp) => {
    setSelectedTest(comp);
    setTestPlan(null);
    setLoadingPlan(true);
    const { data: impact } = await getImpact(comp.id);
    const { data: plan, error } = await getTestPlan(comp.id);
    if (plan) setTestPlan(plan);
    else addNotification(error || 'Failed to load test plan', 'error');
    setLoadingPlan(false);
  };

  const uncoveredComponents = nonTests.filter(c => c.test_count === 0);

  return (
    <div className="test-page">
      {/* Left panel */}
      <div className="test-sidebar">
        <div className="test-sidebar-header">
          <div className="section-title" style={{ margin: 0 }}>TEST FILES</div>
          <span className="text-xs muted">{tests.length} found</span>
        </div>
        <div className="test-list">
          {loading && <div className="loading-container"><div className="spinner"/></div>}
          {!loading && tests.length === 0 && (
            <div className="empty-container text-sm">No test files detected.</div>
          )}
          {tests.map(t => (
            <button
              key={t.id}
              className={`test-list-item ${selectedTest?.id === t.id ? 'test-list-item--active' : ''}`}
              onClick={() => selectTest(t)}
            >
              <span style={{ color: 'var(--green)' }}>✓</span>
              <div>
                <div className="text-sm" style={{ fontWeight: 500 }}>{t.name}</div>
                <div className="mono text-xs muted">{t.path}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Coverage gap indicator */}
        <div className="test-gap-section">
          <div className="section-title">COVERAGE GAPS</div>
          <div className="test-gap-count">
            <span style={{ color: 'var(--yellow)', fontSize: 20, fontWeight: 700 }}>
              {uncoveredComponents.length}
            </span>
            <span className="text-xs muted"> components with no detected tests</span>
          </div>
          <div className="test-gap-list">
            {uncoveredComponents.slice(0, 8).map(c => (
              <div key={c.id} className="test-gap-item">
                <span style={{ color: 'var(--yellow)' }}>⚠</span>
                <span className="mono text-xs muted truncate">{c.path}</span>
              </div>
            ))}
            {uncoveredComponents.length > 8 && (
              <div className="text-xs muted" style={{ padding: '4px 0' }}>
                +{uncoveredComponents.length - 8} more
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="test-main">
        {!selectedTest ? (
          <div className="empty-container" style={{ height: '100%' }}>
            <div style={{ fontSize: 32 }}>🧪</div>
            <h3 style={{ color: 'var(--text-secondary)' }}>Select a Test File</h3>
            <p className="muted text-sm">View test plans and coverage gaps.</p>
          </div>
        ) : (
          <div className="test-detail page-container" style={{ maxHeight: '100%', overflowY: 'auto' }}>
            <div className="test-detail-header">
              <h2 style={{ fontSize: 18, fontWeight: 600 }}>{selectedTest.name}</h2>
              <span className="mono text-xs muted">{selectedTest.path}</span>
            </div>

            {loadingPlan && <div className="loading-container"><div className="spinner"/></div>}

            {testPlan && (
              <>
                <div className="test-plan-disclaimer">
                  ⚠ This is a recommendation only — not proof of complete coverage.
                </div>

                {testPlan.existing_tests?.length > 0 && (
                  <div className="test-section">
                    <div className="section-title">DETECTED TESTS IN FILE</div>
                    {testPlan.existing_tests.map((t, i) => (
                      <div key={i} className="test-item-row">
                        <span style={{ color: 'var(--green)' }}>✓</span>
                        <span className="mono text-xs">{t}</span>
                      </div>
                    ))}
                  </div>
                )}

                {testPlan.recommended_tests?.length > 0 && (
                  <div className="test-section">
                    <div className="section-title">RECOMMENDED TESTS</div>
                    {testPlan.recommended_tests.map((t, i) => (
                      <div key={i} className="test-item-row">
                        <span style={{ color: 'var(--accent)' }}>→</span>
                        <span className="text-sm">{t}</span>
                      </div>
                    ))}
                  </div>
                )}

                {testPlan.coverage_gaps?.length > 0 && (
                  <div className="test-section">
                    <div className="section-title">COVERAGE GAPS</div>
                    {testPlan.coverage_gaps.map((g, i) => (
                      <div key={i} className="test-item-row">
                        <span style={{ color: 'var(--yellow)' }}>⚠</span>
                        <span className="text-sm">{g}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
