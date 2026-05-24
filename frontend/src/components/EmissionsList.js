import React, { useState, useEffect } from 'react';
import api from '../api';
import { Check, X, Flag } from 'lucide-react';

function EmissionsList({ companyId }) {
  const [emissions, setEmissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    approval_status: 'PENDING_REVIEW',
    flagged_anomaly: '',
  });
  const [selectedEmission, setSelectedEmission] = useState(null);

  useEffect(() => {
    fetchEmissions();
  }, [companyId, filters]);

  const fetchEmissions = async () => {
    setLoading(true);
    try {
      const params = {
        company: companyId,
        ...filters,
      };
      if (!filters.flagged_anomaly) delete params.flagged_anomaly;

      const response = await api.get('/emissions/', { params });
      setEmissions(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching emissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (emission) => {
    try {
      await api.post(`/emissions/${emission.id}/approve/`, {
        reason: 'Approved by analyst',
      });
      setEmissions(emissions.map((e) => (e.id === emission.id ? { ...e, approval_status: 'APPROVED' } : e)));
      setSelectedEmission(null);
    } catch (error) {
      console.error('Error approving emission:', error);
    }
  };

  const handleReject = async (emission) => {
    try {
      await api.post(`/emissions/${emission.id}/reject/`, {
        reason: 'Rejected by analyst',
      });
      setEmissions(emissions.map((e) => (e.id === emission.id ? { ...e, approval_status: 'REJECTED' } : e)));
      setSelectedEmission(null);
    } catch (error) {
      console.error('Error rejecting emission:', error);
    }
  };

  const handleFlag = async (emission, anomaly) => {
    try {
      await api.post(`/emissions/${emission.id}/flag_anomaly/`, {
        anomaly_type: anomaly,
        notes: `Flagged as ${anomaly}`,
      });
      setEmissions(
        emissions.map((e) =>
          e.id === emission.id ? { ...e, flagged_anomaly: anomaly } : e
        )
      );
    } catch (error) {
      console.error('Error flagging emission:', error);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow flex gap-4">
        <select
          value={filters.approval_status}
          onChange={(e) =>
            setFilters({ ...filters, approval_status: e.target.value })
          }
          className="px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="NEEDS_CLARIFICATION">Needs Clarification</option>
        </select>

        <select
          value={filters.flagged_anomaly}
          onChange={(e) =>
            setFilters({ ...filters, flagged_anomaly: e.target.value })
          }
          className="px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Anomalies</option>
          <option value="UNIT_MISMATCH">Unit Mismatch</option>
          <option value="MISSING_FACTOR">Missing Factor</option>
          <option value="OUTLIER">Outlier</option>
          <option value="DUPLICATE_LIKELY">Likely Duplicate</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Category</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Quantity</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">CO₂e (kg)</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Scope</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Anomaly</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {emissions.map((emission) => (
              <tr key={emission.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedEmission(emission)}>
                <td className="px-6 py-4 text-sm text-gray-900">{emission.category_display}</td>
                <td className="px-6 py-4 text-sm text-gray-700">
                  {emission.quantity_value} {emission.quantity_unit}
                </td>
                <td className="px-6 py-4 text-sm font-semibold text-gray-900">
                  {emission.quantity_kg_co2e?.toFixed(2) || 'N/A'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-700">{emission.scope_display}</td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={emission.approval_status} />
                </td>
                <td className="px-6 py-4 text-sm">
                  {emission.flagged_anomaly !== 'NONE' && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs">
                      <Flag size={12} />
                      {emission.flagged_anomaly}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm flex gap-2" onClick={(e) => e.stopPropagation()}>
                  {emission.approval_status === 'PENDING_REVIEW' && (
                    <>
                      <button
                        onClick={() => handleApprove(emission)}
                        className="p-1 hover:bg-green-100 text-green-600 rounded"
                      >
                        <Check size={16} />
                      </button>
                      <button
                        onClick={() => handleReject(emission)}
                        className="p-1 hover:bg-red-100 text-red-600 rounded"
                      >
                        <X size={16} />
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail panel */}
      {selectedEmission && (
        <EmissionDetailPanel
          emission={selectedEmission}
          onClose={() => setSelectedEmission(null)}
          onApprove={handleApprove}
          onReject={handleReject}
          onFlag={handleFlag}
        />
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const statusConfig = {
    PENDING_REVIEW: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Pending Review' },
    APPROVED: { bg: 'bg-green-100', text: 'text-green-700', label: 'Approved' },
    REJECTED: { bg: 'bg-red-100', text: 'text-red-700', label: 'Rejected' },
    NEEDS_CLARIFICATION: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Needs Clarification' },
  };

  const config = statusConfig[status] || {};
  return (
    <span className={`inline-flex px-2 py-1 rounded text-xs font-semibold ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
}

function EmissionDetailPanel({ emission, onClose, onApprove, onReject, onFlag }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-end z-50">
      <div className="bg-white w-full max-w-md h-full overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold">Emission Details</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              ✕
            </button>
          </div>

          <div className="space-y-4">
            <DetailRow label="Category" value={emission.category_display} />
            <DetailRow label="Scope" value={emission.scope_display} />
            <DetailRow label="Quantity" value={`${emission.quantity_value} ${emission.quantity_unit}`} />
            <DetailRow label="CO₂e (kg)" value={emission.quantity_kg_co2e?.toFixed(4) || 'N/A'} />
            <DetailRow label="Activity Date" value={emission.activity_date} />
            {emission.facility && <DetailRow label="Facility" value={emission.facility} />}
            {emission.vendor_supplier && <DetailRow label="Vendor" value={emission.vendor_supplier} />}
            {emission.analyst_notes && <DetailRow label="Notes" value={emission.analyst_notes} />}
          </div>

          {emission.approval_status === 'PENDING_REVIEW' && (
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => onApprove(emission)}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg flex items-center justify-center gap-2"
              >
                <Check size={16} /> Approve
              </button>
              <button
                onClick={() => onReject(emission)}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg flex items-center justify-center gap-2"
              >
                <X size={16} /> Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div>
      <p className="text-sm text-gray-600">{label}</p>
      <p className="text-gray-900 font-medium">{value}</p>
    </div>
  );
}

export default EmissionsList;
