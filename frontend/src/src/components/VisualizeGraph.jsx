import React, { useState, useEffect, useRef, useMemo } from 'react';

const API_BASE = 'http://localhost:8000/simulations';

export default function VisualizeGraph({ migration }) {
  // Datos del Servidor
  const [milestones, setMilestones] = useState([]);      // Etapas que afectan a este camino
  const [allStages, setAllStages] = useState([]);        // Registro global de migraciones
  const [skeleton, setSkeleton] = useState(null);        // Topología del camino
  const [currentStepEdges, setCurrentStepEdges] = useState(null); // Aristas rojas/puntos
  
  // Estado de Navegación
  const [pathNumber, setPathNumber] = useState(''); 
  const [stageIdx, setStageIdx] = useState(0);           // Índice en el array de hitos
  const [loading, setLoading] = useState(false);

  // Pan & Zoom
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // 1. Carga Inicial: Hitos y Todas las Etapas
  useEffect(() => {
    if (migration?.id) {
      // Cargamos los hitos del camino
      fetch(`${API_BASE}/${migration.id}/critical-paths`)
        .then(res => res.json())
        .then(data => {
          setMilestones(data);
          if (data.length > 0) {
            setPathNumber(String(data[0].path_number));
            loadSkeleton(data[0].path_number);
          }
        });

      // Cargamos TODAS las etapas para la acumulación local
      fetch(`${API_BASE}/${migration.id}/stages`)
        .then(res => res.json())
        .then(data => setAllStages(data));
    }
  }, [migration.id]);

  const loadSkeleton = async (num) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/${migration.id}/critical-paths/${num}/topology`);
      const data = await res.json();
      setSkeleton(data);
      setStageIdx(0);
      
      // Busquem els hitos específics d'aquest path per carregar la primera etapa
      const pathInfo = milestones.find(p => p.path_number === Number(num));
      const firstStage = pathInfo?.affected_stages[0] || 0;
      loadStepEdges(firstStage);
    } catch (err) {
      console.error("Error loading skeleton:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadStepEdges = (stageNum) => {
    fetch(`${API_BASE}/${migration.id}/stages/${stageNum}/critical-path-update`)
      .then(res => res.json())
      .then(data => setCurrentStepEdges(data));
  };

  // 2. LÓGICA DE ACUMULACIÓN
  const cloudNodes = useMemo(() => {
    if (!milestones.length || pathNumber === '' || !allStages.length || !skeleton) return new Set();
    
    const pathInfo = milestones.find(p => p.path_number === Number(pathNumber));
    const currentStageLimit = pathInfo?.affected_stages[stageIdx] ?? 0;

    const accumulated = new Set(skeleton.initial_cloud_nodes || []);
    allStages.forEach((stage, idx) => {
      if (idx <= currentStageLimit) {
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
      loadStepEdges(pathInfo.affected_stages[nextIdx]);
    }
  };

  const renderGraph = () => {
    if (!skeleton || !currentStepEdges) return null;

    const nodeIds = Object.keys(skeleton.nodes_mapping);
    const totalNodes = nodeIds.length;
    const getPos = (i) => {
      const angle = (i / totalNodes) * 2 * Math.PI;
      const radius = Math.max(250, totalNodes * 20);
      return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) };
    };

    return (
      <g style={{ 
        transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
        transformOrigin: '0 0',
        transition: isDragging ? 'none' : 'transform 0.1s ease-out'
      }}>
        <g transform={`translate(${containerRef.current?.clientWidth / 2 || 400}, ${containerRef.current?.clientHeight / 2 || 300})`}>
          {/* ARISTAS */}
          {Object.entries(skeleton.edge_latencies).map(([edgeKey, lat]) => {
            const [sId, tId] = edgeKey.split('|');
            const sIdx = nodeIds.indexOf(sId);
            const tIdx = nodeIds.indexOf(tId);
            if (sIdx === -1 || tIdx === -1) return null;

            const p1 = getPos(sIdx);
            const p2 = getPos(tIdx);

            const isCritical = currentStepEdges.worst_path_edges.some(e => e[0] === sId && e[1] === tId);
            const isExtra = currentStepEdges.extra_latency_edges.some(e => e[0] === sId && e[1] === tId);

            return (
              <line 
                key={edgeKey} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke={isCritical || isExtra ? "#ef4444" : "#cbd5e1"}
                strokeWidth={isCritical ? "5" : "2"}
                strokeDasharray={isExtra && !isCritical ? "6,6" : ""}
                className="transition-all duration-500"
              />
            );
          })}

          {/* NODOS */}
          {nodeIds.map((id, i) => {
            const pos = getPos(i);
            const isCloud = cloudNodes.has(id);

            return (
              <g key={id} transform={`translate(${pos.x}, ${pos.y})`}>
                <circle 
                  r="28" 
                  fill={isCloud ? "#3b82f6" : "#94a3b8"}
                  stroke="white" strokeWidth="4"
                  className="transition-colors duration-700 shadow-2xl cursor-pointer hover:stroke-slate-800"
                />
                <text textAnchor="middle" dy=".3em" className="text-[10px] font-black fill-white pointer-events-none">{id}</text>
                <text y="45" textAnchor="middle" className="text-[9px] font-bold fill-slate-500 uppercase tracking-widest pointer-events-none">
                  {isCloud ? 'CLOUD' : 'ON-PREM'}
                </text>
              </g>
            );
          })}
        </g>
      </g>
    );
  };

  const onMouseDown = (e) => { setIsDragging(true); setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y }); };
  const onMouseMove = (e) => { if (isDragging) setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }); };

  return (
    <div className="flex flex-col h-full bg-slate-50 relative font-sans overflow-hidden select-none" ref={containerRef}>
      
      {/* FLOATING HEADER: PATH INPUT & ZOOM CONTROLS */}
      <div className="absolute top-6 left-6 right-6 flex justify-between items-start z-10 pointer-events-none">
        
        {/* Lado Izquierdo: Input de Path y Leyenda */}
        <div className="flex flex-col gap-4 pointer-events-auto">
          <div className="bg-white/90 backdrop-blur-md p-4 rounded-2xl shadow-lg border border-slate-200/60 flex flex-col">
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

          {/* Leyenda Visual */}
          <div className="bg-white/90 backdrop-blur-md p-4 rounded-2xl shadow-lg border border-slate-200/60 flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-[#94a3b8] border-2 border-white shadow-sm"></div>
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">On-Premise</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-[#3b82f6] border-2 border-white shadow-sm"></div>
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Cloud Node</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-3 h-1 rounded-full bg-[#ef4444]"></div>
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Critical Path</span>
            </div>
          </div>
        </div>

        {/* Lado Derecho: Controles de Zoom */}
        <div className="bg-white/90 backdrop-blur-md p-1.5 rounded-2xl shadow-lg border border-slate-200/60 flex flex-col gap-1 pointer-events-auto">
          <button onClick={() => setZoom(z => z + 0.1)} className="w-10 h-10 flex items-center justify-center bg-transparent hover:bg-slate-100 rounded-xl text-slate-600 font-bold text-xl transition-colors">+</button>
          <div className="w-6 h-[1px] bg-slate-200 mx-auto my-1"></div>
          <button onClick={() => setZoom(z => Math.max(0.1, z - 0.1))} className="w-10 h-10 flex items-center justify-center bg-transparent hover:bg-slate-100 rounded-xl text-slate-600 font-bold text-xl transition-colors">-</button>
          <div className="w-6 h-[1px] bg-slate-200 mx-auto my-1"></div>
          <button onClick={() => {setZoom(1); setPan({x:0, y:0})}} className="w-10 h-10 flex items-center justify-center bg-transparent hover:bg-slate-100 rounded-xl text-slate-400 font-black text-[9px] uppercase tracking-tighter transition-colors">RST</button>
        </div>
      </div>

      {/* GRAPH CANVAS AREA */}
      <div 
        className={`flex-1 relative w-full h-full ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`} 
        onMouseDown={onMouseDown} 
        onMouseMove={onMouseMove} 
        onMouseUp={() => setIsDragging(false)} 
        onMouseLeave={() => setIsDragging(false)}
      >
        <svg className="w-full h-full absolute inset-0 pointer-events-none">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#cbd5e1" strokeWidth="0.5" strokeOpacity="0.4"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          {renderGraph()}
        </svg>

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-sm z-30">
            <div className="flex flex-col items-center gap-4">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-slate-200 border-t-blue-600"></div>
              <p className="text-xs font-black text-blue-600 uppercase tracking-widest">Processing Data...</p>
            </div>
          </div>
        )}
      </div>

      {/* FLOATING BOTTOM NAVIGATION */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20">
        <div className="bg-white/95 backdrop-blur-xl px-8 py-5 rounded-full shadow-2xl border border-slate-200/60 flex items-center gap-10">
          
          <button 
            onClick={() => handleNavigate(-1)} 
            disabled={stageIdx === 0} 
            className="group flex items-center gap-3 px-6 py-3 bg-slate-50 border border-slate-200 rounded-full hover:bg-slate-100 disabled:opacity-30 transition-all"
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
            className="group flex items-center gap-3 px-6 py-3 bg-blue-600 rounded-full hover:bg-blue-700 disabled:opacity-30 shadow-lg shadow-blue-200 transition-all"
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