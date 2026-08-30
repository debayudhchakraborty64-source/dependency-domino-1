import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import useStore from '../store/useStore';

// ─── Mock the API service ─────────────────────────────────────────────────────
jest.mock('../services/apiService', () => ({
  getHealth: jest.fn().mockResolvedValue({ data: { status: 'ok', watsonx_configured: false }, error: null }),
  getConfig: jest.fn().mockResolvedValue({ data: { app_env: 'test', max_upload_size_mb: 50 }, error: null }),
  listRepositories: jest.fn().mockResolvedValue({
    data: [{
      id: 'demo-developer-portal',
      name: 'Developer Portal',
      source: 'demo',
      total_files: 42,
      languages: [{ language: 'javascript', count: 20, percentage: 48 }],
      directories: 8,
      status: 'complete',
      is_demo: true,
      created_at: new Date().toISOString(),
    }],
    error: null
  }),
  getRepository: jest.fn().mockResolvedValue({
    data: {
      id: 'demo-developer-portal',
      name: 'Developer Portal',
      is_demo: true,
      status: 'complete',
      total_files: 42,
    },
    error: null
  }),
  getComponents: jest.fn().mockResolvedValue({
    data: {
      components: [
        {
          id: 'comp-auth', name: 'authService.js', path: 'frontend/src/services/authService.js',
          language: 'javascript', type: 'service', risk: 'high', risk_score: 72,
          direct_dependency_count: 3, dependent_count: 5, test_count: 2,
          metadata: { lines: 134, functions: ['login', 'logout'], imports: [], exports: [], is_test: false },
        },
        {
          id: 'comp-login', name: 'Login.jsx', path: 'frontend/src/components/pages/Login.jsx',
          language: 'jsx', type: 'file', risk: 'medium', risk_score: 45,
          direct_dependency_count: 2, dependent_count: 1, test_count: 1,
          metadata: { lines: 112, functions: ['Login'], imports: [], exports: [], is_test: false },
        },
        {
          id: 'comp-test', name: 'auth.test.js', path: 'tests/frontend/auth.test.js',
          language: 'javascript', type: 'test', risk: 'low', risk_score: 10,
          direct_dependency_count: 1, dependent_count: 0, test_count: 0,
          metadata: { lines: 88, functions: ['describe', 'it'], imports: [], exports: [], is_test: true },
        },
      ],
      total: 3,
      page: 1,
      per_page: 100,
    },
    error: null
  }),
  getRisks: jest.fn().mockResolvedValue({
    data: {
      repository_id: 'demo-developer-portal',
      total_components: 35,
      critical_count: 2, high_count: 8, medium_count: 12, low_count: 13, unknown_count: 0,
      weak_test_coverage_count: 10,
      top_risk_components: [],
    },
    error: null
  }),
  getDependencyGraph: jest.fn().mockResolvedValue({
    data: { nodes: [], edges: [], node_count: 0, edge_count: 0 },
    error: null
  }),
  getImpact: jest.fn().mockResolvedValue({
    data: {
      component_id: 'comp-auth',
      component_path: 'frontend/src/services/authService.js',
      impact_score: 72,
      risk_level: 'high',
      direct_dependencies: ['comp-api'],
      indirect_dependencies: [],
      dependents: ['comp-login', 'comp-context'],
      affected_components: ['comp-login', 'comp-context'],
      related_tests: ['comp-test'],
      risk_factors: [{ factor: 'High dependent count', weight: 20, description: '5 components depend on this file' }],
      score_explanation: 'Impact score 72/100',
      insufficient_data: false,
    },
    error: null
  }),
  explainImpact: jest.fn().mockResolvedValue({
    data: {
      component_id: 'comp-auth',
      summary: 'authService.js has a HIGH impact score of 72/100.',
      why_it_matters: 'This service handles authentication for the entire application.',
      potential_impact: 'Multiple components could be affected.',
      risk_factors: ['High dependent count'],
      recommended_actions: ['Run authentication tests'],
      test_recommendations: ['auth.test.js'],
      ai_available: false,
      model_used: 'rule-based',
    },
    error: null
  }),
  getTestPlan: jest.fn().mockResolvedValue({
    data: {
      component_id: 'comp-auth',
      existing_tests: ['tests/frontend/auth.test.js'],
      recommended_tests: ['Run unit tests for authService.js'],
      coverage_gaps: [],
      ai_generated: false,
    },
    error: null
  }),
  generateReport: jest.fn().mockResolvedValue({
    data: {
      id: 'report-1',
      repository_id: 'demo-developer-portal',
      repository_name: 'Developer Portal',
      component_id: 'comp-auth',
      component_path: 'frontend/src/services/authService.js',
      impact_score: 72,
      risk_level: 'high',
      direct_dependencies: ['frontend/src/services/apiService.js'],
      indirect_dependencies: [],
      affected_components: ['frontend/src/components/pages/Login.jsx'],
      related_tests: ['tests/frontend/auth.test.js'],
      risk_factors: ['5 components depend on this file'],
      ai_explanation: { summary: 'High impact', ai_available: false },
      recommended_actions: ['Run all auth tests'],
      generated_at: new Date().toISOString(),
    },
    error: null
  }),
  simulateChange: jest.fn().mockResolvedValue({
    data: {
      component_id: 'comp-auth',
      change_description: 'Change token validation',
      affected_components: ['frontend/src/components/pages/Login.jsx'],
      risk_level: 'high',
      risk_factors: ['High dependent count'],
      recommended_tests: ['auth.test.js'],
      ai_consequence_summary: 'Changing token validation could affect Login and Profile components.',
      ai_available: false,
    },
    error: null
  }),
  search: jest.fn().mockResolvedValue({
    data: [
      { id: 'comp-auth', name: 'authService.js', path: 'frontend/src/services/authService.js', type: 'service', language: 'javascript', risk_score: 72, snippet: '' },
    ],
    error: null
  }),
  uploadRepository: jest.fn().mockResolvedValue({ data: null, error: 'Mock upload' }),
}));

