import React, { useState, useRef } from 'react';
import { toast } from 'react-hot-toast';
import AlgorithmParamsForm from './AlgorithmParamsForm';

export default function SetupModal({ onClose, onConfirm, isCalculating, templateData }) {
  const [migrationName, setMigrationName] = useState(templateData ? `${templateData.name} (Copy)` : '');
  const [files, setFiles] = useState({ edges: null, nodes: null, paths: null });
  const [algorithmType, setAlgorithmType] = useState(templateData?.algorithm_type || 'guangorithm');
  const [params, setParams] = useState({ 
    c_min: templateData?.c_min ?? 1, 
    c_max: templateData?.c_max ?? 5, 
    l_max: templateData?.l_max ?? 150, 
    l_extra: templateData?.l_extra ?? 30,
    threshold: templateData?.threshold ?? 10,
    algorithm_type: templateData?.algorithm_type ?? 'guangorithm'
  });

  const [constraints, setConstraints] = useState(templateData?.blocked_components ? [...templateData.blocked_components] : []);
  const [newNodeId, setNewNodeId] = useState('');
  const [newStage, setNewStage] = useState('');

  const fileInputs = { edges: useRef(null), nodes: useRef(null), paths: useRef(null) };

  // --- CAPA DE SEGURIDAD Y SANEAMIENTO ---
  // Permite solo alfanuméricos, guiones, barras bajas y espacios.
  const sanitizeString = (str) => str.replace(/[^a-zA-Z0-9 _-]/g, '').trim();

  const handleFileChange = (type) => (e) => {
    if (e.target.files[0]) setFiles(prev => ({ ...prev, [type]: e.target.files[0] }));
  };

  const addConstraint = () => {
    if (!newNodeId || !newStage) {
      toast.error("Please provide both Node ID and Stage number.");
      return;
    }

    const sanitizedId = sanitizeString(newNodeId);
    const stageNum = parseInt(newStage, 10);

    // Validación defensiva de constraints
    if (!sanitizedId) {
      toast.error("Invalid Node ID. Only alphanumeric characters, hyphens, and underscores allowed.");
      return;
    }
    if (isNaN(stageNum) || stageNum < 1) {
      toast.error("Stage must be a valid positive number.");
      return;
    }
    if (constraints.some(c => c.component_name === sanitizedId)) {
      toast.error(`A constraint for node "${sanitizedId}" already exists.`);
      return;
    }

    setConstraints([...constraints, { component_name: sanitizedId, stage_number: stageNum }]);
    setNewNodeId('');
    setNewStage('');
  };

  const removeConstraint = (index) => {
    setConstraints(constraints.filter((_, i) => i !== index));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // 1. Validación de Archivos (si no es un clonado)
    if (!templateData && (!files.edges || !files.nodes || !files.paths)) {
      toast.error("Please upload all required CSV files (nodes, edges, paths).");
      return;
    }

    // 2. Saneamiento del Nombre
    const sanitizedName = sanitizeString(migrationName);
    if (!sanitizedName) {
      toast.error("Please provide a valid alphanumeric project name.");
      return;
    }

    // 3. Validación Matemática de Algoritmos (Coherencia de datos)
    const cMin = parseInt(params.c_min, 10);
    const cMax = parseInt(params.c_max, 10);
    const lMax = parseFloat(params.l_max);
    const lExtra = parseFloat(params.l_extra);
    const threshold = parseFloat(params.threshold);

    if (isNaN(cMin) || isNaN(cMax) || cMin < 1 || cMin > cMax) {
      toast.error("Invalid capacity: C_MIN must be at least 1 and cannot exceed C_MAX.");
      return;
    }
    if (isNaN(lMax) || isNaN(lExtra) || lMax <= 0 || lExtra < 0) {
      toast.error("Latency parameters must be valid positive numbers.");
      return;
    }
    if (isNaN(threshold) || threshold < 0 || threshold > 100) {
      toast.error("Threshold must be a valid percentage between 0 and 100.");
      return;
    }

    // 4. Construcción del Payload Seguro
    const formData = new FormData();
    formData.append("name", sanitizedName);
    formData.append("l_extra", lExtra);
    formData.append("c_min", cMin);
    formData.append("c_max", cMax);
    formData.append("l_max", lMax);
    formData.append("threshold", threshold);
    formData.append("algorithm_type", params.algorithm_type);
    formData.append("blocked_components", JSON.stringify(constraints));

    if (templateData) {
      formData.append("base_sim_id", templateData.id);
    } else {
      formData.append("nodes_file", files.nodes);
      formData.append("edges_file", files.edges);
      formData.append("paths_file", files.paths);
    }

    try {
      onConfirm(formData);
    } catch (error) {
      console.error(error);
      toast.error("An unexpected error occurred while preparing the simulation data.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl flex flex-col max-h-[90vh]">
        <div className="px-8 py-6 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Migration Setup</h2>
            <p className="text-slate-400 text-sm">Configure your project data and algorithm constraints</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-colors">✕</button>
        </div>

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
            
            <div className="space-y-4 border-b border-slate-100 pb-6">
              <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">Input Data</h3>
              {templateData ? (
                <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 flex items-center gap-3">
                  <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-emerald-900">Linked Files</p>
                    <p className="text-xs text-emerald-700">Base simulation files will be used.</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase">Input Files (.csv)</label>
                  {['nodes', 'edges', 'paths'].map((type) => (
                    <div key={type} onClick={() => fileInputs[type].current.click()} className={`group cursor-pointer flex items-center p-4 border-2 border-dashed rounded-xl transition-all ${files[type] ? 'border-emerald-200 bg-emerald-50/50' : 'border-slate-200 hover:border-blue-300 hover:bg-blue-50/30'}`}>
                      <div className="flex-1">
                        <p className="text-xs font-bold text-slate-700 capitalize">{type} File</p>
                        <p className={`text-[11px] truncate ${files[type] ? 'text-emerald-600' : 'text-slate-400'}`}>{files[type] ? files[type].name : 'Click to upload'}</p>
                      </div>
                      <div className={`text-lg ${files[type] ? 'text-emerald-500' : 'text-slate-300 group-hover:text-blue-400'}`}>{files[type] ? '✓' : '+'}</div>
                      <input type="file" ref={fileInputs[type]} className="hidden" onChange={handleFileChange(type)} accept=".csv" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          
          {/* 2. NODE CONSTRAINTS */}
          <div className="flex-1 p-8 border-r border-slate-100 flex flex-col bg-slate-50/30">
            <h3 className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-6">2. Node Constraints</h3>
            
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 space-y-3 mb-6">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 ml-1">NODE ID</span>
                  <input type="text" placeholder="Ex: N-102" value={newNodeId} onChange={(e) => setNewNodeId(e.target.value)} className="w-full p-2.5 text-sm border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50" />
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 ml-1">STAGE</span>
                  <input type="number" min="1" placeholder="1-10" value={newStage} onChange={(e) => setNewStage(e.target.value)} className="w-full p-2.5 text-sm border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50" />
                </div>
              </div>
              <button onClick={addConstraint} className="w-full py-3 bg-slate-800 text-white text-[10px] font-bold rounded-lg hover:bg-slate-900 transition-all uppercase tracking-widest">
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
            <AlgorithmParamsForm params={params} setParams={setParams} />
            <div className="pt-8 space-y-3">
              <button onClick={handleSubmit} disabled={isCalculating} className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all disabled:opacity-50 active:scale-[0.98]">
                {isCalculating ? 'Processing...' : 'Start Migration'}
              </button>
              <button onClick={onClose} className="w-full py-2 text-slate-400 text-xs font-semibold uppercase tracking-widest hover:text-slate-600 transition-colors">Cancel Process</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}