import { useState, useEffect } from 'react';
import {
  Waves,
  Plus,
  Search,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  FileText,
  Filter,
  Users,
  BarChart3,
} from 'lucide-react';

type WaveStatus = 'planned' | 'in_progress' | 'completed' | 'paused' | 'cancelled';

interface MigrationWave {
  id: number;
  name: string;
  description: string | null;
  status: WaveStatus;
  total_applications: number;
  scanned_applications: number;
  provisioned_applications: number;
  progress_percentage: number;
  provisioned_percentage: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface WaveWithApplications extends MigrationWave {
  application_ids: number[];
}

interface Application {
  id: number;
  name: string;
  criticality: 'low' | 'medium' | 'high' | 'critical';
  business_unit_id: number;
}

interface Division {
  id: number;
  name: string;
  organization_id: number;
}

interface WaveReport {
  wave_id: number;
  wave_name: string;
  status: WaveStatus;
  total_applications: number;
  scanned_applications: number;
  provisioned_applications: number;
  progress_percentage: number;
  provisioned_percentage: number;
  started_at: string | null;
  completed_at: string | null;
  duration_minutes: number | null;
  policies_extracted: number;
  policies_provisioned: number;
  high_risk_policies: number;
  conflicts_detected: number;
}

export default function MigrationWavesPage() {
  const [waves, setWaves] = useState<MigrationWave[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [divisions, setDivisions] = useState<Division[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddAppsModal, setShowAddAppsModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showVelocityModal, setShowVelocityModal] = useState(false);
  const [selectedWave, setSelectedWave] = useState<WaveWithApplications | null>(null);
  const [report, setReport] = useState<WaveReport | null>(null);
  const [velocityData, setVelocityData] = useState<WaveReport[]>([]);

  // Filters
  const [statusFilter, setStatusFilter] = useState<WaveStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    application_ids: [] as number[],
  });

  // Selected applications for adding to wave
  const [selectedAppIds, setSelectedAppIds] = useState<number[]>([]);
  const [criticalityFilter, setCriticalityFilter] = useState<string>('all');
  const [divisionFilter, setDivisionFilter] = useState<string>('all');

  useEffect(() => {
    fetchWaves();
    fetchApplications();
    fetchDivisions();
  }, [statusFilter]);

  // Fetch applications when division filter changes
  useEffect(() => {
    fetchApplications();
  }, [divisionFilter]);

  const fetchWaves = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const response = await fetch(`http://localhost:7777/api/v1/migration-waves/?${params}`, {
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) throw new Error('Failed to fetch migration waves');

      const data = await response.json();
      setWaves(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch migration waves');
    } finally {
      setLoading(false);
    }
  };

