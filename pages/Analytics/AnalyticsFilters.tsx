import React from "react";
import type { FilterOptions } from "../../services/AnalyticsService";
import { Filter, RefreshCw } from "lucide-react";

interface Props {
  filters: FilterOptions;
  setFilters: React.Dispatch<React.SetStateAction<FilterOptions>>;
  onApply: () => void;
  onReset: () => void;
}

export default function AnalyticsFilters({ filters, setFilters, onApply, onReset }: Props) {
  const handleChange = (field: keyof FilterOptions, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 mb-6 flex flex-col md:flex-row flex-wrap gap-4 items-end">
      <div className="flex items-center gap-2 text-brandBlue font-bold mr-2">
         <Filter size={20} /> Filters
      </div>
      
      <div className="flex-1 min-w-[150px]">
        <label className="block text-xs text-gray-500 mb-1">Date Range</label>
        <select 
           value={filters.dateRange} 
           onChange={e => handleChange("dateRange", e.target.value)}
           className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option>Today</option>
          <option>Last 7 Days</option>
          <option>Last 30 Days</option>
          <option>Last 3 Months</option>
          <option>Custom Range</option>
        </select>
      </div>

      <div className="flex-1 min-w-[150px]">
        <label className="block text-xs text-gray-500 mb-1">State</label>
        <select disabled className="w-full border border-gray-300 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-500">
          <option>Maharashtra</option>
        </select>
      </div>

      <div className="flex-1 min-w-[150px]">
        <label className="block text-xs text-gray-500 mb-1">District</label>
        <select 
           value={filters.district} 
           onChange={e => handleChange("district", e.target.value)}
           className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option>All</option>
          <option>Pune</option>
          <option>Nashik</option>
          <option>Nagpur</option>
          <option>Mumbai</option>
          <option>Chhatrapati Sambhajinagar</option>
        </select>
      </div>

      <div className="flex-1 min-w-[150px]">
        <label className="block text-xs text-gray-500 mb-1">Species</label>
        <select 
           value={filters.species} 
           onChange={e => handleChange("species", e.target.value)}
           className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option>All</option>
          <option>Cattle</option>
          <option>Buffalo</option>
          <option>Goat</option>
          <option>Sheep</option>
          <option>Poultry</option>
          <option>Pig</option>
        </select>
      </div>

      <div className="flex-1 min-w-[150px]">
        <label className="block text-xs text-gray-500 mb-1">Disease</label>
        <select 
           value={filters.disease} 
           onChange={e => handleChange("disease", e.target.value)}
           className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option>All</option>
          <option>FMD</option>
          <option>LSD</option>
          <option>PPR</option>
          <option>Brucellosis</option>
        </select>
      </div>

      <div className="flex gap-2 w-full md:w-auto mt-2 md:mt-0">
        <button onClick={onReset} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors">
          Reset
        </button>
        <button onClick={onApply} className="px-4 py-2 bg-brandBlue text-white hover:bg-blue-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
          <RefreshCw size={16} /> Apply Filters
        </button>
      </div>
    </div>
  );
}

