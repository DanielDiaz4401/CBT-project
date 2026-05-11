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
    const newObj = { component_name: newNodeId, stage_number: parseInt(newStage) };
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
    formData.append('threshold', params.umbral);
    formData.append('blocked_components', JSON.stringify(constraints));

    onConfirm(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="px-8 py-6 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Migration Setup</h2>
            <p className="text-slate-400 text-sm">Configure your project data and algorithm constraints</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-colors">✕</button>
        </div>

        {/* Cuerpo del modal - Flex Layout para igualdad de columnas */}
        <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
          
          {/* 1. PROJECT & DATA */}
          <div className="flex-1 p-8 border-r border-slate-100 flex flex-col gap-6">
            <h3 className="text-xs font-bold text-blue-600 uppercase tracking-widest">1. Project & Data</h3>
            
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-500 uppercase">Project Name</label>
              <input 
                type="text" 
                value={migrationName}
                onChange={(e) => setMigrationName(e.target.value)}
                placeholder="e.g. Core Banking Migration"
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm bg-slate-50/50"
              />
            </div>

            <div className="space-y-3">
              <label className="block text-xs font-bold text-slate-500 uppercase">Input Files (.csv)</label>
              {['nodes', 'edges', 'paths'].map((type) => (
                <div 
                  key={type} 
                  onClick={() => fileInputs[type].current.click()} 
                  className={`group cursor-pointer flex items-center p-4 border-2 border-dashed rounded-xl transition-all ${
                    files[type] ? 'border-emerald-200 bg-emerald-50/50' : 'border-slate-200 hover:border-blue-300 hover:bg-blue-50/30'
                  }`}
                >
                  <div className="flex-1">
                    <p className="text-xs font-bold text-slate-700 capitalize">{type} File</p>
                    <p className={`text-[11px] truncate ${files[type] ? 'text-emerald-600' : 'text-slate-400'}`}>
                      {files[type] ? files[type].name : 'Click to upload'}
                    </p>
                  </div>
                  <div className={`text-lg ${files[type] ? 'text-emerald-500' : 'text-slate-300 group-hover:text-blue-400'}`}>
                    {files[type] ? '✓' : '+'}
                  </div>
                  <input type="file" ref={fileInputs[type]} className="hidden" onChange={handleFileChange(type)} accept=".csv" />
                </div>
              ))}
            </div>
          </div>

          {/* 2. NODE CONSTRAINTS */}
          <div className="flex-1 p-8 border-r border-slate-100 flex flex-col bg-slate-50/30">
            <h3 className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-6">2. Node Constraints</h3>
            
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 space-y-3 mb-6">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 ml-1">NODE ID</span>
                  <input 
                    type="text" 
                    placeholder="Ex: N-102"
                    value={newNodeId}
                    onChange={(e) => setNewNodeId(e.target.value)}
                    className="w-full p-2.5 text-sm border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50"
                  />
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 ml-1">STAGE</span>
                  <input 
                    type="number" 
                    placeholder="1-10"
                    value={newStage}
                    onChange={(e) => setNewStage(e.target.value)}
                    className="w-full p-2.5 text-sm border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50"
                  />
                </div>
              </div>
              <button 
                onClick={addConstraint}
                className="w-full py-3 bg-slate-800 text-white text-[10px] font-bold rounded-lg hover:bg-slate-900 transition-all uppercase tracking-widest"
              >
                Add Constraint
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-2 min-h-[200px]">
              {constraints.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-100 rounded-xl">
                  <p className="text-xs italic">No constraints added yet</p>
                </div>
              ) : (
                constraints.map((c, i) => (
                  <div key={i} className="flex items-center justify-between bg-white border border-slate-200 p-3 rounded-xl shadow-sm animate-in fade-in slide-in-from-bottom-1">
                    <div className="flex gap-3 items-center">
                      <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-md border border-blue-100">ID: {c.component_name}</span>
                      <span className="text-[10px] font-bold bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md border border-slate-200">STAGE: {c.stage_number}</span>
                    </div>
                    <button onClick={() => removeConstraint(i)} className="text-slate-300 hover:text-red-500 transition-colors p-1">✕</button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 3. ALGORITHM PARAMETERS */}
          <div className="flex-1 p-8 flex flex-col justify-between">
            <div className="space-y-6">
              <h3 className="text-xs font-bold text-blue-600 uppercase tracking-widest">3. Algorithm</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase">C_MIN</label>
                  <input type="number" value={params.c_min} onChange={(e) => setParams({...params, c_min: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50" />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase">C_MAX</label>
                  <input type="number" value={params.c_max} onChange={(e) => setParams({...params, c_max: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50" />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase">L_MIN (ms)</label>
                  <input type="number" value={params.l_max} onChange={(e) => setParams({...params, l_max: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50" />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase">L_EXTRA (ms)</label>
                  <input type="number" value={params.l_extra} onChange={(e) => setParams({...params, l_extra: e.target.value})} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50" />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[10px] font-bold text-slate-400 uppercase">Threshold (%)</label>
                <div className="relative flex items-center">
                  <input 
                    type="number" 
                    value={params.umbral} 
                    onChange={(e) => setParams({...params, umbral: e.target.value})} 
                    className="w-full p-3 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 pr-10" 
                  />
                  <span className="absolute right-4 text-slate-400 text-sm font-bold">%</span>
                </div>
              </div>
            </div>

            <div className="pt-8 space-y-3">
              <button 
                onClick={handleSubmit}
                disabled={isCalculating}
                className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all disabled:opacity-50 active:scale-[0.98]"
              >
                {isCalculating ? 'Processing...' : 'Start Migration'}
              </button>
              <button onClick={onClose} className="w-full py-2 text-slate-400 text-xs font-semibold hover:text-slate-600 transition-colors uppercase tracking-widest">
                Cancel Process
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}