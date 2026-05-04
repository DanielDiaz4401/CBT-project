import React, { useState, useEffect } from 'react';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ReferenceLine, AreaChart, Area, LineChart, Line, Legend, ComposedChart,
  PieChart, Pie, Cell
} from 'recharts';
import { Activity, Clock, Cpu, Zap } from 'lucide-react';

export default function VisualizeStages({ migration }) {
  const [stagesData, setStagesData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const params = migration?.params || { l_max: 150, c_min: 1, c_max: 5 };

  useEffect(() => {
    if (migration?.id) {
      setLoading(true);
      fetch(`http://localhost:8000/simulations/get_stages/${migration.id}`)
        .then(res => res.json())
        .then(data => {
          let currentTotal = 0;
          const formattedData = data.map((s, index) => {
            currentTotal += s.migrated_components.length;
            return {
              ...s,
              etapa: index, // MANTENIM la variable original en castellà/català
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

  // CÀLCULS D'EFICIÈNCIA
  const totalMigrated = stagesData.length > 0 ? stagesData[stagesData.length - 1].cumulative : 0;
  const realStages = stagesData.length;
  // Etapes òptimes = Total components / Màxim components per etapa
  const optimalStages = totalMigrated > 0 ? Math.ceil(totalMigrated / Number(params.c_max)) : 0;
  // Eficiència = (etapes òptimes / etapes reals) * 100
  const efficiencyPercentage = realStages > 0 ? Math.min(100, Math.round((optimalStages / realStages) * 100)) : 0;

  // Dades pel gràfic d'anell
  const pieData = [
    { name: 'Efficiency', value: efficiencyPercentage },
    { name: 'Remaining', value: 100 - efficiencyPercentage }
  ];

  if (loading) return <div className="p-20 text-center font-bold animate-pulse text-slate-400">Loading statistics...</div>;

  return (
    <div className="flex flex-col h-full bg-slate-50 overflow-y-auto p-8 font-sans">
      
      {/* 1. KPI Cards (4 columnes) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-4 mb-2">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg"><Activity size={20}/></div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Total Stages</p>
          </div>
          <p className="text-3xl font-black text-slate-900">{stagesData.length}</p>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-4 mb-2">
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg"><Clock size={20}/></div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Final Latency</p>
          </div>
          <p className="text-3xl font-black text-slate-900">
            {stagesData[stagesData.length - 1]?.worst_critical_time.toFixed(2)} <span className="text-sm font-bold text-slate-400">ms</span>
          </p>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-4 mb-2">
            <div className="p-2 bg-purple-50 text-purple-600 rounded-lg"><Cpu size={20}/></div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Total Migrated</p>
          </div>
          <p className="text-3xl font-black text-slate-900">
            {stagesData[stagesData.length - 1]?.cumulative || 0}
          </p>
        </div>

        {/* TARGETA D'EFICIÈNCIA */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <div className="p-2 bg-amber-50 text-amber-500 rounded-lg"><Zap size={20}/></div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Efficiency</p>
            </div>
            <p className="text-3xl font-black text-slate-900">
              {efficiencyPercentage}<span className="text-xl">%</span>
            </p>
          </div>
          <div className="w-16 h-16">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={20}
                  outerRadius={30}
                  startAngle={90}
                  endAngle={-270}
                  dataKey="value"
                  stroke="none"
                >
                  <Cell fill="#f59e0b" />
                  <Cell fill="#f1f5f9" />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 2. GRÀFIC 1: Latència Crítica */}
      <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm mb-8">
        <div className="mb-6">
          <h3 className="font-black text-slate-800 uppercase tracking-tight">Latency Evolution</h3>
          <p className="text-slate-400 text-xs font-bold">Worst path time versus L_MAX limit</p>
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={stagesData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              {/* Fem servir la variable 'etapa' interna original, però no la traduïm per evitar errors */}
              <XAxis dataKey="etapa" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
              <YAxis tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} unit="ms" />
              <Tooltip 
                contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 20px rgba(0,0,0,0.05)'}} 
                labelFormatter={(label) => `Stage: ${label}`}
              />
              <ReferenceLine y={Number(params.l_max)} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'LIMIT', fill: '#ef4444', fontSize: 10, fontWeight: 'bold' }} />
              <Area type="monotone" dataKey="worst_critical_time" name="Worst Path Time" stroke="#3b82f6" strokeWidth={3} fill="#3b82f6" fillOpacity={0.1} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. GRÀFIC 2: Migration Status & Efficiency */}
      <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
        <div className="mb-6">
          <h3 className="font-black text-slate-800 uppercase tracking-tight">Migration Status and Efficiency</h3>
          <p className="text-slate-400 text-xs font-bold">Actual progress vs theoretical limits C_MIN and C_MAX</p>
        </div>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={stagesData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="etapa" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
              <YAxis tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
              <Tooltip 
                contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 20px rgba(0,0,0,0.05)'}}
                labelFormatter={(label) => `Stage: ${label}`}
              />
              <Legend verticalAlign="top" height={36} iconType="circle" />
              
              <Line 
                type="monotone" 
                dataKey="theoMax" 
                stroke="#10b981" 
                strokeDasharray="5 5" 
                dot={false} 
                name="Best Case (C_MAX)" 
                strokeWidth={2} 
              />
              
              <Line 
                type="monotone" 
                dataKey="theoMin" 
                stroke="#ef4444" 
                strokeDasharray="5 5" 
                dot={false} 
                name="Worst Case (C_MIN)" 
                strokeWidth={2} 
              />
              
              <Area 
                type="stepAfter" 
                dataKey="cumulative" 
                fill="#3b82f6" 
                stroke="#3b82f6" 
                fillOpacity={0.1} 
                strokeWidth={3} 
                name="Actual Cumulative Migration" 
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}