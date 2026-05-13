import React, { useState, useRef } from 'react';
import AlgorithmParamsForm from './AlgorithmParamsForm';

export default function SetupModal({ onClose, onConfirm, isCalculating, templateData }) {
  const [migrationName, setMigrationName] = useState(templateData ? `${templateData.name} (Copy)` : '');
  const [files, setFiles] = useState({ edges: null, nodes: null, paths: null });
  const [params, setParams] = useState({ 
    c_min: templateData?.c_min ?? 1, 
    c_max: templateData?.c_max ?? 5, 
    l_max: templateData?.l_max ?? 150, 
    l_extra: templateData?.l_extra ?? 30,
    umbral: templateData?.threshold ?? 10
  });

  const [constraints, setConstraints] = useState(templateData?.blocked_components ? [...templateData.blocked_components] : []);
  const [newNodeId, setNewNodeId] = useState('');
  const [newStage, setNewStage] = useState('');

  const fileInputs = { edges: useRef(null), nodes: useRef(null), paths: useRef(null) };

  const handleFileChange = (type) => (e) => {
    if (e.target.files[0]) setFiles(prev => ({ ...prev, [type]: e.target.files[0] }));
  };

  const addConstraint = () => {
    if (!newNodeId || !newStage) return;
    setConstraints([...constraints, { component_name: newNodeId, stage_number: parseInt(newStage) }]);
    setNewNodeId('');
    setNewStage('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("name", migrationName);
    formData.append("l_extra", params.l_extra);
    formData.append("c_min", params.c_min);
    formData.append("c_max", params.c_max);
    formData.append("l_max", params.l_max);
    formData.append("threshold", params.umbral);
    formData.append("blocked_components", JSON.stringify(constraints));

    if (templateData) {
      formData.append("base_sim_id", templateData.id);
    } else {
      formData.append("nodes_file", files.nodes);
      formData.append("edges_file", files.edges);
      formData.append("paths_file", files.paths);
    }
    onConfirm(formData);
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
          {/* Secciones 1 y 2 omitidas aquí por brevedad, se mantienen igual */}
          <div className="flex-1 p-8 border-r border-slate-100 flex flex-col gap-6">
             {/* ... UI de Proyectos y Archivos ... */}
          </div>
          
          <div className="flex-1 p-8 border-r border-slate-100 flex flex-col bg-slate-50/30">
             {/* ... UI de Constraints ... */}
          </div>

          <div className="flex-1 p-8 flex flex-col justify-between">
            <AlgorithmParamsForm params={params} setParams={setParams} />
            <div className="pt-8 space-y-3">
              <button onClick={handleSubmit} disabled={isCalculating} className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold shadow-lg shadow-blue-200">
                {isCalculating ? 'Processing...' : 'Start Migration'}
              </button>
              <button onClick={onClose} className="w-full py-2 text-slate-400 text-xs font-semibold uppercase tracking-widest">Cancel Process</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}