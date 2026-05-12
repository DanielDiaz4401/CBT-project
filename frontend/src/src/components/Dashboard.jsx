import React, { useState } from 'react';
import WelcomeScreen from './WelcomeScreen';
import MigrationList from './MigrationList';
import SetupModal from './SetupModal';
import MigrationDetail from './MigrationDetail';
import MigrationCompare from './MigrationCompare'; 
import { useSimulations } from '../hooks/useSimulations'; // <-- Importamos nuestro hook

export default function Dashboard() {
  // Consumimos la capa de red
  const { migrations, loading, createMigration, deleteMigration } = useSimulations();

  // Estados exclusivos de UI y navegación
  const [view, setView] = useState('welcome');
  const [selectedMigrationId, setSelectedMigrationId] = useState(null); // <-- Guardamos el ID, no el objeto
  const [selectedForCompareIds, setSelectedForCompareIds] = useState([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [migrationTemplate, setMigrationTemplate] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);

  // Derivamos el estado: Single Source of Truth
  // Al buscar el objeto directamente en la lista, si el SSE actualiza la lista, 
  // las vistas de detalle y comparación se actualizan automáticamente.
  const selectedMigration = migrations.find(m => m.id === selectedMigrationId) || null;
  const selectedForCompare = migrations.filter(m => selectedForCompareIds.includes(m.id));

  const handleNewMigration = () => {
    setMigrationTemplate(null); 
    setIsModalOpen(true);
  };

  const handleConfirmSetup = async (formData) => {
    setIsCalculating(true);
    try {
      await createMigration(formData); // Usamos el método abstraído
      setIsModalOpen(false);
    } catch (error) {
      alert("Error: " + error.message);
    } finally {
      setIsCalculating(false);
    }
  };

  const handleViewDetail = (migration) => {
    setSelectedMigrationId(migration.id);
    setView('detail');
  };

  const handleCompare = (ids) => {
    setSelectedForCompareIds(ids);
    setView('compare');
  };

  const handleDeleteMigration = async (id) => {
    if (window.confirm("Are you sure you want to delete this simulation?")) {
      try {
        await deleteMigration(id); // Usamos el método abstraído
      } catch (err) {
        console.error("Failed to delete:", err);
      }
    }
  };

  const handleCloneMigration = (migration) => {
    setMigrationTemplate(migration);
    setIsModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {view === 'welcome' && (
        <WelcomeScreen onStart={() => setView('list')} />
      )}

      {view === 'list' && (
        <MigrationList
          migrations={migrations}
          onNewMigration={handleNewMigration}
          onCloneMigration={handleCloneMigration}
          onViewDetail={handleViewDetail}
          onDeleteMigration={handleDeleteMigration}
          onCompare={handleCompare} 
        />
      )}

      {view === 'compare' && (
        <MigrationCompare 
          selectedMigrations={selectedForCompare} 
          onBack={() => setView('list')} 
        />
      )}

      {view === 'detail' && selectedMigration && (
        <MigrationDetail
          migration={selectedMigration}
          onBack={() => {
            setSelectedMigrationId(null);
            setView('list');
          }}
        />
      )}

      {isModalOpen && (
        <SetupModal
          templateData={migrationTemplate}
          onClose={() => setIsModalOpen(false)}
          onConfirm={handleConfirmSetup}
          isCalculating={isCalculating}
        />
      )}
    </div>
  );
}