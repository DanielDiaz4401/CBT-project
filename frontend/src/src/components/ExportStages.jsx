import React, { useState, useEffect } from 'react';
import { Download } from 'lucide-react'; 
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

  const handleExportJSON = () => {
    if (stagesData.length === 0) return;

    // Translated index to 'stage'
    const exportData = stagesData.map((s, i) => ({ stage: i, ...s }));
    
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `migration_report_${migration.name || 'data'}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  const handleDownloadArtifact = (fileType) => {
    if (!migration) return;

    // Actualizado al nuevo endpoint REST
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
      <div className="bg-white p-8 border-b border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h2 className="text-2xl font-black text-slate-800 mb-2">Export Data</h2>
          <p className="text-slate-500 text-sm">Download configuration artifacts or the final stage report.</p>
        </div>

        <div className="flex gap-3">
          <button 
            onClick={handleExportJSON}
            className="flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-900 text-white rounded-xl font-bold shadow-lg transition-all"
          >
            <Download size={18} />
            <span>Download Stages (JSON)</span>
          </button>

          {/* New specific download buttons for CSVs */}
          <div className="flex bg-slate-100 rounded-xl p-1 border border-slate-200">
            {['nodes', 'edges', 'paths'].map(type => (
              <button
                key={type}
                onClick={() => handleDownloadArtifact(type)}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-white hover:text-blue-600 hover:shadow-sm rounded-lg transition-all capitalize"
              >
                {type} CSV
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Data Preview (Kept your original table design) */}
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