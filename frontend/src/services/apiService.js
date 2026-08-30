/**
 * Dependency Domino - API Service
 * Centralized axios-based API client for all backend calls.
 * All errors are normalized into user-friendly messages.
 */
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// Normalize error messages
function normalizeError(err) {
  if (err.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(d => d.msg).join('; ');
    return `Server error (${err.response.status})`;
  }
  if (err.request) return 'Network error — check that the backend is running.';
  return err.message || 'Unknown error';
}

// ─── Repository ───────────────────────────────────────────────────────────────

export async function uploadRepository(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const resp = await api.post('/api/repositories/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => {
        if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total));
      },
    });
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function listRepositories() {
  try {
    const resp = await api.get('/api/repositories');
    return { data: resp.data.repositories, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function getRepository(repoId) {
  try {
    const resp = await api.get(`/api/repositories/${repoId}`);
    return { data: resp.data.repository, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function analyzeRepository(repoId) {
  try {
    const resp = await api.post(`/api/repositories/${repoId}/analyze`);
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function getDependencyGraph(repoId) {
  try {
    const resp = await api.get(`/api/repositories/${repoId}/graph`);
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function getComponents(repoId, params = {}) {
  try {
    const resp = await api.get(`/api/repositories/${repoId}/components`, { params });
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function getRisks(repoId) {
  try {
    const resp = await api.get(`/api/repositories/${repoId}/risks`);
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

// ─── Components ───────────────────────────────────────────────────────────────

export async function getComponent(componentId) {
  try {
    const resp = await api.get(`/api/components/${componentId}`);
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function getImpact(componentId) {
  try {
    const resp = await api.post(`/api/components/${componentId}/impact`);
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function explainImpact(componentId, changeDescription = null) {
  try {
    const resp = await api.post(`/api/components/${componentId}/explain`, {
      component_id: componentId,
      change_description: changeDescription,
    });
    return { data: resp.data, error: null };
  } catch (err) {
    const error = normalizeError(err);
    // Return fallback explanation on 404
    if (err.response?.status === 404) {
      return { 
        data: {
          summary: 'Component not found in repository.',
          ai_available: false,
          ai_generated: false,
        }, 
        error: null 
      };
    }
    return { data: null, error };
  }
}

export async function getTestPlan(componentId, changeDescription = null) {
  try {
    const resp = await api.post(`/api/components/${componentId}/test-plan`, {
      component_id: componentId,
      change_description: changeDescription,
    });
    return { data: resp.data, error: null };
  } catch (err) {
    const error = normalizeError(err);
    // Return fallback test plan on 404
    if (err.response?.status === 404) {
      return { 
        data: {
          existing_tests: [],
          recommended_tests: ['Upload repository to see test recommendations'],
          ai_generated: false,
        }, 
        error: null 
      };
    }
    return { data: null, error };
  }
}

export async function simulateChange(componentId, changeDescription) {
  try {
    const resp = await api.post(`/api/components/${componentId}/simulate`, {
      component_id: componentId,
      change_description: changeDescription,
    });
    return { data: resp.data, error: null };
  } catch (err) {
    const error = normalizeError(err);
    // Return fallback simulation on 404
    if (err.response?.status === 404) {
      return { 
        data: {
          original_impact_score: 0,
          simulated_impact_score: 0,
          change_in_impact: 0,
          potential_risks: ['Component not found'],
          recommendations: ['Upload repository to test simulations'],
        }, 
        error: null 
      };
    }
    return { data: null, error };
  }
}

// ─── Search ───────────────────────────────────────────────────────────────────

export async function search(query, repoId = null) {
  try {
    const params = { q: query };
    if (repoId) params.repo_id = repoId;
    const resp = await api.get('/api/search', { params });
    return { data: resp.data.results, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export async function generateReport(repositoryId, componentId, includeAI = true) {
  try {
    const resp = await api.post('/api/reports', {
      repository_id: repositoryId,
      component_id: componentId,
      include_ai: includeAI,
    });
    return { data: resp.data, error: null };
  } catch (err) {
    const error = normalizeError(err);
    // Return fallback report on 404
    if (err.response?.status === 404) {
      return { 
        data: {
          component_path: 'unknown',
          repository_name: 'unknown',
          impact_score: 0,
          risk_level: 'unknown',
          generated_at: new Date().toISOString(),
        }, 
        error: null 
      };
    }
    return { data: null, error };
  }
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function getHealth() {
  try {
    const resp = await api.get('/api/health');
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export async function getConfig() {
  try {
    const resp = await api.get('/api/config');
    return { data: resp.data, error: null };
  } catch (err) {
    return { data: null, error: normalizeError(err) };
  }
}

export default api;
