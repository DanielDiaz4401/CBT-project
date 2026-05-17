import React from 'react';
import { ChevronLeft } from 'lucide-react';

export default function AlgorithmInformation({ setShowAlgoInfo }) {
  return (
    <div className="absolute inset-0 z-30 bg-white overflow-y-auto animate-in fade-in zoom-in-95 duration-200">
      
      {/* HEADER FIJO (Se queda pegado arriba al hacer scroll) */}
      <div className="sticky top-0 bg-white/90 backdrop-blur-md border-b border-slate-100 px-8 py-4 z-10">
        <button 
          onClick={() => setShowAlgoInfo(false)}
          className="flex items-center gap-2 text-blue-600 font-bold hover:text-blue-700 transition-colors w-max"
        >
          <ChevronLeft size={20} /> Volver a Configuración
        </button>
      </div>

      {/* CONTENIDO TIPO "DOCUMENTO / MARKDOWN" */}
      <div className="p-8 md:p-12">
        <div className="max-w-4xl mx-auto w-full text-slate-700 space-y-12">
          
          {/* Título Principal */}
          <div>
             <h2 className="text-3xl font-black text-slate-900 mb-4">Información de Motores Algorítmicos</h2>
             <p className="text-slate-600 leading-relaxed text-lg">
               A continuación se detalla el funcionamiento interno, ventajas y estrategias de mitigación de latencia de cada uno de los motores de resolución disponibles en la plataforma.
             </p>
          </div>
          
          {/* SECCIÓN: Guangorithm */}
          <section className="space-y-4">
             <h3 className="text-2xl font-bold text-slate-800 border-b border-slate-200 pb-2">Guangorithm (Leiden CPM)</h3>
             <p className="leading-relaxed">
               Optimización basada en comunidades estructurales. Utiliza el algoritmo de Leiden con resolución CPM para agrupar componentes con alta afinidad de latencia antes de planificar las etapas.
             </p>
             
             {/* Placeholder para Markdown futuro */}
             <div className="bg-slate-50 p-6 rounded-xl border-2 border-dashed border-slate-200 font-mono text-sm text-slate-500">
               [ Espacio preparado para futuras fórmulas matemáticas o tablas de complejidad ]
             </div>
             
             <ul className="list-disc pl-5 space-y-1 font-medium text-slate-600">
               <li>Alta cohesión estructural</li>
               <li>Ideal para sistemas con alta densidad de microservicios</li>
             </ul>
          </section>

          {/* SECCIÓN: Robergorithm V2 */}
          <section className="space-y-4">
             <h3 className="text-2xl font-bold text-slate-800 border-b border-slate-200 pb-2">Robergorithm V2</h3>
             <p className="leading-relaxed">
               Enfoque heurístico basado en el camino crítico. Prioriza la migración de componentes que eliminan cruces de frontera (cross-boundary) en las rutas de mayor latencia.
             </p>
             <ul className="list-disc pl-5 space-y-1 font-medium text-slate-600">
               <li>Reactivo al estado actual del grafo</li>
               <li>Estrategia de reducción agresiva de latencia</li>
             </ul>
          </section>
          
          {/* SECCIÓN: Robergorithm V3 */}
          <section className="space-y-4">
             <h3 className="text-2xl font-bold text-slate-800 border-b border-slate-200 pb-2">Robergorithm V3 (Branches)</h3>
             <p className="leading-relaxed">
               Versión avanzada que evalúa no solo el camino crítico principal, sino todas las ramas (branches) desde la raíz hasta las hojas para evitar cuellos de botella secundarios o "efectos sándwich".
             </p>
             <ul className="list-disc pl-5 space-y-1 font-medium text-slate-600">
               <li>Máxima seguridad en el cumplimiento de requisitos (Compliance)</li>
               <li>Control estricto de bifurcaciones en el árbol de dependencias</li>
             </ul>
          </section>

          {/* Espacio extra al final para scroll holgado */}
          <div className="h-12"></div>
        </div>
      </div>
    </div>
  );
}