  const fetchApplications = async () => {
    try {
      const params = new URLSearchParams();
      if (divisionFilter !== 'all') {
        params.append('division_id', divisionFilter);
      }

      const response = await fetch(`http://localhost:7777/api/v1/applications/?${params}`, {
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) throw new Error('Failed to fetch applications');

      const data = await response.json();
      setApplications(data);
    } catch (err) {
      console.error('Failed to fetch applications:', err);
    }
  };

  const fetchDivisions = async () => {
    try {
      // Fetch from the first organization (assuming single org for now)
      const response = await fetch('http://localhost:7777/api/v1/organizations/1/divisions', {
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch divisions');
        return;
      }

      const data = await response.json();
      setDivisions(data);
    } catch (err) {
      console.error('Failed to fetch divisions:', err);
    }
  };

  const fetchWaveDetails = async (waveId: number) => {
    try {
      const response = await fetch(`http://localhost:7777/api/v1/migration-waves/${waveId}`, {
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) throw new Error('Failed to fetch wave details');

      const data = await response.json();
      setSelectedWave(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch wave details');
    }
  };

  const fetchReport = async (waveId: number) => {
    try {
      const response = await fetch(`http://localhost:7777/api/v1/migration-waves/${waveId}/report`, {
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) throw new Error('Failed to generate report');

      const data = await response.json();
      setReport(data);
      setShowReportModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    }
  };

  const createWave = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch('http://localhost:7777/api/v1/migration-waves/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': 'test-tenant-001',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) throw new Error('Failed to create migration wave');

      await fetchWaves();
      setShowCreateModal(false);
      setFormData({ name: '', description: '', application_ids: [] });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create migration wave');
    }
  };

  const updateWaveStatus = async (waveId: number, status: WaveStatus) => {
    try {
      const response = await fetch(`http://localhost:7777/api/v1/migration-waves/${waveId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': 'test-tenant-001',
        },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) throw new Error('Failed to update wave status');

      await fetchWaves();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update wave status');
    }
  };

  const startWaveScan = async (waveId: number) => {
    try {
      const response = await fetch(`http://localhost:7777/api/v1/migration-waves/${waveId}/scan`, {
        method: 'POST',
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) throw new Error('Failed to start wave scan');

      const data = await response.json();
      setError('');

      // Show success message
      alert(`Scan started for ${data.application_count} applications (${data.repository_count} repositories)\nTask ID: ${data.task_id}`);

      await fetchWaves();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start wave scan');
    }
  };

  const fetchVelocityComparison = async () => {
    try {
      const response = await fetch('http://localhost:7777/api/v1/migration-waves/velocity-comparison?limit=10', {
        headers: {
          'X-Tenant-ID': 'test-tenant-001',
        },
      });

      if (!response.ok) throw new Error('Failed to fetch velocity comparison');

      const data = await response.json();
      setVelocityData(data);
      setShowVelocityModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch velocity comparison');
    }
  };

  const addApplicationsToWave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedWave || selectedAppIds.length === 0) return;

    try {
      const response = await fetch(
        `http://localhost:7777/api/v1/migration-waves/${selectedWave.id}/applications`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Tenant-ID': 'test-tenant-001',
          },
          body: JSON.stringify({ application_ids: selectedAppIds }),
        }
      );

      if (!response.ok) throw new Error('Failed to add applications');

      await fetchWaves();
      await fetchWaveDetails(selectedWave.id);
      setShowAddAppsModal(false);
      setSelectedAppIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add applications');
    }
  };

  const getStatusIcon = (status: WaveStatus) => {
    switch (status) {
      case 'planned':
        return <Clock className="w-5 h-5 text-gray-500" />;
      case 'in_progress':
        return <Play className="w-5 h-5 text-blue-600" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'paused':
        return <Pause className="w-5 h-5 text-amber-600" />;
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-red-600" />;
    }
  };

  const getStatusColor = (status: WaveStatus) => {
    switch (status) {
      case 'planned':
        return 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300';
      case 'in_progress':
        return 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300';
      case 'completed':
        return 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300';
      case 'paused':
        return 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300';
      case 'cancelled':
        return 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300';
    }
  };

  const filteredWaves = waves.filter((wave) => {
    const matchesSearch = wave.name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const filteredApplications = applications.filter((app) => {
    if (criticalityFilter !== 'all' && app.criticality !== criticalityFilter) {
      return false;
    }
    // Don't show apps already in the wave
    if (selectedWave && selectedWave.application_ids.includes(app.id)) {
      return false;
    }
    return true;
  });

  if (loading && waves.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600 dark:text-gray-400">Loading migration waves...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Migration Waves
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage phased rollout of application migrations
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => fetchVelocityComparison()}
            className="inline-flex items-center px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Compare Velocity
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Wave
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search waves..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as WaveStatus | 'all')}
            className="pl-10 pr-8 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
          >
            <option value="all">All Statuses</option>
            <option value="planned">Planned</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="paused">Paused</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Waves Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredWaves.map((wave) => (
          <div
            key={wave.id}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <Waves className="w-5 h-5 text-blue-600 dark:text-blue-500" />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                    {wave.name}
                  </h3>
                </div>
                {wave.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">{wave.description}</p>
                )}
              </div>
              <div className={`flex items-center gap-2 px-3 py-1 rounded-lg ${getStatusColor(wave.status)}`}>
                {getStatusIcon(wave.status)}
                <span className="text-sm font-medium capitalize">{wave.status.replace('_', ' ')}</span>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                  {wave.total_applications}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Total Apps</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-500">
                  {wave.scanned_applications}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Scanned</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-500">
                  {wave.provisioned_applications}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Provisioned</div>
              </div>
            </div>

            {/* Progress Bars */}
            <div className="space-y-3 mb-4">
              <div>
                <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                  <span>Scan Progress</span>
                  <span>{wave.progress_percentage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${wave.progress_percentage}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                  <span>Provisioning Progress</span>
                  <span>{wave.provisioned_percentage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-green-600 dark:bg-green-500 h-2 rounded-full transition-all"
                    style={{ width: `${wave.provisioned_percentage}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 flex-wrap">
              {wave.status === 'planned' && (
                <button
                  onClick={() => updateWaveStatus(wave.id, 'in_progress')}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                >
                  <Play className="w-4 h-4 mr-1.5" />
                  Start
                </button>
              )}
              {wave.status === 'in_progress' && (
                <button
                  onClick={() => updateWaveStatus(wave.id, 'paused')}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                >
                  <Pause className="w-4 h-4 mr-1.5" />
                  Pause
                </button>
              )}
              {wave.status === 'paused' && (
                <button
                  onClick={() => updateWaveStatus(wave.id, 'in_progress')}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                >
                  <Play className="w-4 h-4 mr-1.5" />
                  Resume
                </button>
              )}
              <button
                onClick={async () => {
                  await fetchWaveDetails(wave.id);
                  setShowAddAppsModal(true);
                }}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
              >
                <Users className="w-4 h-4 mr-1.5" />
                Manage Apps
              </button>
              {(wave.status === 'planned' || wave.status === 'in_progress') && wave.total_applications > 0 && (
                <button
                  onClick={() => startWaveScan(wave.id)}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                >
                  <TrendingUp className="w-4 h-4 mr-1.5" />
                  Start Bulk Scan
                </button>
              )}
              <button
                onClick={() => fetchReport(wave.id)}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
              >
                <FileText className="w-4 h-4 mr-1.5" />
                Report
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredWaves.length === 0 && (
        <div className="text-center py-12">
          <Waves className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-50">No migration waves</h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Get started by creating a new migration wave.
          </p>
          <div className="mt-6">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Wave
            </button>
          </div>
        </div>
      )}

      {/* Create Wave Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Create Migration Wave
            </h2>
            <form onSubmit={createWave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Wave Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50"
                  placeholder="Phase 1 - Critical Apps"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50"
                  placeholder="Top 100 critical applications for initial rollout"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setFormData({ name: '', description: '', application_ids: [] });
                  }}
                  className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-lg"
                >
                  Create Wave
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Applications Modal */}
      {showAddAppsModal && selectedWave && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Manage Applications - {selectedWave.name}
            </h2>

            {/* Current apps count */}
            <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div className="text-sm text-blue-600 dark:text-blue-400">
                Current applications in wave: {selectedWave.total_applications}
              </div>
            </div>

            <form onSubmit={addApplicationsToWave} className="space-y-4">
              {/* Division Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Filter by Division
                </label>
                <select
                  value={divisionFilter}
                  onChange={(e) => setDivisionFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50"
                >
                  <option value="all">All Divisions</option>
                  {divisions.map((division) => (
                    <option key={division.id} value={division.id.toString()}>
                      {division.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Criticality Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Filter by Criticality
                </label>
                <select
                  value={criticalityFilter}
                  onChange={(e) => setCriticalityFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50"
                >
                  <option value="all">All</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              {/* Application List */}
              <div className="border border-gray-200 dark:border-gray-800 rounded-lg max-h-64 overflow-y-auto">
                {filteredApplications.map((app) => (
                  <label
                    key={app.id}
                    className="flex items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer border-b border-gray-200 dark:border-gray-800 last:border-0"
                  >
                    <input
                      type="checkbox"
                      checked={selectedAppIds.includes(app.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedAppIds([...selectedAppIds, app.id]);
                        } else {
                          setSelectedAppIds(selectedAppIds.filter((id) => id !== app.id));
                        }
                      }}
                      className="mr-3"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-50">
                        {app.name}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                        Criticality: {app.criticality}
                      </div>
                    </div>
                  </label>
                ))}
              </div>

              <div className="text-sm text-gray-600 dark:text-gray-400">
                {selectedAppIds.length} application(s) selected
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddAppsModal(false);
                    setSelectedAppIds([]);
                    setCriticalityFilter('all');
                    setDivisionFilter('all');
                  }}
                  className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={selectedAppIds.length === 0}
                  className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add {selectedAppIds.length} Application(s)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {showReportModal && report && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-6">
              Migration Wave Report
            </h2>

            <div className="space-y-6">
              {/* Wave Info */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-2">
                  {report.wave_name}
                </h3>
                <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg ${getStatusColor(report.status)}`}>
                  {getStatusIcon(report.status)}
                  <span className="text-sm font-medium capitalize">{report.status.replace('_', ' ')}</span>
                </div>
              </div>

              {/* Progress */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                    {report.scanned_applications} / {report.total_applications}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Applications Scanned</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                    {report.provisioned_applications} / {report.total_applications}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Applications Provisioned</div>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {report.policies_extracted}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Policies Extracted</div>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {report.policies_provisioned}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Policies Provisioned</div>
                </div>
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {report.high_risk_policies}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">High Risk Policies</div>
                </div>
                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                    {report.conflicts_detected}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Conflicts Detected</div>
                </div>
              </div>

              {/* Timeline */}
              {report.started_at && (
                <div className="space-y-2">
                  <div className="text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Started: </span>
                    <span className="text-gray-900 dark:text-gray-50">
                      {new Date(report.started_at).toLocaleString()}
                    </span>
                  </div>
                  {report.completed_at && (
                    <>
                      <div className="text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Completed: </span>
                        <span className="text-gray-900 dark:text-gray-50">
                          {new Date(report.completed_at).toLocaleString()}
                        </span>
                      </div>
                      {report.duration_minutes && (
                        <div className="text-sm">
                          <span className="text-gray-600 dark:text-gray-400">Duration: </span>
                          <span className="text-gray-900 dark:text-gray-50">
                            {report.duration_minutes < 60
                              ? `${report.duration_minutes.toFixed(0)} minutes`
                              : `${(report.duration_minutes / 60).toFixed(1)} hours`}
                          </span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowReportModal(false)}
                className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Velocity Comparison Modal */}
      {showVelocityModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-4xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-6">
              Migration Velocity Comparison
            </h2>

            <div className="space-y-4">
              {velocityData.length === 0 && (
                <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                  No wave data available for comparison
                </div>
              )}

              {velocityData.map((wave) => (
                <div
                  key={wave.wave_id}
                  className="border border-gray-200 dark:border-gray-800 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50">
                        {wave.wave_name}
                      </h3>
                      <div className={`inline-flex items-center gap-2 px-2 py-1 rounded mt-1 ${getStatusColor(wave.status)}`}>
                        {getStatusIcon(wave.status)}
                        <span className="text-xs font-medium capitalize">{wave.status.replace('_', ' ')}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      {wave.duration_minutes && (
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                          {wave.duration_minutes < 60
                            ? `${wave.duration_minutes.toFixed(0)}m`
                            : `${(wave.duration_minutes / 60).toFixed(1)}h`}
                        </div>
                      )}
                      <div className="text-xs text-gray-600 dark:text-gray-400">Duration</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-3">
                    <div className="bg-gray-50 dark:bg-gray-800 rounded p-3">
                      <div className="text-lg font-bold text-gray-900 dark:text-gray-50">
                        {wave.total_applications}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Applications</div>
                    </div>
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-3">
                      <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                        {wave.policies_extracted}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Policies</div>
                    </div>
                    <div className="bg-green-50 dark:bg-green-900/20 rounded p-3">
                      <div className="text-lg font-bold text-green-600 dark:text-green-400">
                        {wave.policies_provisioned}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Provisioned</div>
                    </div>
                    <div className="bg-amber-50 dark:bg-amber-900/20 rounded p-3">
                      <div className="text-lg font-bold text-amber-600 dark:text-amber-400">
                        {wave.duration_minutes && wave.total_applications > 0
                          ? (wave.duration_minutes / wave.total_applications).toFixed(1)
                          : 'N/A'}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Min/App</div>
                    </div>
                  </div>

                  {wave.started_at && (
                    <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
                      <span>Started: {new Date(wave.started_at).toLocaleDateString()}</span>
                      {wave.completed_at && (
                        <span className="ml-4">
                          Completed: {new Date(wave.completed_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowVelocityModal(false)}
                className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
