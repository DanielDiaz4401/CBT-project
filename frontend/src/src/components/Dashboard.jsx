import React, { useState, useEffect } from 'react';
import WelcomeScreen from './WelcomeScreen';
import MigrationList from './MigrationList';
import SetupModal from './SetupModal';
import MigrationDetail from './MigrationDetail';
import MigrationCompare from './MigrationCompare'; 

const API_BASE = 'http://localhost:8000/simulations';

export default function Dashboard() {
  const [view, setView] = useState('welcome');
  const [migrations, setMigrations] = useState([]);
  const [selectedMigration, setSelectedMigration] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [migrationTemplate, setMigrationTemplate] = useState(null);
  const [selectedForCompare, setSelectedForCompare] = useState([]);

  const handleNewMigration = () => {
    setMigrationTemplate(null); 
    setIsModalOpen(true);
  };

  // 1. Load initial list data
  useEffect(() => {
    fetch(API_BASE)
      .then(res => res.json())
      .then(data => setMigrations(data))
      .catch(err => console.error("Error loading list:", err));
  }, []);

  // 2. SSE for real-time updates
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/events/stream`);

    sse.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setMigrations(prev => prev.map(m =>
        m.id === update.id ? { ...m, status: update.status } : m
      ));

      if (selectedMigration && selectedMigration.id === update.id) {
        setSelectedMigration(prev => ({ ...prev, status: update.status }));
      }
    };

    sse.onerror = () => {
      console.error("SSE connection error.");
    };

    return () => sse.close();
  }, [selectedMigration]);

  const handleConfirmSetup = async (formData) => {
    setIsCalculating(true);
    try {
      const res = await fetch(`${API_BASE}`, {
        method: 'POST',
        body: formData 
      });
      if (!res.ok) throw new Error("Creation error");
      const newSim = await res.json();
      setMigrations(prev => [newSim, ...prev]);
      setIsModalOpen(false);
    } catch (error) {
      alert("Error: " + error.message);
    } finally {
      setIsCalculating(false);
    }
  };

  const handleViewDetail = (migration) => {
    setSelectedMigration(migration);
    setView('detail');
  };

  const handleCompare = (ids) => {
    const selected = migrations.filter(m => ids.includes(m.id));
    setSelectedForCompare(selected);
    setView('compare');
  };

  const handleDeleteMigration = async (id) => {
    if (window.confirm("Are you sure you want to delete this simulation?")) {
      try {
        await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
        setMigrations(prev => prev.filter(m => m.id !== id));
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
            setSelectedMigration(null);
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