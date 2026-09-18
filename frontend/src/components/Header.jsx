import React from 'react';
import { LogOut } from 'lucide-react';
import logoIcon from '../assets/logo-icon.png';

const Header = ({ onLogoClick, user, onLogout }) => {
  const initials = (user?.username || user?.email || '?')
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200 px-4 md:px-6 py-3 shadow-sm">
      <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
        <button
          onClick={onLogoClick}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
        >
          <img
            src={logoIcon}
            alt="MedPak AI"
            className="w-11 h-11"
          />
          <div className="hidden sm:block text-left">
            <h1 className="text-xl font-extrabold text-navy tracking-tight leading-none">
              MedPak <span className="text-primary-600">AI</span>
            </h1>
            <p className="text-[11px] text-slate-400 font-medium tracking-wide leading-none mt-1">
              Smart Medicine Information, Better Health
            </p>
          </div>
        </button>

        {user && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5 bg-slate-50 border border-slate-200 rounded-full pl-1 pr-3.5 py-1">
              <div
                className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 text-white text-xs font-bold flex items-center justify-center shadow-sm select-none"
                title={user.email}
              >
                {initials}
              </div>
              <span className="hidden md:block text-sm font-semibold text-slate-700 max-w-[140px] truncate">
                {user.username}
              </span>
            </div>
            <button
              onClick={onLogout}
              title="Sign out"
              className="p-2.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
