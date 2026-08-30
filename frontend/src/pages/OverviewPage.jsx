import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { listRepositories, getRepository, getRisks } from '../services/apiService';
import UploadModal from '../components/repository/UploadModal';
import './OverviewPage.css';

const DEMO_REPO_ID = 'demo-developer-portal';

export default function OverviewPage() {
  const navigate = useNavigate();
  const { activeRepo, setActiveRepo, backendStatus, watsonxConfigured, watsonxStatus, watsonxModel, setRepositories } = useStore();
  const [risks, setRisks] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);

  useEffect(() => {
    listRepositories().then(({ data }) => {
      if (data) setRepositories(data);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeRepo) {
      getRisks(activeRepo.id).then(({ data }) => {
        if (data) setRisks(data);
      });
    }
  }, [activeRepo]);

  const openDemo = async () => {
    setLoadingDemo(true);
    const { data } = await getRepository(DEMO_REPO_ID);
    if (data) {
      setActiveRepo(data);
      navigate('/dependency-map');
    }
    setLoadingDemo(false);
  };

  return (
    <div className="page-container overview-page">

      {/* ── Hero ─────────────────────────────────────────────── */}
      <div className="overview-hero fade-in-up">
        <div className="overview-hero-eyebrow">
          <span className="badge badge-ai badge-label">PRE-CHANGE IMPACT INTELLIGENCE</span>
        </div>
        <h1 className="overview-hero-title">
          Know the <span className="hero-gradient-text">blast radius</span><br />
          before you touch the code.
        </h1>
        <p className="overview-hero-sub">
          Dependency Domino analyzes your repository's dependency graph and
          predicts what could break when you change a file — before you commit.
        </p>
        <div className="overview-hero-actions">
          <button className="btn btn-primary btn-lg overview-cta" onClick={() => setShowUpload(true)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Analyze Repository
          </button>
          <button className="btn btn-secondary btn-lg" onClick={openDemo} disabled={loadingDemo}>
            {loadingDemo ? (
              <><span className="spinner" style={{ width: 13, height: 13, borderWidth: 1.5 }} /> Loading…</>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Open Demo Repository
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Status metric cards ───────────────────────────────── */}
      <div className="overview-status-grid">
        <MetricCard
          label="Backend"
          value={backendStatus === 'ok' ? 'Connected' : 'Offline'}
          badgeClass={backendStatus === 'ok' ? 'badge-online' : 'badge-offline'}
          icon={<ServerIcon />}
        />
        <MetricCard
          label="IBM watsonx.ai"
          value={
            watsonxStatus === 'CONFIGURED' ? 'Connected' :
            watsonxStatus === 'NO_MODEL'   ? 'No model set' :
            watsonxConfigured              ? 'Configured' :
                                             'Not configured'
          }
          badgeClass={
            watsonxStatus === 'CONFIGURED' ? 'badge-ai' :
            watsonxStatus === 'NO_MODEL'   ? 'badge-warn' :
                                             'badge-offline'
          }
          icon={<AIIcon />}
          sub={watsonxModel || undefined}
        />
        <MetricCard
          label="Active Repository"
          value={activeRepo ? activeRepo.name : 'None'}
          badgeClass={activeRepo ? 'badge-online' : 'badge-unknown'}
          icon={<RepoIcon />}
          mono={!!activeRepo}
        />
        <MetricCard
          label="Analysis Status"
          value={activeRepo ? activeRepo.status : '—'}
          badgeClass={activeRepo?.status === 'complete' ? 'badge-online' : activeRepo ? 'badge-warn' : 'badge-unknown'}
          icon={<PulseIcon />}
          mono
        />
      </div>

      {/* ── Repository stats ──────────────────────────────────── */}
      {activeRepo && (
        <div className="overview-stats-section">
          <h2 className="section-title">Repository — {activeRepo.name}</h2>
          {activeRepo.is_demo && (
            <div className="demo-banner">
              <span className="badge badge-demo">DEMO REPOSITORY</span>
              <span className="muted text-sm" style={{ marginLeft: 10 }}>
                "Developer Portal" — sample data for hackathon demo
              </span>
            </div>
          )}
          <div className="overview-repo-grid">
            <StatBlock label="Files" value={activeRepo.total_files} />
            <StatBlock label="Directories" value={activeRepo.directories} />
            {activeRepo.languages?.map(l => (
              <StatBlock key={l.language} label={l.language} value={l.count} sub={`${l.percentage}%`} />
            ))}
          </div>
        </div>
      )}

      {/* ── Risk overview ─────────────────────────────────────── */}
      {risks && (
        <div className="overview-stats-section">
          <h2 className="section-title">Codebase Risk Overview</h2>
          <div className="overview-repo-grid">
            <StatBlock label="Total Components" value={risks.total_components} />
            <StatBlock label="Critical Risk" value={risks.critical_count} color="var(--risk-critical)" />
            <StatBlock label="High Risk" value={risks.high_count} color="var(--risk-high)" />
            <StatBlock label="Medium Risk" value={risks.medium_count} color="var(--risk-medium)" />
            <StatBlock label="Low Risk" value={risks.low_count} color="var(--risk-low)" />
            <StatBlock label="Weak Test Coverage" value={risks.weak_test_coverage_count} color="var(--yellow)" />
          </div>
        </div>
      )}

      {/* ── How it works — Timeline grid ─────────────────────── */}
      <div className="overview-how-section">
        <h2 className="section-title">How It Works</h2>
        <div className="overview-steps-grid">
          {STEPS.map((s, i) => (
            <div key={i} className="step-card card">
              <div className="step-card-num">
                <span>{String(i + 1).padStart(2, '0')}</span>
              </div>
              <div className="step-card-icon" aria-hidden="true">{s.icon}</div>
              <div className="step-card-title">{s.title}</div>
              <div className="step-card-desc">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}

// ── Data ────────────────────────────────────────────────────────────────────

const STEPS = [
  {
    title: 'Import Repository',
    desc: 'Upload a ZIP or use the pre-loaded demo repository.',
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
  },
  {
    title: 'Analyze Structure',
    desc: 'The engine parses imports, exports, and dependency relationships.',
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  },
  {
    title: 'Build Dependency Graph',
    desc: 'All relationships are modeled as a directed dependency graph.',
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 12l10-6.5M7 12l10 6.5"/></svg>,
  },
  {
    title: 'Select a Component',
    desc: 'Choose any file or function you plan to modify.',
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>,
  },
  {
    title: 'Analyze Change Impact',
    desc: 'The domino effect shows exactly what could break.',
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
  },
  {
    title: 'Get AI Explanation',
    desc: 'IBM watsonx.ai explains risk and recommends test steps.',
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a9 9 0 110 18A9 9 0 0112 2z"/><path d="M12 6v6l4 2"/></svg>,
  },
];

// ── Sub-components ───────────────────────────────────────────────────────────

function MetricCard({ label, value, badgeClass, icon, mono, sub }) {
  const getBadgeStyle = () => {
    if (badgeClass === 'badge-online') {
      return { 
        background: 'rgba(16, 185, 129, 0.12)', 
        color: 'var(--green)',
        borderRadius: '4px',
        padding: '4px 10px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '12px',
        fontWeight: '600',
        fontFamily: mono ? 'var(--font-mono)' : 'inherit'
      };
    } else if (badgeClass === 'badge-offline') {
      return { 
        background: 'rgba(239, 68, 68, 0.12)', 
        color: 'var(--red)',
        borderRadius: '4px',
        padding: '4px 10px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '12px',
        fontWeight: '600'
      };
    } else if (badgeClass === 'badge-ai') {
      return { 
        background: 'rgba(79, 139, 255, 0.12)', 
        color: 'var(--accent)',
        borderRadius: '4px',
        padding: '4px 10px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '12px',
        fontWeight: '600'
      };
    } else if (badgeClass === 'badge-warn') {
      return { 
        background: 'rgba(245, 158, 11, 0.12)', 
        color: 'var(--yellow)',
        borderRadius: '4px',
        padding: '4px 10px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '12px',
        fontWeight: '600'
      };
    }
    return {};
  };

  return (
    <div className="metric-card card card-sm">
      <div className="metric-card-header">
        <span className="metric-card-icon">{icon}</span>
        <span className="metric-card-label muted text-xs">{label}</span>
      </div>
      <div className="metric-card-body">
        <span className="metric-card-value" style={getBadgeStyle()}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor' }} />
          {value}
        </span>
        {sub && (
          <div className="metric-card-sub muted" style={{ fontSize: 10, marginTop: 4, fontFamily: 'var(--font-mono)' }}>
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}

function StatBlock({ label, value, sub, color }) {
  return (
    <div className="stat-block card card-sm">
      <div className="stat-block-value" style={{ color: color || 'var(--text-primary)' }}>
        {value ?? '—'}
        {sub && <span className="stat-block-sub muted text-sm"> {sub}</span>}
      </div>
      <div className="stat-block-label text-xs muted">{label}</div>
    </div>
  );
}

// ── Inline icons for metric cards ────────────────────────────────────────────

function ServerIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
      <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
      <line x1="6" y1="6" x2="6.01" y2="6"/>
      <line x1="6" y1="18" x2="6.01" y2="18"/>
    </svg>
  );
}

function AIIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a9 9 0 110 18A9 9 0 0112 2z"/>
      <path d="M8 12h8M12 8v8"/>
    </svg>
  );
}

function RepoIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
    </svg>
  );
}

function PulseIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  );
}
