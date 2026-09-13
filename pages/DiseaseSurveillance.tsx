import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

const tabs = ['Reported Cases', 'Suspected Outbreaks', 'Confirmed Outbreaks', 'Mortality Reports'];

export default function DiseaseSurveillance() {
  const { reports } = useAppContext();
  const [activeTab, setActiveTab] = useState(tabs[0]);
  
  // Filter logic based on tabs (simplified)
  const filteredReports = reports.filter(r => {
    if (activeTab === 'Reported Cases') return true;
    if (activeTab === 'Suspected Outbreaks') return r.status === 'Suspected';
    if (activeTab === 'Confirmed Outbreaks') return r.status === 'Confirmed';
    if (activeTab === 'Mortality Reports') return r.numberDead > 0;
    return true;
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-4 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab 
                ? 'border-brandBlue text-brandBlue' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-gray-100 flex flex-wrap gap-4 items-end">
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">Date Range</label>
          <select className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border">
            <option>Last 30 days</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">Species</label>
          <select className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border">
            <option>All</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">District</label>
          <select className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border">
            <option>All</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">Disease</label>
          <select className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border">
            <option>All</option>
          </select>
        </div>
        <button className="bg-brandBlue text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-600 transition-colors">
          Search
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              {['Date', 'Village', 'District', 'Species', 'Disease', 'Cases', 'Deaths', 'Status'].map(col => (
                <th key={col} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredReports.map((row) => (
              <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.date}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.village}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.district}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.species}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.disease || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.numberAffected}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.numberDead}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    row.status === 'Suspected' ? 'bg-red-100 text-red-800' :
                    row.status === 'Under Review' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {row.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="p-4 border-t border-gray-200 flex justify-end">
        <button className="bg-brandBlue text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-600 transition-colors">
          View Details
        </button>
      </div>
    </div>
  );
}
