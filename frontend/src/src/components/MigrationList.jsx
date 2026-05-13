import React, { useState } from 'react';
import StatCards from './StatCards';
import SimulationsTable from './SimulationsTable';

export default function MigrationList({ migrations, onNewMigration, onCloneMigration, onViewDetail, onDeleteMigration, onCompare }) {
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);

  const toggleSelection = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Migrations Dashboard</h1>
          <p className="text-slate-500">Manage and monitor your cloud strategy</p>
        </div>
        <div className="flex gap-3">
          {isSelectMode && selectedIds.length >= 2 && (
            <button onClick={() => onCompare(selectedIds)} className="px-4 py-2 bg-blue-600 text-white rounded-lg font-bold text-sm shadow-lg">
              Compare Selected ({selectedIds.length})
            </button>
          )}
          <button onClick={() => setIsSelectMode(!isSelectMode)} className={`px-4 py-2 rounded-lg font-bold text-sm ${isSelectMode ? 'bg-slate-800 text-white' : 'bg-slate-200 text-slate-700'}`}>
            {isSelectMode ? 'Cancel Selection' : 'Select to Compare'}
          </button>
          <button onClick={onNewMigration} className="px-6 py-2 bg-blue-600 text-white rounded-lg font-bold text-sm shadow-lg shadow-blue-200">
            + New Migration
          </button>
        </div>
      </div>

      <StatCards migrations={migrations} />
      
      <SimulationsTable 
        migrations={migrations}
        isSelectMode={isSelectMode}
        selectedIds={selectedIds}
        onToggleSelection={toggleSelection}
        onClone={onCloneMigration}
        onDelete={onDeleteMigration}
        onViewDetail={onViewDetail}
      />
    </div>
  );
}