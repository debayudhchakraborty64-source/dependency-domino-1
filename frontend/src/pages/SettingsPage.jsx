import React, { useEffect, useState } from 'react';
import useStore from '../store/useStore';
import { getHealth, getConfig } from '../services/apiService';
import './SettingsPage.css';

export default function SettingsPage() {
  const { watsonxConfigured, backendStatus } = useStore();
  const [config, setConfig] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    Promise.all([getHealth(), getConfig()]).then(([h, c]) => {
      if (h.data) setHealth(h.data);
      if (c.data) setConfig(c.data);
    });
  }, []);

  return (
    <div className="page-container settings-page">
      <h1 className="settings-title">Settings</h1>

      {/* Backend connection */}
      <section className="settings-section card">
        <div className="section-title">BACKEND CONNECTION</div>
        <div className="settings-row">
          <div className="settings-row-label">API Status</div>
          <div className={`settings-status ${backendStatus === 'ok' ? 'settings-status--ok' : 'settings-status--err'}`}>
            {backendStatus === 'ok' ? '✓ Connected' : '✕ Offline'}
          </div>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">Environment</div>
          <span className="tag">{config?.app_env || '—'}</span>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">Max Upload Size</div>
          <span className="tag">{config?.max_upload_size_mb}MB</span>
        </div>
      </section>

      {/* AI status */}
      <section className="settings-section card">
        <div className="section-title">IBM watsonx.ai</div>
        <div className="settings-row">
          <div className="settings-row-label">Configuration Status</div>
          <div className={`settings-status ${watsonxConfigured ? 'settings-status--ok' : 'settings-status--warn'}`}>
            {watsonxConfigured ? '✓ Configured' : '⚠ Not configured — rule-based mode active'}
          </div>
        </div>
        {watsonxConfigured && config?.watsonx?.url && (
          <div className="settings-row">
            <div className="settings-row-label">Endpoint</div>
            <span className="tag mono text-xs">{config.watsonx.url}</span>
          </div>
        )}
        {watsonxConfigured && config?.watsonx?.model_id && (
          <div className="settings-row">
            <div className="settings-row-label">Model</div>
            <span className="tag mono text-xs">{config.watsonx.model_id}</span>
          </div>
        )}
        <div className="settings-note">
          API keys are stored in backend environment variables and are never exposed to the frontend.
          To configure watsonx.ai, set <code className="code-inline">WATSONX_API_KEY</code>,{' '}
          <code className="code-inline">WATSONX_PROJECT_ID</code>, and{' '}
          <code className="code-inline">WATSONX_URL</code> in the backend <code className="code-inline">.env</code> file.
        </div>
      </section>

      {/* Analysis settings */}
      <section className="settings-section card">
        <div className="section-title">ANALYSIS SETTINGS</div>
        <div className="settings-row">
          <div className="settings-row-label">Max files per repository</div>
          <span className="tag">2,000</span>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">Max file size analyzed</div>
          <span className="tag">500 KB</span>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">Languages supported</div>
          <span className="text-sm muted">JavaScript, JSX, TypeScript, TSX, Python, CSS, HTML, JSON, YAML</span>
        </div>
        <div className="settings-note">
          Dependency analysis is static (no code execution). ZIP path traversal protection is active.
          node_modules, .git, dist, build, __pycache__, and .venv directories are excluded.
        </div>
      </section>

      {/* About */}
      <section className="settings-section card">
        <div className="section-title">ABOUT</div>
        <div className="settings-row">
          <div className="settings-row-label">Application</div>
          <span className="text-sm">Dependency Domino v1.0.0</span>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">Description</div>
          <span className="text-sm muted">Pre-change impact intelligence for developers</span>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">Developed with</div>
          <span className="text-sm">IBM Bob AI assistant</span>
        </div>
        <div className="settings-row">
          <div className="settings-row-label">AI Runtime</div>
          <span className="text-sm">IBM watsonx.ai (when configured)</span>
        </div>
      </section>
    </div>
  );
}
