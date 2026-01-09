import React, { useEffect, useState } from 'react';
import { Plus, Trash2, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

interface PBACProvider {
  provider_id: number;
  tenant_id: string;
  provider_type: 'opa' | 'aws_verified_permissions' | 'axiomatics' | 'plainid';
  name: string;
  endpoint_url: string;
  api_key?: string;
  configuration?: string;
  created_at: string;
  updated_at: string;
}

interface ProvisioningOperation {
  operation_id: number;
  tenant_id: string;
  provider_id: number;
  policy_id: number;
  status: 'pending' | 'in_progress' | 'success' | 'failed';
  translated_policy?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

interface Policy {
  policy_id: number;
  subject: string;
  resource: string;
  action: string;
  status: string;
}

export default function ProvisioningPage() {
  const [providers, setProviders] = useState<PBACProvider[]>([]);
  const [operations, setOperations] = useState<ProvisioningOperation[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<number | null>(null);
  const [selectedPolicies, setSelectedPolicies] = useState<number[]>([]);
  const [provisioning, setProvisioning] = useState(false);

  // New provider form state
  const [providerForm, setProviderForm] = useState({
    provider_type: 'opa' as 'opa' | 'aws_verified_permissions' | 'axiomatics' | 'plainid',
    name: '',
    endpoint_url: '',
    api_key: '',
    configuration: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [providersRes, operationsRes, policiesRes] = await Promise.all([
        fetch('/api/v1/provisioning/providers/'),
        fetch('/api/v1/provisioning/operations/'),
        fetch('/api/v1/policies/'),
      ]);

      if (providersRes.ok) {
        const data = await providersRes.json();
        setProviders(data);
      }

      if (operationsRes.ok) {
        const data = await operationsRes.json();
        setOperations(data);
      }

      if (policiesRes.ok) {
        const data = await policiesRes.json();
        setPolicies(data.policies || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddProvider = async () => {
    try {
      const response = await fetch('/api/v1/provisioning/providers/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(providerForm),
      });

      if (response.ok) {
        setShowAddProvider(false);
        setProviderForm({
          provider_type: 'opa',
          name: '',
          endpoint_url: '',
          api_key: '',
          configuration: '',
        });
        fetchData();
      }
    } catch (error) {
      console.error('Error adding provider:', error);
    }
  };

  const handleDeleteProvider = async (providerId: number) => {
    if (!confirm('Are you sure you want to delete this provider?')) return;

    try {
      const response = await fetch(`/api/v1/provisioning/providers/${providerId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchData();
      }
    } catch (error) {
      console.error('Error deleting provider:', error);
    }
  };

  const handleProvision = async () => {
    if (!selectedProvider || selectedPolicies.length === 0) {
      alert('Please select a provider and at least one policy');
      return;
    }

    setProvisioning(true);
    try {
      const response = await fetch('/api/v1/provisioning/provision/bulk/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: selectedProvider,
          policy_ids: selectedPolicies,
        }),
      });

      if (response.ok) {
        setSelectedPolicies([]);
        fetchData();
        alert('Provisioning started successfully');
      }
    } catch (error) {
      console.error('Error provisioning:', error);
      alert('Provisioning failed');
    } finally {
      setProvisioning(false);
    }
  };

  const togglePolicySelection = (policyId: number) => {
    setSelectedPolicies((prev) =>
      prev.includes(policyId)
        ? prev.filter((id) => id !== policyId)
        : [...prev, policyId]
    );
  };

  const getProviderTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      opa: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      aws_verified_permissions: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
      axiomatics: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      plainid: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    };

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${colors[type] || colors.opa}`}>
        {type.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'in_progress':
        return <Clock className="h-5 w-5 text-blue-600 animate-spin" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-600" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">Provisioning</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Configure PBAC platforms and provision policies
        </p>
      </div>

      {/* Providers Section */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-50">PBAC Providers</h2>
          <button
            onClick={() => setShowAddProvider(true)}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Provider
          </button>
        </div>

        {providers.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No PBAC providers configured yet
          </div>
        ) : (
          <div className="space-y-3">
            {providers.map((provider) => (
              <div
                key={provider.provider_id}
                className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-800 rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    {getProviderTypeBadge(provider.provider_type)}
                    <span className="font-medium text-gray-900 dark:text-gray-50">{provider.name}</span>
                  </div>
                  <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    {provider.endpoint_url}
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteProvider(provider.provider_id)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Provider Modal */}
      {showAddProvider && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-4">Add PBAC Provider</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Provider Type
                </label>
                <select
                  value={providerForm.provider_type}
                  onChange={(e) => setProviderForm({ ...providerForm, provider_type: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                >
                  <option value="opa">OPA</option>
                  <option value="aws_verified_permissions">AWS Verified Permissions</option>
                  <option value="axiomatics">Axiomatics</option>
                  <option value="plainid">PlainID</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={providerForm.name}
                  onChange={(e) => setProviderForm({ ...providerForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  placeholder="My OPA Instance"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {providerForm.provider_type === 'aws_verified_permissions' ? 'AWS Region' : 'Endpoint URL'}
                </label>
                <input
                  type="text"
                  value={providerForm.endpoint_url}
                  onChange={(e) => setProviderForm({ ...providerForm, endpoint_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  placeholder={providerForm.provider_type === 'aws_verified_permissions' ? 'us-east-1' : 'http://localhost:8181'}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API Key (optional)
                </label>
                <input
                  type="password"
                  value={providerForm.api_key}
                  onChange={(e) => setProviderForm({ ...providerForm, api_key: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Configuration (optional)
                </label>
                <textarea
                  value={providerForm.configuration}
                  onChange={(e) => setProviderForm({ ...providerForm, configuration: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50 font-mono text-sm"
                  rows={3}
                  placeholder={providerForm.provider_type === 'aws_verified_permissions'
                    ? '{"policy_store_id": "PSEXAMPLEabcdefg12345"}'
                    : '{}'}
                />
                {providerForm.provider_type === 'aws_verified_permissions' && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    JSON format. Required: policy_store_id. Optional: aws_access_key_id, aws_secret_access_key
                  </p>
                )}
              </div>
            </div>
            <div className="mt-6 flex space-x-3">
              <button
                onClick={handleAddProvider}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add Provider
              </button>
              <button
                onClick={() => setShowAddProvider(false)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provision Policies Section */}
      {providers.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-4">Provision Policies</h2>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Provider
            </label>
            <select
              value={selectedProvider || ''}
              onChange={(e) => setSelectedProvider(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
            >
              <option value="">Choose a provider</option>
              {providers.map((provider) => (
                <option key={provider.provider_id} value={provider.provider_id}>
                  {provider.name} ({provider.provider_type})
                </option>
              ))}
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Policies
            </label>
            <div className="max-h-64 overflow-y-auto border border-gray-300 dark:border-gray-700 rounded-md">
              {policies.filter(p => p.status === 'approved').map((policy) => (
                <div
                  key={policy.policy_id}
                  className="flex items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-200 dark:border-gray-800 last:border-b-0"
                >
                  <input
                    type="checkbox"
                    checked={selectedPolicies.includes(policy.policy_id)}
                    onChange={() => togglePolicySelection(policy.policy_id)}
                    className="h-4 w-4 text-blue-600 rounded"
                  />
                  <div className="ml-3 flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-50">
                      {policy.subject} → {policy.action} → {policy.resource}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={handleProvision}
            disabled={provisioning || !selectedProvider || selectedPolicies.length === 0}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {provisioning ? 'Provisioning...' : `Provision ${selectedPolicies.length} Policies`}
          </button>
        </div>
      )}

      {/* Recent Operations */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-4">Recent Operations</h2>

        {operations.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No provisioning operations yet
          </div>
        ) : (
          <div className="space-y-3">
            {operations.slice(0, 10).map((operation) => (
              <div
                key={operation.operation_id}
                className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-800 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {getStatusIcon(operation.status)}
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-50">
                      Policy #{operation.policy_id}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      {new Date(operation.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {operation.status}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
