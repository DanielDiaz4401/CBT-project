import React, { useState, useEffect } from 'react';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  LineChart, Line, Legend, BarChart, Bar
} from 'recharts';
import { ArrowLeft, Layers, Zap, Clock } from 'lucide-react';

export default function MigrationCompare({ selectedMigrations, onBack }) {
  const [comparisonData, setComparisonData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Colors per diferenciar les migracions
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'];

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);
      try {
        const results = await Promise.all(
          selectedMigrations.map(m => 
            fetch(`http://localhost:8000/simulations/get_stages/${m.id}`).then(res => res.json())
          )
        );

        // Busquem el màxim d'etapes per a l'eix X
        const maxStages = Math.max(...results.map(r => r.length));
        
        // Formategem les dades per als gràfics
        const chartData = Array.from({ length: maxStages }, (_, i) => {
          const entry = { etapa: i };
          results.forEach((stages, idx) => {
            const mName = selectedMigrations[idx].name;
            if (stages[i]) {
              entry[`latency_${idx}`] = stages[i].worst_critical_time;
              entry[`migrated_${idx}`] = stages[i].migrated_components.length;
            }
          });
          return entry;
        });

        setComparisonData(chartData);
      } catch (err) {
        console.error("Error comparant dades:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [selectedMigrations]);

  if (loading) return <div className="p-20 text-center animate-pulse">Comparing data...</div>;

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 p-8 font-sans">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button onClick={onBack} className="p-2 hover:bg-white rounded-full transition-all border border-transparent hover:border-slate-200">
          <ArrowLeft size={24} />
        </button>
        <h1 className="text-3xl font-bold text-slate-900">Compare Migrations</h1>
      </div>

      {/* 1. Resum ràpid de KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {selectedMigrations.map((m, idx) => (
          <div key={m.id} className="bg-white p-6 rounded-3xl border-t-4 shadow-sm" style={{ borderTopColor: colors[idx % colors.length] }}>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{m.name}</p>
            <div className="flex justify-between items-end">
              <div>
                <p className="text-2xl font-black text-slate-900">{m.result?.total_stages || 'N/A'} <span className="text-xs text-slate-400">Stages</span></p>
              </div>
              <div className={`px-2 py-1 rounded text-[10px] font-bold text-white`} style={{ backgroundColor: colors[idx % colors.length] }}>
                #{idx + 1}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 2. Gràfic de Latència Comparada*/}
      <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm mb-8">
        <div className="mb-6 flex items-center gap-3">
          <Clock className="text-blue-500" />
          <h3 className="font-black text-slate-800 uppercase tracking-tight">Latency Comparison</h3>
        </div>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="etapa" tick={{fontSize: 10}} />
              <YAxis unit="ms" tick={{fontSize: 10}} />
              <Tooltip contentStyle={{borderRadius: '16px', border: 'none'}} />
              <Legend />
              {selectedMigrations.map((m, idx) => (
                <Line 
                  key={m.id}
                  type="monotone" 
                  dataKey={`latency_${idx}`} 
                  name={m.name} 
                  stroke={colors[idx % colors.length]} 
                  strokeWidth={3} 
                  dot={false} 
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Gràfic de Nodes Migrats per Etapa */}
      <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <Layers className="text-emerald-500" />
          <h3 className="font-black text-slate-800 uppercase tracking-tight">Migration Velocity (Nodes per Stage)</h3>
        </div>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="etapa" tick={{fontSize: 10}} />
              <YAxis tick={{fontSize: 10}} />
              <Tooltip contentStyle={{borderRadius: '16px', border: 'none'}} />
              <Legend />
              {selectedMigrations.map((m, idx) => (
                <Bar 
                  key={m.id}
                  dataKey={`migrated_${idx}`} 
                  name={m.name} 
                  fill={colors[idx % colors.length]} 
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}