import React, { useState, useRef } from 'react';

export default function SetupModal({ onClose, onConfirm, isCalculating }) {
  const [migrationName, setMigrationName] = useState('');
  const [files, setFiles] = useState({ edges: null, nodes: null, paths: null });
  const [params, setParams] = useState({ 
    c_min: 1, 
    c_max: 5, 
    l_max: 150, 
    l_extra: 30,
    umbral: 10 
  });

  const fileInputs = {
    edges: useRef(null),
    nodes: useRef(null),
    paths: useRef(null)
  };

  const handleFileChange = (type) => (e) => {
    if (e.target.files[0]) {
      setFiles(prev => ({ ...prev, [type]: e.target.files[0] }));
    }
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!migrationName || !files.nodes || !files.edges || !files.paths) {
      alert("Por favor, rellena el nombre y sube los 3 archivos CSV.");
      return;
    }

    const formData = new FormData();
    formData.append('name', migrationName);
    formData.append('nodes_file', files.nodes);
    formData.append('edges_file', files.edges);
    formData.append('paths_file', files.paths);
    formData.append('l_extra', params.l_extra);
    formData.append('c_min', params.c_min);
    formData.append('c_max', params.c_max);
    formData.append('l_max', params.l_max);
    formData.append('threshold', params.umbral);

    onConfirm(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col">
        <div className="px-8 py-6 border-b border-slate-100 flex justify-between items-center bg-white">
          <h2 className="text-2xl font-bold text-slate-800">Migration Setup</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl transition-colors">✕</button>
        </div>

        <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-10 overflow-y-auto max-h-[85vh]">
          <div className="space-y-6">
            <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider">1. Project & Data</h3>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Project Name</label>
              <input 
                type="text" 
                value={migrationName}
                onChange={(e) => setMigrationName(e.target.value)}
                placeholder="e.g. Core Banking Migration"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all"
              />
            </div>
            <div className="space-y-3">
              <label className="block text-sm font-bold text-slate-700">Required CSV Files</label>
              {['nodes', 'edges', 'paths'].map((type) => (
                <div 
                  key={type} 
                  onClick={() => fileInputs[type].current.click()} 
                  className={`cursor-pointer flex items-center p-4 border border-dashed rounded-xl transition-all ${
                    files[type] ? 'border-emerald-300 bg-emerald-50' : 'border-slate-300 hover:border-blue-400 hover:bg-blue-50'
                  }`}
                >
                  <div className={`p-2 rounded-lg mr-4 ${files[type] ? 'bg-emerald-100' : 'bg-slate-100'}`}>
                    <svg className={`w-6 h-6 ${files[type] ? 'text-emerald-600' : 'text-slate-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-bold text-slate-700 capitalize">{type} File</p>
                    <p className={`text-xs truncate ${files[type] ? 'text-emerald-600' : 'text-slate-400'}`}>
                      {files[type] ? files[type].name : 'Click to upload .csv'}
                    </p>
                  </div>
                  <input type="file" ref={fileInputs[type]} className="hidden" onChange={handleFileChange(type)} accept=".csv" />
                </div>
              ))}
            </div>
          </div>

          {/* Columna Dreta: Algoritme */}
          <div className="space-y-6 bg-slate-50 p-6 rounded-2xl">
            <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider">2. Algorithm Parameters</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">C_MIN</label>
                <input type="number" value={params.c_min} onChange={(e) => setParams({...params, c_min: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">C_MAX</label>
                <input type="number" value={params.c_max} onChange={(e) => setParams({...params, c_max: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">L_MAX (ms)</label>
                <input type="number" value={params.l_max} onChange={(e) => setParams({...params, l_max: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">L_EXTRA (ms)</label>
                <input type="number" value={params.l_extra} onChange={(e) => setParams({...params, l_extra: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div className="pt-2">
              <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Threshold (%)</label>
              <div className="relative flex items-center">
                <input 
                  type="number" 
                  min="0" max="100"
                  value={params.umbral} 
                  onChange={(e) => setParams({...params, umbral: e.target.value})} 
                  className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 pr-10" 
                />
                <span className="absolute right-3 text-slate-400 font-bold">%</span>
              </div>
            </div>
            <div className="pt-6 space-y-3">
              <button 
                onClick={handleSubmit}
                disabled={isCalculating}
                className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold shadow-lg hover:bg-blue-700 transition-all disabled:opacity-50"
              >
                {isCalculating ? 'Processing...' : 'Start Calculation'}
              </button>
              <button onClick={onClose} className="w-full py-2 text-slate-400 text-sm font-medium hover:text-slate-600 transition-colors">Back to Dashboard</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}