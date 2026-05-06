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

  const [constraints, setConstraints] = useState([]);
  const [newNodeId, setNewNodeId] = useState('');
  const [newStage, setNewStage] = useState('');

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

  const addConstraint = () => {
    if (!newNodeId || !newStage) return;
    const newObj = { node_id: newNodeId, stage: parseInt(newStage) };
    setConstraints([...constraints, newObj]);
    setNewNodeId('');
    setNewStage('');
  };

  const removeConstraint = (index) => {
    setConstraints(constraints.filter((_, i) => i !== index));
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
    formData.append('c_min', params.c_min);
    formData.append('c_max', params.c_max);
    formData.append('l_max', params.l_max);
    formData.append('l_extra', params.l_extra);
    formData.append('umbral', params.umbral);
    formData.append('constraints', JSON.stringify(constraints));

    onConfirm(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl h-150 overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="flex-none px-8 py-5 border-b border-slate-100 flex justify-between items-center bg-white">
          <h2 className="text-2xl font-bold text-slate-800">Migration Setup</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl transition-colors">✕</button>
        </div>

        {/* Cuerpo del modal */}
        <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-8 overflow-hidden items-start h-full">
          
          {/* 1. PROJECT & DATA */}
          <div className="flex flex-col h-full overflow-hidden space-y-6">
            <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider">1. Project & Data</h3>
            <div className="flex-none">
              <label className="block text-sm font-bold text-slate-700 mb-2">Project Name</label>
              <input 
                type="text" 
                value={migrationName}
                onChange={(e) => setMigrationName(e.target.value)}
                placeholder="e.g. Core Banking Migration"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm"
              />
            </div>
            <div className="space-y-3 overflow-y-auto pr-2">
              {['nodes', 'edges', 'paths'].map((type) => (
                <div 
                  key={type} 
                  onClick={() => fileInputs[type].current.click()} 
                  className={`cursor-pointer flex items-center p-3 border border-dashed rounded-xl transition-all ${
                    files[type] ? 'border-emerald-300 bg-emerald-50' : 'border-slate-300 hover:border-blue-400 hover:bg-blue-50'
                  }`}
                >
                  <div className="flex-1">
                    <p className="text-xs font-bold text-slate-700 capitalize">{type} File</p>
                    <p className={`text-[10px] truncate ${files[type] ? 'text-emerald-600' : 'text-slate-400'}`}>
                      {files[type] ? files[type].name : 'Click to upload .csv'}
                    </p>
                  </div>
                  <input type="file" ref={fileInputs[type]} className="hidden" onChange={handleFileChange(type)} accept=".csv" />
                </div>
              ))}
            </div>
          </div>

          {/* 2. NODE CONSTRAINTS */}
          <div className="flex flex-col h-full overflow-hidden space-y-4 border-l border-r border-slate-100 px-4">
            <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider">2. Node Constraints</h3>
            
            <div className="flex-none bg-slate-50 p-4 rounded-xl space-y-3 border border-slate-200">
              <div className="grid grid-cols-2 gap-2">
                <input 
                  type="text" 
                  placeholder="Node ID"
                  value={newNodeId}
                  onChange={(e) => setNewNodeId(e.target.value)}
                  className="p-2 text-xs border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input 
                  type="number" 
                  placeholder="Stage"
                  value={newStage}
                  onChange={(e) => setNewStage(e.target.value)}
                  className="p-2 text-xs border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button 
                onClick={addConstraint}
                className="w-full py-2.5 bg-slate-800 text-white text-[10px] font-black rounded-lg hover:bg-slate-900 transition-all uppercase tracking-widest leading-loose"
              >
                + CREATE NEW OBJECT
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-2 pb-4">
              {constraints.length === 0 ? (
                <p className="text-[10px] text-slate-400 text-center py-10 italic">No node constraints defined</p>
              ) : (
                constraints.map((c, i) => (
                  <div key={i} className="flex items-center justify-between bg-white border border-slate-100 p-2 rounded-lg shadow-sm">
                    <div className="flex gap-2 items-center">
                      <span className="text-[9px] font-bold bg-blue-50 text-blue-600 px-2 py-1 rounded border border-blue-100">ID: {c.node_id}</span>
                      <span className="text-[9px] font-bold bg-slate-100 text-slate-600 px-2 py-1 rounded border border-slate-200">STAGE: {c.stage}</span>
                    </div>
                    <button onClick={() => removeConstraint(i)} className="text-slate-300 hover:text-red-500 transition-colors px-1">✕</button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 3. ALGORITHM PARAMETERS */}
          <div className="flex flex-col h-full overflow-hidden space-y-5 bg-slate-50 p-6 rounded-2xl">
            <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider">3. Algorithm</h3>
            
            <div className="flex-1 overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">C_MIN</label>
                  <input type="number" value={params.c_min} onChange={(e) => setParams({...params, c_min: e.target.value})} className="w-full p-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">C_MAX</label>
                  <input type="number" value={params.c_max} onChange={(e) => setParams({...params, c_max: e.target.value})} className="w-full p-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">L_MIN (ms)</label>
                  <input type="number" value={params.l_max} onChange={(e) => setParams({...params, l_max: e.target.value})} className="w-full p-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">L_EXTRA (ms)</label>
                  <input type="number" value={params.l_extra} onChange={(e) => setParams({...params, l_extra: e.target.value})} className="w-full p-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div className="mt-4">
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Threshold (%)</label>
                <div className="relative flex items-center">
                  <input 
                    type="number" 
                    value={params.umbral} 
                    onChange={(e) => setParams({...params, umbral: e.target.value})} 
                    className="w-full p-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 pr-8" 
                  />
                  <span className="absolute right-3 text-slate-400 text-xs font-bold">%</span>
                </div>
              </div>
            </div>

            <div className="flex-none pt-4 space-y-3">
              <button 
                onClick={handleSubmit}
                disabled={isCalculating}
                className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold shadow-lg hover:bg-blue-700 transition-all disabled:opacity-50"
              >
                {isCalculating ? 'Processing...' : 'Start Migration'}
              </button>
              <button onClick={onClose} className="w-full py-2 text-slate-400 text-xs font-medium hover:text-slate-600 transition-colors">Back to Dashboard</button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}