import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  ChevronDown,
  ChevronUp,
  FileWarning,
  Building2,
  Zap,
} from "lucide-react";

const API_BASE = "/api/v1";

interface InconsistentEnforcement {
  id: number;
  tenant_id: string;
  resource_type: string;
  resource_description: string | null;
  affected_application_ids: number[];
  policy_ids: number[];
  inconsistency_description: string;
  severity: "low" | "medium" | "high" | "critical";
  recommended_policy: {
    subject: string;
    resource: string;
    action: string;
    conditions: string | null;
  };
  recommendation_explanation: string;
  status: "pending" | "acknowledged" | "resolved" | "dismissed";
  resolution_notes: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

interface Application {
  id: number;
  name: string;
  criticality: string;
}

interface Policy {
  id: number;
  subject: string;
  resource: string;
  action: string;
  conditions: string | null;
  application_id: number;
}

export default function InconsistentEnforcementPage() {
  const [inconsistencies, setInconsistencies] = useState<InconsistentEnforcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [expandedInconsistency, setExpandedInconsistency] = useState<number | null>(null);
  const [applications, setApplications] = useState<Map<number, Application>>(new Map());
  const [policies, setPolicies] = useState<Map<number, Policy>>(new Map());

  useEffect(() => {
    fetchInconsistencies();
    fetchApplications();
    fetchPolicies();
  }, [filterStatus, filterSeverity]);

  const fetchInconsistencies = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }
      if (filterSeverity !== "all") {
        params.append("severity", filterSeverity);
      }
      const response = await fetch(`${API_BASE}/inconsistent-enforcement/?${params}`);
      const data = await response.json();
      setInconsistencies(data);
    } catch (error) {
      console.error("Failed to fetch inconsistencies:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchApplications = async () => {
    try {
      const response = await fetch(`${API_BASE}/applications/?skip=0&limit=1000`);
      const data = await response.json();
      const appMap = new Map<number, Application>();
      data.forEach((app: Application) => {
        appMap.set(app.id, app);
      });
      setApplications(appMap);
    } catch (error) {
      console.error("Failed to fetch applications:", error);
    }
  };

  const fetchPolicies = async () => {
    try {
      const response = await fetch(`${API_BASE}/policies/?skip=0&limit=10000`);
      const data = await response.json();
      const policyMap = new Map<number, Policy>();
      data.forEach((policy: Policy) => {
        policyMap.set(policy.id, policy);
      });
      setPolicies(policyMap);
    } catch (error) {
      console.error("Failed to fetch policies:", error);
    }
  };

  const detectInconsistencies = async () => {
    try {
      setDetecting(true);
      const response = await fetch(`${API_BASE}/inconsistent-enforcement/detect`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to detect inconsistencies");
      const result = await response.json();
      alert(
        `Detection complete! Found ${result.inconsistencies_found} inconsistenc${
          result.inconsistencies_found === 1 ? "y" : "ies"
        }.`
      );
      fetchInconsistencies();
    } catch (error) {
      console.error("Failed to detect inconsistencies:", error);
      alert("Failed to detect inconsistencies. Please try again.");
    } finally {
      setDetecting(false);
    }
  };

  const updateStatus = async (
    inconsistencyId: number,
    status: string,
    notes?: string
  ) => {
    try {
      await fetch(`${API_BASE}/inconsistent-enforcement/${inconsistencyId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          resolution_notes: notes,
          resolved_by: "admin@example.com", // TODO: Use actual user email
        }),
      });
      fetchInconsistencies();
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20";
      case "high":
        return "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20";
      case "medium":
        return "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20";
      case "low":
        return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20";
      default:
        return "text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "acknowledged":
        return <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />;
      case "resolved":
        return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />;
      case "dismissed":
        return <XCircle className="w-5 h-5 text-gray-600 dark:text-gray-400" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Inconsistent Enforcement
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Cross-application policy inconsistencies and standardization recommendations
          </p>
        </div>
        <button
          onClick={detectInconsistencies}
          disabled={detecting}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors disabled:opacity-50"
        >
          {detecting ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Detecting...
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              Detect Inconsistencies
            </>
          )}
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Status:
          </label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-50 text-sm"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Severity:
          </label>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-50 text-sm"
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Inconsistencies List */}
      {inconsistencies.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
          <Shield className="w-16 h-16 text-green-600 dark:text-green-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50">
            No Inconsistencies Found
          </h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Your policies are consistently enforced across applications.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {inconsistencies.map((inc) => {
            const isExpanded = expandedInconsistency === inc.id;
            const affectedApps = inc.affected_application_ids
              .map((id) => applications.get(id)?.name || `App ${id}`)
              .join(", ");

            return (
              <div
                key={inc.id}
                className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6"
              >
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <FileWarning className="w-6 h-6 text-red-600 dark:text-red-400 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                          {inc.resource_type}
                        </h3>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(
                            inc.severity
                          )}`}
                        >
                          {inc.severity.toUpperCase()}
                        </span>
                        <div className="flex items-center gap-1">
                          {getStatusIcon(inc.status)}
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {inc.status}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                        {inc.inconsistency_description}
                      </p>
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <Building2 className="w-4 h-4" />
                        <span>
                          Affects {inc.affected_application_ids.length} application
                          {inc.affected_application_ids.length !== 1 ? "s" : ""}: {affectedApps}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      setExpandedInconsistency(isExpanded ? null : inc.id)
                    }
                    className="p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    )}
                  </button>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-800 space-y-6">
                    {/* Affected Policies */}
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-50 mb-3">
                        Current Policies ({inc.policy_ids.length})
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {inc.policy_ids.map((policyId) => {
                          const policy = policies.get(policyId);
                          const app = policy
                            ? applications.get(policy.application_id)
                            : null;

                          if (!policy) return null;

                          return (
                            <div
                              key={policyId}
                              className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                            >
                              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                                {app?.name || `App ${policy.application_id}`}
                              </div>
                              <div className="space-y-1 text-sm">
                                <div>
                                  <span className="text-gray-600 dark:text-gray-400">
                                    Subject:{" "}
                                  </span>
                                  <span className="text-gray-900 dark:text-gray-50 font-medium">
                                    {policy.subject}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-gray-600 dark:text-gray-400">
                                    Action:{" "}
                                  </span>
                                  <span className="text-gray-900 dark:text-gray-50 font-medium">
                                    {policy.action}
                                  </span>
                                </div>
                                {policy.conditions && (
                                  <div>
                                    <span className="text-gray-600 dark:text-gray-400">
                                      Conditions:{" "}
                                    </span>
                                    <span className="text-gray-900 dark:text-gray-50">
                                      {policy.conditions}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Recommended Policy */}
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                      <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-50 mb-3">
                        Recommended Standardized Policy
                      </h4>
                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">
                            Subject:{" "}
                          </span>
                          <span className="text-blue-900 dark:text-blue-50 font-medium">
                            {inc.recommended_policy.subject}
                          </span>
                        </div>
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">
                            Resource:{" "}
                          </span>
                          <span className="text-blue-900 dark:text-blue-50 font-medium">
                            {inc.recommended_policy.resource}
                          </span>
                        </div>
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">
                            Action:{" "}
                          </span>
                          <span className="text-blue-900 dark:text-blue-50 font-medium">
                            {inc.recommended_policy.action}
                          </span>
                        </div>
                        {inc.recommended_policy.conditions && (
                          <div>
                            <span className="text-blue-700 dark:text-blue-300">
                              Conditions:{" "}
                            </span>
                            <span className="text-blue-900 dark:text-blue-50">
                              {inc.recommended_policy.conditions}
                            </span>
                          </div>
                        )}
                      </div>
                      <p className="mt-3 text-sm text-blue-800 dark:text-blue-200">
                        {inc.recommendation_explanation}
                      </p>
                    </div>

                    {/* Actions */}
                    {inc.status === "pending" && (
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => {
                            const notes = prompt(
                              "Enter acknowledgement notes (optional):"
                            );
                            updateStatus(inc.id, "acknowledged", notes || undefined);
                          }}
                          className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors text-sm"
                        >
                          Acknowledge
                        </button>
                        <button
                          onClick={() => {
                            const notes = prompt(
                              "Enter resolution notes describing how the policy was standardized:"
                            );
                            if (notes) {
                              updateStatus(inc.id, "resolved", notes);
                            }
                          }}
                          className="px-4 py-2 bg-green-600 dark:bg-green-500 text-white rounded-lg hover:bg-green-700 dark:hover:bg-green-600 transition-colors text-sm"
                        >
                          Mark as Resolved
                        </button>
                        <button
                          onClick={() => {
                            const notes = prompt(
                              "Enter reason for dismissing this inconsistency:"
                            );
                            if (notes) {
                              updateStatus(inc.id, "dismissed", notes);
                            }
                          }}
                          className="px-4 py-2 bg-gray-600 dark:bg-gray-500 text-white rounded-lg hover:bg-gray-700 dark:hover:bg-gray-600 transition-colors text-sm"
                        >
                          Dismiss
                        </button>
                      </div>
                    )}

                    {/* Resolution Info */}
                    {inc.status !== "pending" && inc.resolution_notes && (
                      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-50 mb-2">
                          Resolution Notes
                        </h4>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {inc.resolution_notes}
                        </p>
                        {inc.resolved_by && (
                          <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                            Resolved by {inc.resolved_by} on{" "}
                            {inc.resolved_at
                              ? new Date(inc.resolved_at).toLocaleDateString()
                              : "N/A"}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
