import React, { useEffect, useState } from 'react';
import Dashboard from './components/Dashboard';
import EmissionsList from './components/EmissionsList';
import DataUpload from './components/DataUpload';
import { Menu, Upload, BarChart3, Plus } from 'lucide-react';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    console.log('App mounted, fetching companies...');
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      console.log('Fetching companies...');
      // Test with direct fetch first
      const apiUrl = process.env.REACT_APP_API_URL || 'https://breathe-esg-data-review-1.onrender.com/api';
      const response = await fetch(`${apiUrl}/companies/`);
      console.log('Fetch response status:', response.status);
      const data = await response.json();
      console.log('Fetch response data:', data);
      
      const companiesList = data.results || data;
      console.log('Companies list after parsing:', companiesList);
      setCompanies(Array.isArray(companiesList) ? companiesList : []);
      if (Array.isArray(companiesList) && companiesList.length > 0) {
        console.log('Setting selected company to:', companiesList[0].id);
        setSelectedCompany(companiesList[0].id);
      } else {
        console.log('No companies found in list');
      }
    } catch (error) {
      console.error('Error fetching companies:', error);
      setCompanies([]);
    }
  };

  const handleCompanyChange = (e) => {
    setSelectedCompany(e.target.value);
  };

  const createCompany = async () => {
    const name = prompt('Company name:');
    if (!name) return;
    const industry = prompt('Industry (optional):') || '';
    const headquarters = prompt('Headquarters (optional):') || '';
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'https://breathe-esg-data-review-1.onrender.com/api';
      const resp = await fetch(`${apiUrl}/companies/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, industry, headquarters }),
      });
      if (!resp.ok) {
        const err = await resp.text();
        alert('Failed to create company: ' + err);
        return;
      }
      await fetchCompanies();
      alert('Company created');
    } catch (err) {
      console.error(err);
      alert('Error creating company');
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-white border-r border-gray-200 transition-all duration-200`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          <span className={`font-bold text-lg ${!sidebarOpen && 'hidden'}`}>
            Breathe ESG
          </span>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <Menu size={20} />
          </button>
        </div>

        <nav className="p-4 space-y-2">
          <NavButton
            icon={<BarChart3 size={20} />}
            label="Dashboard"
            active={currentPage === 'dashboard'}
            onClick={() => setCurrentPage('dashboard')}
            collapsed={!sidebarOpen}
          />
          <NavButton
            icon={<Upload size={20} />}
            label="Upload Data"
            active={currentPage === 'upload'}
            onClick={() => setCurrentPage('upload')}
            collapsed={!sidebarOpen}
          />
          <NavButton
            icon={<BarChart3 size={20} />}
            label="Review Data"
            active={currentPage === 'review'}
            onClick={() => setCurrentPage('review')}
            collapsed={!sidebarOpen}
          />
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-gray-200 px-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {currentPage === 'dashboard' && 'Dashboard'}
            {currentPage === 'upload' && 'Upload Data'}
            {currentPage === 'review' && 'Review Emissions'}
          </h1>

          {/* Company selector */}
          <div className="flex items-center gap-2">
          <select
            value={selectedCompany || ''}
            onChange={handleCompanyChange}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a company</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
          <button
            onClick={createCompany}
            title="Add company"
            className="ml-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus size={16} />
          </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto p-8">
          {selectedCompany ? (
            <>
              {currentPage === 'dashboard' && (
                <Dashboard companyId={selectedCompany} />
              )}
              {currentPage === 'upload' && (
                <DataUpload companyId={selectedCompany} />
              )}
              {currentPage === 'review' && (
                <EmissionsList companyId={selectedCompany} />
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">
                No companies available. Please add a company first.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function NavButton({ icon, label, active, onClick, collapsed }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
        active
          ? 'bg-blue-100 text-blue-700'
          : 'text-gray-700 hover:bg-gray-100'
      }`}
    >
      {icon}
      {!collapsed && <span>{label}</span>}
    </button>
  );
}

export default App;