// ─── Import components after mocking ─────────────────────────────────────────
import { AppShell } from '../App';
import OverviewPage from '../pages/OverviewPage';
import RepositoryPage from '../pages/RepositoryPage';
import RiskCenterPage from '../pages/RiskCenterPage';
import SettingsPage from '../pages/SettingsPage';
import ImpactPage from '../pages/ImpactPage';

// ─── Helpers ──────────────────────────────────────────────────────────────────
function renderWithRouter(component, route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {component}
    </MemoryRouter>
  );
}

// AppShell already expects to be inside a Router — MemoryRouter provides it
function renderApp(route = '/overview') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppShell />
    </MemoryRouter>
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('App', () => {
  test('renders without crashing', async () => {
    const { container } = renderApp('/overview');
    await waitFor(() => {
      expect(container.querySelector('.app-layout')).toBeInTheDocument();
    });
  });

  test('shows sidebar navigation', async () => {
    renderApp('/overview');
    await waitFor(() => {
      expect(screen.getByText('Dependency')).toBeInTheDocument();
    });
  });

  test('sidebar has all nav items', async () => {
    renderApp('/overview');
    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument();
      expect(screen.getByText('Repository')).toBeInTheDocument();
      expect(screen.getByText('Dependency Map')).toBeInTheDocument();
      expect(screen.getByText('Risk Center')).toBeInTheDocument();
    });
  });
});

describe('OverviewPage', () => {
  beforeEach(() => {
    useStore.setState({ activeRepo: null, backendStatus: 'ok', watsonxConfigured: false });
  });

  test('renders hero text', async () => {
    renderWithRouter(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/Know the blast radius/)).toBeInTheDocument();
    });
  });

  test('renders analyze repository button', async () => {
    renderWithRouter(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText('Analyze Repository')).toBeInTheDocument();
    });
  });

  test('shows backend status', async () => {
    useStore.setState({ backendStatus: 'ok' });
    renderWithRouter(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/Connected/)).toBeInTheDocument();
    });
  });

  test('shows watsonx not configured warning', async () => {
    useStore.setState({ watsonxConfigured: false });
    renderWithRouter(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/Rule-based mode/)).toBeInTheDocument();
    });
  });

  test('shows demo repo stats when loaded', async () => {
    useStore.setState({
      activeRepo: { id: 'demo', name: 'Developer Portal', is_demo: true, total_files: 42, languages: [], directories: 5, status: 'complete' }
    });
    renderWithRouter(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText('Developer Portal')).toBeInTheDocument();
    });
  });
});

