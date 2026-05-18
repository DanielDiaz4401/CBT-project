import React, { useState, useEffect, useMemo, memo } from 'react';
import ReactECharts from 'echarts-for-react';

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL;

// --- 1. SUBCOMPONENTE AISLADO DEL CANVAS ---
const GraphInteractiveCanvas = memo(({ skeleton, cloudNodes, currentStepEdges, loading, migration }) => {
  if (!skeleton || !currentStepEdges) return null;

  // Extraemos el l_extra de la simulación (por si no existe, ponemos 0 de seguridad)
  const lExtra = migration?.l_extra || 0;

  const nodeIds = Object.keys(skeleton.nodes_mapping);

  const nodes = nodeIds.map(id => {
    const isCloud = cloudNodes.has(id);
    const isNewlyMigrated = currentStepEdges.newly_migrated_nodes?.includes(id);

    return {
      id: id, 
      name: id,
      symbolSize: isNewlyMigrated ? 48 : 42, 
      itemStyle: {
        color: isCloud ? '#3b82f6' : '#94a3b8',
        borderColor: isNewlyMigrated ? '#1e3a8a' : '#ffffff', 
        borderWidth: isNewlyMigrated ? 4 : 3,
        shadowBlur: isNewlyMigrated ? 15 : 8,
        shadowColor: isNewlyMigrated ? 'rgba(59, 130, 246, 0.6)' : 'rgba(0,0,0,0.12)'
      },
      label: {
        show: true,
        position: 'bottom',
        distance: 8,
        fontSize: 11,
        fontWeight: 'bold',
        color: '#334155'
      }
    };
  });

  // Modificamos los links para inyectarles la data bruta de latencia
  const links = Object.entries(skeleton.edge_latencies).map(([edgeKey, baseLatency]) => {
    const [sId, tId] = edgeKey.split('|');
    
    const worstEdges = currentStepEdges?.worst_path_edges || [];
    const extraEdges = currentStepEdges?.extra_latency_edges || [];

    const isCritical = worstEdges.some(e => 
      (e[0] || e.invoker) === sId && (e[1] || e.invoked) === tId
    );
    const isExtra = extraEdges.some(e => 
      (e[0] || e.invoker) === sId && (e[1] || e.invoked) === tId
    );

    return {
      id: edgeKey,
      source: sId,
      target: tId,
      // Guardamos estos datos personalizados para que el tooltip los pueda leer
      baseLatency: Number(baseLatency),
      isExtra: isExtra,
      lExtraValue: Number(lExtra),
      lineStyle: {
        color: isCritical || isExtra ? '#ef4444' : '#cbd5e1',
        width: isCritical ? 5 : 2,
        type: isExtra && !isCritical ? 'dashed' : 'solid',
        curveness: 0.15
      },
      symbol: ['none', 'arrow'],
      symbolSize: [0, isCritical ? 12 : 8]
    };
  });

  const option = {
    animationDurationUpdate: 800, 
    animationEasingUpdate: 'quinticInOut',
    // 🔥 AQUÍ ESTÁ LA MAGIA DEL TOOLTIP 🔥
    tooltip: {
      show: true,
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#cbd5e1',
      borderWidth: 1,
      padding: 14,
      borderRadius: 8,
      shadowBlur: 15,
      shadowColor: 'rgba(0,0,0,0.1)',
      formatter: (params) => {
        // Si el usuario hace hover sobre una arista (link)
        if (params.dataType === 'edge') {
          const { source, target, baseLatency, isExtra, lExtraValue } = params.data;
          
          let html = `
            <div style="font-weight:900; font-size:13px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 8px; color: #0f172a;">
              ${source} <span style="color:#94a3b8; margin: 0 4px;">➔</span> ${target}
            </div>
            <div style="display:flex; justify-content:space-between; gap:24px; margin-bottom:4px;">
              <span style="color:#64748b; font-weight:700; font-size:12px;">Base Latency:</span>
              <span style="color:#3b82f6; font-weight:900; font-size:12px;">${baseLatency.toFixed(2)} ms</span>
            </div>
          `;
          
          if (isExtra) {
            const total = baseLatency + lExtraValue;
            html += `
              <div style="display:flex; justify-content:space-between; gap:24px; margin-bottom:8px;">
                <span style="color:#64748b; font-weight:700; font-size:12px;">Cross-Traffic Penalty:</span>
                <span style="color:#ef4444; font-weight:900; font-size:12px;">+${lExtraValue.toFixed(2)} ms</span>
              </div>
              <div style="display:flex; justify-content:space-between; gap:24px; border-top: 1px dashed #cbd5e1; padding-top: 8px;">
                <span style="color:#0f172a; font-weight:800; font-size:13px;">Total Latency:</span>
                <span style="color:#ef4444; font-weight:900; font-size:14px;">${total.toFixed(2)} ms</span>
              </div>
            `;
          }
          return html;
        } 
        // Si el usuario hace hover sobre un nodo
        else if (params.dataType === 'node') {
          const isCloud = cloudNodes.has(params.data.id);
          const env = isCloud ? 'Cloud Environment' : 'On-Premise Server';
          const color = isCloud ? '#3b82f6' : '#94a3b8';
          return `
            <div style="font-weight:900; font-size:14px; color: #0f172a; margin-bottom: 4px;">${params.data.id}</div>
            <div style="color: ${color}; font-weight:bold; font-size:12px;">● ${env}</div>
          `;
        }
      }
    },
    series: [{
      id: 'migration-topology', 
      type: 'graph',
      layout: 'force',
      top: 0, bottom: 0, left: 0, right: 0,
      data: nodes,
      links: links,
      roam: true, 
      draggable: true, 
      force: {
        repulsion: 3000, 
        edgeLength: [150, 350], 
        gravity: 0.03, 
        layoutAnimation: true 
      },
      emphasis: {
        focus: 'adjacency', 
        scale: true, 
        lineStyle: { width: 5 } 
      },
      blur: {
        itemStyle: { opacity: 1 },
        lineStyle: { opacity: 1 }
      }
    }]
  };

  return (
    <div className="flex-1 relative w-full h-full bg-slate-50 overflow-hidden cursor-move">
      <div 
        className="absolute inset-0 pointer-events-none" 
        style={{ backgroundImage: 'radial-gradient(#cbd5e1 1.5px, transparent 1.5px)', backgroundSize: '32px 32px', opacity: 0.4 }}
      ></div>
      
      <ReactECharts 
        option={option} 
        style={{ height: '100%', width: '100%', position: 'absolute', zIndex: 10 }} 
        notMerge={false} 
        lazyUpdate={true}
      />
      
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-sm z-30 pointer-events-none">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-slate-200 border-t-blue-600"></div>
            <p className="text-xs font-black text-blue-600 uppercase tracking-widest">Processing Data...</p>
          </div>
        </div>
      )}
    </div>
  );
});

