import React, { useState } from 'react';
import api from '../api';
import { Upload, AlertCircle } from 'lucide-react';

function DataUpload({ companyId }) {
  const [sourceType, setSourceType] = useState('SAP');
  const [rawData, setRawData] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const sourceDescriptions = {
    SAP: 'SAP Fuel & Procurement CSV (PO_NUMBER, MATERIAL, DESCRIPTION, QTY_RECEIVED, UOM, RECEIPT_DATE, VENDOR, COST_CENTER)',
    UTILITY: 'Utility CSV (Account_Number, Meter_ID, Billing_Period_Start, Billing_Period_End, Usage_kWh, Peak_Demand_kW, Total_Charge_USD)',
    TRAVEL: 'Corporate Travel CSV (Expense_ID, Category, Date, Origin, Destination, Distance_km, Class_of_Service, Duration_Nights)',
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      // Parse CSV rows
      const lines = rawData.split('\n').filter((line) => line.trim());
      if (lines.length < 2) {
        setMessage({ type: 'error', text: 'Please include header row and at least one data row' });
        setLoading(false);
        return;
      }

      const headers = lines[0].split(',').map((h) => h.trim());
      const rows = lines.slice(1).map((line) => {
        const values = line.split(',');
        const obj = {};
        headers.forEach((header, idx) => {
          obj[header] = values[idx]?.trim();
        });
        return obj;
      });

      // Upload
      const response = await api.post('/upload/', {
        company_id: companyId,
        source_type: sourceType,
        data: rows,
      });

      setMessage({
        type: 'success',
        text: `Successfully ingested ${response.data.ingested_count} records. ${response.data.failed_count} failed.`,
      });
      setRawData('');
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Upload failed',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-lg shadow space-y-6">
        {/* Source type selector */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Data Source Type
          </label>
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="SAP">SAP Fuel & Procurement</option>
            <option value="UTILITY">Utility Electricity</option>
            <option value="TRAVEL">Corporate Travel</option>
          </select>

          <p className="text-sm text-gray-600 mt-2">
            <strong>Format:</strong> {sourceDescriptions[sourceType]}
          </p>
        </div>

        {/* CSV input */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            CSV Data
          </label>
          <textarea
            value={rawData}
            onChange={(e) => setRawData(e.target.value)}
            placeholder="Paste CSV data here (including header row)"
            className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <p className="text-xs text-gray-500 mt-2">
            Include header row. Each row represents one record.
          </p>
        </div>

        {/* Example */}
        <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
          <h3 className="font-semibold text-sm text-blue-900 mb-2 flex items-center gap-2">
            <AlertCircle size={16} />
            Example
          </h3>
          <pre className="text-xs text-blue-800 overflow-x-auto">
{sourceType === 'SAP' ? 
`PO_NUMBER,MATERIAL,DESCRIPTION,QTY_RECEIVED,UOM,RECEIPT_DATE,VENDOR,COST_CENTER
4500001,MAT-123,Diesel Fuel,1000,L,2026-05-10,VEN-999,CC-0001`
: sourceType === 'UTILITY' ?
`Account_Number,Meter_ID,Billing_Period_Start,Billing_Period_End,Usage_kWh,Peak_Demand_kW,Total_Charge_USD
ACC-001,M-001,2026-04-15,2026-05-14,45230,185.5,4521.30`
:
`Expense_ID,Category,Date,Origin,Destination,Distance_km,Class_of_Service,Duration_Nights
EXP-001,Airfare,2026-05-10,ORD,SEA,2100,Economy,`
}
          </pre>
        </div>

        {/* Message */}
        {message && (
          <div
            className={`p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={loading || !rawData.trim()}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
        >
          <Upload size={20} />
          {loading ? 'Uploading...' : 'Upload Data'}
        </button>
      </form>
    </div>
  );
}

export default DataUpload;
