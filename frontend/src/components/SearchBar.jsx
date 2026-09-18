import React, { useState, useRef } from 'react';
import { Search, Camera, UploadCloud, Loader2, X, ScanLine, Sparkles } from 'lucide-react';

// One-tap examples — also showcase strengths, combos, and multi-salt support
const EXAMPLES = ['Panadol', 'Panadol CF', 'Risek 20mg', 'Brufen 400', 'Augmentin 625'];

const SearchBar = ({ onSearch, onScan, isSearching, isScanning }) => {
  const [query, setQuery] = useState('');
  const cameraInputRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim().length >= 2) {
      onSearch(query.trim());
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onScan(file);
    }
    if (e.target) e.target.value = '';
  };

  const clearSearch = () => {
    setQuery('');
    onSearch('');
  };

  const busy = isScanning || isSearching;

  return (
    <div className="w-full max-w-4xl mx-auto mb-8 animate-slide-up">
      
      {/* Main Search Input */}
      <form onSubmit={handleSubmit} className="relative flex items-center mb-6">
        <div className="absolute left-4 text-slate-400 pointer-events-none">
          {isSearching ? (
            <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          ) : (
            <Search className="w-5 h-5" />
          )}
        </div>
        
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by brand (e.g. Panadol) or salt (e.g. Paracetamol)..."
          className="input-search"
          disabled={busy}
          autoFocus
        />
        
        {query && (
          <button 
            type="button" 
            onClick={clearSearch}
            className="absolute right-4 p-1.5 text-slate-400 hover:text-slate-600 transition-colors rounded-lg hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </form>

      {/* One-tap example searches */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="inline-flex items-center gap-1 text-xs text-slate-400 font-medium">
          <Sparkles className="w-3.5 h-3.5" /> Try:
        </span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            disabled={busy}
            onClick={() => {
              setQuery(ex);
              onSearch(ex);
            }}
            className="text-xs bg-white border border-slate-200 hover:border-primary-400 hover:text-primary-700 hover:bg-primary-50/50 text-slate-600 px-3 py-1.5 rounded-full transition-all font-medium disabled:opacity-50 disabled:pointer-events-none"
          >
            {ex}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4 my-6">
        <div className="flex-1 h-px bg-slate-200"></div>
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">or scan medicine box</span>
        <div className="flex-1 h-px bg-slate-200"></div>
      </div>

      {/* OCR Buttons */}
      <div className="flex gap-4 justify-center">
        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
          disabled={busy}
          className="flex items-center gap-2.5 bg-white border-2 border-dashed border-slate-200 hover:border-primary-400 hover:bg-primary-50/50 px-6 py-4 rounded-2xl font-semibold text-slate-600 hover:text-primary-700 transition-all disabled:opacity-50 disabled:pointer-events-none"
        >
          {isScanning ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Camera className="w-5 h-5" />
          )}
          <span className="hidden sm:inline">Take Photo</span>
          <span className="sm:hidden">Camera</span>
        </button>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
          className="flex items-center gap-2.5 bg-white border-2 border-dashed border-slate-200 hover:border-primary-400 hover:bg-primary-50/50 px-6 py-4 rounded-2xl font-semibold text-slate-600 hover:text-primary-700 transition-all disabled:opacity-50 disabled:pointer-events-none"
        >
          {isScanning ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <UploadCloud className="w-5 h-5" />
          )}
          <span className="hidden sm:inline">Upload Image</span>
          <span className="sm:hidden">Upload</span>
        </button>
      </div>

      {/* Scanning indicator */}
      {isScanning && (
        <div className="mt-6 flex items-center justify-center gap-2 text-sm text-primary-600 font-medium animate-pulse">
          <ScanLine className="w-4 h-4" />
          Scanning image... This may take a moment on first use.
        </div>
      )}

      {/* Hidden file inputs */}
      <input 
        type="file" ref={cameraInputRef} onChange={handleFileChange}
        accept="image/*" capture="environment" className="hidden" 
      />
      <input 
        type="file" ref={fileInputRef} onChange={handleFileChange}
        accept="image/*" className="hidden" 
      />
    </div>
  );
};

export default SearchBar;
