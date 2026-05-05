import React from 'react';
import { Pill } from 'lucide-react';

const Header = ({ onLogoClick }) => {
  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200 px-6 py-3 shadow-sm">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <button 
          onClick={onLogoClick}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
        >
          <div className="bg-gradient-to-br from-primary-500 to-primary-700 p-2.5 rounded-xl shadow-md">
            <Pill className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              MedPak <span className="text-primary-600">AI</span>
            </h1>
            <p className="text-[11px] text-slate-400 font-medium tracking-wide leading-none">
              🇵🇰 Smart Medicine Assistant
            </p>
          </div>
        </button>
      </div>
    </header>
  );
};

export default Header;
