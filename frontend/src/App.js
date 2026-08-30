import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import CommandPalette from './components/ui/CommandPalette';
import NotificationStack from './components/ui/NotificationStack';
import OverviewPage from './pages/OverviewPage';
import RepositoryPage from './pages/RepositoryPage';
import DependencyMapPage from './pages/DependencyMapPage';
import ImpactPage from './pages/ImpactPage';
import RiskCenterPage from './pages/RiskCenterPage';
import TestImpactPage from './pages/TestImpactPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import useStore from './store/useStore';
import { getHealth } from './services/apiService';

/**
 * AppShell: the inner app that works inside any router context.
 * Exported for use in tests (where MemoryRouter is injected externally).
 */
export function AppShell() {
  const { setBackendStatus, setCommandPaletteOpen, commandPaletteOpen } = useStore();

  // Check backend health on mount and retry periodically
  useEffect(() => {
    let isMounted = true;
    let retryTimeout;

    const checkHealth = async () => {
      try {
        const { data, error } = await getHealth();
        if (!isMounted) return;
        
        if (data && data.status === 'ok') {
          setBackendStatus('ok', data.watsonx_configured, data.watsonx_status, data.model_configured ? data.watsonx_model_id : null);
          // Success - don't retry
        } else {
          setBackendStatus('error', false);
          // Retry in 3 seconds
          retryTimeout = setTimeout(checkHealth, 3000);
        }
      } catch (err) {
        if (!isMounted) return;
        setBackendStatus('error', false);
        // Retry in 3 seconds
        retryTimeout = setTimeout(checkHealth, 3000);
      }
    };

    checkHealth();

    return () => {
      isMounted = false;
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [setBackendStatus]);

  // Global keyboard shortcut: Cmd/Ctrl+K for command palette
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-content">
        <Header />
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/repository" element={<RepositoryPage />} />
          <Route path="/dependency-map" element={<DependencyMapPage />} />
          <Route path="/impact" element={<ImpactPage />} />
          <Route path="/risk-center" element={<RiskCenterPage />} />
          <Route path="/test-impact" element={<TestImpactPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </div>
      {commandPaletteOpen && <CommandPalette />}
      <NotificationStack />
    </div>
  );
}

/** Default export: wraps AppShell in BrowserRouter for production. */
export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
