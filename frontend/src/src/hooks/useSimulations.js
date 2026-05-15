import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL;

export function useSimulations() {
  const [migrations, setMigrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 1. Carga inicial de datos
  useEffect(() => {
    fetch(API_BASE)
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch initial data");
        return res.json();
      })
      .then(data => {
        setMigrations(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading list:", err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // 2. Conexión a Server-Sent Events (SSE)
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/events/stream`);

    sse.onmessage = async (event) => {
      const update = JSON.parse(event.data);

      // 1. Si el nuevo estado es 'error' o 'failed', pedimos los datos frescos al backend
      if (update.status === 'error' || update.status === 'failed') {
        try {
          const res = await fetch(`${API_BASE}/${update.id}`);
          const freshData = await res.json();

          // Actualizamos la lista con el objeto completo (incluyendo el error_message real)
          setMigrations(prev => prev.map(m => m.id === update.id ? freshData : m));
        } catch (err) {
          console.error("Error al refrescar detalle tras fallo:", err);
        }
      } else {
        // 2. Si es 'running' o 'completed', simplemente actualizamos el estado como antes
        setMigrations(prev => prev.map(m =>
          m.id === update.id ? { ...m, status: update.status } : m
        ));
      }
    };

    sse.onerror = () => {
      console.error("SSE connection error.");
      // Aquí en un futuro podrías implementar lógica de reconexión
    };

    return () => sse.close();
  }, []);

  // 3. Métodos mutadores
  const createMigration = async (formData) => {
    const res = await fetch(API_BASE, {
      method: 'POST',
      body: formData 
    });
    if (!res.ok) throw new Error("Creation error");
    const newSim = await res.json();
    setMigrations(prev => [newSim, ...prev]);
    return newSim;
  };

  const deleteMigration = async (id) => {
    await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
    setMigrations(prev => prev.filter(m => m.id !== id));
  };

  return { 
    migrations, 
    loading, 
    error, 
    createMigration, 
    deleteMigration 
  };
}