import React from 'react';
import { Pill, Building2, Tag, ChevronRight } from 'lucide-react';

const MedicineCard = ({ medicine, onClick }) => {
  const priceNum = Number(medicine.retail_price_num) || 0;
  const price = priceNum > 0 ? `Rs. ${medicine.retail_price}` : 'Price N/A';
  const brandName = medicine.brand_name || medicine.NAME || 'Medicine';
  const saltName = medicine.salt_name || medicine.NAME || 'Generic';
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
          <h3 className="text-lg font-bold text-slate-800 leading-tight group-hover:text-primary-600 transition-colors truncate" title={brandName}>
            {brandName}
          </h3>
          <p className="text-sm text-slate-500 font-medium mt-1 truncate" title={saltName}>
            {saltName}
          </p>
        </div>
        <div className="bg-primary-50 text-primary-700 text-sm font-bold px-3 py-1 rounded-lg border border-primary-100 whitespace-nowrap flex-shrink-0">
          {price}
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
