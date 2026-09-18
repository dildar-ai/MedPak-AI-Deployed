import React from 'react';
import { Pill, Building2, Tag, ChevronRight, Wifi, RefreshCw } from 'lucide-react';
import { unitWord } from '../lib/format';

const MedicineCard = ({ medicine, onClick }) => {
  // Live price only — DB prices are outdated and never shown to users.
  const livePrice = medicine.live_price_pkr || null;
  const pricePerUnit = livePrice ? medicine.price_per_unit : null;
  const packDesc = medicine.pack_desc || '';

  const brandName = medicine.brand_name || medicine.NAME || 'Medicine';
  const saltName = medicine.salt_name || medicine.NAME || 'Generic';
  const saltDisplay = medicine.salt_names?.length
    ? medicine.salt_names.join(' + ')
    : saltName;
  const form = medicine.form || '';
  const strength = medicine.strength || '';
  const packing = medicine.packing || '';
  const company = medicine.company || 'Unknown';

  return (
    <div 
      onClick={() => onClick(medicine)}
      className="glass-card p-5 cursor-pointer flex flex-col h-full animate-fade-in group"
    >
      <div className="flex justify-between items-start mb-3 gap-2">
        <div className="min-w-0">
          <h3 className="text-lg font-bold text-slate-800 leading-tight group-hover:text-primary-600 transition-colors truncate" title={`${brandName} ${form}`}>
            {brandName} {form && <span className="font-extrabold text-slate-500 ml-1">{form}</span>}
          </h3>
          <p className="text-sm text-slate-500 font-medium mt-1 truncate" title={saltDisplay}>
            {saltDisplay}
          </p>
        </div>

        {/* ── Price Badge Area ── */}
        <div className="flex flex-col items-end flex-shrink-0 gap-1">
          {livePrice ? (
            <div className="text-sm font-bold px-3 py-1 rounded-lg border whitespace-nowrap bg-emerald-50 text-emerald-700 border-emerald-200">
              Rs. {livePrice}
            </div>
          ) : (
            <div className="flex items-center gap-1 text-xs font-medium px-3 py-1 rounded-lg border whitespace-nowrap bg-slate-50 text-slate-400 border-slate-200">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Live price…
            </div>
          )}
          {livePrice && (
            <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-medium">
              <Wifi className="w-3 h-3" /> Live
            </span>
          )}
          {livePrice && packDesc && (
            <span className="text-[10px] text-slate-400 font-medium whitespace-nowrap" title={`Price covers: ${packDesc}`}>
              for {packDesc}
            </span>
          )}
          {pricePerUnit && pricePerUnit > 0 && (
            <span className="text-[10px] text-slate-400 font-medium">
              Rs. {pricePerUnit}/{unitWord(packDesc)}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2 mt-3 flex-grow">
        {(form || strength) && (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Pill className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <span className="truncate">{[form, strength].filter(Boolean).join(' ')}</span>
          </div>
        )}
        
        {packing && (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Tag className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <span>Pack: {packing}</span>
          </div>
        )}
        
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Building2 className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <span className="truncate" title={company}>{company}</span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-sm font-medium text-primary-600 group-hover:text-primary-700">
        <span>View full details</span>
        <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
      </div>
    </div>
  );
};

export default MedicineCard;
