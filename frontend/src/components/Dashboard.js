import React, { useEffect, useState, useCallback } from 'react';
import api from '../api';
import { Activity, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';

function Dashboard({ companyId }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/dashboard/summary/', {
        params: { company_id: companyId },
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [fetchStats]);

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  if (!stats) {
    return <div className="text-center py-12">No data available</div>;
  }

  const totalCO2e = (parseFloat(stats.total_co2e_kg) / 1000).toFixed(2); // Convert to tonnes

  return (
    <div className="space-y-6">
      {/* Key metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Records"
          value={stats.total_records}
          icon={<Activity size={24} />}
          color="blue"
        />
        <StatCard
          title="Total CO₂e"
          value={`${totalCO2e}T`}
          icon={<TrendingUp size={24} />}
          color="green"
        />
        <StatCard
          title="Pending Review"
          value={stats.pending_review}
          icon={<AlertCircle size={24} />}
          color="yellow"
        />
        <StatCard
          title="Approved"
          value={stats.approved}
          icon={<CheckCircle size={24} />}
          color="green"
        />
      </div>

      {/* By Scope */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(stats.by_scope || {}).map(([scope, count]) => (
          <div key={scope} className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-semibold text-gray-900 mb-2">{formatScope(scope)}</h3>
            <p className="text-3xl font-bold text-blue-600">{count}</p>
          </div>
        ))}
      </div>

      {/* By Category */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">By Category</h2>
        <div className="space-y-2">
          {Object.entries(stats.by_category || {})
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10)
            .map(([category, count]) => (
              <div key={category} className="flex justify-between items-center">
                <span className="text-gray-700">{formatCategory(category)}</span>
                <span className="font-semibold">{count}</span>
              </div>
            ))}
        </div>
      </div>

      {/* Flagged Anomalies */}
      {Object.keys(stats.flagged_anomalies || {}).length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertCircle size={20} className="text-yellow-600" />
            Flagged Anomalies
          </h2>
          <div className="space-y-2">
            {Object.entries(stats.flagged_anomalies).map(([anomaly, count]) => (
              <div key={anomaly} className="flex justify-between">
                <span className="text-gray-700">{formatAnomaly(anomaly)}</span>
                <span className="font-semibold text-yellow-600">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  const colorClass = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
  }[color];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className={`${colorClass} w-12 h-12 rounded-lg flex items-center justify-center mb-4`}>
        {icon}
      </div>
      <h3 className="text-gray-600 text-sm font-medium">{title}</h3>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
    </div>
  );
}

function formatScope(scope) {
  const map = {
    SCOPE_1: 'Scope 1 - Direct',
    SCOPE_2: 'Scope 2 - Purchased',
    SCOPE_3: 'Scope 3 - Value Chain',
  };
  return map[scope] || scope;
}

function formatCategory(cat) {
  return cat
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function formatAnomaly(anomaly) {
  const map = {
    UNIT_MISMATCH: 'Unit Conversion Unclear',
    MISSING_FACTOR: 'Emission Factor Missing',
    OUTLIER: 'Outlier Value',
    DATE_INCONSISTENT: 'Date Inconsistent',
    DUPLICATE_LIKELY: 'Likely Duplicate',
  };
  return map[anomaly] || anomaly;
}

export default Dashboard;
