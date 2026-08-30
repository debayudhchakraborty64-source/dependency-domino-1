import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState, useReactFlow,
  ReactFlowProvider,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import useStore from '../store/useStore';
import { getDependencyGraph, getImpact, listRepositories } from '../services/apiService';
import ImpactPanel from '../components/impact/ImpactPanel';
import './DependencyMapPage.css';

// ─── Color maps ───────────────────────────────────────────────────────────────
const RISK_COLORS = {
  critical: '#f85149', high: '#f0883e', medium: '#e3b341', low: '#3fb950', unknown: '#525969',
};
const LANG_COLORS = {
  javascript: '#f1e05a', jsx: '#61dafb', typescript: '#3178c6',
  tsx: '#3178c6', python: '#3572A5', css: '#563d7c', other: '#8b93a4',
};
const NODE_TYPE_COLORS = {
  file: '#4f81ff', function: '#29bfff', test: '#3fb950',
  service: '#9b6dff', api: '#f0883e', module: '#8b93a4',
};

// ─── Custom node component ────────────────────────────────────────────────────
function DominoNode({ data }) {
  const { label, language, type, risk, score, phase, isSelected, isDirect, isIndirect, isTest, isHighlighted, isDimmed } = data;

  let borderColor = NODE_TYPE_COLORS[type] || '#4f81ff';
  let bg = '#1a1e26';
  let opacity = isDimmed ? 0.2 : 1;
  let glowColor = 'none';
  let scale = 1;

  if (isHighlighted) {
    borderColor = '#06B6D4';
    bg = '#0d1e22';
    glowColor = '0 0 14px 3px rgba(6,182,212,0.45)';
    scale = 1.08;
  } else if (isSelected) {
    borderColor = '#fff';
    bg = '#252a38';
    glowColor = '0 0 12px 3px rgba(79,129,255,0.5)';
    scale = 1.1;
  } else if (isDirect && phase >= 2) {
    borderColor = RISK_COLORS[risk] || '#f0883e';
    bg = '#221e18';
    glowColor = `0 0 8px 2px ${RISK_COLORS[risk]}44`;
  } else if (isIndirect && phase >= 3) {
    borderColor = '#e3b341';
    bg = '#1e1c15';
  } else if (isTest && phase >= 4) {
    borderColor = '#3fb950';
    bg = '#151e16';
  }

  return (
    <div
      className={`domino-node ${isSelected ? 'domino-node--selected' : ''} ${isHighlighted ? 'domino-node--highlighted' : ''} ${phase >= 2 && !isDimmed ? 'domino-node--active' : ''}`}
      style={{
        opacity,
        borderColor,
        background: bg,
        boxShadow: glowColor,
        transform: `scale(${scale})`,
        transition: 'all 300ms ease',
      }}
      title={data.path}
    >
      <div className="domino-node-top">
        <span className="domino-node-lang" style={{ background: LANG_COLORS[language] || '#888' }} />
        <span className="domino-node-name">{label}</span>
      </div>
      <div className="domino-node-meta">
        <span className="domino-node-type">{type}</span>
        {score > 0 && (
          <span className="domino-node-score" style={{ color: RISK_COLORS[risk] }}>
            {Math.round(score)}
          </span>
        )}
      </div>
    </div>
  );
}

const nodeTypes = { dominoNode: DominoNode };

// ─── Layout helper (simple force-directed approximation) ─────────────────────
function layoutNodes(nodes, edges) {
  const nodeMap = {};
  nodes.forEach(n => { nodeMap[n.id] = n; });

  // Simple layered layout: find roots (no incoming edges), then BFS
  const inDegree = {};
  nodes.forEach(n => { inDegree[n.id] = 0; });
  edges.forEach(e => { if (inDegree[e.target] !== undefined) inDegree[e.target]++; });

  const layers = [];
  const visited = new Set();
  const queue = nodes.filter(n => inDegree[n.id] === 0);
  if (queue.length === 0) {
    // Fallback: place in grid
    return nodes.map((n, i) => ({
      ...n,
      position: { x: (i % 8) * 180, y: Math.floor(i / 8) * 100 },
    }));
  }

  let layer = [...queue];
  while (layer.length > 0) {
    layers.push(layer.map(n => n.id));
    layer.forEach(n => visited.add(n.id));
    const nextLayer = [];
    layer.forEach(n => {
      edges
        .filter(e => e.source === n.id && !visited.has(e.target))
        .forEach(e => {
          if (!nextLayer.find(x => x.id === e.target)) {
            const target = nodeMap[e.target];
            if (target) nextLayer.push(target);
          }
        });
    });
    layer = nextLayer;
  }

  // Add any unvisited nodes at end
  nodes.filter(n => !visited.has(n.id)).forEach(n => {
    layers.push([n.id]);
  });

  const result = [];
  layers.forEach((layerIds, li) => {
    layerIds.forEach((id, ni) => {
      const n = nodeMap[id];
      if (n) {
        result.push({
          ...n,
          position: {
            x: ni * 200 - (layerIds.length * 100),
            y: li * 120,
          },
        });
      }
    });
  });
  return result;
}

