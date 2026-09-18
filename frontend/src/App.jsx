import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Home from './components/Home';
import SearchBar from './components/SearchBar';
import MedicineCard from './components/MedicineCard';
import MedicineDetail from './components/MedicineDetail';
import Chatbot from './components/Chatbot';
import Auth from './components/Auth';
import Toast from './components/Toast';
import { medicineApi, authApi, authStorage } from './lib/api';
import logoIcon from './assets/logo-icon.png';

function App() {
  const [mode, setMode] = useState('home'); // 'home', 'search', 'chat'

  // ── Auth state ────────────────────────────────────────────────────────────
  const [user, setUser] = useState(null);
  const [showAuth, setShowAuth] = useState(!authStorage.getToken());
  const [isCheckingAuth, setIsCheckingAuth] = useState(!!authStorage.getToken());

  // Validate any stored token on mount and refresh the user profile
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!authStorage.getToken()) return;
      try {
        const data = await authApi.me();
        if (!cancelled) setUser(data.user);
      } catch {
        // 401 → interceptor already cleared storage + fired the event below
      } finally {
        if (!cancelled) setIsCheckingAuth(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Token expired / rejected mid-session → back to the login screen
  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setShowAuth(true);
      setMode('home');
    };
    window.addEventListener('medpak:unauthorized', onUnauthorized);
    return () => window.removeEventListener('medpak:unauthorized', onUnauthorized);
  }, []);

  const handleAuthSuccess = (token, authUser) => {
    authStorage.set(token, authUser);
    setUser(authUser);
    setShowAuth(false);
    setMode('home');
  };

  const handleLogout = () => {
    authStorage.clear();
    setUser(null);
    setShowAuth(true);
    setMode('home');
    setSearchResults([]);
    setHasSearched(false);
    setScanInfo(null);
    setSelectedDrugId(null);
  };

  // ── Search state ──────────────────────────────────────────────────────────
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [scanInfo, setScanInfo] = useState(null); // {scanned_text, search_used}
  const [selectedDrugId, setSelectedDrugId] = useState(null);
  const [selectedBrandData, setSelectedBrandData] = useState(null);
  // Sequence guard so a slow search can't clobber a newer one
  const searchSeqRef = useRef(0);

  const goHome = () => {
    setMode('home');
    setSearchResults([]);
    setHasSearched(false);
    setScanInfo(null);
    setSelectedDrugId(null);
  };

  // The backend scrapes prices in the background after a search; refetch
  // once a few seconds later so cards pending a live price fill in.
  const schedulePriceRefetch = (query, seq, delay = 6000) => {
    setTimeout(async () => {
      if (seq !== searchSeqRef.current) return; // user searched again
      try {
        const data = await medicineApi.search(query);
        if (seq !== searchSeqRef.current) return;
        setSearchResults(data.results || []);
      } catch { /* keep showing the previous results */ }
    }, delay);
  };

  const handleSearch = async (query) => {
    if (!query) {
      setSearchResults([]);
      setHasSearched(false);
      setScanInfo(null);
      setSelectedDrugId(null);
      return;
    }

    const seq = ++searchSeqRef.current;
    setIsSearching(true);
    setSelectedDrugId(null);
    setScanInfo(null);
    try {
      const data = await medicineApi.search(query);
      if (seq !== searchSeqRef.current) return; // superseded by a newer search
      setSearchResults(data.results || []);
      setHasSearched(true);
      if ((data.results || []).some((r) => !r.live_price_pkr)) {
        schedulePriceRefetch(query, seq);
      }
    } catch (error) {
      if (seq !== searchSeqRef.current) return;
      console.error("Search failed", error);
      const errDetail = error.response?.data?.detail;
      alert(typeof errDetail === 'string' ? errDetail : "Failed to connect to the server. Is the backend running?");
    } finally {
      if (seq === searchSeqRef.current) setIsSearching(false);
    }
  };

  const handleScan = async (file) => {
    const seq = ++searchSeqRef.current;
    setIsScanning(true);
    setSelectedDrugId(null);
    setScanInfo(null);
    try {
      const data = await medicineApi.scan(file);
      if (seq !== searchSeqRef.current) return;
      if (data.results && data.results.length > 0) {
        setSearchResults(data.results);
        setHasSearched(true);
        setScanInfo({ scanned_text: data.scanned_text, search_used: data.search_used });
        if (data.results.some((r) => !r.live_price_pkr)) {
          schedulePriceRefetch(data.search_used, seq);
        }
      } else {
        alert(data.message || "Could not read any text from the image. Try a clearer photo.");
      }
    } catch (error) {
      if (seq !== searchSeqRef.current) return;
      console.error("Scan failed", error);
      const errDetail = error.response?.data?.detail || "Failed to scan. Try a smaller or clearer image.";
      alert(errDetail);
    } finally {
      if (seq === searchSeqRef.current) setIsScanning(false);
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

                {/* Loading skeletons */}
                {(isSearching || isScanning) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-6 animate-pulse">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="bg-white rounded-2xl border border-slate-200 p-5 h-48">
                        <div className="h-5 bg-slate-200 rounded w-2/3 mb-3" />
                        <div className="h-3.5 bg-slate-100 rounded w-1/2 mb-2.5" />
                        <div className="h-3.5 bg-slate-100 rounded w-1/3 mb-6" />
                        <div className="flex gap-2">
                          <div className="h-7 bg-slate-100 rounded-full w-20" />
                          <div className="h-7 bg-slate-100 rounded-full w-16" />
                        </div>
                      </div>
                    ))}
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

  // ─── Auth gate ────────────────────────────────────────────────────────────
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50">
        <img src={logoIcon} alt="MedPak AI" className="w-16 h-16 mb-5 animate-fade-in" />
        <div className="w-10 h-10 border-4 border-primary-100 border-t-primary-600 rounded-full animate-spin" />
        <p className="mt-4 text-sm text-slate-500">Signing you in...</p>
      </div>
    );
  }

  if (showAuth) {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className={`flex flex-col bg-slate-50 ${mode === 'chat' ? 'h-[100dvh] overflow-hidden' : 'min-h-screen'}`}>
      <Toast />
      <Header onLogoClick={goHome} user={user} onLogout={handleLogout} />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
