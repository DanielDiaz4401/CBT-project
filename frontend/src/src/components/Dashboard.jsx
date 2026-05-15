import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast'; // <-- 1. Importamos la librería
import WelcomeScreen from './WelcomeScreen';
import MigrationList from './MigrationList';
import SetupModal from './SetupModal';
import MigrationDetail from './MigrationDetail';
import MigrationCompare from './MigrationCompare'; 

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL;

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

  useEffect(() => {
    fetch(API_BASE)
      .then(res => res.json())
      .then(data => setMigrations(data))
      .catch(err => {
        console.error("Error loading list:", err);
        toast.error("Could not connect to the server."); // <-- Feedback de error de red
      });
  }, []);

useEffect(() => {
    const sse = new EventSource(`${API_BASE}/events/stream`);

    sse.onmessage = async (event) => {
      const update = JSON.parse(event.data);

      // Si la simulación ha fallado, pedimos a la API el objeto completo 
      // para traer el 'error_message' que el backend guardó en la base de datos.
      if (update.status === 'error' || update.status === 'failed') {
        try {
          const res = await fetch(`${API_BASE}/${update.id}`);
          if (!res.ok) throw new Error("Failed to fetch fresh data");
          const freshData = await res.json();
          
          setMigrations(prev => prev.map(m =>
            m.id === update.id ? freshData : m
          ));

          if (selectedMigration && selectedMigration.id === update.id) {
            setSelectedMigration(freshData);
          }
        } catch (err) {
          console.error("Error al refrescar detalle tras fallo:", err);
        }
      } else {
        // Si todo va bien (running o completed), solo actualizamos el status para no saturar la red
        setMigrations(prev => prev.map(m =>
          m.id === update.id ? { ...m, status: update.status } : m
        ));

        if (selectedMigration && selectedMigration.id === update.id) {
          setSelectedMigration(prev => ({ ...prev, status: update.status }));
        }
      }
    };

    sse.onerror = () => {
      console.error("SSE connection error.");
    };

    return () => sse.close();
  }, [selectedMigration]);

  const handleConfirmSetup = async (formData) => {
    setIsCalculating(true);
    // <-- Iniciamos un toast en estado de "carga"
    const loadingToast = toast.loading('Starting migration simulation...'); 
    
    try {
      const res = await fetch(`${API_BASE}`, {
        method: 'POST',
        body: formData 
      });
      if (!res.ok) throw new Error("Server rejected the request");
      
      const newSim = await res.json();
      setMigrations(prev => [newSim, ...prev]);
      setIsModalOpen(false);
      
      // <-- Actualizamos el toast a "éxito"
      toast.success('Migration started successfully!', { id: loadingToast }); 
    } catch (error) {
      console.error(error);
      // <-- Actualizamos el toast a "error"
      toast.error(`Creation failed: ${error.message}`, { id: loadingToast }); 
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

const handleDeleteMigration = (id) => {
    // 1. Lanzamos un toast personalizado y persistente (duration: Infinity)
    toast((t) => (
      <div className="flex flex-col gap-3 min-w-[250px]">
        <div className="flex items-start gap-3">
          <div className="text-amber-500 bg-amber-50 p-1.5 rounded-lg">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800">Confirm Deletion</p>
            <p className="text-xs text-slate-500 mt-1">This action cannot be undone. All stage data will be lost.</p>
          </div>
        </div>
        
        {/* 2. Botones de acción dentro del toast */}
        <div className="flex gap-2 justify-end mt-2">
          <button 
            onClick={() => toast.dismiss(t.id)} 
            className="px-3 py-2 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={async () => {
              // Cerramos el diálogo de confirmación
              toast.dismiss(t.id);
              
              // Iniciamos el flujo de red (igual que antes)
              const loadingToast = toast.loading('Deleting simulation...', {
                style: { background: '#1e293b', color: '#fff' }
              });
              try {
                await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
                setMigrations(prev => prev.filter(m => m.id !== id));
                toast.success('Simulation deleted successfully.', { id: loadingToast });
              } catch (err) {
                console.error("Failed to delete:", err);
                toast.error('Failed to delete simulation.', { id: loadingToast });
              }
            }} 
            className="px-3 py-2 text-xs font-bold text-white bg-red-500 hover:bg-red-600 shadow-md shadow-red-200 rounded-lg transition-colors"
          >
            Yes, Delete
          </button>
        </div>
      </div>
    ), {
      duration: Infinity, // Evita que se cierre solo
      style: {
        background: '#fff', // Forzamos fondo blanco para que resalte sobre el tema oscuro de tus otros toasts
        color: '#0f172a',
        padding: '16px',
        maxWidth: '400px',
        border: '1px solid #e2e8f0',
        boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)'
      }
    });
  };

  const handleCloneMigration = (migration) => {
    setMigrationTemplate(migration);
    setIsModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* 2. Inyectamos el Toaster globalmente en la app */}
      <Toaster 
        position="bottom-right" 
        toastOptions={{
          style: {
            borderRadius: '12px',
            background: '#1e293b',
            color: '#fff',
            fontSize: '14px',
            fontWeight: 'bold'
          },
        }} 
      />

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