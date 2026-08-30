/**
 * Dependency Domino - Global State Store (Zustand)
 * Manages: active repository, selected component, impact data, UI state
 */
import { create } from 'zustand';

const useStore = create((set, get) => ({
  // ── Repository ─────────────────────────────────────────────────────────────
  activeRepo: null,
  repositories: [],
  setActiveRepo: (repo) => set({ activeRepo: repo }),
  setRepositories: (repos) => set({ repositories: repos }),

  // ── Selected component ─────────────────────────────────────────────────────
  selectedComponent: null,
  setSelectedComponent: (comp) => set({ selectedComponent: comp }),

  // ── Impact analysis ────────────────────────────────────────────────────────
  impact: null,
  setImpact: (impact) => set({ impact }),
  clearImpact: () => set({ impact: null }),

  // ── AI Explanation ─────────────────────────────────────────────────────────
  explanation: null,
  setExplanation: (exp) => set({ explanation: exp }),

  // ── Test plan ──────────────────────────────────────────────────────────────
  testPlan: null,
  setTestPlan: (plan) => set({ testPlan: plan }),

  // ── Graph ──────────────────────────────────────────────────────────────────
  graph: null,
  setGraph: (g) => set({ graph: g }),

  // ── Domino animation state ─────────────────────────────────────────────────
  dominoActive: false,
  dominoPhase: 0,   // 0=idle, 1=selected, 2=direct, 3=indirect, 4=tests, 5=complete
  startDomino: () => set({ dominoActive: true, dominoPhase: 1 }),
  advanceDomino: () => set(s => ({ dominoPhase: Math.min(s.dominoPhase + 1, 5) })),
  resetDomino: () => set({ dominoActive: false, dominoPhase: 0 }),

  // ── Backend health ─────────────────────────────────────────────────────────
  backendStatus: 'unknown', // 'ok' | 'error' | 'unknown'
  watsonxConfigured: false,
  watsonxStatus: 'unknown', // 'connected' | 'not_configured' | 'unavailable' | 'unknown'
  watsonxModel: null,
  setBackendStatus: (status, watsonx, wxStatus, wxModel) => set({
    backendStatus: status,
    watsonxConfigured: !!watsonx,
    watsonxStatus: wxStatus || (watsonx ? 'connected' : 'not_configured'),
    watsonxModel: wxModel || null,
  }),

  // ── UI: active nav page ────────────────────────────────────────────────────
  activePage: 'overview',
  setActivePage: (page) => set({ activePage: page }),

  // ── Command palette ────────────────────────────────────────────────────────
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  // ── Search ──────────────────────────────────────────────────────────────────
  searchQuery: '',
  setSearchQuery: (q) => set({ searchQuery: q }),

  // ── Notifications ──────────────────────────────────────────────────────────
  notifications: [],
  addNotification: (msg, type = 'info') =>
    set(s => ({
      notifications: [...s.notifications, { id: Date.now(), msg, type }].slice(-5),
    })),
  removeNotification: (id) =>
    set(s => ({ notifications: s.notifications.filter(n => n.id !== id) })),
}));

export default useStore;
