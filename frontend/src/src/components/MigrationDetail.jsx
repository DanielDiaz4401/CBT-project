import React, { useState } from 'react';
import VisualizeStages from './VisualizeStages';
import VisualizeGraph from './VisualizeGraph';  
import ExportStages from './ExportStages';

export default function MigrationDetail({ migration, onBack }) {
  const [activeTab, setActiveTab] = useState('statistics');

  if (!migration) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="text-center p-10 bg-white shadow-xl rounded-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-500 font-bold">Loading migration data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans">
      <div className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M15 19l-7-7 7-7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <div>
            <h1 className="text-xl font-black text-slate-900 leading-none">{migration.name}</h1>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
              {new Date(migration.created_at || migration.date).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex bg-slate-100 p-1 rounded-2xl border border-slate-200">
          <button onClick={() => setActiveTab('statistics')} className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${activeTab === 'statistics' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Visualize Statistics</button>
          <button onClick={() => setActiveTab('graph')} className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${activeTab === 'graph' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Visualize Graph</button>
          <button onClick={() => setActiveTab('export')} className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${activeTab === 'export' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Export Data</button>
        </div>
        <div className="w-32"></div>
      </div>

      <div className="flex-1 overflow-hidden p-6">
        <div className="bg-white rounded-3xl shadow-xl border border-slate-200 h-full overflow-hidden flex flex-col">
          {activeTab === 'statistics' && <VisualizeStages migration={migration} />}
          {activeTab === 'graph' && <VisualizeGraph migration={migration} />}
          {activeTab === 'export' && <ExportStages migration={migration} />}
        </div>
      </div>
    </div>
  );
}