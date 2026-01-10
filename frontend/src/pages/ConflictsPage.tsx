import { AlertTriangle, CheckCircle2, GitMerge, XCircle, Building2 } from "lucide-react";
import { useEffect, useState } from "react";

interface Evidence {
  id: number;
  file_path: string;
  line_start: number;
  line_end: number;
  code_snippet: string;
}

interface Application {
  id: number;
  name: string;
  criticality: string;
  business_unit_id: number;
}

interface Policy {
  id: number;
  subject: string;
  resource: string;
  action: string;
  conditions: string | null;
  description: string | null;
  status: string;
  risk_level: string | null;
  source_type: string;
  evidence: Evidence[];
  application_id: number | null;
  application?: Application;
}

interface Conflict {
  id: number;
  policy_a_id: number;
  policy_b_id: number;
  policy_a: Policy;
  policy_b: Policy;
  conflict_type: string;
  description: string;
  severity: string;
  ai_recommendation: string | null;
  status: string;
  resolution_strategy: string | null;
  resolution_notes: string | null;
  resolved_at: string | null;
  created_at: string;
}

export default function ConflictsPage() {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [detectingCrossApp, setDetectingCrossApp] = useState(false);
  const [selectedConflict, setSelectedConflict] = useState<Conflict | null>(null);
  const [filterStatus, setFilterStatus] = useState<"all" | "pending" | "resolved">("all");
  const [showCrossAppOnly, setShowCrossAppOnly] = useState(false);

  useEffect(() => {
    fetchConflicts();
  }, [filterStatus, showCrossAppOnly]);

  const fetchConflicts = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }
      if (showCrossAppOnly) {
        params.append("cross_application_only", "true");
      }

      const response = await fetch(`/api/v1/conflicts/?${params.toString()}`);
      const data = await response.json();
      setConflicts(data.conflicts);
    } catch (error) {
      console.error("Failed to fetch conflicts:", error);
    } finally {
      setLoading(false);
    }
  };

  const detectConflicts = async () => {
    try {
      setDetecting(true);
      const response = await fetch("/api/v1/conflicts/detect", {
        method: "POST",
      });
      const data = await response.json();
      setConflicts(data.conflicts);
    } catch (error) {
      console.error("Failed to detect conflicts:", error);
      alert("Failed to detect conflicts. Make sure ANTHROPIC_API_KEY is set.");
    } finally {
      setDetecting(false);
    }
  };

  const detectCrossAppConflicts = async () => {
    try {
      setDetectingCrossApp(true);
      const response = await fetch("/api/v1/conflicts/detect-cross-application", {
        method: "POST",
      });
      const data = await response.json();
      setConflicts(data.conflicts);
      setShowCrossAppOnly(true);
      alert(`Detected ${data.total} cross-application conflicts`);
    } catch (error) {
      console.error("Failed to detect cross-application conflicts:", error);
      alert("Failed to detect cross-application conflicts. Make sure ANTHROPIC_API_KEY is set.");
    } finally {
      setDetectingCrossApp(false);
    }
  };

  const resolveConflict = async (conflictId: number, strategy: string) => {
    try {
      const notes = prompt("Resolution notes (optional):");
      const response = await fetch(`/api/v1/conflicts/${conflictId}/resolve`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resolution_strategy: strategy,
          resolution_notes: notes || null,
        }),
      });

      if (response.ok) {
        await fetchConflicts();
        setSelectedConflict(null);
      }
    } catch (error) {
      console.error("Failed to resolve conflict:", error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400";
      case "medium":
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-400";
      case "low":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400";
    }
  };

  const getConflictTypeLabel = (type: string) => {
    switch (type) {
      case "contradictory":
        return "Contradictory";
      case "overlapping":
        return "Overlapping";
      case "inconsistent":
        return "Inconsistent";
      default:
        return type;
    }
  };

  const filteredConflicts = conflicts;

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50 mb-2">
            Policy Conflicts
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Detect and resolve conflicting authorization policies
          </p>
        </div>

        {/* Actions and Filters */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setFilterStatus("all")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterStatus("pending")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "pending"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => setFilterStatus("resolved")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "resolved"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              Resolved
            </button>
            <div className="border-l border-gray-300 dark:border-gray-700 mx-2"></div>
            <button
              onClick={() => setShowCrossAppOnly(!showCrossAppOnly)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                showCrossAppOnly
                  ? "bg-purple-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              <Building2 className="w-4 h-4" />
              Cross-App Only
            </button>
          </div>

          <div className="flex gap-2">
            <button
              onClick={detectConflicts}
              disabled={detecting}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {detecting ? "Detecting..." : "Detect Conflicts"}
            </button>
            <button
              onClick={detectCrossAppConflicts}
              disabled={detectingCrossApp}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
            >
              <Building2 className="w-4 h-4" />
              {detectingCrossApp ? "Detecting..." : "Detect Cross-App Conflicts"}
            </button>
          </div>
        </div>

        {/* Conflicts List */}
        {loading ? (
          <div className="text-center py-12 text-gray-600 dark:text-gray-400">Loading conflicts...</div>
        ) : filteredConflicts.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-50 mb-2">
              No conflicts found
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {filterStatus === "all"
                ? "No policy conflicts detected. Click 'Detect Conflicts' to scan for conflicts."
                : `No ${filterStatus} conflicts.`}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredConflicts.map((conflict) => (
              <div
                key={conflict.id}
                className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6"
              >
                {/* Conflict Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <AlertTriangle
                      className={`w-5 h-5 ${
                        conflict.severity === "high"
                          ? "text-red-500"
                          : conflict.severity === "medium"
                            ? "text-amber-500"
                            : "text-blue-500"
                      }`}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900 dark:text-gray-50">
                          {getConflictTypeLabel(conflict.conflict_type)} Conflict
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(conflict.severity)}`}>
                          {conflict.severity.toUpperCase()}
                        </span>
                        {conflict.status === "resolved" && (
                          <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                            RESOLVED
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {conflict.description}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Conflicting Policies */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {/* Policy A */}
                  <div className="bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Policy A (ID: {conflict.policy_a.id})
                      </h4>
                      {conflict.policy_a.application && (
                        <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-400 text-xs rounded flex items-center gap-1">
                          <Building2 className="w-3 h-3" />
                          {conflict.policy_a.application.name}
                        </span>
                      )}
                    </div>
                    <div className="space-y-1 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Who:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{conflict.policy_a.subject}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">What:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{conflict.policy_a.resource}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">How:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{conflict.policy_a.action}</span>
                      </div>
                      {conflict.policy_a.conditions && (
                        <div>
                          <span className="text-gray-600 dark:text-gray-400">When:</span>{" "}
                          <span className="text-gray-900 dark:text-gray-50">{conflict.policy_a.conditions}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Policy B */}
                  <div className="bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Policy B (ID: {conflict.policy_b.id})
                      </h4>
                      {conflict.policy_b.application && (
                        <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-400 text-xs rounded flex items-center gap-1">
                          <Building2 className="w-3 h-3" />
                          {conflict.policy_b.application.name}
                        </span>
                      )}
                    </div>
                    <div className="space-y-1 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Who:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{conflict.policy_b.subject}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">What:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{conflict.policy_b.resource}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">How:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{conflict.policy_b.action}</span>
                      </div>
                      {conflict.policy_b.conditions && (
                        <div>
                          <span className="text-gray-600 dark:text-gray-400">When:</span>{" "}
                          <span className="text-gray-900 dark:text-gray-50">{conflict.policy_b.conditions}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* AI Recommendation */}
                {conflict.ai_recommendation && (
                  <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
                    <h4 className="text-sm font-medium text-blue-900 dark:text-blue-400 mb-2">
                      AI Recommendation
                    </h4>
                    <p className="text-sm text-blue-800 dark:text-blue-300">{conflict.ai_recommendation}</p>
                  </div>
                )}

                {/* Resolution Info */}
                {conflict.status === "resolved" && (
                  <div className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-4">
                    <h4 className="text-sm font-medium text-green-900 dark:text-green-400 mb-2">
                      Resolution Applied
                    </h4>
                    <div className="text-sm text-green-800 dark:text-green-300">
                      <div>Strategy: <strong>{conflict.resolution_strategy}</strong></div>
                      {conflict.resolution_notes && <div className="mt-1">Notes: {conflict.resolution_notes}</div>}
                      {conflict.resolved_at && (
                        <div className="mt-1 text-xs">
                          Resolved: {new Date(conflict.resolved_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                {conflict.status === "pending" && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => resolveConflict(conflict.id, "keep_a")}
                      className="flex-1 px-4 py-2 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium"
                    >
                      Keep Policy A
                    </button>
                    <button
                      onClick={() => resolveConflict(conflict.id, "keep_b")}
                      className="flex-1 px-4 py-2 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium"
                    >
                      Keep Policy B
                    </button>
                    <button
                      onClick={() => resolveConflict(conflict.id, "merge")}
                      className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium flex items-center justify-center gap-2"
                    >
                      <GitMerge className="w-4 h-4" />
                      Merge Policies
                    </button>
                    <button
                      onClick={() => resolveConflict(conflict.id, "custom")}
                      className="flex-1 px-4 py-2 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium"
                    >
                      Custom Resolution
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
