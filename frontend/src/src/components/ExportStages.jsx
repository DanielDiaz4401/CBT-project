import React, { useState, useEffect } from 'react';
import { Download } from 'lucide-react'; 

export default function ExportStages({ migration }) {
  const [stagesData, setStagesData] = useState([]);
  const [loading, setLoading] = useState(true);

  const API_BASE = 'http://localhost:8000/simulations';

  useEffect(() => {
    if (migration?.id) {
      setLoading(true);
      fetch(`${API_BASE}/${migration.id}/stages`)
        .then(res => {
          if (!res.ok) throw new Error("Error al obtener las etapas");
          return res.json();
        })
        .then(data => {
          setStagesData(data);
          setLoading(false);
        })
        .catch(err => {
          console.error("Error en ExportStages:", err);
          setLoading(false);
        });
    }
  }, [migration.id]);

  const handleExportJSON = () => {
    if (stagesData.length === 0) return;

    // Al exportar, podemos añadir el índice al JSON para que el receptor sepa el orden
    const exportData = stagesData.map((s, i) => ({ etapa: i, ...s }));
    
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `reporte_migracion_${migration.name || 'data'}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <p className="text-slate-400 font-bold animate-pulse">Cargando reporte...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-8 bg-white relative">
      <div className="flex justify-between items-center mb-8 shrink-0">
        <div>
          <h2 className="text-3xl font-black text-slate-800 uppercase tracking-tight">Plan Global de Migración</h2>
          <p className="text-slate-500 text-base mt-1">Secuencia completa de componentes migrados por posición en el array.</p>
        </div>
        <button 
          onClick={handleExportJSON} 
          className="flex items-center gap-2 bg-blue-600 text-white px-8 py-4 rounded-xl font-bold text-sm uppercase tracking-widest hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 active:scale-95"
        >
          <Download size={18} />
          Exportar Reporte JSON
        </button>
      </div>

      <div className="flex-1 border border-slate-200 rounded-2xl overflow-hidden shadow-sm flex flex-col bg-slate-50">
        <div className="overflow-y-auto flex-1 h-0">
          <table className="w-full text-left relative">
            <thead className="bg-slate-100 border-b-2 border-slate-200 sticky top-0 z-10 shadow-sm">
              <tr>
                <th className="p-6 text-xs font-black text-slate-500 uppercase tracking-widest w-48">Etapa (Índice)</th>
                <th className="p-6 text-xs font-black text-slate-500 uppercase tracking-widest">Componentes Migrados</th>
                <th className="p-6 text-xs font-black text-slate-500 uppercase tracking-widest text-right">Latencia Resultante</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {stagesData.map((stage, index) => (
                <tr key={index} className="hover:bg-blue-50/40 transition-colors">
                  <td className="p-6 align-top">
                    <span className="w-12 h-12 flex items-center justify-center bg-blue-50 text-blue-600 rounded-xl font-black text-lg border border-blue-100 shadow-sm">
                      {index}
                    </span>
                  </td>
                  <td className="p-6">
                    <div className="flex flex-wrap gap-2">
                      {stage.migrated_components.map((comp, i) => (
                        <span key={i} className="px-3 py-1.5 bg-slate-50 text-slate-700 rounded-lg text-[11px] font-bold border border-slate-200 shadow-sm">
                          {comp}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-6 text-right align-top">
                    <span className="font-mono font-bold text-slate-600">
                      {stage.worst_critical_time.toFixed(2)} ms
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}