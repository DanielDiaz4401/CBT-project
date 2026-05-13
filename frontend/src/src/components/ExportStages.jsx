import React, { useState, useEffect } from 'react';
import { Download, FileJson, FileSpreadsheet } from 'lucide-react'; // Añadimos iconos más semánticos
import toast from 'react-hot-toast';

export default function ExportStages({ migration }) {
  const [stagesData, setStagesData] = useState([]);
  const [loading, setLoading] = useState(true);

  const API_BASE = import.meta.env.PUBLIC_API_BASE_URL;

  useEffect(() => {
    if (migration?.id) {
      setLoading(true);
      fetch(`${API_BASE}/${migration.id}/stages`)
        .then(res => {
          if (!res.ok) throw new Error("Error fetching stages");
          return res.json();
        })
        .then(data => {
          setStagesData(data);
          setLoading(false);
        })
        .catch(err => {
          console.error("Error in ExportStages:", err);
          setLoading(false);
        });
    }
  }, [migration.id]);

  // --- EXPORTAR A JSON ---
  const handleExportJSON = () => {
    if (stagesData.length === 0) return;

    const exportData = stagesData.map((s, i) => ({ stage: i, ...s }));
    
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `migration_report_${migration.name || 'data'}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  // --- EXPORTAR A CSV (NUEVO) ---
  const handleExportCSV = () => {
    if (stagesData.length === 0) return;

    // 1. Definir cabeceras
    const headers = ["Stage", "Migrated Components", "Worst Critical Time (ms)"];

    // 2. Mapear los datos a filas CSV
    const rows = stagesData.map((stage, index) => {
      // Envolvemos el array de componentes en comillas para que las comas no rompan las columnas
      const componentsString = `"${stage.migrated_components.join(', ')}"`;
      
      return [
        index,
        componentsString,
        stage.worst_critical_time.toFixed(4)
      ].join(",");
    });

    // 3. Unir cabeceras y filas con saltos de línea
    const csvContent = [headers.join(","), ...rows].join("\n");

    // 4. Crear el Blob y descargar
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `migration_report_${migration.name || 'data'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadArtifact = (fileType) => {
    if (!migration) return;

    const url = `${API_BASE}/${migration.id}/artifacts/${fileType}`;

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`Could not download ${fileType}`);
        return res.blob();
      })
      .then(blob => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `${migration.name}_${fileType}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch(err => toast.error(err.message));
  };

  if (loading) {
    return <div className="p-20 text-center animate-pulse font-bold text-slate-400">Loading export data...</div>;
  }

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header / Actions */}
      <div className="bg-white p-8 border-b border-slate-200 shadow-sm flex flex-col xl:flex-row xl:items-center justify-between gap-6">
        <div>
          <h2 className="text-2xl font-black text-slate-800 mb-2">Export Data</h2>
          <p className="text-slate-500 text-sm">Download configuration artifacts or the final stage report.</p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          
          {/* Botones de Exportación del Reporte */}
          <div className="flex gap-2">
            <button 
              onClick={handleExportCSV}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-md shadow-emerald-600/20 transition-all text-sm"
            >
              <FileSpreadsheet size={18} />
              <span>Report CSV</span>
            </button>

            <button 
              onClick={handleExportJSON}
              className="flex items-center gap-2 px-5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl font-bold shadow-md transition-all text-sm"
            >
              <FileJson size={18} />
              <span>Report JSON</span>
            </button>
          </div>

          <div className="w-px h-8 bg-slate-200 hidden sm:block"></div>

          {/* Artefactos Base (Nodos, Aristas, Paths) */}
          <div className="flex bg-slate-100 rounded-xl p-1.5 border border-slate-200">
            {['nodes', 'edges', 'paths'].map(type => (
              <button
                key={type}
                onClick={() => handleDownloadArtifact(type)}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-600 hover:bg-white hover:text-blue-600 hover:shadow-sm rounded-lg transition-all capitalize"
                title={`Download original ${type} file`}
              >
                <Download size={14} />
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Data Preview */}
      <div className="flex-1 overflow-auto p-8">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="p-6 text-xs font-black text-slate-500 uppercase tracking-widest w-24">Stage</th>
                <th className="p-6 text-xs font-black text-slate-500 uppercase tracking-widest">Migrated Components</th>
                <th className="p-6 text-xs font-black text-slate-500 uppercase tracking-widest text-right">Resulting Latency</th>
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