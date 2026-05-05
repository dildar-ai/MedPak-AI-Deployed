import React, { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, ShieldAlert, CheckCircle2, Pill, Activity, Receipt, Loader2, Info } from 'lucide-react';
import { medicineApi } from '../lib/api';

const Section = ({ icon: Icon, iconColor, title, titleUrdu, children }) => (
  <section className="mb-8 last:mb-0">
    <h3 className="text-lg font-bold text-slate-800 mb-1 flex items-center gap-2">
      <Icon className={`w-5 h-5 ${iconColor}`} />
      {title}
    </h3>
    {titleUrdu && (
      <p className="text-sm text-slate-400 font-urdu mb-3">{titleUrdu}</p>
    )}
    <div className="text-slate-600 leading-relaxed whitespace-pre-wrap text-[15px]">
      {children}
    </div>
  </section>
);

const MedicineDetail = ({ drugId, brandData, onBack }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alternatives, setAlternatives] = useState([]);
  const [activeTab, setActiveTab] = useState('info');

  useEffect(() => {
    const fetchDetails = async () => {
      setLoading(true);
      try {
        const data = await medicineApi.getDetails(drugId);
        setDetails(data);
        
        medicineApi.getAlternatives(drugId).then(altData => {
          setAlternatives(altData.alternatives || []);
        }).catch(err => console.error("Failed to load alternatives", err));
        
      } catch (error) {
        console.error("Failed to load details", error);
      } finally {
        setLoading(false);
      }
    };
    
    if (drugId) fetchDetails();
  }, [drugId]);

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

  const tabs = [
    { key: 'info', label: 'Information', labelUrdu: 'معلومات', icon: Activity },
    { key: 'dosage', label: 'Dosage', labelUrdu: 'خوراک', icon: Pill },
    { key: 'alternatives', label: 'Alternatives', labelUrdu: 'متبادل', icon: Receipt },
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
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-100 rounded-full blur-3xl opacity-40 -translate-y-1/2 translate-x-1/4 pointer-events-none"></div>
        
        <div className="relative z-10">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="badge badge-primary">Code: {drug.CODE}</span>
            <span className="badge badge-slate">Generic Salt</span>
          </div>
          
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-1">{drug.NAME}</h2>
          
          {brandData && brandData.brand_name && brandData.brand_name !== drug.NAME && (
            <p className="text-base text-slate-600 font-medium">
              Brand: <span className="text-primary-700 font-semibold">{brandData.brand_name}</span>
            </p>
          )}
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
                ? 'bg-white text-primary-700 shadow-sm' 
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
                neonatal: { en: 'Neonatal (نوزائیدہ)', color: 'bg-purple-50 border-purple-100' },
                paediatric: { en: 'Paediatric (بچوں)', color: 'bg-blue-50 border-blue-100' },
                adult: { en: 'Adult (بالغ)', color: 'bg-green-50 border-green-100' },
              };
              const label = ageLabels[ageGroup];

              return dosage[ageGroup] && dosage[ageGroup].length > 0 && (
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
                        <div className="flex gap-2 flex-wrap">
                          <span className="badge badge-primary">{d.FREQ}</span>
                          <span className="badge bg-slate-200 text-slate-700">{d.ROUTE}</span>
                          {d.SINGLE && <span className="badge bg-purple-100 text-purple-700">Max: {d.SINGLE}</span>}
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
        {activeTab === 'alternatives' && (
          <div className="animate-fade-in">
            <h3 className="text-lg font-bold text-slate-800 mb-1">Cheaper Alternatives for {drug.NAME}</h3>
            <p className="text-sm text-slate-400 mb-5">{drug.NAME} کے سستے متبادل</p>
            
            {alternatives.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="py-3 px-4 font-semibold text-slate-700 text-sm">Brand / برانڈ</th>
                      <th className="py-3 px-4 font-semibold text-slate-700 text-sm">Form</th>
                      <th className="py-3 px-4 font-semibold text-slate-700 text-sm hidden md:table-cell">Company</th>
                      <th className="py-3 px-4 font-semibold text-slate-700 text-sm text-right">Price (PKR)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {alternatives.map((alt, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-semibold text-primary-700 text-sm">{alt.brand_product_name}</td>
                        <td className="py-3 px-4 text-slate-600 text-sm">{alt.form} {alt.strength}</td>
                        <td className="py-3 px-4 text-slate-500 text-sm hidden md:table-cell">{alt.company}</td>
                        <td className="py-3 px-4 font-bold text-slate-800 text-right text-sm">{alt.retail_price}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                <Receipt className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <p>No priced alternatives found.</p>
                <p className="text-sm text-slate-400 mt-1">کوئی متبادل نہیں ملا۔</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MedicineDetail;