// ─── Main page ────────────────────────────────────────────────────────────────
function DependencyMapInner() {
  const {
    activeRepo, setActiveRepo, selectedComponent, setSelectedComponent,
    impact, setImpact, dominoActive, dominoPhase, startDomino, advanceDomino, resetDomino,
    addNotification,
  } = useStore();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterLang, setFilterLang] = useState('');
  const [filterRisk, setFilterRisk] = useState('');
  const [filterType, setFilterType] = useState('');
  const [showPanel, setShowPanel] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedId, setHighlightedId] = useState(null);
  const { fitView, setCenter } = useReactFlow();
  const dominoTimerRef = useRef(null);

  // Load graph when activeRepo changes
  useEffect(() => {
    if (!activeRepo) {
      // Try to load first repo
      listRepositories().then(({ data }) => {
        if (data?.length) setActiveRepo(data[0]);
      });
      return;
    }
    loadGraph(activeRepo.id);
  }, [activeRepo]);

  const loadGraph = async (repoId) => {
    setLoading(true);
    setError(null);
    const { data, error } = await getDependencyGraph(repoId);
    if (error) { setError(error); setLoading(false); return; }
    setGraphData(data);
    buildReactFlowGraph(data, null, null);
    setLoading(false);
    setTimeout(() => fitView({ padding: 0.15 }), 100);
  };

  const buildReactFlowGraph = useCallback((data, selectedId, impactData) => {
    if (!data) return;

    const affectedSet = new Set();
    const directSet = new Set();
    const indirectSet = new Set();
    const testSet = new Set();
    let hasSelection = false;

    if (selectedId && impactData) {
      hasSelection = true;
      impactData.direct_dependencies?.forEach(id => directSet.add(id));
      impactData.indirect_dependencies?.forEach(id => indirectSet.add(id));
      impactData.related_tests?.forEach(id => testSet.add(id));
      impactData.affected_components?.forEach(id => affectedSet.add(id));
    }

    // Apply language/risk/type/search filters
    let filteredNodes = data.nodes;
    if (filterLang) filteredNodes = filteredNodes.filter(n => n.language === filterLang);
    if (filterRisk) filteredNodes = filteredNodes.filter(n => n.risk === filterRisk);
    if (filterType) filteredNodes = filteredNodes.filter(n => n.type === filterType);

    const filteredIds = new Set(filteredNodes.map(n => n.id));

    const rfNodes = filteredNodes.map(n => ({
      id: n.id,
      type: 'dominoNode',
      data: {
        label: n.name,
        path: n.path,
        language: n.language,
        type: n.type,
        risk: n.risk,
        score: n.risk_score,
        isSelected: n.id === selectedId,
        isDirect: directSet.has(n.id),
        isIndirect: indirectSet.has(n.id),
        isTest: testSet.has(n.id),
        isHighlighted: highlightedId === n.id,
        isDimmed: hasSelection && n.id !== selectedId && !directSet.has(n.id) && !indirectSet.has(n.id) && !testSet.has(n.id) && !affectedSet.has(n.id),
        phase: dominoPhase,
      },
      position: { x: 0, y: 0 },
    }));

    const rfEdges = data.edges
      .filter(e => filteredIds.has(e.source) && filteredIds.has(e.target))
      .map(e => {
        const isDirect = directSet.has(e.target) && e.source === selectedId;
        const isAffected = affectedSet.has(e.source) || affectedSet.has(e.target);
        return {
          id: `${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          type: 'smoothstep',
          animated: isDirect && dominoPhase >= 2,
          style: {
            stroke: isDirect ? RISK_COLORS.high : isAffected ? '#e3b341' : '#262b35',
            strokeWidth: isDirect ? 2 : 1,
            opacity: hasSelection && !isDirect && !isAffected ? 0.15 : 0.7,
          },
          markerEnd: { type: MarkerType.ArrowClosed, color: isDirect ? RISK_COLORS.high : '#262b35' },
        };
      });

    const laid = layoutNodes(rfNodes, rfEdges);
    setNodes(laid);
    setEdges(rfEdges);
  }, [filterLang, filterRisk, filterType, dominoPhase, highlightedId, setNodes, setEdges]);

  // Rebuild graph when filters or phase change
  useEffect(() => {
    if (graphData) {
      buildReactFlowGraph(graphData, selectedComponent?.id, impact);
    }
  }, [filterLang, filterRisk, filterType, dominoPhase, highlightedId, graphData, selectedComponent, impact]);

  // Domino animation sequence
  const triggerDomino = useCallback(() => {
    if (!selectedComponent || !impact) return;
    resetDomino();
    startDomino();
    let phase = 1;
    const advance = () => {
      phase++;
      advanceDomino();
      if (phase < 5) {
        dominoTimerRef.current = setTimeout(advance, 600);
      }
    };
    dominoTimerRef.current = setTimeout(advance, 500);
  }, [selectedComponent, impact, startDomino, advanceDomino, resetDomino]);

  useEffect(() => {
    return () => clearTimeout(dominoTimerRef.current);
  }, []);

  const onNodeClick = useCallback(async (_, node) => {
    const comp = { id: node.id, name: node.data.label, path: node.data.path,
      language: node.data.language, type: node.data.type, risk: node.data.risk,
      risk_score: node.data.score, repository_id: activeRepo?.id };
    setSelectedComponent(comp);
    resetDomino();
    setShowPanel(true);

    // Load impact
    const { data, error } = await getImpact(node.id);
    if (data) {
      setImpact(data);
      buildReactFlowGraph(graphData, node.id, data);
    } else if (error) {
      addNotification(`Impact error: ${error}`, 'error');
    }
  }, [activeRepo, graphData, buildReactFlowGraph, setSelectedComponent, setImpact, resetDomino, addNotification]);

  // Search suggestions (max 8 matching nodes)
  const searchSuggestions = useMemo(() => {
    if (!searchQuery.trim() || !graphData) return [];
    const q = searchQuery.toLowerCase();
    return graphData.nodes
      .filter(n => n.name.toLowerCase().includes(q) || n.path.toLowerCase().includes(q))
      .slice(0, 8);
  }, [searchQuery, graphData]);

  const handleSearchSelect = useCallback((node) => {
    setHighlightedId(node.id);
    setSearchQuery(node.path);
    // Pan to the node after graph rebuilds
    setTimeout(() => {
      const rfNode = nodes.find(n => n.id === node.id);
      if (rfNode) {
        setCenter(rfNode.position.x + 70, rfNode.position.y + 30, { zoom: 1.4, duration: 500 });
      }
    }, 80);
  }, [nodes, setCenter]);

  const clearSearch = () => {
    setSearchQuery('');
    setHighlightedId(null);
  };

  const uniqueLangs = graphData ? [...new Set(graphData.nodes.map(n => n.language))] : [];
  const uniqueRisks = graphData ? [...new Set(graphData.nodes.map(n => n.risk))] : [];
  const uniqueTypes = graphData ? [...new Set(graphData.nodes.map(n => n.type))] : [];

  return (
    <div className="depmap-page">
      {/* Toolbar */}
      <div className="depmap-toolbar">
        <div className="depmap-toolbar-left">
          <span className="section-title" style={{ margin: 0 }}>
            {activeRepo ? activeRepo.name : 'No Repository'} — Dependency Map
          </span>
          {graphData && (
            <span className="text-xs muted">
              {graphData.node_count} nodes · {graphData.edge_count} edges
            </span>
          )}
        </div>
        <div className="depmap-filters">
          {/* Node search */}
          <div className="depmap-search-wrap">
            <input
              className="input depmap-search-input"
              type="text"
              placeholder="Search nodes…"
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); if (!e.target.value) clearSearch(); }}
              aria-label="Search nodes"
              aria-autocomplete="list"
            />
            {searchQuery && (
              <button className="depmap-search-clear" onClick={clearSearch} aria-label="Clear search">✕</button>
            )}
            {searchSuggestions.length > 0 && (
              <div className="depmap-search-dropdown" role="listbox">
                {searchSuggestions.map(n => (
                  <button
                    key={n.id}
                    className="depmap-search-option"
                    role="option"
                    aria-selected={highlightedId === n.id}
                    onClick={() => handleSearchSelect(n)}
                  >
                    <span className="depmap-search-option-name">{n.name}</span>
                    <span className="depmap-search-option-path muted">{n.path}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <select className="input" value={filterLang} onChange={e => setFilterLang(e.target.value)} style={{ maxWidth: 120 }} aria-label="Filter language">
            <option value="">All languages</option>
            {uniqueLangs.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
          <select className="input" value={filterRisk} onChange={e => setFilterRisk(e.target.value)} style={{ maxWidth: 110 }} aria-label="Filter risk">
            <option value="">All risk</option>
            {uniqueRisks.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select className="input" value={filterType} onChange={e => setFilterType(e.target.value)} style={{ maxWidth: 110 }} aria-label="Filter type">
            <option value="">All types</option>
            {uniqueTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => { setFilterLang(''); setFilterRisk(''); setFilterType(''); clearSearch(); resetDomino(); setSelectedComponent(null); setImpact(null); }}
          >
            Reset
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => fitView({ padding: 0.15, duration: 400 })}
          >
            Fit View
          </button>
        </div>
        {selectedComponent && impact && (
          <button
            className="btn btn-primary depmap-domino-btn"
            onClick={triggerDomino}
          >
            ⚡ Analyze Change Impact
          </button>
        )}
      </div>

      <div className="depmap-body">
        {/* Graph canvas */}
        <div className="depmap-canvas">
          {loading && <div className="loading-container" style={{ position: 'absolute', zIndex: 10 }}><div className="spinner"/><span>Building dependency graph…</span></div>}
          {error && <div className="error-container"><div className="error-title">Error</div><div>{error}</div></div>}
          {!activeRepo && !loading && (
            <div className="empty-container">Select a repository to view its dependency map.</div>
          )}

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.1}
            maxZoom={3}
            attributionPosition="bottom-right"
          >
            <Background color="#1c2028" gap={24} size={1} />
            <Controls />
            <MiniMap
              nodeColor={n => NODE_TYPE_COLORS[n.data?.type] || '#4f81ff'}
              style={{ background: '#13161b', border: '1px solid #262b35' }}
            />
          </ReactFlow>

          {/* Domino phase indicator */}
          {dominoActive && (
            <div className="domino-phase-indicator">
              <DominoPhaseDisplay phase={dominoPhase} />
            </div>
          )}

          {/* Legend */}
          <div className="depmap-legend">
            <div className="legend-title">NODE TYPE</div>
            {Object.entries(NODE_TYPE_COLORS).map(([type, color]) => (
              <div key={type} className="legend-item">
                <span className="legend-dot" style={{ background: color }} />
                <span>{type}</span>
              </div>
            ))}
            <div className="legend-title" style={{ marginTop: 8 }}>RISK</div>
            {Object.entries(RISK_COLORS).map(([risk, color]) => (
              <div key={risk} className="legend-item">
                <span className="legend-dot" style={{ background: color }} />
                <span>{risk}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Impact panel */}
        {showPanel && selectedComponent && (
          <ImpactPanel
            onClose={() => { setShowPanel(false); resetDomino(); setSelectedComponent(null); setImpact(null); buildReactFlowGraph(graphData, null, null); }}
          />
        )}
      </div>
    </div>
  );
}

function DominoPhaseDisplay({ phase }) {
  const PHASES = [
    null,
    { label: 'SELECTED', color: '#fff', desc: 'Component selected' },
    { label: 'DIRECT IMPACT', color: '#f0883e', desc: 'Direct dependencies activated' },
    { label: 'INDIRECT IMPACT', color: '#e3b341', desc: 'Secondary blast radius' },
    { label: 'TEST COVERAGE', color: '#3fb950', desc: 'Related tests identified' },
    { label: 'BLAST RADIUS COMPLETE', color: '#f85149', desc: 'Full impact calculated' },
  ];
  const p = PHASES[phase];
  if (!p) return null;
  return (
    <div className="domino-phase" style={{ borderColor: p.color }}>
      <span className="domino-phase-label" style={{ color: p.color }}>{p.label}</span>
      <span className="domino-phase-desc">{p.desc}</span>
    </div>
  );
}

export default function DependencyMapPage() {
  return (
    <ReactFlowProvider>
      <DependencyMapInner />
    </ReactFlowProvider>
  );
}
