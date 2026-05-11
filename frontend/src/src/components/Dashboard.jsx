import React, { useState, useEffect } from 'react';
import WelcomeScreen from './WelcomeScreen';
import MigrationList from './MigrationList';
import SetupModal from './SetupModal';
import MigrationDetail from './MigrationDetail';
import MigrationCompare from './MigrationCompare'; // 1. Importamos el nuevo componente

const API_BASE = 'http://localhost:8000/simulations';

export default function Dashboard() {
  const [view, setView] = useState('welcome');
  const [migrations, setMigrations] = useState([]);
  const [showSetup, setShowSetup] = useState(false);
  const [selectedMigration, setSelectedMigration] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  
  // 2. Estado para guardar qué migraciones se van a comparar
  const [selectedForCompare, setSelectedForCompare] = useState([]);

  // 1. Carregar dades inicials de la llista
  useEffect(() => {
    fetch(API_BASE + '/')
      .then(res => res.json())
      .then(data => setMigrations(data))
      .catch(err => console.error("Error cargando lista:", err));
  }, []);

  // 2. SSE para actualizaciones en tiempo real
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/stream`);

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
      console.error("Error en conexión SSE.");
    };

    return () => sse.close();
  }, [selectedMigration]);

  const handleConfirmSetup = async (formData) => {
    setIsCalculating(true);
    try {
      const res = await fetch(`${API_BASE}/calculate`, {
        method: 'POST',
        body: formData 
      });
      if (!res.ok) throw new Error("Error en la creación");
      const newSim = await res.json();
      setMigrations(prev => [newSim, ...prev]);
      setShowSetup(false);
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

  // 3. Función para activar la vista de comparación
  const handleCompare = (ids) => {
    const selected = migrations.filter(m => ids.includes(m.id));
    setSelectedForCompare(selected);
    setView('compare');
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

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {view === 'welcome' && (
        <WelcomeScreen onStart={() => setView('list')} />
      )}

      {view === 'list' && (
        <MigrationList
          migrations={migrations}
          onNewMigration={() => setShowSetup(true)}
          onViewDetail={handleViewDetail}
          onDeleteMigration={handleDeleteMigration}
          onCompare={handleCompare} // 4. Pasamos la función a la lista
        />
      )}

      {/* 5. Nueva vista de comparación */}
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

      {showSetup && (
        <SetupModal
          onClose={() => setShowSetup(false)}
          onConfirm={handleConfirmSetup}
          isCalculating={isCalculating}
        />
      )}
    </div>
  );
}