describe('RepositoryPage', () => {
  beforeEach(() => {
    useStore.setState({
      activeRepo: {
        id: 'demo-developer-portal', name: 'Developer Portal', is_demo: true,
        status: 'complete', total_files: 42,
      }
    });
  });

  test('renders component table', async () => {
    renderWithRouter(<RepositoryPage />);
    await waitFor(() => {
      expect(screen.getByText('authService.js')).toBeInTheDocument();
    });
  });

  test('shows language filter', async () => {
    renderWithRouter(<RepositoryPage />);
    await waitFor(() => {
      expect(screen.getByText('All languages')).toBeInTheDocument();
    });
  });

  test('renders file search input', async () => {
    renderWithRouter(<RepositoryPage />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Filter files…')).toBeInTheDocument();
    });
  });
});

describe('RiskCenterPage', () => {
  beforeEach(() => {
    useStore.setState({
      activeRepo: { id: 'demo-developer-portal', name: 'Developer Portal' }
    });
  });

  test('renders risk center title', async () => {
    renderWithRouter(<RiskCenterPage />);
    await waitFor(() => {
      expect(screen.getByText('Codebase Risk Center')).toBeInTheDocument();
    });
  });

  test('shows risk summary cards', async () => {
    renderWithRouter(<RiskCenterPage />);
    await waitFor(() => {
      expect(screen.getByText('Total Components')).toBeInTheDocument();
      expect(screen.getByText('Critical')).toBeInTheDocument();
    });
  });
});

describe('SettingsPage', () => {
  test('renders settings page', async () => {
    renderWithRouter(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });
  });

  test('shows API status section', async () => {
    renderWithRouter(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('BACKEND CONNECTION')).toBeInTheDocument();
    });
  });

  test('shows watsonx.ai section', async () => {
    renderWithRouter(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('IBM watsonx.ai')).toBeInTheDocument();
    });
  });

  test('does not expose API keys', async () => {
    renderWithRouter(<SettingsPage />);
    await waitFor(() => {
      const content = document.body.innerHTML;
      // Should not contain any token or key-like strings
      expect(content).not.toMatch(/eyJ[A-Za-z0-9._-]{20}/); // JWT pattern
      expect(content).not.toMatch(/[a-z0-9]{40}/i);          // API key pattern
    });
  });
});

describe('ImpactPage', () => {
  beforeEach(() => {
    useStore.setState({
      activeRepo: { id: 'demo-developer-portal', name: 'Developer Portal' },
      selectedComponent: null,
      impact: null,
    });
  });

  test('renders component selector', async () => {
    renderWithRouter(<ImpactPage />);
    await waitFor(() => {
      expect(screen.getByText('SELECT COMPONENT')).toBeInTheDocument();
    });
  });

  test('shows empty state when no component selected', async () => {
    renderWithRouter(<ImpactPage />);
    await waitFor(() => {
      expect(screen.getByText('Select a Component')).toBeInTheDocument();
    });
  });

  test('shows components list', async () => {
    renderWithRouter(<ImpactPage />);
    await waitFor(() => {
      expect(screen.getByText('authService.js')).toBeInTheDocument();
      expect(screen.getByText('Login.jsx')).toBeInTheDocument();
    });
  });
});

describe('Search', () => {
  test('renders search input in header', async () => {
    renderApp('/overview');
    await waitFor(() => {
      const inputs = screen.getAllByPlaceholderText(/Search/i);
      expect(inputs.length).toBeGreaterThan(0);
    });
  });
});

describe('CommandPalette', () => {
  test('command palette opens with keyboard shortcut', async () => {
    renderApp('/overview');
    await waitFor(() => {
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
    });
    await waitFor(() => {
      expect(screen.getByText('Open Repository')).toBeInTheDocument();
    });
  });

  test('command palette closes with Escape', async () => {
    renderApp('/overview');
    await waitFor(() => {
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
    });
    await waitFor(() => {
      expect(screen.getByText('Open Dependency Map')).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByText('Open Dependency Map')).not.toBeInTheDocument();
    });
  });
});
