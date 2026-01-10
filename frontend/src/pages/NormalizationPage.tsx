import { useState, useEffect } from 'react';
import { GitMerge, Check, X, RefreshCw, TrendingUp, Shield, AlertTriangle } from 'lucide-react';
import { apiClient } from '../api/client';

interface RoleMapping {
  id: number;
  standard_role: string;
  variant_roles: string[];
  affected_applications: number[];
  affected_policy_count: number;
  confidence_score: number;
  reasoning: string;
  status: string;
  approved_by: string | null;
  created_at: string;
}

interface RoleDiscovery {
  roles: string[];
  standard_role: string;
  confidence: number;
  reasoning: string;
  application_count: number;
  applications: string[];
  apps_by_role: Record<string, string[]>;
}

interface NormalizationStats {
  total_mappings: number;
  suggested: number;
  approved: number;
  applied: number;
  total_policies_normalized: number;
}

export default function NormalizationPage() {
  const [mappings, setMappings] = useState<RoleMapping[]>([]);
  const [discoveries, setDiscoveries] = useState<RoleDiscovery[]>([]);
  const [stats, setStats] = useState<NormalizationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState<RoleMapping | null>(null);
  const [approverEmail, setApproverEmail] = useState('');

  useEffect(() => {
    loadMappings();
    loadStats();
  }, []);

  const loadMappings = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/normalization/mappings');
      setMappings(response.data);
    } catch (error) {
      console.error('Error loading mappings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await apiClient.get('/normalization/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const discoverRoles = async () => {
    try {
      setDiscovering(true);
      const response = await apiClient.post('/normalization/discover', {
        min_applications: 2,
      });
      setDiscoveries(response.data);
    } catch (error) {
      console.error('Error discovering roles:', error);
    } finally {
      setDiscovering(false);
    }
  };

  const createMapping = async (discovery: RoleDiscovery) => {
    try {
      await apiClient.post('/normalization/mappings', {
        standard_role: discovery.standard_role,
        variant_roles: discovery.roles,
        affected_applications: [], // Will be computed by backend
        confidence_score: discovery.confidence,
        reasoning: discovery.reasoning,
      });
      await loadMappings();
      await loadStats();
      setDiscoveries(discoveries.filter(d => d !== discovery));
    } catch (error) {
      console.error('Error creating mapping:', error);
    }
  };

  const applyMapping = async (mapping: RoleMapping) => {
    if (!approverEmail) {
      alert('Please enter your email address');
      return;
    }

    try {
      await apiClient.post(`/normalization/mappings/${mapping.id}/apply`, {
        approved_by: approverEmail,
      });
      await loadMappings();
      await loadStats();
      setSelectedMapping(null);
      alert('Role mapping applied successfully!');
    } catch (error) {
      console.error('Error applying mapping:', error);
      alert('Error applying mapping');
    }
  };

  const deleteMapping = async (mappingId: number) => {
    if (!confirm('Are you sure you want to delete this mapping?')) {
      return;
    }

    try {
      await apiClient.delete(`/normalization/mappings/${mappingId}`);
      await loadMappings();
      await loadStats();
    } catch (error) {
      console.error('Error deleting mapping:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'suggested':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'approved':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'applied':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-green-600 dark:text-green-400';
    if (confidence >= 60) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
            Cross-Application Role Normalization
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Detect and normalize equivalent roles across applications using AI analysis
          </p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <GitMerge className="w-5 h-5 text-blue-600 dark:text-blue-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Mappings</span>
              </div>
              <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {stats.total_mappings}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Suggested</span>
              </div>
              <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {stats.suggested}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <Check className="w-5 h-5 text-green-600 dark:text-green-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Approved</span>
              </div>
              <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {stats.approved}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-600 dark:text-purple-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Applied</span>
              </div>
              <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {stats.applied}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-indigo-600 dark:text-indigo-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Policies Normalized</span>
              </div>
              <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {stats.total_policies_normalized}
              </p>
            </div>
          </div>
        )}

        {/* Discover Button */}
        <div className="mb-8">
          <button
            onClick={discoverRoles}
            disabled={discovering}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${discovering ? 'animate-spin' : ''}`} />
            {discovering ? 'Discovering...' : 'Discover Role Variations'}
          </button>
        </div>

        {/* Discoveries Section */}
        {discoveries.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Discovered Role Variations ({discoveries.length})
            </h2>
            <div className="space-y-4">
              {discoveries.map((discovery, idx) => (
                <div
                  key={idx}
                  className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50">
                          {discovery.standard_role}
                        </h3>
                        <span className={`text-sm font-medium ${getConfidenceColor(discovery.confidence)}`}>
                          {discovery.confidence}% confidence
                        </span>
                      </div>

                      <div className="mb-3">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Detected variants: </span>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {discovery.roles.map(role => (
                            <span
                              key={role}
                              className="px-2 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-sm"
                            >
                              {role}
                            </span>
                          ))}
                        </div>
                      </div>

                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                        {discovery.reasoning}
                      </p>

                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        <strong>Affects {discovery.application_count} applications:</strong>{' '}
                        {discovery.applications.slice(0, 5).join(', ')}
                        {discovery.applications.length > 5 && ` and ${discovery.applications.length - 5} more`}
                      </div>
                    </div>

                    <button
                      onClick={() => createMapping(discovery)}
                      className="ml-4 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Create Mapping
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mappings Section */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">
            Role Mappings ({mappings.length})
          </h2>

          {loading ? (
            <div className="text-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400" />
              <p className="mt-2 text-gray-600 dark:text-gray-400">Loading mappings...</p>
            </div>
          ) : mappings.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
              <GitMerge className="w-12 h-12 mx-auto text-gray-400" />
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                No role mappings yet. Click "Discover Role Variations" to start.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {mappings.map(mapping => (
                <div
                  key={mapping.id}
                  className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-800"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50">
                          {mapping.standard_role}
                        </h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(mapping.status)}`}>
                          {mapping.status.toUpperCase()}
                        </span>
                        <span className={`text-sm font-medium ${getConfidenceColor(mapping.confidence_score)}`}>
                          {mapping.confidence_score}% confidence
                        </span>
                      </div>

                      <div className="mb-3">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Variants: </span>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {mapping.variant_roles.map(role => (
                            <span
                              key={role}
                              className="px-2 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-sm"
                            >
                              {role}
                            </span>
                          ))}
                        </div>
                      </div>

                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        {mapping.reasoning}
                      </p>

                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Affects <strong>{mapping.affected_policy_count} policies</strong> across{' '}
                        <strong>{mapping.affected_applications.length} applications</strong>
                      </div>

                      {mapping.approved_by && (
                        <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                          Approved by: {mapping.approved_by}
                        </div>
                      )}
                    </div>

                    <div className="ml-4 flex gap-2">
                      {mapping.status === 'suggested' && (
                        <>
                          <button
                            onClick={() => setSelectedMapping(mapping)}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
                          >
                            Apply
                          </button>
                          <button
                            onClick={() => deleteMapping(mapping.id)}
                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      {mapping.status === 'applied' && (
                        <span className="px-4 py-2 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-lg text-sm font-medium">
                          <Check className="w-4 h-4 inline mr-1" />
                          Applied
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Apply Mapping Modal */}
        {selectedMapping && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full border border-gray-200 dark:border-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
                Apply Role Mapping
              </h3>

              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                This will update <strong>{selectedMapping.affected_policy_count} policies</strong> across{' '}
                <strong>{selectedMapping.affected_applications.length} applications</strong> to use the
                standard role name: <strong>{selectedMapping.standard_role}</strong>
              </p>

              <input
                type="email"
                placeholder="Your email address"
                value={approverEmail}
                onChange={e => setApproverEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50 mb-4"
              />

              <div className="flex gap-2">
                <button
                  onClick={() => applyMapping(selectedMapping)}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                >
                  Confirm & Apply
                </button>
                <button
                  onClick={() => setSelectedMapping(null)}
                  className="flex-1 px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-50 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
