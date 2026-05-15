import React, { useState, useEffect } from 'react';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ReferenceLine, AreaChart, Area, LineChart, Line, Legend, ComposedChart,
  PieChart, Pie, Cell
} from 'recharts';
import { Activity, Clock, Cpu, Zap, Settings, BarChart3, Lock, AlertTriangle, CheckCircle } from 'lucide-react';

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL;

export default function VisualizeStages({ migration }) {
  const [stagesData, setStagesData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Configuration parameters
  const params = { 
    l_max: migration?.l_max ?? 150, 
    c_min: migration?.c_min ?? 1, 
    c_max: migration?.c_max ?? 5, 
    l_extra: migration?.l_extra ?? 0, 
    threshold: migration?.threshold ?? migration?.umbral ?? 0 
  };

  // Get fixed nodes (blocked_components) of the migration
  const fixedNodes = migration?.blocked_components || [];

  useEffect(() => {
    if (migration?.id) {
      setLoading(true);
      fetch(`${API_BASE}/${migration.id}/stages`)
        .then(res => res.json())
        .then(data => {
          let currentTotal = 0;
          const formattedData = data.map((s, index) => {
            currentTotal += s.migrated_components.length;
            return {
              ...s,
              stage: index, // Changed from etapa to stage
              cumulative: currentTotal,
              theoMin: (index + 1) * Number(params.c_min),
              theoMax: (index + 1) * Number(params.c_max)
            };
          });
          setStagesData(formattedData);
          setLoading(false);
        })
        .catch(err => {
          console.error("Error loading statistics:", err);
          setLoading(false);
        });
    }
  }, [migration.id, params.c_min, params.c_max]);

  const totalMigrated = stagesData.length > 0 ? stagesData[stagesData.length - 1].cumulative : 0;
  const realStages = stagesData.length;
  const optimalStages = totalMigrated > 0 ? Math.ceil(totalMigrated / Number(params.c_max)) : 0;
  const efficiencyPercentage = realStages > 0 ? Math.min(100, Math.round((optimalStages / realStages) * 100)) : 0;

  const pieData = [
    { name: 'Efficiency', value: efficiencyPercentage },
    { name: 'Remaining', value: 100 - efficiencyPercentage }
  ];

  if (loading) return <div className="p-20 text-center font-bold animate-pulse text-slate-400">Loading statistics...</div>;

  return (
    <div className="flex flex-col h-full bg-slate-50 overflow-y-auto p-8 font-sans">
      
      {/* 1. PARAMETERS SECTION */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4 text-slate-400">
          <Settings size={16} />
          <h3 className="text-[10px] font-black uppercase tracking-widest">Configuration Parameters</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {[
            { 
              label: 'Algorithm', 
              // Leemos directamente de 'migration' que es de donde viene el dato de la BD
              value: (migration.algorithm_type === 'guangorithm') ? 'Guangorithm' : 
                     (migration.algorithm_type === 'robergorithm_v2') ? 'Robergorithm V2' : 
                     (migration.algorithm_type === 'robergorithm_v3') ? 'Robergorithm V3' : 
                     (migration.algorithm_type || 'Unknown'),
              highlight: true 
            },
            { label: 'C-Min', value: params.c_min },
            { label: 'C-Max', value: params.c_max },
            { label: 'L-Max Limit', value: `${params.l_max} ms` },
            { label: 'Extra Latency', value: `+${params.l_extra} ms` },
            { label: 'Threshold', value: `${params.threshold}%` }
          ].map((item, i) => (
            <div key={i} className={`bg-white px-4 py-4 rounded-2xl border border-slate-200 shadow-sm min-w-0 ${item.highlight ? 'border-l-4 border-l-blue-500' : ''}`}>
              <p className="text-[9px] font-bold text-slate-400 uppercase mb-1 truncate">{item.label}</p>
              <p className="text-xl font-black text-slate-700 truncate" title={item.value}>{item.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FIXED NODES (CONSTRAINTS) SECTION */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4 text-slate-400">
          <Lock size={16} />
          <h3 className="text-[10px] font-black uppercase tracking-widest">Fixed Nodes</h3>
        </div>
        {fixedNodes.length > 0 ? (
          <div className="flex flex-wrap gap-4">
            {fixedNodes.map((node, index) => (
              <div key={index} className="bg-white px-5 py-3 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
                <div className="p-2 bg-slate-50 text-slate-400 rounded-lg shrink-0">
                  <Lock size={16} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-[9px] font-bold text-slate-400 uppercase">Component</span>
                  <span className="text-sm font-black text-slate-700 truncate max-w-[120px]" title={node.component_name}>{node.component_name}</span>
                </div>
                <div className="h-8 w-[1px] bg-slate-100 mx-1 shrink-0"></div>
                <div className="flex flex-col shrink-0">
                  <span className="text-[9px] font-bold text-slate-400 uppercase">Fixed Stage</span>
                  <span className="text-sm font-black text-blue-600">#{node.stage_number}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white border border-dashed border-slate-200 p-5 rounded-2xl flex items-center gap-3">
            <div className="p-2 bg-slate-50 text-slate-300 rounded-lg">
              <Lock size={16} />
            </div>
            <p className="text-xs font-bold text-slate-400 uppercase">No fixed node constraints defined for this migration</p>
          </div>
        )}
      </div>

      {/* 2. STATISTICS SECTION (KPI CARDS) */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4 text-slate-400">
          <BarChart3 size={16} />
          <h3 className="text-[10px] font-black uppercase tracking-widest">Execution Results</h3>
        </div>
        
        {/* Cambiado a xl:grid-cols-5 para dar más aire en pantallas medianas */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          
          <div className={`p-6 rounded-2xl border shadow-sm flex flex-col justify-center ${migration.status === 'failed' ? 'bg-amber-50/50 border-amber-200' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center gap-4 mb-2">
              <div className={`p-2 rounded-lg shrink-0 ${migration.status === 'failed' ? 'bg-amber-100 text-amber-600' : 'bg-emerald-50 text-emerald-600'}`}>
                {migration.status === 'failed' ? <AlertTriangle size={20}/> : <CheckCircle size={20}/>}
              </div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">Compliance</p>
            </div>
            {/* Cambiado "Violated" por "Not Met" y suavizados los colores a tonos amber/naranja */}
            <p className={`text-2xl font-black truncate ${migration.status === 'failed' ? 'text-amber-700' : 'text-slate-900'}`}>
              {migration.status === 'failed' ? 'Not Met' : 'All Met'}
            </p>
            {migration.status === 'failed' && (
              <p className="text-[10px] font-bold text-amber-600 uppercase mt-1">Fallback Forced</p>
            )}
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-center">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg shrink-0"><Activity size={20}/></div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">Total Stages</p>
            </div>
            <p className="text-3xl font-black text-slate-900">{stagesData.length}</p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-center">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg shrink-0"><Clock size={20}/></div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">Final Latency</p>
            </div>
            <p className="text-3xl font-black text-slate-900 truncate">
              {stagesData[stagesData.length - 1]?.worst_critical_time.toFixed(2)} <span className="text-sm font-bold text-slate-400">ms</span>
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-center">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-purple-50 text-purple-600 rounded-lg shrink-0"><Cpu size={20}/></div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">Total Migrated</p>
            </div>
            <p className="text-3xl font-black text-slate-900">
              {stagesData[stagesData.length - 1]?.cumulative || 0}
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between gap-2 overflow-hidden">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-amber-50 text-amber-500 rounded-lg shrink-0"><Zap size={20}/></div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">Efficiency</p>
              </div>
              <p className="text-3xl font-black text-slate-900 truncate">
                {efficiencyPercentage}<span className="text-xl">%</span>
              </p>
            </div>
            {/* Quitamos ResponsiveContainer y fijamos width/height para evitar el aplastamiento */}
            <div className="shrink-0 flex items-center justify-center">
              <PieChart width={64} height={64}>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={20} outerRadius={30} startAngle={90} endAngle={-270} dataKey="value" stroke="none">
                  <Cell fill="#f59e0b" />
                  <Cell fill="#f1f5f9" />
                </Pie>
              </PieChart>
            </div>
          </div>
        </div>
      </div>

      {/* 3. CHARTS */}
      <div className="space-y-8">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
          <div className="mb-6">
            <h3 className="font-black text-slate-800 uppercase tracking-tight">Latency Evolution</h3>
            <p className="text-slate-400 text-xs font-bold">Worst path time versus L_MAX limit</p>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stagesData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="stage" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <YAxis tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} unit="ms" />
                <Tooltip 
                  contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 20px rgba(0,0,0,0.05)'}} 
                  labelFormatter={(label) => `Stage: ${label}`}
                />
                <ReferenceLine 
                  y={Number(params.l_max)} 
                  stroke="#ef4444" 
                  strokeDasharray="5 5" 
                  label={{ value: 'LIMIT', fill: '#ef4444', fontSize: 10, fontWeight: 'bold', position: 'insideBottomRight' }} 
                />
                <Area type="monotone" dataKey="worst_critical_time" name="Worst Path Time" stroke="#3b82f6" strokeWidth={3} fill="#3b82f6" fillOpacity={0.1} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
          <div className="mb-6">
            <h3 className="font-black text-slate-800 uppercase tracking-tight">Migration Status and Efficiency</h3>
            <p className="text-slate-400 text-xs font-bold">Actual progress vs theoretical limits C_MIN and C_MAX</p>
          </div>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={stagesData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="stage" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <YAxis tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 20px rgba(0,0,0,0.05)'}}
                  labelFormatter={(label) => `Stage: ${label}`}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Line type="monotone" dataKey="theoMax" stroke="#10b981" strokeDasharray="5 5" dot={false} name="Best Case (C_MAX)" strokeWidth={2} />
                <Line type="monotone" dataKey="theoMin" stroke="#ef4444" strokeDasharray="5 5" dot={false} name="Worst Case (C_MIN)" strokeWidth={2} />
                <Area type="stepAfter" dataKey="cumulative" fill="#3b82f6" stroke="#3b82f6" fillOpacity={0.1} strokeWidth={3} name="Actual Cumulative Migration" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}