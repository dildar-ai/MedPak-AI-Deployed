import React from 'react';
import { Search, MessageSquareHeart, Sparkles } from 'lucide-react';

const Home = ({ setMode }) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 md:py-20 animate-fade-in">
      
      {/* Hero */}
      <div className="text-center mb-14">
        <div className="inline-flex items-center gap-2 bg-primary-50 border border-primary-200 text-primary-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
          <Sparkles className="w-4 h-4" />
          Powered by AI • پاکستان کے لیے
        </div>
        <h2 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight mb-5 leading-tight">
          Welcome to <span className="text-primary-600">MedPak AI</span>
        </h2>
        <p className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto leading-relaxed">
          Your intelligent medicine companion for Pakistan. Find medicines, check prices, explore alternatives, and get bilingual AI-powered guidance.
        </p>
      </div>

      {/* Mode Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 w-full max-w-3xl">
        
        {/* Search Mode */}
        <button 
          onClick={() => setMode('search')}
          className="group relative flex flex-col items-center p-8 md:p-10 bg-white rounded-3xl border border-slate-200 shadow-sm hover:shadow-xl hover:border-blue-300 hover:-translate-y-1 transition-all duration-300 overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-40 h-40 bg-blue-100/50 rounded-full blur-3xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          
          <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
            <Search className="w-8 h-8" />
          </div>
          
          <h3 className="text-xl font-bold text-slate-800 mb-2">Search Medicine</h3>
          <p className="text-sm text-slate-500 text-center leading-relaxed">
            Type a medicine name, salt, or scan a medicine box to find details, prices & alternatives.
          </p>

          <div className="mt-5 text-xs font-semibold text-blue-600 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
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
            Ask anything in English or Urdu — symptoms, treatments, drug interactions, or general medical queries.
          </p>

          <div className="mt-5 text-xs font-semibold text-emerald-600 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
            Start Chatting →
          </div>
        </button>
      </div>

      {/* Footer Disclaimer */}
      <p className="mt-14 text-xs text-slate-400 text-center max-w-xl leading-relaxed">
        ⚠️ یہ معلومات صرف آگاہی کے لیے ہے — This tool is for informational purposes only. Always consult a licensed doctor or pharmacist.
      </p>
    </div>
  );
};

export default Home;
