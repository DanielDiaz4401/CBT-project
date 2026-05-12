import React, { useState, useEffect } from 'react';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area, Legend
} from 'recharts';
import { ArrowLeft, Layers, Zap, Clock, Settings } from 'lucide-react';

export default function MigrationCompare({ selectedMigrations, onBack }) {
  const [comparisonData, setComparisonData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [extraStats, setExtraStats] = useState({});

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'];

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);
      try {
        const results = await Promise.all(
          selectedMigrations.map(m => 
            fetch(`http://localhost:8000/simulations/get_stages/${m.id}`).then(res => res.json())
          )
        );

        const maxStages = Math.max(...results.map(r => r.length));
        const newStats = {};
        
        const chartData = Array.from({ length: maxStages }, (_, i) => {
          const entry = { etapa: i };
          results.forEach((stages, idx) => {
            if (stages[i]) {
              entry[`latency_${idx}`] = stages[i].worst_critical_time;
              
              // Acumulado
              const currentTotal = stages.slice(0, i + 1).reduce((acc, s) => acc + s.migrated_components.length, 0);
              entry[`cumulative_${idx}`] = currentTotal;
            }
            
            // Calculamos las estadísticas solo en la primera iteración
            if (i === 0) {
              const totalMigrated = stages.reduce((acc, s) => acc + s.migrated_components.length, 0);
              // AHORA LEE DIRECTAMENTE DE LA RAÍZ: selectedMigrations[idx].c_max
              const cMax = Number(selectedMigrations[idx].c_max || 5); 
              const optimal = Math.ceil(totalMigrated / cMax);
              const real = stages.length;
              
              newStats[idx] = {
                efficiency: real > 0 ? Math.min(100, Math.round((optimal / real) * 100)) : 0,
                total: totalMigrated,
                stagesCount: real // Guardamos el número de etapas reales calculado
              };
            }
          });
          return entry;
        });

        setExtraStats(newStats);
        setComparisonData(chartData);
      } catch (err) {
        console.error("Error comparando datos:", err);
      } finally {
        setLoading(false);
      }
    };

    if (selectedMigrations.length > 0) fetchAllData();
  }, [selectedMigrations]);

  if (loading) return <div className="p-20 text-center animate-pulse font-bold text-slate-400">Comparing data...</div>;

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 p-8 font-sans text-slate-900">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button onClick={onBack} className="p-2 hover:bg-white rounded-full transition-all border border-slate-200 shadow-sm">
          <ArrowLeft size={24} />
        </button>
        <h1 className="text-3xl font-black tracking-tight">COMPARE MIGRATIONS</h1>
      </div>

      {/* 1. GRID COMPARATIVO */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {selectedMigrations.slice(0, 4).map((m, idx) => (
          <div key={m.id} className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
            <div className="h-2 w-full" style={{ backgroundColor: colors[idx % colors.length] }}></div>
            <div className="p-6 space-y-6 flex-1 flex flex-col">
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Scenario {idx + 1}</p>
                <h3 className="text-lg font-bold truncate text-slate-800">{m.name}</h3>
              </div>

              {/* Parámetros actualizados con el nuevo esquema del Backend */}
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                <div className="flex items-center gap-2 mb-3 text-slate-400">
                  <Settings size={14} />
                  <span className="text-[10px] font-black uppercase">Parameters</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'C-MAX', val: m.c_max },
                    { label: 'L-MAX', val: `${m.l_max}ms` },
                    { label: 'THRSH', val: `${m.threshold}%` },
                    { label: 'EXTRA', val: `+${m.l_extra}ms` }
                  ].map((p, i) => (
                    <div key={i}>
                      <p className="text-[8px] font-black text-slate-400 uppercase leading-none mb-1">{p.label}</p>
                      <p className="text-xs font-bold text-slate-700">{p.val !== undefined ? p.val : 'N/A'}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* KPIs (Usando el stagesCount calculado internamente) */}
              <div className="mt-auto pt-4 grid grid-cols-2 gap-4 border-t border-slate-50">
                <div className="flex flex-col">
                  <div className="flex items-center gap-1 text-blue-500 mb-1">
                    <Layers size={14} />
                    <span className="text-[10px] font-black uppercase">Stages</span>
                  </div>
                  <p className="text-2xl font-black text-slate-900">{extraStats[idx]?.stagesCount || '0'}</p>
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-1 text-amber-500 mb-1">
                    <Zap size={14} />
                    <span className="text-[10px] font-black uppercase">Efficiency</span>
                  </div>
                  <p className="text-2xl font-black text-amber-600">{extraStats[idx]?.efficiency || '0'}%</p>
                </div>
              </div>
            </div>
          </div>
        ))}

        {selectedMigrations.length < 4 && 
          Array.from({ length: 4 - selectedMigrations.length }).map((_, i) => (
            <div key={`empty-${i}`} className="hidden lg:flex flex-col border-2 border-dashed border-slate-200 rounded-3xl bg-slate-100/30 items-center justify-center p-6">
              <p className="text-slate-300 text-[10px] font-black uppercase tracking-widest italic">Available Slot</p>
            </div>
          ))
        }
      </div>

      {/* 2. GRÁFICOS */}
      <div className="space-y-8">
        <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
          <div className="mb-6 flex items-center gap-3 text-slate-400">
            <Clock size={18} />
            <h3 className="font-black uppercase text-xs tracking-widest">Latency Evolution</h3>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="etapa" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <YAxis unit="ms" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 20px rgba(0,0,0,0.05)'}} />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                {selectedMigrations.map((m, idx) => (
                  <Area 
                    key={m.id}
                    type="monotone" 
                    dataKey={`latency_${idx}`} 
                    name={m.name} 
                    stroke={colors[idx % colors.length]} 
                    fill={colors[idx % colors.length]} 
                    fillOpacity={0.05} 
                    strokeWidth={3} 
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
          <div className="mb-6 flex items-center gap-3 text-slate-400">
            <Layers size={18} />
            <h3 className="font-black uppercase text-xs tracking-widest">Migration Status (Cumulative)</h3>
          </div>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="etapa" tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <YAxis tick={{fontSize: 10, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 20px rgba(0,0,0,0.05)'}} />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                {selectedMigrations.map((m, idx) => (
                  <Area 
                    key={m.id}
                    type="stepAfter" 
                    dataKey={`cumulative_${idx}`} 
                    name={m.name} 
                    stroke={colors[idx % colors.length]} 
                    fill={colors[idx % colors.length]} 
                    fillOpacity={0.05} 
                    strokeWidth={3} 
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}