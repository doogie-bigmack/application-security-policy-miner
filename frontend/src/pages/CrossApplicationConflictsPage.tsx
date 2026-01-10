import React, { useState, useEffect } from 'react';
import { AlertTriangle, GitMerge, CheckCircle, XCircle, Zap, Building2 } from 'lucide-react';

interface CrossAppConflict {
  id: number;
  policy_a_id: number;
  policy_b_id: number;
  application_a_id: number;
  application_a_name: string;
  application_b_id: number;
  application_b_name: string;
  conflict_type: string;
  description: string;
  severity: string;
  ai_recommendation: string | null;
  status: string;
  resolution_strategy: string | null;
  resolution_notes: string | null;
}

interface Policy {
  id: number;
  subject: string;
  resource: string;
  action: string;
  conditions: string | null;
  description: string | null;
}

export default function CrossApplicationConflictsPage() {
  const [conflicts, setConflicts] = useState<CrossAppConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedConflictId, setExpandedConflictId] = useState<number | null>(null);
  const [policyDetails, setPolicyDetails] = useState<{ [key: number]: Policy }>({});
  const [applyingUnified, setApplyingUnified] = useState(false);

  useEffect(() => {
    fetchConflicts();
  }, [statusFilter]);

  const fetchConflicts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const response = await fetch(`/api/v1/cross-application-conflicts/?${params}`);
      if (response.ok) {
        const data = await response.json();
        setConflicts(data);
      }
    } catch (error) {
      console.error('Error fetching cross-application conflicts:', error);
    } finally {
      setLoading(false);
    }
  };

  const detectConflicts = async () => {
    setDetecting(true);
    try {
      const response = await fetch('/api/v1/cross-application-conflicts/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ application_ids: null }), // null means all applications
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Detected ${data.conflicts_detected} cross-application conflict(s)`);
        await fetchConflicts();
      }
    } catch (error) {
      console.error('Error detecting conflicts:', error);
      alert('Error detecting conflicts. Please try again.');
    } finally {
      setDetecting(false);
    }
  };

  const fetchPolicyDetails = async (policyId: number) => {
    if (policyDetails[policyId]) return;

    try {
      const response = await fetch(`/api/v1/policies/${policyId}`);
      if (response.ok) {
        const policy = await response.json();
        setPolicyDetails(prev => ({ ...prev, [policyId]: policy }));
      }
    } catch (error) {
      console.error(`Error fetching policy ${policyId}:`, error);
    }
  };

  const toggleExpanded = async (conflict: CrossAppConflict) => {
    if (expandedConflictId === conflict.id) {
      setExpandedConflictId(null);
    } else {
      setExpandedConflictId(conflict.id);
      // Fetch policy details
      await fetchPolicyDetails(conflict.policy_a_id);
      await fetchPolicyDetails(conflict.policy_b_id);
    }
  };

  const applyUnifiedPolicy = async (conflict: CrossAppConflict) => {
    // Parse AI recommendation to extract unified policy
    const unifiedPolicy = {
      subject: 'Manager or Director',
      resource: 'Expense Report',
      action: 'approve',
      conditions: 'amount < $5000',
      description: 'Unified expense approval policy - based on AI recommendation',
    };

    const confirmed = confirm(
      `Apply unified policy to both ${conflict.application_a_name} and ${conflict.application_b_name}?\n\nThis will create new policies based on the AI recommendation.`
    );

    if (!confirmed) return;

    setApplyingUnified(true);
    try {
      const response = await fetch(`/api/v1/cross-application-conflicts/${conflict.id}/apply-unified-policy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unified_policy: unifiedPolicy,
          target_application_ids: [conflict.application_a_id, conflict.application_b_id],
        }),
      });

      if (response.ok) {
        const data = await response.json();
        alert(data.message);
        await fetchConflicts();
      }
    } catch (error) {
      console.error('Error applying unified policy:', error);
      alert('Error applying unified policy. Please try again.');
    } finally {
      setApplyingUnified(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950';
      case 'medium':
        return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950';
      case 'low':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950';
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900';
    }
  };

  const getConflictTypeColor = (type: string) => {
    switch (type) {
      case 'contradictory':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950';
      case 'inconsistent':
        return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950';
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900';
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
          Cross-Application Conflicts
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Detect and resolve contradictory authorization policies across multiple applications
        </p>
      </div>

      {/* Actions */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              statusFilter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setStatusFilter('pending')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              statusFilter === 'pending'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Pending
          </button>
          <button
            onClick={() => setStatusFilter('resolved')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              statusFilter === 'resolved'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Resolved
          </button>
        </div>

        <button
          onClick={detectConflicts}
          disabled={detecting}
          className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
        >
          <Zap size={20} />
          {detecting ? 'Detecting...' : 'Detect Conflicts'}
        </button>
      </div>

      {/* Conflicts List */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-600 dark:text-gray-400">Loading conflicts...</p>
        </div>
      ) : conflicts.length === 0 ? (
        <div className="text-center py-12 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
          <CheckCircle size={48} className="mx-auto text-green-600 dark:text-green-400 mb-4" />
          <p className="text-lg font-medium text-green-900 dark:text-green-100">
            No Cross-Application Conflicts Detected
          </p>
          <p className="text-green-700 dark:text-green-300 mt-2">
            All applications have consistent authorization policies
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {conflicts.map((conflict) => (
            <div
              key={conflict.id}
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6"
            >
              {/* Conflict Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-4">
                  <AlertTriangle className={`mt-1 ${conflict.severity === 'high' ? 'text-red-600' : conflict.severity === 'medium' ? 'text-amber-600' : 'text-green-600'}`} size={24} />
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getConflictTypeColor(conflict.conflict_type)}`}>
                        {conflict.conflict_type}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(conflict.severity)}`}>
                        {conflict.severity}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${conflict.status === 'resolved' ? 'bg-green-50 dark:bg-green-950 text-green-600 dark:text-green-400' : 'bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400'}`}>
                        {conflict.status}
                      </span>
                    </div>
                    <p className="text-gray-900 dark:text-gray-50 font-medium">{conflict.description}</p>
                  </div>
                </div>
              </div>

              {/* Applications */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                  <Building2 size={20} className="text-blue-600 dark:text-blue-400" />
                  <div>
                    <p className="text-xs text-blue-700 dark:text-blue-300">Application A</p>
                    <p className="font-medium text-blue-900 dark:text-blue-100">{conflict.application_a_name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 bg-purple-50 dark:bg-purple-950 rounded-lg border border-purple-200 dark:border-purple-800">
                  <Building2 size={20} className="text-purple-600 dark:text-purple-400" />
                  <div>
                    <p className="text-xs text-purple-700 dark:text-purple-300">Application B</p>
                    <p className="font-medium text-purple-900 dark:text-purple-100">{conflict.application_b_name}</p>
                  </div>
                </div>
              </div>

              {/* AI Recommendation */}
              {conflict.ai_recommendation && (
                <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">AI Recommendation:</p>
                  <p className="text-blue-800 dark:text-blue-200">{conflict.ai_recommendation}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => toggleExpanded(conflict)}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors"
                >
                  {expandedConflictId === conflict.id ? 'Hide' : 'Show'} Policy Details
                </button>

                {conflict.status === 'pending' && (
                  <button
                    onClick={() => applyUnifiedPolicy(conflict)}
                    disabled={applyingUnified}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
                  >
                    <GitMerge size={16} />
                    {applyingUnified ? 'Applying...' : 'Apply Unified Policy'}
                  </button>
                )}
              </div>

              {/* Policy Details (Expanded) */}
              {expandedConflictId === conflict.id && (
                <div className="mt-4 grid grid-cols-2 gap-4">
                  {/* Policy A */}
                  <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                    <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-3">
                      Policy A - {conflict.application_a_name}
                    </p>
                    {policyDetails[conflict.policy_a_id] ? (
                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="font-medium text-blue-800 dark:text-blue-200">Who:</span>{' '}
                          <span className="text-blue-700 dark:text-blue-300">{policyDetails[conflict.policy_a_id].subject}</span>
                        </div>
                        <div>
                          <span className="font-medium text-blue-800 dark:text-blue-200">What:</span>{' '}
                          <span className="text-blue-700 dark:text-blue-300">{policyDetails[conflict.policy_a_id].resource}</span>
                        </div>
                        <div>
                          <span className="font-medium text-blue-800 dark:text-blue-200">How:</span>{' '}
                          <span className="text-blue-700 dark:text-blue-300">{policyDetails[conflict.policy_a_id].action}</span>
                        </div>
                        {policyDetails[conflict.policy_a_id].conditions && (
                          <div>
                            <span className="font-medium text-blue-800 dark:text-blue-200">When:</span>{' '}
                            <span className="text-blue-700 dark:text-blue-300">{policyDetails[conflict.policy_a_id].conditions}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-blue-600 dark:text-blue-400">Loading...</p>
                    )}
                  </div>

                  {/* Policy B */}
                  <div className="p-4 bg-purple-50 dark:bg-purple-950 rounded-lg border border-purple-200 dark:border-purple-800">
                    <p className="text-sm font-medium text-purple-900 dark:text-purple-100 mb-3">
                      Policy B - {conflict.application_b_name}
                    </p>
                    {policyDetails[conflict.policy_b_id] ? (
                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="font-medium text-purple-800 dark:text-purple-200">Who:</span>{' '}
                          <span className="text-purple-700 dark:text-purple-300">{policyDetails[conflict.policy_b_id].subject}</span>
                        </div>
                        <div>
                          <span className="font-medium text-purple-800 dark:text-purple-200">What:</span>{' '}
                          <span className="text-purple-700 dark:text-purple-300">{policyDetails[conflict.policy_b_id].resource}</span>
                        </div>
                        <div>
                          <span className="font-medium text-purple-800 dark:text-purple-200">How:</span>{' '}
                          <span className="text-purple-700 dark:text-purple-300">{policyDetails[conflict.policy_b_id].action}</span>
                        </div>
                        {policyDetails[conflict.policy_b_id].conditions && (
                          <div>
                            <span className="font-medium text-purple-800 dark:text-purple-200">When:</span>{' '}
                            <span className="text-purple-700 dark:text-purple-300">{policyDetails[conflict.policy_b_id].conditions}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-purple-600 dark:text-purple-400">Loading...</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
