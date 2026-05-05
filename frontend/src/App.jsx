import React, { useState } from 'react';
import Header from './components/Header';
import Home from './components/Home';
import SearchBar from './components/SearchBar';
import MedicineCard from './components/MedicineCard';
import MedicineDetail from './components/MedicineDetail';
import Chatbot from './components/Chatbot';
import { medicineApi } from './lib/api';

function App() {
  const [mode, setMode] = useState('home'); // 'home', 'search', 'chat'
  
  // Search state
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [scanInfo, setScanInfo] = useState(null); // {scanned_text, search_used}
  const [selectedDrugId, setSelectedDrugId] = useState(null);
  const [selectedBrandData, setSelectedBrandData] = useState(null);

  const goHome = () => {
    setMode('home');
    setSearchResults([]);
    setHasSearched(false);
    setScanInfo(null);
    setSelectedDrugId(null);
  };

  const handleSearch = async (query) => {
    if (!query) {
      setSearchResults([]);
      setHasSearched(false);
      setScanInfo(null);
      setSelectedDrugId(null);
      return;
    }

    setIsSearching(true);
    setSelectedDrugId(null);
    setScanInfo(null);
    try {
      const data = await medicineApi.search(query);
      setSearchResults(data.results || []);
      setHasSearched(true);
    } catch (error) {
      console.error("Search failed", error);
      alert("Failed to connect to the server. Is the backend running?");
    } finally {
      setIsSearching(false);
    }
  };

  const handleScan = async (file) => {
    setIsScanning(true);
    setSelectedDrugId(null);
    setScanInfo(null);
    try {
      const data = await medicineApi.scan(file);
      if (data.results && data.results.length > 0) {
        setSearchResults(data.results);
        setHasSearched(true);
        setScanInfo({ scanned_text: data.scanned_text, search_used: data.search_used });
      } else {
        alert(data.message || "Could not read any text from the image. Try a clearer photo.");
      }
    } catch (error) {
      console.error("Scan failed", error);
      const errDetail = error.response?.data?.detail || "Failed to scan. Try a smaller or clearer image.";
      alert(errDetail);
    } finally {
      setIsScanning(false);
    }
  };

  const handleCardClick = (medicine) => {
    setSelectedBrandData(medicine);
    setSelectedDrugId(medicine.drug_id ?? medicine.CODE);
  };

  const renderContent = () => {
    // ─── HOME ──────────────────────────────────────────────────────────
    if (mode === 'home') {
      return <Home setMode={setMode} />;
    }
    
    // ─── CHAT ──────────────────────────────────────────────────────────
    if (mode === 'chat') {
      return (
        <div className="flex-1 flex justify-center items-stretch p-0 md:p-6 overflow-hidden min-h-0">
          <Chatbot onBack={goHome} />
        </div>
      );
    }

    // ─── SEARCH ────────────────────────────────────────────────────────
    if (mode === 'search') {
      return (
        <div className="flex-1 overflow-y-auto">
          <div className="w-full max-w-6xl mx-auto px-4 md:px-6 py-6">
            <div className="mb-6">
              <button 
                onClick={goHome} 
                className="text-slate-400 hover:text-slate-700 flex items-center gap-1.5 text-sm font-medium transition-colors"
              >
                ← Back to Home
              </button>
            </div>

            {!selectedDrugId ? (
              <>
                <div className="text-center mb-8">
                  <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight mb-2">
                    Find Medicines in Pakistan
                  </h2>
                  <p className="text-sm text-slate-500">پاکستان میں دوائیں تلاش کریں</p>
                </div>

                <SearchBar 
                  onSearch={handleSearch} 
                  onScan={handleScan}
                  isSearching={isSearching}
                  isScanning={isScanning}
                />

                {/* Scan Result Info */}
                {scanInfo && (
                  <div className="max-w-4xl mx-auto mb-6 bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm">
                    <p className="text-blue-800">
                      📸 Scanned text: <strong>{scanInfo.scanned_text}</strong> → Searching for: <strong>{scanInfo.search_used}</strong>
                    </p>
                  </div>
                )}

                {/* Results */}
                {hasSearched && !isSearching && !isScanning && (
                  <div className="animate-fade-in mt-4 max-w-6xl mx-auto">
                    <h3 className="text-lg font-bold text-slate-800 mb-5">
                      {searchResults.length > 0 
                        ? `Found ${searchResults.length} results` 
                        : 'No results found'
                      }
                    </h3>
                    
                    {searchResults.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        {searchResults.map((med, idx) => (
                          <MedicineCard
                            key={med.drug_id ?? med.CODE ?? idx}
                            medicine={med}
                            onClick={handleCardClick}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-14 bg-white rounded-2xl border border-slate-200">
                        <p className="text-lg font-medium text-slate-600">No medicines found.</p>
                        <p className="text-slate-400 mt-2 text-sm">
                          Try checking the spelling or scan the medicine box instead.
                        </p>
                        <p className="text-slate-400 text-sm mt-1 font-urdu">
                          ہجے چیک کریں یا دوا کا ڈبہ اسکین کریں۔
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <MedicineDetail 
                drugId={selectedDrugId} 
                brandData={selectedBrandData}
                onBack={() => setSelectedDrugId(null)} 
              />
            )}
          </div>
        </div>
      );
    }
  };

  return (
    <div className={`flex flex-col bg-slate-50 ${mode === 'chat' ? 'h-[100dvh] overflow-hidden' : 'min-h-screen'}`}>
      <Header onLogoClick={goHome} />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
