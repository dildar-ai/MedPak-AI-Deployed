import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowLeft, AlertTriangle, ShieldAlert, CheckCircle2,
  Pill, Activity, Receipt, Loader2, Info, MessageSquareHeart,
  Bot, User, Send, Sparkles, Wifi, TrendingDown,
  RefreshCw, Clock,
} from 'lucide-react';
import { medicineApi } from '../lib/api';
import { unitWord } from '../lib/format';
import ReactMarkdown from 'react-markdown';

// ── Reusable info section ───────────────────────────────────────────────────
const Section = ({ icon: Icon, iconColor, title, titleUrdu, children }) => (
  <section className="mb-8 last:mb-0">
    <h3 className="text-lg font-bold text-slate-800 mb-1 flex items-center gap-2">
      <Icon className={`w-5 h-5 ${iconColor}`} />
      {title}
    </h3>
    {titleUrdu && <p className="text-sm text-slate-400 font-urdu mb-3">{titleUrdu}</p>}
    <div className="text-slate-600 leading-relaxed whitespace-pre-wrap text-[15px]">
      {children}
    </div>
  </section>
);

// ── Inline AI chat panel (used inside the Ask AI tab) ──────────────────────
const MedicineChat = ({ drugId, drugName }) => {
  const SUGGESTIONS = [
    `Is ${drugName} safe during pregnancy?`,
    `What are the common side effects of ${drugName}?`,
    `Can I take ${drugName} with food?`,
    `What is the usual adult dose of ${drugName}?`,
    `Is ${drugName} safe for children?`,
    `Can ${drugName} be taken with paracetamol?`,
    `What happens if I miss a dose of ${drugName}?`,
    `Are there cheaper alternatives to ${drugName}?`,
  ];

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const cleanResponse = (text) =>
    text.replace(/<think>[\s\S]*?<\/think>\s*/g, '').trim();

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || isLoading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setIsLoading(true);
    try {
      const data = await medicineApi.chat(msg, drugId, sessionId);
      if (data.session_id && !sessionId) setSessionId(data.session_id);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: cleanResponse(data.answer),
      }]);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to connect. Please try again.';
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ ${detail}` }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const detectUrdu = (t) => /[\u0600-\u06FF]/.test(t);

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* Suggestion pills — hide once chat has started */}
      {messages.length === 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-primary-500" />
            <p className="text-sm font-semibold text-slate-600">Suggested questions</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => send(q)}
                className="text-xs bg-primary-50 hover:bg-primary-100 text-primary-700 border border-primary-200 hover:border-primary-400 px-3 py-1.5 rounded-full transition-all font-medium"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message thread */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1" style={{ maxHeight: '380px' }}>
        {messages.map((msg, idx) => {
          const isUrdu = msg.role === 'assistant' && detectUrdu(msg.content);
          return (
            <div key={idx} className={`flex gap-2.5 max-w-[90%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.role === 'user' ? 'bg-slate-200' : 'bg-primary-100 text-primary-700'
              }`}>
                {msg.role === 'user' ? <User className="w-3.5 h-3.5 text-slate-600" /> : <Bot className="w-3.5 h-3.5" />}
              </div>
              <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-tr-sm'
                  : 'bg-slate-50 border border-slate-200 text-slate-800 rounded-tl-sm'
              }`}>
                {msg.role === 'user' ? msg.content : (
                  <div className={`prose prose-sm prose-slate max-w-none ${isUrdu ? 'font-urdu text-right' : ''}`}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex gap-2.5 max-w-[80%]">
            <div className="w-7 h-7 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-2xl rounded-tl-sm flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-primary-500" /> Thinking...
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input row */}
      <div className="flex gap-2 mt-auto">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder={`Ask anything about ${drugName}...`}
          disabled={isLoading}
          className="flex-1 bg-slate-100 text-slate-900 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 border border-transparent transition-all"
        />
        <button
          onClick={() => send()}
          disabled={!input.trim() || isLoading}
          className="p-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-500 disabled:opacity-40 disabled:bg-slate-300 transition-all"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

// ── Main MedicineDetail component ───────────────────────────────────────────
// Poll the alternatives endpoint while the backend's background bulk scrape
// (ALL brands of this salt, scraped simultaneously) is still running.
const POLL_INTERVAL_MS = 2500;
const MAX_POLLS = 80; // ~3.3 minutes

const MedicineDetail = ({ drugId, brandData, onBack }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [altData, setAltData] = useState(null);
  const [altLoading, setAltLoading] = useState(false);
  const [altError, setAltError] = useState(false);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('info');
  const pollCountRef = useRef(0);
  const pollTimerRef = useRef(null);

  // Live price for the clicked brand (DB prices are outdated — never shown)
  const [brandLivePrice, setBrandLivePrice] = useState(null);
  // What the price covers, e.g. { pack_desc: "10 caps", price_per_unit: 15.9 }
  const [brandPackInfo, setBrandPackInfo] = useState(null);
  const [brandPriceState, setBrandPriceState] = useState('fetching'); // fetching | done

  const fetchAlternatives = async (isPoll = false) => {
    if (!isPoll) setAltLoading(true);
    if (isPoll) setPricesLoading(true);
    try {
      // Compare against the brand the user clicked, when known
      const brand = brandData?.brand_product_name || brandData?.brand_name || null;
      const brandForm = brandData?.form || null;
      const brandStrength = brandData?.strength || null;
      const data = await medicineApi.getAlternatives(drugId, brand, brandForm, brandStrength);
      setAltData(data);
      setAltError(false);
      // The backend responds instantly with saved prices and scrapes ALL
      // remaining brands of this salt in the background — keep polling
      // while that job runs so new prices fill in automatically.
      const scraping = data.scraping;
      if (scraping?.in_progress && pollCountRef.current < MAX_POLLS) {
        pollCountRef.current += 1;
        pollTimerRef.current = setTimeout(() => fetchAlternatives(true), POLL_INTERVAL_MS);
      } else {
        setPricesLoading(false);
      }
    } catch (err) {
      console.error('Failed to load alternatives', err);
      setAltError(true);
      setPricesLoading(false);
    } finally {
      if (!isPoll) setAltLoading(false);
    }
  };

  useEffect(() => {
    pollCountRef.current = 0;
    clearTimeout(pollTimerRef.current);
    const fetchDetails = async () => {
      setLoading(true);
      try {
        const brandName = brandData?.brand_product_name || null;
        const data = await medicineApi.getDetails(drugId, brandName);
        setDetails(data);
        fetchAlternatives(false);
      } catch (error) {
        console.error('Failed to load details', error);
      } finally {
        setLoading(false);
      }
    };
    if (drugId) fetchDetails();
    return () => {
      pollCountRef.current = MAX_POLLS + 1; // stop polling after unmount
      clearTimeout(pollTimerRef.current);
    };
  }, [drugId]);

  // Fetch the live price for the clicked brand (this waits for the scrape)
  useEffect(() => {
    let cancelled = false;
    if (brandData?.live_price_pkr) {
      setBrandLivePrice(brandData.live_price_pkr);
      setBrandPackInfo({
        pack_desc: brandData.pack_desc || null,
        price_per_unit: brandData.price_per_unit || null,
      });
      setBrandPriceState('done');
      return;
    }
    setBrandLivePrice(null);
    setBrandPackInfo(null);
    setBrandPriceState('fetching');
    (async () => {
      try {
        const name = brandData?.brand_product_name || brandData?.brand_name || details?.drug?.NAME;
        if (name) {
          const data = await medicineApi.getLivePrice(name, brandData?.strength || null);
          if (!cancelled) {
            setBrandLivePrice(data.live_price_pkr);
            setBrandPackInfo({
              pack_desc: data.pack_desc || null,
              price_per_unit: data.price_per_unit || null,
            });
          }
        }
      } catch {
        // price simply unavailable
      } finally {
        if (!cancelled) setBrandPriceState('done');
      }
    })();
    return () => { cancelled = true; };
  }, [drugId, brandData, details]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 className="w-10 h-10 text-primary-500 animate-spin mb-4" />
        <p className="text-slate-500 font-medium">Loading medicine profile...</p>
        <p className="text-sm text-slate-400 mt-1">دوا کی معلومات لوڈ ہو رہی ہیں...</p>
      </div>
    );
  }

  if (!details || !details.drug) {
    return (
      <div className="text-center py-24">
        <p className="text-slate-500 text-lg">Could not load medicine details.</p>
        <p className="text-sm text-slate-400 mt-1">دوا کی معلومات نہیں مل سکیں۔</p>
        <button onClick={onBack} className="btn-secondary mt-6 mx-auto">Go Back</button>
      </div>
    );
  }

  const { drug, dosage } = details;

  // Combination products (e.g. Panadol-CF) have multiple salts. Show the
  // full composition instead of only the single salt of the clicked DID.
  const saltNames = details?.salts?.length
    ? details.salts.map(s => s.salt_name)
    : [drug.NAME];
  const displaySalt = saltNames.join(' + ');

  const tabs = [
    { key: 'info',         label: 'Information',  icon: Activity },
    { key: 'dosage',       label: 'Dosage',        icon: Pill },
    { key: 'alternatives', label: 'Alternatives',  icon: Receipt },
    { key: 'askai',        label: 'Ask AI',        icon: MessageSquareHeart },
  ];

  return (
    <div className="animate-fade-in pb-10">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mb-6 font-medium transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        Back to search
      </button>

      {/* Header Card */}
      <div className="glass-card p-6 md:p-8 mb-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-100 rounded-full blur-3xl opacity-40 -translate-y-1/2 translate-x-1/4 pointer-events-none" />
        <div className="relative z-10">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="badge badge-primary">Code: {drug.CODE}</span>
            <span className="badge badge-slate">{saltNames.length > 1 ? 'Combination Salt' : 'Generic Salt'}</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-1">{displaySalt}</h2>
          {brandData?.brand_name && brandData.brand_name !== drug.NAME && (
            <p className="text-base text-slate-600 font-medium">
              Brand: <span className="text-primary-700 font-semibold">{brandData.brand_name}</span>
            </p>
          )}

          {/* ── Price Section (live only — DB prices are outdated) ── */}
          <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
            {brandLivePrice ? (
              <div className="flex flex-wrap items-center gap-2 text-emerald-600 text-sm">
                <Wifi className="w-4 h-4" />
                <span>Live Price: <strong className="text-emerald-700">Rs. {brandLivePrice}</strong></span>
                {brandPackInfo?.pack_desc && (
                  <span className="text-slate-400">for {brandPackInfo.pack_desc}</span>
                )}
                {brandPackInfo?.price_per_unit > 0 && (
                  <span className="text-slate-400">
                    (Rs. {brandPackInfo.price_per_unit} per {unitWord(brandPackInfo.pack_desc)})
                  </span>
                )}
                <span className="text-[10px] bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full border border-emerald-200">LIVE</span>
              </div>
            ) : brandPriceState === 'fetching' ? (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Fetching live price…</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Wifi className="w-4 h-4" />
                <span>Live price unavailable right now</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto gap-1 mb-6 bg-slate-100 p-1 rounded-xl">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all whitespace-nowrap ${
              activeTab === tab.key
                ? tab.key === 'askai'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-white text-primary-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 md:p-8">

        {/* INFO TAB */}
        {activeTab === 'info' && (
          <div className="animate-fade-in">
            {drug.OVERVIEW && (
              <Section icon={CheckCircle2} iconColor="text-primary-500" title="Overview" titleUrdu="جائزہ">
                {drug.OVERVIEW}
              </Section>
            )}
            {drug.INDICATIONS && (
              <Section icon={Activity} iconColor="text-blue-500" title="Uses / Indications" titleUrdu="استعمال">
                {drug.INDICATIONS}
              </Section>
            )}
            {drug.EFFECTS && (
              <Section icon={AlertTriangle} iconColor="text-amber-500" title="Side Effects" titleUrdu="مضر اثرات">
                {drug.EFFECTS}
              </Section>
            )}
            {drug.CONTRAINDICATIONS && (
              <Section icon={ShieldAlert} iconColor="text-red-500" title="Do Not Use If" titleUrdu="پرہیز">
                {drug.CONTRAINDICATIONS}
              </Section>
            )}
            {drug.warnings && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mt-6">
                <h4 className="font-bold text-amber-800 mb-1 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" /> Warnings / احتیاط
                </h4>
                <p className="text-amber-700 text-sm leading-relaxed">{drug.warnings}</p>
              </div>
            )}
            {drug.STORAGE && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mt-4">
                <h4 className="font-bold text-blue-800 mb-1 flex items-center gap-2">
                  <Info className="w-5 h-5" /> Storage / حفاظت
                </h4>
                <p className="text-blue-700 text-sm leading-relaxed">{drug.STORAGE}</p>
              </div>
            )}
          </div>
        )}

        {/* DOSAGE TAB */}
        {activeTab === 'dosage' && (
          <div className="space-y-6 animate-fade-in">
            {['neonatal', 'paediatric', 'adult'].map(ageGroup => {
              const ageLabels = {
                neonatal:   { en: 'Neonatal (نوزائیدہ)', color: 'bg-purple-50 border-purple-100' },
                paediatric: { en: 'Paediatric (بچوں)',  color: 'bg-blue-50 border-blue-100' },
                adult:      { en: 'Adult (بالغ)',        color: 'bg-green-50 border-green-100' },
              };
              const label = ageLabels[ageGroup];
              return dosage[ageGroup]?.length > 0 && (
                <div key={ageGroup} className={`border rounded-xl overflow-hidden shadow-sm ${label.color}`}>
                  <div className={`px-5 py-3 border-b ${label.color}`}>
                    <h3 className="font-bold text-slate-800">{label.en}</h3>
                  </div>
                  <div className="bg-white divide-y divide-slate-100">
                    {dosage[ageGroup].map((d, idx) => (
                      <div key={idx} className="p-5 flex flex-col md:flex-row gap-3 md:items-center">
                        <div className="flex-1">
                          <p className="font-bold text-slate-900">{d.DOSE}</p>
                          {d.INSTRUCTION && <p className="text-slate-500 text-sm mt-1">{d.INSTRUCTION}</p>}
                        </div>
                        {/* Plain-language badges — "24 hourly"→"Once daily", "PO"→"By mouth" */}
                        <div className="flex gap-2 flex-wrap md:justify-end">
                          {(d.freq_human || d.FREQ) && (
                            <span className="badge badge-primary" title="How often to take it">
                              {d.freq_human || d.FREQ}
                            </span>
                          )}
                          {(d.route_human || d.ROUTE) && (
                            <span className="badge bg-slate-200 text-slate-700" title="How the medicine is taken">
                              {d.route_human || d.ROUTE}
                            </span>
                          )}
                          {(d.single_human || d.SINGLE) && (
                            <span className="badge bg-purple-100 text-purple-700" title="Maximum amount in a single dose">
                              {d.single_human || `Max single dose: ${d.SINGLE}`}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
            {dosage && Object.values(dosage).every(d => !d || d.length === 0) && (
              <div className="text-center py-12 text-slate-500">
                <Pill className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <p>No specific dosage information available.</p>
                <p className="text-sm text-slate-400 mt-1">اس دوا کی خوراک کی تفصیلات دستیاب نہیں ہیں۔</p>
              </div>
            )}
          </div>
        )}

        {/* ALTERNATIVES TAB */}
        {activeTab === 'alternatives' && (() => {
          // Initial loading state
          if (altLoading && !altData) {
            return (
              <div className="flex flex-col items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin mb-3" />
                <p className="text-slate-500 font-medium">Loading price comparison...</p>
                <p className="text-sm text-slate-400 mt-1 font-urdu">قیمتوں کا موازنہ لوڈ ہو رہا ہے...</p>
              </div>
            );
          }
          // Error state — show message with retry
          if (altError && !altData) {
            return (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <AlertTriangle className="w-10 h-10 text-amber-400 mb-3" />
                <p className="text-slate-700 font-semibold mb-1">Couldn’t load price comparison</p>
                <p className="text-sm text-slate-500 mb-4 max-w-xs">
                  The request timed out. Please try again — it may take a moment for medicines with many brands.
                </p>
                <button
                  onClick={() => { setAltError(false); setAltLoading(true); fetchAlternatives(false); }}
                  className="btn-primary"
                >
                  <RefreshCw className="w-4 h-4" /> Retry
                </button>
              </div>
            );
          }

          const alts = altData?.alternatives || [];
          const cheapest = altData?.cheapest;
          const coverage = altData?.price_coverage;
          const currentBrand = altData?.current_brand;
          const scraping = altData?.scraping;
          const scrapePct = scraping?.brands_total > 0
            ? Math.round((scraping.brands_done / scraping.brands_total) * 100)
            : 0;
          const hasAlts = alts.length > 0;

          return (
            <div className="animate-fade-in">
              <div className="flex items-start justify-between mb-1">
                <h3 className="text-lg font-bold text-slate-800">Price Comparison — {displaySalt}</h3>
                {pricesLoading && (
                  <span className="flex items-center gap-1.5 text-xs text-amber-600 font-medium">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Updating prices...
                  </span>
                )}
                {altError && altData && (
                  <span className="flex items-center gap-1.5 text-xs text-red-500 font-medium">
                    <AlertTriangle className="w-3.5 h-3.5" /> Price update failed — showing cached data
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-400 mb-4">{displaySalt} کے تمام برانڈز اور قیمتیں</p>

              {/* Live scrape progress — the backend is checking ALL brands
                  of this salt simultaneously in the background */}
              {scraping?.in_progress && (
                <div className="bg-primary-50 border border-primary-200 rounded-xl p-4 mb-5">
                  <div className="flex items-center gap-2 text-primary-800 text-sm font-semibold mb-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Fetching live prices for all {scraping.brands_total} brands…
                  </div>
                  <div className="h-1.5 bg-primary-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full transition-all duration-700"
                      style={{ width: `${scrapePct}%` }}
                    />
                  </div>
                  <p className="text-xs text-primary-600 mt-2">
                    {scraping.brands_done} of {scraping.brands_total} brands checked — prices appear
                    below as they're found and are saved for your next visit.
                  </p>
                </div>
              )}

              {/* Savings Banner — only when both sides have live prices */}
              {cheapest && currentBrand?.best_price && cheapest.best_price < currentBrand.best_price && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-5 flex flex-wrap items-center gap-3">
                  <div className="w-9 h-9 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center">
                    <TrendingDown className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-emerald-800 text-sm">
                      Cheapest: {cheapest.brand_product_name} at Rs. {cheapest.best_price}
                      {cheapest.pack_desc ? ` for ${cheapest.pack_desc}` : ''}
                      {cheapest.price_per_unit > 0 ? ` (Rs. ${cheapest.price_per_unit}/${unitWord(cheapest.pack_desc)})` : ''}
                    </p>
                    <p className="text-emerald-600 text-xs">
                      Save Rs. {cheapest.savings?.save_pkr ?? 0}
                      {cheapest.savings_basis === 'per_unit' ? ` per ${unitWord(cheapest.pack_desc)}` : ''} ({cheapest.savings?.save_pct || 0}% cheaper than {currentBrand.name})
                    </p>
                  </div>
                  {cheapest.price_source === 'live' && (
                    <span className="flex items-center gap-1 text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200 font-medium">
                      <Wifi className="w-3 h-3" /> LIVE
                    </span>
                  )}
                </div>
              )}

              {/* Reference brand without a live price → savings can't be trusted */}
              {currentBrand && !currentBrand.best_price && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 mb-5 text-xs text-slate-500">
                  Live price for <strong>{currentBrand.name}</strong> couldn't be found online, so savings
                  can't be calculated. Prices below are live prices from Pakistani pharmacies.
                </div>
              )}

              {/* Coverage Indicator */}
              {coverage && coverage.with_live > 0 && (
                <div className="flex items-center gap-2 mb-4 text-xs text-slate-500">
                  <Clock className="w-3.5 h-3.5" />
                  <span>
                    Live prices for {coverage.with_live} of {coverage.total} brands
                    {coverage.no_live_price > 0 && (
                      <span className="text-slate-400"> — {coverage.no_live_price} couldn't be priced online</span>
                    )}
                  </span>
                </div>
              )}

              {hasAlts ? (
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200">
                        <th className="py-3 px-4 font-semibold text-slate-700 text-xs">Brand</th>
                        <th className="py-3 px-3 font-semibold text-slate-700 text-xs">Form</th>
                        <th className="py-3 px-3 font-semibold text-slate-700 text-xs hidden md:table-cell">Company</th>
                        <th className="py-3 px-3 font-semibold text-slate-700 text-xs text-right">Live Price</th>
                        <th className="py-3 px-3 font-semibold text-slate-700 text-xs text-right hidden lg:table-cell">Per Unit</th>
                        <th className="py-3 px-3 font-semibold text-slate-700 text-xs text-right">Savings</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {alts.map((alt, idx) => {
                        const isLive = alt.price_source === 'live';
                        const savings = alt.savings;
                        const isCheapest = idx === 0 && alts.length > 1;
                        const isYours = currentBrand && alt.brand_product_name === currentBrand.name;
                        return (
                          <tr key={idx} className={`hover:bg-slate-50 transition-colors ${isCheapest ? 'bg-emerald-50/40' : ''} ${isYours ? 'bg-primary-50/50' : ''}`}>
                            {/* Brand */}
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-1.5">
                                <span className="font-semibold text-primary-700 text-sm">{alt.brand_product_name}</span>
                                {isYours && (
                                  <span className="text-[9px] bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded-full font-semibold border border-primary-200">
                                    Yours
                                  </span>
                                )}
                                {isLive && (
                                  <span className="flex items-center gap-0.5 text-[9px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-medium">
                                    <Wifi className="w-2.5 h-2.5" />
                                  </span>
                                )}
                              </div>
                              {alt.sources?.[0]?.name && (
                                <p className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[120px]">{alt.sources[0].name}</p>
                              )}
                            </td>
                            {/* Form */}
                            <td className="py-3 px-3 text-slate-600 text-xs">{alt.form} {alt.strength}</td>
                            {/* Company */}
                            <td className="py-3 px-3 text-slate-500 text-xs hidden md:table-cell">{alt.company}</td>
                            {/* Live Price — always says what it covers */}
                            <td className="py-3 px-3 text-right align-top">
                              {alt.live_price ? (
                                <div>
                                  <span className="font-bold text-emerald-700 text-sm">Rs. {alt.live_price}</span>
                                  {alt.pack_desc ? (
                                    <div className="text-[10px] text-slate-400 mt-0.5">for {alt.pack_desc}</div>
                                  ) : alt.price_title ? (
                                    <div className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[140px] mx-auto" title={alt.price_title}>
                                      as listed
                                    </div>
                                  ) : null}
                                </div>
                              ) : pricesLoading || scraping?.in_progress ? (
                                <span className="inline-block w-12 h-4 bg-slate-200 rounded animate-pulse" />
                              ) : (
                                <span className="text-slate-400 text-xs">—</span>
                              )}
                            </td>
                            {/* Per Unit — only when derived from the scraped pack */}
                            <td className="py-3 px-3 text-right hidden lg:table-cell">
                              {alt.price_per_unit > 0 ? (
                                <span className="text-slate-600 text-xs">
                                  Rs. {alt.price_per_unit}/{unitWord(alt.pack_desc)}
                                </span>
                              ) : (
                                <span className="text-slate-300 text-xs">—</span>
                              )}
                            </td>
                            {/* Savings — live vs live only, per-unit when both packs known */}
                            <td className="py-3 px-3 text-right">
                              {!savings ? (
                                <span className="text-slate-300 text-xs">—</span>
                              ) : savings.is_cheaper ? (
                                <div className="flex flex-col items-end gap-0.5">
                                  <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                                    <TrendingDown className="w-3 h-3" />
                                    {savings.save_pct}%
                                  </span>
                                  {alt.savings_basis === 'per_unit' && (
                                    <span className="text-[9px] text-slate-400">per {unitWord(alt.pack_desc)}</span>
                                  )}
                                </div>
                              ) : savings.save_pct === 0 ? (
                                <span className="text-slate-400 text-xs">same</span>
                              ) : (
                                <span className="text-red-400 text-xs font-medium">+{Math.abs(savings.save_pct || 0)}%</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500">
                  <Receipt className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                  {pricesLoading ? (
                    <p>Fetching live prices from pharmacies...</p>
                  ) : (
                    <>
                      <p>No live prices available right now.</p>
                      <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
                        We only show verified live prices — database prices are outdated and never displayed.
                        Try again in a few minutes.
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Footer note */}
              {hasAlts && (
                <p className="text-[11px] text-slate-400 mt-4 text-center">
                  All prices are live from Pakistani pharmacy websites and include the pack they refer to.
                  Savings compare live prices only — per unit when both pack sizes are known.
                </p>
              )}
            </div>
          );
        })()}

        {/* ASK AI TAB */}
        {activeTab === 'askai' && (
          <div className="animate-fade-in">
            <div className="flex items-center gap-3 mb-5 pb-4 border-b border-slate-100">
              <div className="w-9 h-9 bg-emerald-100 text-emerald-700 rounded-xl flex items-center justify-center">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-base">Ask AI about {displaySalt}</h3>
                <p className="text-xs text-slate-400">{displaySalt} کے بارے میں سوال پوچھیں</p>
              </div>
            </div>
            <MedicineChat drugId={drugId} drugName={displaySalt} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MedicineDetail;
