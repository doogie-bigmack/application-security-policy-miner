import { useState, useEffect } from 'react';
import {
  Building2,
  Plus,
  ChevronRight,
  ChevronDown,
  Edit2,
  Trash2,
  AlertCircle,
  Users,
} from 'lucide-react';

interface BusinessUnit {
  id: number;
  name: string;
  description: string | null;
  division_id: number;
  created_at: string;
  updated_at: string;
}

interface Division {
  id: number;
  name: string;
  description: string | null;
  organization_id: number;
  created_at: string;
  updated_at: string;
  business_units?: BusinessUnit[];
}

interface Organization {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  divisions?: Division[];
}

export default function OrganizationsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [expandedOrgs, setExpandedOrgs] = useState<Set<number>>(new Set());
  const [expandedDivisions, setExpandedDivisions] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showOrgModal, setShowOrgModal] = useState(false);
  const [showDivisionModal, setShowDivisionModal] = useState(false);
  const [showBusinessUnitModal, setShowBusinessUnitModal] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<number | null>(null);
  const [selectedDivision, setSelectedDivision] = useState<number | null>(null);
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null);

  // Form states
  const [orgName, setOrgName] = useState('');
  const [orgDescription, setOrgDescription] = useState('');
  const [divisionName, setDivisionName] = useState('');
  const [divisionDescription, setDivisionDescription] = useState('');
  const [businessUnitName, setBusinessUnitName] = useState('');
  const [businessUnitDescription, setBusinessUnitDescription] = useState('');

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:7777/api/v1/organizations/');
      if (!response.ok) throw new Error('Failed to fetch organizations');
      const data = await response.json();
      setOrganizations(data);
    } catch (err) {
      setError('Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  const fetchOrgHierarchy = async (orgId: number) => {
    try {
      const response = await fetch(`http://localhost:7777/api/v1/organizations/${orgId}/hierarchy`);
      if (!response.ok) throw new Error('Failed to fetch hierarchy');
      const data = await response.json();
      setOrganizations((prev) =>
        prev.map((org) => (org.id === orgId ? data : org))
      );
    } catch (err) {
      setError('Failed to load organization hierarchy');
    }
  };

  const toggleOrg = (orgId: number) => {
    const newExpanded = new Set(expandedOrgs);
    if (newExpanded.has(orgId)) {
      newExpanded.delete(orgId);
    } else {
      newExpanded.add(orgId);
      // Fetch hierarchy if not already loaded
      const org = organizations.find((o) => o.id === orgId);
      if (!org?.divisions) {
        fetchOrgHierarchy(orgId);
      }
    }
    setExpandedOrgs(newExpanded);
  };

  const toggleDivision = (divisionId: number) => {
    const newExpanded = new Set(expandedDivisions);
    if (newExpanded.has(divisionId)) {
      newExpanded.delete(divisionId);
    } else {
      newExpanded.add(divisionId);
    }
    setExpandedDivisions(newExpanded);
  };

  const createOrganization = async () => {
    try {
      const response = await fetch('http://localhost:7777/api/v1/organizations/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: orgName, description: orgDescription }),
      });
      if (!response.ok) throw new Error('Failed to create organization');
      await fetchOrganizations();
      setShowOrgModal(false);
      setOrgName('');
      setOrgDescription('');
    } catch (err) {
      setError('Failed to create organization');
    }
  };

  const createDivision = async () => {
    if (!selectedOrg) return;
    try {
      const response = await fetch(
        `http://localhost:7777/api/v1/organizations/${selectedOrg}/divisions`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: divisionName, description: divisionDescription }),
        }
      );
      if (!response.ok) throw new Error('Failed to create division');
      await fetchOrgHierarchy(selectedOrg);
      setShowDivisionModal(false);
      setDivisionName('');
      setDivisionDescription('');
      setSelectedOrg(null);
    } catch (err) {
      setError('Failed to create division');
    }
  };

  const createBusinessUnit = async () => {
    if (!selectedDivision) return;
    try {
      const response = await fetch(
        `http://localhost:7777/api/v1/organizations/divisions/${selectedDivision}/business-units`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: businessUnitName,
            description: businessUnitDescription,
          }),
        }
      );
      if (!response.ok) throw new Error('Failed to create business unit');
      // Find org containing this division and refresh
      const org = organizations.find((o) =>
        o.divisions?.some((d) => d.id === selectedDivision)
      );
      if (org) await fetchOrgHierarchy(org.id);
      setShowBusinessUnitModal(false);
      setBusinessUnitName('');
      setBusinessUnitDescription('');
      setSelectedDivision(null);
    } catch (err) {
      setError('Failed to create business unit');
    }
  };

  const deleteOrganization = async (orgId: number) => {
    if (!confirm('Delete this organization? This will also delete all divisions and business units.'))
      return;
    try {
      const response = await fetch(`http://localhost:7777/api/v1/organizations/${orgId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete organization');
      await fetchOrganizations();
    } catch (err) {
      setError('Failed to delete organization');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading organizations...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Organizations
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Manage your organizational hierarchy: organizations, divisions, and business units
          </p>
        </div>
        <button
          onClick={() => setShowOrgModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Organization
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        </div>
      )}

      {/* Organizations List */}
      <div className="space-y-4">
        {organizations.length === 0 ? (
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-12 text-center">
            <Building2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-2">
              No organizations yet
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Get started by creating your first organization
            </p>
            <button
              onClick={() => setShowOrgModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Create Organization
            </button>
          </div>
        ) : (
          organizations.map((org) => (
            <div
              key={org.id}
              className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
            >
              {/* Organization */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => toggleOrg(org.id)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {expandedOrgs.has(org.id) ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronRight className="h-5 w-5" />
                    )}
                  </button>
                  <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-50">
                      {org.name}
                    </h3>
                    {org.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {org.description}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setSelectedOrg(org.id);
                      setShowDivisionModal(true);
                    }}
                    className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                    title="Add Division"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => deleteOrganization(org.id)}
                    className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                    title="Delete Organization"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Divisions */}
              {expandedOrgs.has(org.id) && org.divisions && (
                <div className="border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 p-4 pl-12">
                  {org.divisions.length === 0 ? (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No divisions</p>
                  ) : (
                    <div className="space-y-2">
                      {org.divisions.map((division) => (
                        <div key={division.id}>
                          <div className="flex items-center justify-between p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-900">
                            <div className="flex items-center gap-3 flex-1">
                              <button
                                onClick={() => toggleDivision(division.id)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                              >
                                {expandedDivisions.has(division.id) ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </button>
                              <Users className="h-4 w-4 text-green-600 dark:text-green-400" />
                              <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-gray-50">
                                  {division.name}
                                </p>
                                {division.description && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {division.description}
                                  </p>
                                )}
                              </div>
                            </div>
                            <button
                              onClick={() => {
                                setSelectedDivision(division.id);
                                setShowBusinessUnitModal(true);
                              }}
                              className="p-1 text-gray-400 hover:text-green-600 dark:hover:text-green-400"
                              title="Add Business Unit"
                            >
                              <Plus className="h-4 w-4" />
                            </button>
                          </div>

                          {/* Business Units */}
                          {expandedDivisions.has(division.id) &&
                            division.business_units &&
                            division.business_units.length > 0 && (
                              <div className="ml-10 mt-2 space-y-1">
                                {division.business_units.map((bu) => (
                                  <div
                                    key={bu.id}
                                    className="flex items-center gap-3 p-2 rounded text-sm"
                                  >
                                    <div className="h-1 w-1 rounded-full bg-gray-400" />
                                    <span className="text-gray-700 dark:text-gray-300">
                                      {bu.name}
                                    </span>
                                    {bu.description && (
                                      <span className="text-xs text-gray-500 dark:text-gray-400">
                                        - {bu.description}
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Create Organization Modal */}
      {showOrgModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Create Organization
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  placeholder="BigCorp"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description (optional)
                </label>
                <textarea
                  value={orgDescription}
                  onChange={(e) => setOrgDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  rows={3}
                  placeholder="Enterprise organization"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowOrgModal(false);
                    setOrgName('');
                    setOrgDescription('');
                  }}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={createOrganization}
                  disabled={!orgName}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Division Modal */}
      {showDivisionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Create Division
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={divisionName}
                  onChange={(e) => setDivisionName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  placeholder="Finance"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description (optional)
                </label>
                <textarea
                  value={divisionDescription}
                  onChange={(e) => setDivisionDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  rows={3}
                  placeholder="Finance division"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowDivisionModal(false);
                    setDivisionName('');
                    setDivisionDescription('');
                    setSelectedOrg(null);
                  }}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={createDivision}
                  disabled={!divisionName}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Business Unit Modal */}
      {showBusinessUnitModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
              Create Business Unit
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={businessUnitName}
                  onChange={(e) => setBusinessUnitName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  placeholder="Accounts Payable"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description (optional)
                </label>
                <textarea
                  value={businessUnitDescription}
                  onChange={(e) => setBusinessUnitDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
                  rows={3}
                  placeholder="Accounts payable team"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowBusinessUnitModal(false);
                    setBusinessUnitName('');
                    setBusinessUnitDescription('');
                    setSelectedDivision(null);
                  }}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={createBusinessUnit}
                  disabled={!businessUnitName}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
