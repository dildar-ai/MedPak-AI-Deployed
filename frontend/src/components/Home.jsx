import React from 'react';
import {
  Search, MessageSquareHeart, Sparkles, Database, Layers, Banknote,
  TrendingDown, ScanLine, Languages, ShieldCheck,
} from 'lucide-react';
import logo from '../assets/logo.png';

const STATS = [
  { icon: Database, label: '23,332 medicine brands' },
  { icon: Layers, label: '1,956 generics' },
  { icon: Banknote, label: 'Live price scraping' },
];

const FEATURES = [
  {
    icon: Banknote,
    title: 'Live Prices',
    desc: 'Scraped from real Pakistani pharmacies in real time',
    color: 'text-emerald-600 bg-emerald-50',
  },
  {
    icon: TrendingDown,
    title: 'Cheaper Alternatives',
    desc: 'Same salt, same form — compared per unit',
    color: 'text-primary-600 bg-primary-50',
  },
  {
    icon: ScanLine,
    title: 'Scan Medicine Box',
    desc: 'Camera or upload — OCR finds it instantly',
    color: 'text-medical-600 bg-medical-50',
  },
  {
    icon: Languages,
    title: 'English + Urdu AI',
    desc: 'Ask questions in Urdu, Roman Urdu or English',
    color: 'text-violet-600 bg-violet-50',
  },
];

const Home = ({ setMode }) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 md:py-20 animate-fade-in">

      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 bg-primary-50 border border-primary-200 text-primary-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
          <Sparkles className="w-4 h-4" />
          Powered by AI • پاکستان کے لیے
        </div>
        {/* Official brand logo (icon + wordmark + tagline) */}
        <img
          src={logo}
          alt="MedPak AI — Smart Medicine Information, Better Health"
          className="w-64 md:w-80 mx-auto mb-6 drop-shadow-sm"
        />
        <p className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto leading-relaxed">
          Your intelligent medicine companion for Pakistan. Find medicines, check live prices, explore alternatives, and get bilingual AI-powered guidance.
        </p>
      </div>

      {/* Stats badges */}
      <div className="flex flex-wrap items-center justify-center gap-2.5 md:gap-3 mb-10">
        {STATS.map(({ icon: Icon, label }) => (
          <div
            key={label}
            className="flex items-center gap-2 bg-white border border-slate-200 text-slate-600 text-sm font-medium px-4 py-2 rounded-full shadow-sm"
          >
            <Icon className="w-4 h-4 text-primary-500" />
            {label}
          </div>
        ))}
      </div>

      {/* Feature highlights — the pitch at a glance */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 w-full max-w-4xl mb-12">
        {FEATURES.map(({ icon: Icon, title, desc, color }) => (
          <div
            key={title}
            className="flex flex-col items-center text-center p-4 md:p-5 bg-white/70 backdrop-blur-sm border border-slate-200/80 rounded-2xl shadow-sm"
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${color}`}>
              <Icon className="w-5 h-5" />
            </div>
            <h4 className="text-sm font-bold text-slate-800 mb-1">{title}</h4>
            <p className="text-[11px] md:text-xs text-slate-500 leading-snug">{desc}</p>
          </div>
        ))}
      </div>

      {/* Mode Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 w-full max-w-3xl">

        {/* Search Mode */}
        <button
          onClick={() => setMode('search')}
          className="group relative flex flex-col items-center p-8 md:p-10 bg-white rounded-3xl border border-slate-200 shadow-sm hover:shadow-xl hover:border-medical-300 hover:-translate-y-1 transition-all duration-300 overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-40 h-40 bg-medical-100/60 rounded-full blur-3xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

          <div className="w-16 h-16 bg-medical-100 text-medical-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
            <Search className="w-8 h-8" />
          </div>

          <h3 className="text-xl font-bold text-slate-800 mb-2">Search Medicine</h3>
          <p className="text-sm text-slate-500 text-center leading-relaxed">
            Type a medicine name, salt, or scan a medicine box to find details, per-variant prices &amp; cheaper alternatives.
          </p>

          <div className="mt-5 text-xs font-semibold text-medical-600 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
            Get Started →
          </div>
        </button>

        {/* Chat Mode */}
        <button
          onClick={() => setMode('chat')}
          className="group relative flex flex-col items-center p-8 md:p-10 bg-white rounded-3xl border border-slate-200 shadow-sm hover:shadow-xl hover:border-emerald-300 hover:-translate-y-1 transition-all duration-300 overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-40 h-40 bg-emerald-100/50 rounded-full blur-3xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

          <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
            <MessageSquareHeart className="w-8 h-8" />
          </div>

          <h3 className="text-xl font-bold text-slate-800 mb-2">Chat with AI</h3>
          <p className="text-sm text-slate-500 text-center leading-relaxed">
            Ask about any medicine — its uses, side effects, interactions, brands, or prices — in English or Urdu.
          </p>

          <div className="mt-5 text-xs font-semibold text-emerald-600 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
            Start Chatting →
          </div>
        </button>
      </div>

      {/* Footer Disclaimer */}
      <p className="mt-14 text-xs text-slate-400 text-center max-w-xl leading-relaxed">
        <span className="inline-flex items-center gap-1.5 font-medium text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5" /> Information only — not medical advice.
        </span>
        <br />
        ⚠️ یہ معلومات صرف آگاہی کے لیے ہے — This tool is for informational purposes only. Always consult a licensed doctor or pharmacist.
      </p>
    </div>
  );
};

export default Home;
