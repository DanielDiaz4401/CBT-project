import React, { useState, useEffect } from 'react';
import WelcomeScreen from './WelcomeScreen';
import MigrationList from './MigrationList';
import SetupModal from './SetupModal';
import MigrationDetail from './MigrationDetail';

const API_BASE = 'http://localhost:8000/simulations';

export default function Dashboard() {
  const [view, setView] = useState('welcome');
  const [migrations, setMigrations] = useState([]);
  const [selectedMigration, setSelectedMigration] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [migrationTemplate, setMigrationTemplate] = useState(null);

  const handleNewMigration = () => {
    setMigrationTemplate(null); // Limpio
    setIsModalOpen(true);
  };

  // 1. Carregar dades inicials de la llista (simulations.json)
  useEffect(() => {
    fetch(API_BASE + '/')
      .then(res => res.json())
      .then(data => setMigrations(data))
      .catch(err => console.error("Error cargando lista:", err));
  }, []);

  // 2. Guardar a LocalStorage
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/stream`);

    sse.onmessage = (event) => {
      const update = JSON.parse(event.data);
      console.log("Update de estado recibido:", update);

      setMigrations(prev => prev.map(m =>
        m.id === update.id ? { ...m, status: update.status } : m
      ));

      // Si la simulación seleccionada se ha completado, actualizamos su estado
      if (selectedMigration && selectedMigration.id === update.id) {
        setSelectedMigration(prev => ({ ...prev, status: update.status }));
      }
    };

    sse.onerror = () => {
      console.error("Error en conexión SSE. Reintentando...");
    };

    return () => sse.close();
  }, [selectedMigration]);

  // 3. Funció de creació simulant el POST al backend
  const handleConfirmSetup = async (formData) => {
    setIsCalculating(true);
    try {
      const res = await fetch(`${API_BASE}/calculate`, {
        method: 'POST',
        body: formData // Ya viene como FormData del SetupModal
      });

      if (!res.ok) throw new Error("Error en la creación");

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
    console.log("Entrant al detall de:", migration.name);
    console.log("Dades enviades al detall:", migration.result);
    setSelectedMigration(migration);
    setView('detail');
  };

  const handleDeleteMigration = async (id) => {
    if (window.confirm("¿Seguro que quieres borrar esta simulación?")) {
      try {
        await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
        setMigrations(prev => prev.filter(m => m.id !== id));
      } catch (err) {
        console.error("No se pudo borrar:", err);
      }
    }
  };

  const handleCloneMigration = (migration) => {
    // Aquí podrías necesitar un fetch adicional si el objeto 'migration' 
    // de la lista no trae todos los parámetros técnicos (l_max, c_min, etc.)
    setMigrationTemplate(migration);
    setIsModalOpen(true);
  };

  // RENDERITZAT CONDICIONAL SEGUR (Cap canvi visual aquí)
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