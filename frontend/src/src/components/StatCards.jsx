import React from 'react';

export default function StatCards({ migrations }) {
  const total = migrations.length;
  const completed = migrations.filter(m => m.status === 'completed').length;
  const running = migrations.filter(m => m.status === 'running').length;
  const pending = migrations.filter(m => m.status === 'pending').length;
  const failed = migrations.filter(m => m.status === 'failed').length;
  const error = migrations.filter(m => m.status === 'error').length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-10">
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total</p>
        <p className="text-2xl font-bold text-slate-900">{total}</p>
      </div>
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-slate-400">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Pending</p>
        <p className="text-2xl font-bold text-slate-900">{pending}</p>
      </div>
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-blue-500">
        <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-1">Running</p>
        <p className="text-2xl font-bold text-slate-900">{running}</p>
      </div>
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-emerald-500">
        <p className="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-1">Completed</p>
        <p className="text-2xl font-bold text-slate-900">{completed}</p>
      </div>
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-amber-500">
        <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-1">Failed</p>
        <p className="text-2xl font-bold text-slate-900">{failed}</p>
      </div>
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-red-500">
        <p className="text-[10px] font-black text-red-500 uppercase tracking-widest mb-1">Error</p>
        <p className="text-2xl font-bold text-slate-900">{error}</p>
      </div>
    </div>
  );
}