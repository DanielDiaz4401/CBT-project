import React, { useState } from 'react';

export default function MigrationList({ migrations, onNewMigration, onViewDetail, onDeleteMigration }) {
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });

  // Contadores por estado
  const total = migrations.length;
  const completed = migrations.filter(m => m.status === 'completed').length;
  const running = migrations.filter(m => m.status === 'running').length;
  const pending = migrations.filter(m => m.status === 'pending').length;
  const failed = migrations.filter(m => m.status === 'failed').length;

  const toggleSelection = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const requestSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const sortedMigrations = React.useMemo(() => {
    let sortableItems = [...migrations];
    sortableItems.sort((a, b) => {
      // Manejo especial para la fecha (usamos created_at si existe, o date)
      if (sortConfig.key === 'date') {
        const dateA = new Date(a.created_at || a.date).getTime() || 0;
        const dateB = new Date(b.created_at || b.date).getTime() || 0;
        return sortConfig.direction === 'asc' ? dateA - dateB : dateB - dateA;
      }

      // Ordenación estándar para texto (nombre, status)
      const valA = (a[sortConfig.key] || '').toString().toLowerCase();
      const valB = (b[sortConfig.key] || '').toString().toLowerCase();
      
      if (valA < valB) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (valA > valB) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
    return sortableItems;
  }, [migrations, sortConfig]);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Migrations Dashboard</h1>
          <p className="text-slate-500">Manage and monitor your cloud strategy</p>
        </div>

        <div className="flex gap-3">
          {isSelectMode && selectedIds.length >= 2 && (
            <button
              onClick={() => alert(`Comparing migrations: ${selectedIds.join(', ')}`)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg font-bold text-sm shadow-lg hover:bg-blue-700 transition-all"
            >
              Compare Selected ({selectedIds.length})
            </button>
          )}
          <button
            onClick={() => setIsSelectMode(!isSelectMode)}
            className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${isSelectMode ? 'bg-slate-800 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}`}
          >
            {isSelectMode ? 'Cancel Selection' : 'Select to Compare'}
          </button>
          <button
            onClick={onNewMigration}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-bold text-sm shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all"
          >
            + New Migration
          </button>
        </div>
      </div>

      {/* Grid de 5 Contadores */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total</p>
          <p className="text-2xl font-bold text-slate-900">{total}</p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-emerald-500">
          <p className="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-1">Completed</p>
          <p className="text-2xl font-bold text-slate-900">{completed}</p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-blue-500">
          <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-1">Running</p>
          <p className="text-2xl font-bold text-slate-900">{running}</p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-amber-500">
          <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-1">Pending</p>
          <p className="text-2xl font-bold text-slate-900">{pending}</p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm border-l-4 border-l-red-500">
          <p className="text-[10px] font-black text-red-500 uppercase tracking-widest mb-1">Failed</p>
          <p className="text-2xl font-bold text-slate-900">{failed}</p>
        </div>
      </div>

      {/* Tabla con scroll interno y clases estándar de Tailwind */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="max-h-150 overflow-y-auto">
          <table className="w-full text-left relative">
            <thead className="bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
              <tr>
                {isSelectMode && <th className="p-4 w-10"></th>}
                <th
                  onClick={() => requestSort('name')}
                  className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:bg-slate-100 transition-colors select-none"
                >
                  <div className="flex items-center gap-1">
                    Simulation Name
                    {sortConfig.key === 'name' && (<span>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>)}
                  </div>
                </th>
                <th
                  onClick={() => requestSort('date')}
                  className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:bg-slate-100 transition-colors select-none"
                >
                  <div className="flex items-center gap-1">
                    Date
                    {sortConfig.key === 'date' && (<span>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>)}
                  </div>
                </th>
                <th
                  onClick={() => requestSort('status')}
                  className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:bg-slate-100 transition-colors select-none"
                >
                  <div className="flex items-center gap-1">
                    Status
                    {sortConfig.key === 'status' && (<span>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>)}
                  </div>
                </th>
                <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedMigrations.map((m) => (
                <tr key={m.id} className={`hover:bg-slate-50 transition-colors ${selectedIds.includes(m.id) ? 'bg-blue-50/50' : ''}`}>
                  {isSelectMode && (
                    <td className="p-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(m.id)}
                        onChange={() => toggleSelection(m.id)}
                        className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                  )}
                  <td className="p-4">
                    <p className="font-bold text-slate-800">{m.name}</p>
                    {m.status === 'failed' && (
                      <div className="group relative">
                        <p className="text-[10px] text-red-600 font-medium italic truncate max-w-50 cursor-help">
                          {m.error_message}
                        </p>
                        <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 w-100 p-4 bg-slate-900 text-white text-[10px] rounded-xl shadow-2xl font-mono whitespace-pre-wrap break-all border border-slate-700 pointer-events-none transition-all">
                          <div className="text-red-400 font-black mb-2 uppercase tracking-widest text-[9px] border-b border-slate-700 pb-1">
                            Full Error Detail
                          </div>
                          {m.error_message}
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {m.created_at
                      ? new Date(m.created_at).toLocaleString()
                      : (m.date ? new Date(m.date).toLocaleString() : 'N/A')}
                  </td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                      m.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                      m.status === 'failed' ? 'bg-red-100 text-red-700' :
                      m.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                      'bg-blue-100 text-blue-700 animate-pulse'
                    }`}>
                      {m.status}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end items-center gap-4">
                      <button onClick={() => onDeleteMigration(m.id)} className="text-slate-300 hover:text-red-600 transition-colors p-1">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                      <button onClick={() => onViewDetail(m)} className="text-blue-600 hover:text-blue-800 font-bold text-sm">
                        View Report
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {migrations.length === 0 && (
            <div className="p-20 text-center text-slate-400">
              No migrations found. Start a new one.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}