import React, { useEffect, useState } from "react";
import {
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  Zap,
  Shield,
  TrendingUp,
  AlertCircle,
  Info,
  Download,
} from "lucide-react";

const API_BASE = "/api/v1";

interface OPAVerification {
  id: string;
  tenant_id: string;
  application_id: string;
  policy_id: string;
  baseline_inline_checks: number | null;
  baseline_scan_date: string | null;
  code_advisory_id: string | null;
  refactoring_applied: boolean;
  refactoring_applied_at: string | null;
  verification_status: string;
  verification_date: string | null;
  opa_calls_detected: boolean;
  inline_checks_remaining: number | null;
  spaghetti_reduction_percentage: number | null;
  opa_endpoint_url: string | null;
  opa_connection_verified: boolean;
  opa_decision_enforced: boolean;
  inline_latency_ms: number | null;
  opa_latency_ms: number | null;
  latency_overhead_ms: number | null;
  latency_overhead_percentage: number | null;
  verification_notes: string | null;
  created_at: string;
  updated_at: string;
  is_fully_migrated: boolean;
  migration_completeness: number;
}

interface VerificationStats {
  total_verifications: number;
  fully_migrated: number;
  in_progress: number;
  pending: number;
  average_spaghetti_reduction_percentage: number;
  average_latency_overhead_ms: number;
}

export default function OPAVerificationsPage() {
  const [verifications, setVerifications] = useState<OPAVerification[]>([]);
  const [stats, setStats] = useState<VerificationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  useEffect(() => {
    fetchVerifications();
    fetchStats();
  }, [filterStatus]);

  const fetchVerifications = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }
      const response = await fetch(`${API_BASE}/opa-verifications/?${params}`);
      const data = await response.json();
      setVerifications(data);
    } catch (error) {
      console.error("Failed to fetch verifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/opa-verifications/statistics/`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch statistics:", error);
    }
  };

  const exportReport = async () => {
    try {
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }
      const response = await fetch(`${API_BASE}/opa-verifications/export/report/?${params}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `spaghetti-to-lasagna-migration-report-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Failed to export report:", error);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "verified":
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            Verified
          </span>
        );
      case "in_progress":
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400">
            <Activity className="w-3 h-3" />
            In Progress
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
            <XCircle className="w-3 h-3" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-400">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        );
    }
  };

  const getLatencyBadge = (overhead_percentage: number | null) => {
    if (overhead_percentage === null) {
      return <span className="text-gray-400 dark:text-gray-500">-</span>;
    }

    if (overhead_percentage < 10) {
      return (
        <span className="text-green-600 dark:text-green-400 font-medium">
          +{overhead_percentage.toFixed(1)}%
        </span>
      );
    } else if (overhead_percentage < 25) {
      return (
        <span className="text-amber-600 dark:text-amber-400 font-medium">
          +{overhead_percentage.toFixed(1)}%
        </span>
      );
    } else {
      return (
        <span className="text-red-600 dark:text-red-400 font-medium">
          +{overhead_percentage.toFixed(1)}%
        </span>
      );
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
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Lasagna Architecture Verification
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Track migration from inline authorization (spaghetti) to centralized PBAC (lasagna)
          </p>
        </div>
        <button
          onClick={exportReport}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Download className="w-4 h-4" />
          Export Report
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Verifications</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-gray-50 mt-1">
                  {stats.total_verifications}
                </p>
              </div>
              <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Fully Migrated</p>
                <p className="text-2xl font-semibold text-green-600 dark:text-green-400 mt-1">
                  {stats.fully_migrated}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg Spaghetti Reduction</p>
                <p className="text-2xl font-semibold text-blue-600 dark:text-blue-400 mt-1">
                  {(stats.average_spaghetti_reduction_percentage || 0).toFixed(1)}%
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg Latency Overhead</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-gray-50 mt-1">
                  {(stats.average_latency_overhead_ms || 0).toFixed(1)}ms
                </p>
              </div>
              <Zap className="w-8 h-8 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-50"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="verified">Verified</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Verifications List */}
      {verifications.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-12 text-center">
          <Shield className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-2">
            No OPA Verifications Yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Start verifying applications have migrated to centralized PBAC (OPA)
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {verifications.map((verification) => (
            <div
              key={verification.id}
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50">
                      Application {verification.application_id}
                    </h3>
                    {getStatusBadge(verification.verification_status)}
                    {verification.is_fully_migrated && (
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400">
                        <Shield className="w-3 h-3" />
                        Lasagna Architecture ✓
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Policy ID: {verification.policy_id}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-semibold text-blue-600 dark:text-blue-400">
                    {verification.migration_completeness.toFixed(0)}%
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Complete</p>
                </div>
              </div>

              {/* Migration Progress */}
              <div className="mb-4">
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-blue-600 dark:bg-blue-400 h-2 rounded-full transition-all"
                    style={{ width: `${verification.migration_completeness}%` }}
                  ></div>
                </div>
              </div>

              {/* Verification Checks */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                <div className="flex items-center gap-2">
                  {verification.refactoring_applied ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-gray-400 dark:text-gray-600" />
                  )}
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Refactoring Applied
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {verification.opa_calls_detected ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-gray-400 dark:text-gray-600" />
                  )}
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    OPA Calls Detected
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {verification.opa_connection_verified ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-gray-400 dark:text-gray-600" />
                  )}
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Connection Verified
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {verification.opa_decision_enforced ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-gray-400 dark:text-gray-600" />
                  )}
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Decision Enforced
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {verification.inline_checks_remaining === 0 ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                  )}
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    No Inline Checks
                  </span>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-800">
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                    Spaghetti Reduction
                  </p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                      {verification.spaghetti_reduction_percentage?.toFixed(1) || "0.0"}%
                    </span>
                    {verification.baseline_inline_checks !== null && (
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        ({verification.baseline_inline_checks} →{" "}
                        {verification.inline_checks_remaining || 0} checks)
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                    Latency Overhead
                  </p>
                  <div className="flex items-baseline gap-2">
                    {verification.latency_overhead_ms !== null ? (
                      <>
                        <span className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                          +{verification.latency_overhead_ms.toFixed(1)}ms
                        </span>
                        {getLatencyBadge(verification.latency_overhead_percentage)}
                      </>
                    ) : (
                      <span className="text-gray-400 dark:text-gray-500">Not measured</span>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">OPA Endpoint</p>
                  <span className="text-sm text-gray-900 dark:text-gray-50 font-mono">
                    {verification.opa_endpoint_url || "Not configured"}
                  </span>
                </div>
              </div>

              {/* Verification Notes */}
              {verification.verification_notes && (
                <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-blue-900 dark:text-blue-100">
                      {verification.verification_notes}
                    </p>
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="mt-4 flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
                <span>Created: {new Date(verification.created_at).toLocaleString()}</span>
                {verification.verification_date && (
                  <span>
                    Verified: {new Date(verification.verification_date).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
