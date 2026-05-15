import React from 'react';

export default function AlgorithmParamsForm({ params, setParams }) {
  const handleChange = (key, value) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-8">
      {/* --- SELECTOR DE ALGORITMO CON TOOLTIP --- */}
      <div className="space-y-4 relative z-20">
        <div className="flex items-center gap-2">
          <label className="block text-xs font-bold text-slate-500 uppercase">Engine selection</label>
          
          {/* Tooltip CSS puro */}
          <div className="group relative flex items-center justify-center cursor-help">
            <div className="w-4 h-4 bg-slate-200 text-slate-500 rounded-full flex items-center justify-center text-[10px] font-black hover:bg-blue-100 hover:text-blue-600 transition-colors">?</div>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-72 p-4 bg-slate-900 text-white text-[11px] rounded-xl shadow-2xl border border-slate-700 pointer-events-none z-50 animate-in fade-in slide-in-from-bottom-1">
              <p className="font-bold text-blue-400 mb-2 uppercase tracking-widest text-[9px] border-b border-slate-700 pb-1">Engine Specifications</p>
              <ul className="space-y-2">
                <li><strong className="text-emerald-400">Guangorithm:</strong> Heurístico rápido. Complejidad $O(N)$. Ideal para grafos masivos y simulaciones ágiles.</li>
                <li><strong className="text-amber-400">Robergorithm V2:</strong> Búsqueda exhaustiva. Complejidad $O(N^2)$. Máxima precisión, recomendado para infraestructuras críticas.</li>
                <li><strong className="text-purple-400">Robergorithm V3:</strong> Exhaustivo optimizado. Complejidad $O(N \log N)$. Balance perfecto entre rendimiento en memoria y precisión.</li>
              </ul>
            </div>
          </div>
        </div>
        
        <div className="relative">
          <select 
            value={params.algorithm_type} 
            onChange={(e) => handleChange('algorithm_type', e.target.value)}
            className="w-full p-3 border border-slate-200 rounded-xl text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 appearance-none cursor-pointer transition-all hover:border-blue-300"
          >
            <option value="guangorithm">Guangorithm (Fast Heuristic)</option>
            <option value="robergorithm_v2">Robergorithm V2 (Exhaustive)</option>
            <option value="robergorithm_v3">Robergorithm V3 (Optimized)</option>
          </select>
          {/* Flecha personalizada */}
          <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none text-slate-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" /></svg>
          </div>
        </div>
      </div>

      {/* --- PARÁMETROS MATEMÁTICOS --- */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">C_MIN</label>
          <input type="number" value={params.c_min} onChange={(e) => handleChange('c_min', e.target.value)} className="w-full p-3 border border-slate-200 rounded-xl text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50" />
        </div>
        <div className="space-y-2">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">C_MAX</label>
          <input type="number" value={params.c_max} onChange={(e) => handleChange('c_max', e.target.value)} className="w-full p-3 border border-slate-200 rounded-xl text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50" />
        </div>
        <div className="space-y-2">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">L_MAX (ms)</label>
          <input type="number" value={params.l_max} onChange={(e) => handleChange('l_max', e.target.value)} className="w-full p-3 border border-slate-200 rounded-xl text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50" />
        </div>
        <div className="space-y-2">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">L_EXTRA (ms)</label>
          <input type="number" value={params.l_extra} onChange={(e) => handleChange('l_extra', e.target.value)} className="w-full p-3 border border-slate-200 rounded-xl text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50" />
        </div>
      </div>
      <div className="space-y-2">
        <label className="block text-[10px] font-bold text-slate-400 uppercase">Threshold (%)</label>
        <div className="relative flex items-center">
          <input type="number" value={params.threshold} onChange={(e) => handleChange('threshold', e.target.value)} className="w-full p-3 border border-slate-200 rounded-xl text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 pr-10" />
          <span className="absolute right-4 text-slate-400 text-sm font-bold">%</span>
        </div>
      </div>
    </div>
  );
}