import { useState, useEffect } from 'react';
import {
  Package,
  Plus,
  Search,
  Filter,
  Upload,
  AlertCircle,
  X,
  Edit2,
  Trash2,
  Download,
} from 'lucide-react';

type CriticalityLevel = 'low' | 'medium' | 'high' | 'critical';

interface Application {
  id: number;
  name: string;
  description: string | null;
  criticality: CriticalityLevel;
  tech_stack: string | null;
  owner: string | null;
  business_unit_id: number;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

interface BusinessUnit {
  id: number;
  name: string;
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [businessUnits, setBusinessUnits] = useState<BusinessUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [criticalityFilter, setCriticalityFilter] = useState<CriticalityLevel | 'all'>('all');
  const [businessUnitFilter, setBusinessUnitFilter] = useState<number | 'all'>('all');

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    criticality: 'medium' as CriticalityLevel,
    tech_stack: '',
    owner: '',
    business_unit_id: 0,
  });

  // CSV import
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{
    total: number;
    success: number;
    failed: number;
    errors: string[];
  } | null>(null);

  // Count
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchBusinessUnits();
    fetchApplications();
    fetchCount();
  }, [searchTerm, criticalityFilter, businessUnitFilter]);

  const fetchBusinessUnits = async () => {
    try {
      const response = await fetch('http://localhost:7777/api/v1/organizations/');
      if (!response.ok) throw new Error('Failed to fetch organizations');
      const orgs = await response.json();

      // Fetch divisions for each org
      const allBusinessUnits: BusinessUnit[] = [];
      for (const org of orgs) {
        const hierarchyResponse = await fetch(
          `http://localhost:7777/api/v1/organizations/${org.id}/hierarchy`
        );
        if (hierarchyResponse.ok) {
          const hierarchy = await hierarchyResponse.json();
          for (const division of hierarchy.divisions || []) {
            for (const bu of division.business_units || []) {
              allBusinessUnits.push({ id: bu.id, name: `${org.name} > ${division.name} > ${bu.name}` });
            }
          }
        }
      }
      setBusinessUnits(allBusinessUnits);
    } catch (err) {
      console.error('Failed to load business units:', err);
    }
  };

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (criticalityFilter !== 'all') params.append('criticality', criticalityFilter);
      if (businessUnitFilter !== 'all') params.append('business_unit_id', businessUnitFilter.toString());
      params.append('limit', '100');

      const response = await fetch(`http://localhost:7777/api/v1/applications/?${params}`);
      if (!response.ok) throw new Error('Failed to fetch applications');
      const data = await response.json();
      setApplications(data);
    } catch (err) {
      setError('Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const fetchCount = async () => {
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (criticalityFilter !== 'all') params.append('criticality', criticalityFilter);
      if (businessUnitFilter !== 'all') params.append('business_unit_id', businessUnitFilter.toString());

      const response = await fetch(`http://localhost:7777/api/v1/applications/count?${params}`);
      if (!response.ok) throw new Error('Failed to fetch count');
      const data = await response.json();
      setTotalCount(data.count);
    } catch (err) {
      console.error('Failed to fetch count:', err);
    }
  };

  const createApplication = async () => {
    try {
      const response = await fetch('http://localhost:7777/api/v1/applications/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to create application');
      await fetchApplications();
      await fetchCount();
      setShowAddModal(false);
      resetForm();
    } catch (err) {
      setError('Failed to create application');
    }
  };

  const updateApplication = async () => {
    if (!selectedApp) return;
    try {
      const response = await fetch(`http://localhost:7777/api/v1/applications/${selectedApp.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to update application');
      await fetchApplications();
      setShowEditModal(false);
      setSelectedApp(null);
      resetForm();
    } catch (err) {
      setError('Failed to update application');
    }
  };

  const deleteApplication = async () => {
    if (!selectedApp) return;
    try {
      const response = await fetch(`http://localhost:7777/api/v1/applications/${selectedApp.id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete application');
      await fetchApplications();
      await fetchCount();
      setShowDeleteModal(false);
      setSelectedApp(null);
    } catch (err) {
      setError('Failed to delete application');
    }
  };

  const importCSV = async () => {
    if (!csvFile) return;
    try {
      const formData = new FormData();
      formData.append('file', csvFile);

      const response = await fetch('http://localhost:7777/api/v1/applications/import-csv', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error('Failed to import CSV');
      const result = await response.json();
      setImportResult(result);
      await fetchApplications();
      await fetchCount();
      setCsvFile(null);
    } catch (err) {
      setError('Failed to import CSV');
    }
  };

  const downloadCSVTemplate = () => {
    const template = 'name,business_unit_id,description,criticality,tech_stack,owner\nExpenseApp,1,Expense management system,high,Java Spring Boot PostgreSQL,john@example.com';
    const blob = new Blob([template], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'applications_template.csv';
    a.click();
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      criticality: 'medium',
      tech_stack: '',
      owner: '',
      business_unit_id: 0,
    });
  };

  const openEditModal = (app: Application) => {
    setSelectedApp(app);
    setFormData({
      name: app.name,
      description: app.description || '',
      criticality: app.criticality,
      tech_stack: app.tech_stack || '',
      owner: app.owner || '',
      business_unit_id: app.business_unit_id,
    });
    setShowEditModal(true);
  };

  const getCriticalityColor = (criticality: CriticalityLevel) => {
    switch (criticality) {
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'low':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">Applications</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage enterprise applications ({totalCount} total)
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-50 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-700 flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Import CSV
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Application
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search applications..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
            />
          </div>

          {/* Criticality Filter */}
          <div>
            <select
              value={criticalityFilter}
              onChange={(e) => setCriticalityFilter(e.target.value as CriticalityLevel | 'all')}
              className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
            >
              <option value="all">All Criticality Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Business Unit Filter */}
          <div>
            <select
              value={businessUnitFilter}
              onChange={(e) => setBusinessUnitFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
              className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
            >
              <option value="all">All Business Units</option>
              {businessUnits.map((bu) => (
                <option key={bu.id} value={bu.id}>
                  {bu.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <p className="text-red-800 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Applications Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">Loading applications...</div>
      ) : applications.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-12 text-center">
          <Package className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-2">
            No applications found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Get started by adding your first application or importing from CSV
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Application
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {applications.map((app) => (
            <div
              key={app.id}
              className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4 hover:border-blue-500 dark:hover:border-blue-500 transition-colors"
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <Package className="w-5 h-5 text-blue-600" />
                  <h3 className="font-medium text-gray-900 dark:text-gray-50">{app.name}</h3>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => openEditModal(app)}
                    className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      setSelectedApp(app);
                      setShowDeleteModal(true);
                    }}
                    className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getCriticalityColor(app.criticality)}`}>
                  {app.criticality.toUpperCase()}
                </span>

                {app.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                    {app.description}
                  </p>
                )}

                {app.tech_stack && (
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    <strong>Tech:</strong> {app.tech_stack}
                  </p>
                )}

                {app.owner && (
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    <strong>Owner:</strong> {app.owner}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {(showAddModal || showEditModal) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
              {showAddModal ? 'Add Application' : 'Edit Application'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Business Unit *
                </label>
                <select
                  value={formData.business_unit_id}
                  onChange={(e) => setFormData({ ...formData, business_unit_id: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                >
                  <option value={0}>Select business unit</option>
                  {businessUnits.map((bu) => (
                    <option key={bu.id} value={bu.id}>
                      {bu.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Criticality
                </label>
                <select
                  value={formData.criticality}
                  onChange={(e) => setFormData({ ...formData, criticality: e.target.value as CriticalityLevel })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Tech Stack
                </label>
                <input
                  type="text"
                  value={formData.tech_stack}
                  onChange={(e) => setFormData({ ...formData, tech_stack: e.target.value })}
                  placeholder="e.g., Java, Spring Boot, PostgreSQL"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Owner
                </label>
                <input
                  type="text"
                  value={formData.owner}
                  onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
                  placeholder="e.g., john@example.com"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={showAddModal ? createApplication : updateApplication}
                disabled={!formData.name || !formData.business_unit_id}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {showAddModal ? 'Create' : 'Update'}
              </button>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setShowEditModal(false);
                  setSelectedApp(null);
                  resetForm();
                }}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-50 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import CSV Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-2xl">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Import Applications from CSV
            </h2>

            {!importResult ? (
              <div className="space-y-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-900 rounded-lg p-4">
                  <p className="text-sm text-blue-800 dark:text-blue-400">
                    CSV format: name, business_unit_id, description, criticality, tech_stack, owner
                  </p>
                </div>

                <div>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  />
                </div>

                <button
                  onClick={downloadCSVTemplate}
                  className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
                >
                  <Download className="w-4 h-4" />
                  Download CSV Template
                </button>

                <div className="flex gap-2">
                  <button
                    onClick={importCSV}
                    disabled={!csvFile}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Import
                  </button>
                  <button
                    onClick={() => {
                      setShowImportModal(false);
                      setCsvFile(null);
                    }}
                    className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-50 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900 rounded-lg p-4">
                  <p className="text-sm text-green-800 dark:text-green-400">
                    Import complete: {importResult.success} / {importResult.total} applications imported successfully
                  </p>
                  {importResult.failed > 0 && (
                    <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                      {importResult.failed} applications failed to import
                    </p>
                  )}
                </div>

                {importResult.errors.length > 0 && (
                  <div className="max-h-64 overflow-y-auto space-y-1">
                    {importResult.errors.map((error, idx) => (
                      <p key={idx} className="text-xs text-red-600 dark:text-red-400">
                        {error}
                      </p>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => {
                    setShowImportModal(false);
                    setImportResult(null);
                    setCsvFile(null);
                  }}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && selectedApp && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Delete Application
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Are you sure you want to delete <strong>{selectedApp.name}</strong>? This action cannot be undone.
            </p>
            <div className="flex gap-2">
              <button
                onClick={deleteApplication}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Delete
              </button>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setSelectedApp(null);
                }}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-50 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
