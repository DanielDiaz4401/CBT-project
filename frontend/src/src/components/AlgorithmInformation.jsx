import React from 'react';
import { ChevronLeft, Cpu, Network, Route, Zap, ShieldCheck } from 'lucide-react';

export default function AlgorithmInformation({ setShowAlgoInfo }) {
  return (
    <div className="absolute inset-0 z-30 bg-slate-50 overflow-y-auto animate-in fade-in zoom-in-95 duration-200">
      
      {/* STICKY HEADER */}
      <div className="sticky top-0 bg-white/90 backdrop-blur-md border-b border-slate-200 px-8 py-5 z-10 flex justify-between items-center shadow-sm">
        <button 
          onClick={() => setShowAlgoInfo(false)}
          className="flex items-center gap-2 text-blue-600 font-bold hover:text-blue-800 transition-colors w-max"
        >
          <ChevronLeft size={20} /> Back to Setup
        </button>
        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-100 px-3 py-1 rounded-full">
          Technical Documentation
        </span>
      </div>

      {/* WHITEPAPER CONTENT */}
      <div className="p-8 md:p-12 lg:p-16">
        <div className="max-w-4xl mx-auto w-full bg-white p-10 md:p-16 rounded-3xl shadow-xl border border-slate-100 text-slate-700 space-y-16">
          
          {/* Abstract / Header */}
          <header className="space-y-6 text-center border-b border-slate-100 pb-12">
             <h1 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
               Algorithmic Engines for Cloud Migration
             </h1>
             <p className="text-slate-500 text-lg md:text-xl leading-relaxed max-w-2xl mx-auto font-medium">
               A technical overview of the graph-theory based resolution engines designed to minimize cross-boundary latency during phased microservice migrations.
             </p>
          </header>

          {/* ENGINE 1: GUANGORITHM */}
          <section className="space-y-6">
             <div className="flex items-center gap-4 border-b border-slate-200 pb-4">
               <div className="p-3 bg-purple-100 text-purple-700 rounded-xl">
                 <Network size={28} strokeWidth={2.5} />
               </div>
               <div>
                 <h2 className="text-2xl font-black text-slate-900">Guangorithm</h2>
                 <p className="text-sm font-bold text-purple-600 uppercase tracking-widest">Leiden CPM Clustering</p>
               </div>
             </div>
             
             <div className="space-y-4 text-slate-600 leading-relaxed text-lg">
               <p>
                 The <strong>Guangorithm</strong> leverages community detection to preserve structural cohesion. It operates under the premise that microservices with high communication frequencies should be migrated together to prevent hybrid architecture bottlenecks.
               </p>
               <p>
                 Internally, it utilizes the <strong>Leiden algorithm</strong> with a Constant Potts Model (CPM) resolution parameter. By assigning edge weights based on base latency (<code>avg_time</code>), the engine partitions the directed acyclic graph (DAG) into isolated clusters. The migration scheduler then prioritizes nodes within the same cluster to be moved in parallel.
               </p>
             </div>

             <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200">
               <h4 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                 <ShieldCheck size={18} className="text-emerald-500" /> Ideal Use Case
               </h4>
               <p className="text-sm text-slate-600">
                 Best suited for <strong>highly dense, monolithic-like microservice architectures</strong> where structural coupling is severe. Use this engine when preventing architectural fragmentation is more important than optimizing a single specific latency path.
               </p>
             </div>
          </section>

          {/* ENGINE 2: ROBERGORITHM V2 */}
          <section className="space-y-6">
             <div className="flex items-center gap-4 border-b border-slate-200 pb-4">
               <div className="p-3 bg-blue-100 text-blue-700 rounded-xl">
                 <Zap size={28} strokeWidth={2.5} />
               </div>
               <div>
                 <h2 className="text-2xl font-black text-slate-900">Robergorithm V2</h2>
                 <p className="text-sm font-bold text-blue-600 uppercase tracking-widest">Greedy Cross-Boundary Heuristic</p>
               </div>
             </div>
             
             <div className="space-y-4 text-slate-600 leading-relaxed text-lg">
               <p>
                 <strong>Robergorithm V2</strong> is a greedy heuristic engine strictly focused on immediate latency reduction. It calculates a dynamic score for every pending node based on the mathematical delta of <code>L_extra</code> (the latency penalty incurred when crossing the On-Prem/Cloud boundary).
               </p>
               <p>
                 The algorithm evaluates the "Sandwich Effect"—situations where a cloud node invokes an on-prem node, which in turn invokes another cloud node. By scoring components based on <code>eliminated_jumps - new_jumps</code>, it aggressively prioritizes the migration of components that bridge these hybrid gaps.
               </p>
             </div>

             <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200">
               <h4 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                 <ShieldCheck size={18} className="text-emerald-500" /> Ideal Use Case
               </h4>
               <p className="text-sm text-slate-600">
                 Best suited for <strong>reactive optimizations</strong> and moderately coupled systems. Use this engine when you need aggressive, step-by-step reduction of current latency spikes without computing the full topological depth of the network.
               </p>
             </div>
          </section>

          {/* ENGINE 3: ROBERGORITHM V3 */}
          <section className="space-y-6">
             <div className="flex items-center gap-4 border-b border-slate-200 pb-4">
               <div className="p-3 bg-emerald-100 text-emerald-700 rounded-xl">
                 <Route size={28} strokeWidth={2.5} />
               </div>
               <div>
                 <h2 className="text-2xl font-black text-slate-900">Robergorithm V3</h2>
                 <p className="text-sm font-bold text-emerald-600 uppercase tracking-widest">Topological Sort Critical Path</p>
               </div>
             </div>
             
             <div className="space-y-4 text-slate-600 leading-relaxed text-lg">
               <p>
                 <strong>Robergorithm V3</strong> is the most mathematically rigorous engine in the suite. Instead of evaluating individual edges, it computes the absolute worst-case latency across all possible root-to-leaf paths in the network at every simulated stage.
               </p>
               <p>
                 It achieves this by dynamically breaking network cycles and applying a <strong>Topological Sort</strong>. As it traverses the sorted DAG, it propagates the maximum accumulated latency (including <code>L_extra</code> penalties) forward. A component is only approved for migration if its migration does not cause the topological worst-case path to exceed the <code>L_max</code> threshold.
               </p>
             </div>

             <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200">
               <h4 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                 <ShieldCheck size={18} className="text-emerald-500" /> Ideal Use Case
               </h4>
               <p className="text-sm text-slate-600">
                 Best suited for <strong>Strict Compliance Environments</strong> (e.g., Banking, Financial Services) where hard latency limits (SLAs) cannot be breached under any circumstance. Use this engine to guarantee maximum architectural safety.
               </p>
             </div>
          </section>

          {/* Summary Table */}
          <section className="pt-8 border-t border-slate-100">
            <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-6">Engine Comparison Matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 border-b border-slate-200">
                    <th className="p-4 font-bold rounded-tl-xl">Engine</th>
                    <th className="p-4 font-bold">Primary Mechanism</th>
                    <th className="p-4 font-bold">Speed</th>
                    <th className="p-4 font-bold rounded-tr-xl">Safety Guarantee</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-4 font-black">Guangorithm</td>
                    <td className="p-4">Leiden Community Detection</td>
                    <td className="p-4"><span className="text-orange-500 font-bold">Medium</span></td>
                    <td className="p-4">Structural Cohesion</td>
                  </tr>
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-4 font-black">Robergorithm V2</td>
                    <td className="p-4">Greedy Delta Heuristic</td>
                    <td className="p-4"><span className="text-emerald-500 font-bold">Fast</span></td>
                    <td className="p-4">Cross-Boundary Reduction</td>
                  </tr>
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-4 font-black">Robergorithm V3</td>
                    <td className="p-4">Topological Sort Path Evaluation</td>
                    <td className="p-4"><span className="text-orange-500 font-bold">Medium</span></td>
                    <td className="p-4">Strict SLA (L_max) Compliance</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}