// --- 2. COMPONENTE PRINCIPAL ---
export default function VisualizeGraph({ migration }) {
  const [milestones, setMilestones] = useState([]);
  const [allStages, setAllStages] = useState([]);
  const [skeleton, setSkeleton] = useState(null);
  const [currentStepEdges, setCurrentStepEdges] = useState(null);
  
  const [pathNumber, setPathNumber] = useState(''); 
  const [stageIdx, setStageIdx] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (migration?.id) {
      fetch(`${API_BASE}/${migration.id}/critical-paths`)
        .then(res => res.json())
        .then(data => {
          setMilestones(data);
          if (data.length > 0) {
            setPathNumber(String(data[0].path_number));
            loadSkeleton(data[0].path_number, data); 
          }
        });

      fetch(`${API_BASE}/${migration.id}/stages`)
        .then(res => res.json())
        .then(data => setAllStages(data));
    }
  }, [migration.id]);

  const loadStepEdges = (stageNum, currentPathNumber) => {
    const targetPath = currentPathNumber !== undefined ? currentPathNumber : pathNumber;
    
    if (targetPath === '' || targetPath === undefined || targetPath === null) return;

    fetch(`${API_BASE}/${migration.id}/stages/${stageNum}/critical-path-update?path_number=${targetPath}`)
      .then(res => {
        if (!res.ok) throw new Error("Error en la API");
        return res.json();
      })
      .then(data => {
        if (data.worst_path_edges) setCurrentStepEdges(data);
      })
      .catch(err => console.error("Error cargando aristas:", err));
  };

  const loadSkeleton = async (num, freshMilestones) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/${migration.id}/critical-paths/${num}/topology`);
      const data = await res.json();
      setSkeleton(data);
      setStageIdx(0);
      
      const currentMilestones = freshMilestones || milestones;
      const pathInfo = currentMilestones.find(p => p.path_number === Number(num));
      const firstStage = pathInfo?.affected_stages[0] || 0;
      
      loadStepEdges(firstStage, num);
    } catch (err) {
      console.error("Error loading skeleton:", err);
    } finally {
      setLoading(false);
    }
  };

  const cloudNodes = useMemo(() => {
    if (!milestones.length || pathNumber === '' || !allStages.length || !skeleton) return new Set();
    
    const pathInfo = milestones.find(p => p.path_number === Number(pathNumber));
    const currentStageLimit = pathInfo?.affected_stages[stageIdx] ?? 0;

    const accumulated = new Set(skeleton.initial_cloud_nodes || []);
    allStages.forEach((stage) => {
      if (stage.stage_number <= currentStageLimit) {
        stage.migrated_components.forEach(node => accumulated.add(node));
      }
    });
    return accumulated;
  }, [allStages, stageIdx, pathNumber, milestones, skeleton]);

  const handleNavigate = (dir) => {
    const pathInfo = milestones.find(p => p.path_number === Number(pathNumber));
    if (!pathInfo) return;
    
    const nextIdx = stageIdx + dir;
    if (nextIdx >= 0 && nextIdx < pathInfo.affected_stages.length) {
      setStageIdx(nextIdx);
      loadStepEdges(pathInfo.affected_stages[nextIdx], pathNumber);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 relative font-sans overflow-hidden select-none">
      
      <div className="absolute top-6 left-6 flex flex-col gap-4 z-20 pointer-events-none">
        <div className="bg-white/90 backdrop-blur-md p-4 rounded-2xl shadow-lg border border-slate-200/60 flex flex-col pointer-events-auto">
          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Path Number</label>
          <div className="flex items-center gap-3">
            <input 
              type="number"
              value={pathNumber}
              onChange={(e) => {
                const val = e.target.value;
                setPathNumber(val);
                const exists = milestones.some(p => p.path_number === Number(val));
                if (exists) loadSkeleton(Number(val));
              }}
              className="w-20 px-3 py-2 border border-slate-200 rounded-xl font-bold text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 transition-all"
              placeholder="#"
            />
            <span className="text-[10px] font-bold text-slate-400 uppercase">
              / {milestones.length > 0 ? milestones[milestones.length - 1].path_number : '0'}
            </span>
          </div>
        </div>

        <div className="bg-white/90 backdrop-blur-md p-4 rounded-2xl shadow-lg border border-slate-200/60 flex flex-col gap-3 pointer-events-auto">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-[#94a3b8] border-2 border-white shadow-sm"></div>
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">On-Premise</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-[#3b82f6] border-2 border-white shadow-sm"></div>
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Cloud Node</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-[#3b82f6] border-2 border-[#1e3a8a] shadow-[0_0_8px_rgba(59,130,246,0.6)]"></div>
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Just Migrated</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-1 rounded-full bg-[#ef4444]"></div>
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Critical Path</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-0 border-b-2 border-dashed border-[#ef4444]"></div>
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Cross-Traffic (l_extra)</span>
          </div>
        </div>
      </div>

      <GraphInteractiveCanvas 
        skeleton={skeleton} 
        cloudNodes={cloudNodes} 
        currentStepEdges={currentStepEdges} 
        loading={loading}
        migration={migration} // 🔥 Pasamos el objeto migration completo hacia abajo
      />

      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20">
        <div className="bg-white/95 backdrop-blur-xl px-8 py-5 rounded-full shadow-2xl border border-slate-200/60 flex items-center gap-10">
          <button 
            onClick={() => handleNavigate(-1)} 
            disabled={stageIdx === 0} 
            className="group flex items-center gap-3 px-6 py-3 bg-slate-50 border border-slate-200 rounded-full hover:bg-slate-100 disabled:opacity-30 transition-all cursor-pointer"
          >
            <div className="w-8 h-8 flex items-center justify-center bg-white rounded-full shadow-sm text-slate-500 group-hover:text-slate-900 transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M15 19l-7-7 7-7"/></svg>
            </div>
            <span className="font-black text-slate-700 uppercase tracking-widest text-xs hidden md:block">Previous</span>
          </button>

          <div className="flex flex-col items-center min-w-[140px]">
            <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-1">Current Stage</span>
            <span className="text-3xl font-black text-slate-900 leading-none">
              {milestones.find(p => p.path_number === Number(pathNumber))?.affected_stages[stageIdx] ?? 0}
            </span>
          </div>

          <button 
            onClick={() => handleNavigate(1)} 
            disabled={!milestones.find(p => p.path_number === Number(pathNumber)) || stageIdx >= (milestones.find(p => p.path_number === Number(pathNumber))?.affected_stages.length - 1)} 
            className="group flex items-center gap-3 px-6 py-3 bg-blue-600 rounded-full hover:bg-blue-700 disabled:opacity-30 shadow-lg shadow-blue-200 transition-all cursor-pointer"
          >
            <span className="font-black text-white uppercase tracking-widest text-xs hidden md:block">Next Change</span>
            <div className="w-8 h-8 flex items-center justify-center bg-white/20 rounded-full text-white group-hover:bg-white group-hover:text-blue-600 transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7"/></svg>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}