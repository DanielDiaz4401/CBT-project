import React from 'react';

export default function AlgorithmParamsForm({ params, setParams }) {
  const handleChange = (key, value) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6">
      <h3 className="text-xs font-bold text-blue-600 uppercase tracking-widest">3. Algorithm</h3>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">C_MIN</label>
          <input type="number" value={params.c_min} onChange={(e) => handleChange('c_min', e.target.value)} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none bg-slate-50" />
        </div>
        <div className="space-y-1.5">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">C_MAX</label>
          <input type="number" value={params.c_max} onChange={(e) => handleChange('c_max', e.target.value)} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none bg-slate-50" />
        </div>
        <div className="space-y-1.5">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">L_MAX (ms)</label>
          <input type="number" value={params.l_max} onChange={(e) => handleChange('l_max', e.target.value)} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none bg-slate-50" />
        </div>
        <div className="space-y-1.5">
          <label className="block text-[10px] font-bold text-slate-400 uppercase">L_EXTRA (ms)</label>
          <input type="number" value={params.l_extra} onChange={(e) => handleChange('l_extra', e.target.value)} className="w-full p-2.5 border border-slate-200 rounded-lg text-sm outline-none bg-slate-50" />
        </div>
      </div>
      <div className="space-y-1.5">
        <label className="block text-[10px] font-bold text-slate-400 uppercase">Threshold (%)</label>
        <div className="relative flex items-center">
          <input type="number" value={params.umbral} onChange={(e) => handleChange('umbral', e.target.value)} className="w-full p-3 border border-slate-200 rounded-lg text-sm outline-none bg-slate-50 pr-10" />
          <span className="absolute right-4 text-slate-400 text-sm font-bold">%</span>
        </div>
      </div>
    </div>
  );
}