import React from 'react';

export default function WelcomeScreen({ onStart }) {
  return (
    <div className="relative h-screen w-full flex flex-col items-center justify-center overflow-hidden bg-[#f8fafc]">
      {/* Graf de fons decoratiu */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
              <circle cx="50" cy="50" r="2" fill="#00609b" />
              <line x1="50" y1="50" x2="150" y2="50" stroke="#00609b" strokeWidth="0.5" />
              <line x1="50" y1="50" x2="50" y2="150" stroke="#00609b" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <div className="relative z-10 text-center px-6 flex flex-col items-center">
        <div className="mb-10 flex justify-center w-full">
          <img 
            src="/Logo-CaixaBank-Tech.png" 
            alt="CaixaBank Tech" 
            className="h-20 w-auto block object-contain"
          />
        </div>

        <div className="mb-6">
          <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight mb-4">
            Cloud Migration <span className="text-blue-600">Strategy</span>
          </h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto mb-10">
            Optimize the migration of your components to the Cloud by calculating the critical path, 
            controlling latencies, and ensuring efficient stage management.
          </p>
        </div>

        <button
          onClick={onStart}
          className="group relative inline-flex items-center justify-center px-8 py-4 font-bold text-white transition-all duration-200 bg-blue-600 rounded-xl hover:bg-blue-700 shadow-xl hover:shadow-blue-200 active:scale-95"
        >
          Start New Migration
          <svg className="w-5 h-5 ml-3 transition-transform duration-200 group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
      </div>

      <div className="absolute bottom-8 text-slate-400 text-sm font-medium">
        © 2026 CaixaBank TECH - Migration Interface for Eficient Relocation and Deployitment Analysis
      </div>
    </div>
  );
}