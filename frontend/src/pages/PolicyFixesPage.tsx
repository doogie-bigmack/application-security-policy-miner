import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  FileText,
  TestTube,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const API_BASE = "/api/v1";

interface PolicyFix {
  id: number;
  policy_id: number;
  tenant_id: string;
  security_gap_type: string;
  severity: "low" | "medium" | "high" | "critical";
  gap_description: string;
  missing_checks: string | null;
  original_policy: string;
  fixed_policy: string;
  fix_explanation: string;
  test_cases: string | null;
  attack_scenario: string | null;
  status: "pending" | "reviewed" | "applied" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_comment: string | null;
  created_at: string;
  updated_at: string;
}

export default function PolicyFixesPage() {
  const [fixes, setFixes] = useState<PolicyFix[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [expandedFix, setExpandedFix] = useState<number | null>(null);
  const [generatingTests, setGeneratingTests] = useState<number | null>(null);

  useEffect(() => {
    fetchFixes();
  }, [filterStatus, filterSeverity]);

  const fetchFixes = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }
      if (filterSeverity !== "all") {
        params.append("severity", filterSeverity);
      }
      const response = await fetch(`${API_BASE}/policy-fixes/?${params}`);
      const data = await response.json();
      setFixes(data);
    } catch (error) {
      console.error("Failed to fetch fixes:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (fixId: number, status: string, comment?: string) => {
    try {
      await fetch(`${API_BASE}/policy-fixes/${fixId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          reviewed_by: "admin@example.com", // TODO: Use actual user email
          review_comment: comment,
        }),
      });
      fetchFixes();
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  const generateTestCases = async (fixId: number) => {
    try {
      setGeneratingTests(fixId);
      const response = await fetch(`${API_BASE}/policy-fixes/${fixId}/test-cases`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to generate test cases");
      const updatedFix = await response.json();

      // Update the fix in the list
      setFixes((prev) => prev.map((f) => (f.id === fixId ? updatedFix : f)));
    } catch (error) {
      console.error("Failed to generate test cases:", error);
      alert("Failed to generate test cases. Please try again.");
    } finally {
      setGeneratingTests(null);
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
      case "reviewed":
        return <CheckCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />;
      case "applied":
        return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />;
      case "rejected":
        return <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400" />;
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
            Policy Fixes
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            AI-detected security gaps and recommended fixes
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
            Status
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setFilterStatus("all")}
              className={`px-3 py-1 text-sm rounded-lg ${
                filterStatus === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterStatus("pending")}
              className={`px-3 py-1 text-sm rounded-lg ${
                filterStatus === "pending"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => setFilterStatus("reviewed")}
              className={`px-3 py-1 text-sm rounded-lg ${
                filterStatus === "reviewed"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              Reviewed
            </button>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
            Severity
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setFilterSeverity("all")}
              className={`px-3 py-1 text-sm rounded-lg ${
                filterSeverity === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterSeverity("critical")}
              className={`px-3 py-1 text-sm rounded-lg ${
                filterSeverity === "critical"
                  ? "bg-red-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              Critical
            </button>
            <button
              onClick={() => setFilterSeverity("high")}
              className={`px-3 py-1 text-sm rounded-lg ${
                filterSeverity === "high"
                  ? "bg-orange-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              High
            </button>
          </div>
        </div>
      </div>

      {/* Fixes List */}
      {fixes.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-12 text-center">
          <Shield className="w-12 h-12 text-green-600 dark:text-green-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-2">
            No Security Gaps Found
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            All analyzed policies appear to have complete authorization logic.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {fixes.map((fix) => (
            <div
              key={fix.id}
              className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">{getStatusIcon(fix.status)}</div>
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50">
                        {fix.security_gap_type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                      </h3>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(
                          fix.severity
                        )}`}
                      >
                        {fix.severity.toUpperCase()}
                      </span>
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                        Policy #{fix.policy_id}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {fix.gap_description}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setExpandedFix(expandedFix === fix.id ? null : fix.id)}
                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-50"
                >
                  {expandedFix === fix.id ? (
                    <ChevronUp className="w-5 h-5" />
                  ) : (
                    <ChevronDown className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Expanded Details */}
              {expandedFix === fix.id && (
                <div className="space-y-6 border-t border-gray-200 dark:border-gray-800 pt-6">
                  {/* Missing Checks */}
                  {fix.missing_checks && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        Missing Security Checks
                      </h4>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                        {JSON.parse(fix.missing_checks).map((check: string, idx: number) => (
                          <li key={idx}>{check}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Side-by-side Policy Comparison */}
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2 flex items-center gap-2">
                        <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                        Original Policy (with gaps)
                      </h4>
                      <pre className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-xs text-gray-900 dark:text-gray-50 overflow-x-auto border border-red-200 dark:border-red-800">
                        {JSON.stringify(JSON.parse(fix.original_policy), null, 2)}
                      </pre>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                        Fixed Policy (complete logic)
                      </h4>
                      <pre className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg text-xs text-gray-900 dark:text-gray-50 overflow-x-auto border border-green-200 dark:border-green-800">
                        {JSON.stringify(JSON.parse(fix.fixed_policy), null, 2)}
                      </pre>
                    </div>
                  </div>

                  {/* Fix Explanation */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      Fix Explanation
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                      {fix.fix_explanation}
                    </p>
                  </div>

                  {/* Attack Scenario (for privilege escalation) */}
                  {fix.attack_scenario && fix.security_gap_type === "privilege_escalation" && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
                        Attack Scenario
                      </h4>
                      <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg border border-red-200 dark:border-red-800">
                        <pre className="text-xs text-gray-900 dark:text-gray-50 whitespace-pre-wrap font-mono">
                          {fix.attack_scenario}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Test Cases */}
                  {fix.test_cases ? (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2 flex items-center gap-2">
                        <TestTube className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        Security Test Cases
                      </h4>
                      <div className="space-y-3">
                        {JSON.parse(fix.test_cases).map((testCase: any, idx: number) => (
                          <div
                            key={idx}
                            className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                          >
                            <h5 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-1">
                              {testCase.name}
                            </h5>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                              {testCase.scenario}
                            </p>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">
                                  Original:
                                </span>{" "}
                                <span
                                  className={
                                    testCase.expected_original === "ALLOWED"
                                      ? "text-green-600 dark:text-green-400"
                                      : "text-red-600 dark:text-red-400"
                                  }
                                >
                                  {testCase.expected_original}
                                </span>
                              </div>
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">
                                  Fixed:
                                </span>{" "}
                                <span
                                  className={
                                    testCase.expected_fixed === "ALLOWED"
                                      ? "text-green-600 dark:text-green-400"
                                      : "text-red-600 dark:text-red-400"
                                  }
                                >
                                  {testCase.expected_fixed}
                                </span>
                              </div>
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2 italic">
                              {testCase.reasoning}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => generateTestCases(fix.id)}
                      disabled={generatingTests === fix.id}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                    >
                      <TestTube className="w-4 h-4" />
                      {generatingTests === fix.id
                        ? "Generating Test Cases..."
                        : "Generate Test Cases"}
                    </button>
                  )}

                  {/* Review Actions */}
                  {fix.status === "pending" && (
                    <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-800">
                      <button
                        onClick={() => {
                          const comment = prompt("Enter review comment (optional):");
                          updateStatus(fix.id, "reviewed", comment || undefined);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Review & Approve Fix
                      </button>
                      <button
                        onClick={() => {
                          const comment = prompt("Enter reason for rejection:");
                          if (comment) {
                            updateStatus(fix.id, "rejected", comment);
                          }
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                      >
                        <XCircle className="w-4 h-4" />
                        Reject Fix
                      </button>
                    </div>
                  )}

                  {/* Review Info */}
                  {fix.reviewed_at && (
                    <div className="text-xs text-gray-500 dark:text-gray-500 pt-4 border-t border-gray-200 dark:border-gray-800">
                      Reviewed by {fix.reviewed_by} on{" "}
                      {new Date(fix.reviewed_at).toLocaleDateString()}
                      {fix.review_comment && ` - ${fix.review_comment}`}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
