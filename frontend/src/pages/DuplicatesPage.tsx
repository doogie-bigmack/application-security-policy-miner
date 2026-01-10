import { AlertTriangle, CheckCircle2, Copy, GitMerge, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

interface Evidence {
  id: number;
  file_path: string;
  line_start: number;
  line_end: number;
  code_snippet: string;
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
  application_id: number | null;
  evidence: Evidence[];
}

interface DuplicatePolicyMember {
  policy_id: number;
  similarity_to_group: number;
  policy: Policy;
}

interface DuplicateGroup {
  id: number;
  status: string;
  group_name: string | null;
  description: string | null;
  avg_similarity_score: number;
  min_similarity_score: number;
  policy_count: number;
  consolidated_policy_id: number | null;
  consolidation_notes: string | null;
  created_at: string;
  consolidated_at: string | null;
  policies?: DuplicatePolicyMember[];
}

export default function DuplicatesPage() {
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<DuplicateGroup | null>(null);
  const [filterStatus, setFilterStatus] = useState<"all" | "detected" | "consolidated" | "dismissed">("all");
  const [minSimilarity, setMinSimilarity] = useState(0.85);

  useEffect(() => {
    fetchGroups();
  }, [filterStatus]);

  const fetchGroups = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }

      const response = await fetch(`/api/v1/duplicates/?${params.toString()}`);
      const data = await response.json();
      setGroups(data);
    } catch (error) {
      console.error("Failed to fetch duplicate groups:", error);
    } finally {
      setLoading(false);
    }
  };

  const detectDuplicates = async () => {
    try {
      setDetecting(true);
      const response = await fetch("/api/v1/duplicates/detect/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          min_similarity: minSimilarity,
        }),
      });
      const data = await response.json();
      alert(`Found ${data.groups_created} duplicate groups with ${data.policies_in_groups} policies`);
      await fetchGroups();
    } catch (error) {
      console.error("Failed to detect duplicates:", error);
      alert("Failed to detect duplicates. Please try again.");
    } finally {
      setDetecting(false);
    }
  };

  const viewGroupDetails = async (groupId: number) => {
    try {
      const response = await fetch(`/api/v1/duplicates/${groupId}/`);
      const data = await response.json();
      setSelectedGroup(data);
    } catch (error) {
      console.error("Failed to fetch group details:", error);
    }
  };

  const consolidateGroup = async (groupId: number, policyId: number) => {
    try {
      const notes = prompt("Consolidation notes (optional):");
      const response = await fetch(`/api/v1/duplicates/${groupId}/consolidate/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          consolidated_policy_id: policyId,
          notes: notes || null,
        }),
      });

      if (response.ok) {
        alert("Duplicate group consolidated successfully!");
        await fetchGroups();
        setSelectedGroup(null);
      }
    } catch (error) {
      console.error("Failed to consolidate duplicates:", error);
      alert("Failed to consolidate duplicates. Please try again.");
    }
  };

  const dismissGroup = async (groupId: number) => {
    try {
      const notes = prompt("Why is this not a duplicate? (optional):");
      const response = await fetch(`/api/v1/duplicates/${groupId}/dismiss/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes: notes || null,
        }),
      });

      if (response.ok) {
        alert("Duplicate group dismissed successfully!");
        await fetchGroups();
        setSelectedGroup(null);
      }
    } catch (error) {
      console.error("Failed to dismiss duplicates:", error);
      alert("Failed to dismiss duplicates. Please try again.");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "detected":
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-400";
      case "consolidated":
        return "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400";
      case "dismissed":
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400";
    }
  };

  const getRiskLevelColor = (level: string | null) => {
    switch (level) {
      case "high":
        return "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400";
      case "medium":
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-400";
      case "low":
        return "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400";
    }
  };

  const formatSimilarity = (score: number) => {
    return `${(score * 100).toFixed(1)}%`;
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50 mb-2">
            Duplicate Policies
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Detect and consolidate duplicate policies across applications
          </p>
        </div>

        {/* Actions and Filters */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterStatus("all")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterStatus("detected")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "detected"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              Detected
            </button>
            <button
              onClick={() => setFilterStatus("consolidated")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "consolidated"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              Consolidated
            </button>
            <button
              onClick={() => setFilterStatus("dismissed")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === "dismissed"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              Dismissed
            </button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600 dark:text-gray-400">
                Min Similarity:
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={minSimilarity}
                onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
                className="px-3 py-2 w-20 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-50"
              />
            </div>
            <button
              onClick={detectDuplicates}
              disabled={detecting}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Copy className="w-4 h-4" />
              {detecting ? "Detecting..." : "Detect Duplicates"}
            </button>
          </div>
        </div>

        {/* Groups List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="text-gray-600 dark:text-gray-400">Loading duplicate groups...</div>
          </div>
        ) : groups.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
            <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              No duplicate policy groups found. Click "Detect Duplicates" to scan for duplicates.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {groups.map((group) => (
              <div
                key={group.id}
                className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                        {group.description || `Duplicate Group #${group.id}`}
                      </h3>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(group.status)}`}>
                        {group.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Policies:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-gray-50">
                          {group.policy_count}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Avg Similarity:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-gray-50">
                          {formatSimilarity(group.avg_similarity_score)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Min Similarity:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-gray-50">
                          {formatSimilarity(group.min_similarity_score)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => viewGroupDetails(group.id)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                  >
                    View Details
                  </button>
                </div>

                {group.consolidation_notes && (
                  <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
                    <p className="text-sm text-blue-900 dark:text-blue-300">
                      <strong>Notes:</strong> {group.consolidation_notes}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Group Details Modal */}
        {selectedGroup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-900 rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-200 dark:border-gray-800">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-50 mb-2">
                      {selectedGroup.description || `Duplicate Group #${selectedGroup.id}`}
                    </h2>
                    <div className="flex items-center gap-4 text-sm">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(selectedGroup.status)}`}>
                        {selectedGroup.status.toUpperCase()}
                      </span>
                      <span className="text-gray-600 dark:text-gray-400">
                        {selectedGroup.policy_count} policies
                      </span>
                      <span className="text-gray-600 dark:text-gray-400">
                        Avg: {formatSimilarity(selectedGroup.avg_similarity_score)}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedGroup(null)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <XCircle className="w-6 h-6" />
                  </button>
                </div>
              </div>

              <div className="p-6">
                {/* Policy List */}
                <div className="space-y-4">
                  {selectedGroup.policies?.map((member) => (
                    <div
                      key={member.policy_id}
                      className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium text-gray-900 dark:text-gray-50">
                              Policy #{member.policy_id}
                            </h4>
                            {member.policy.risk_level && (
                              <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskLevelColor(member.policy.risk_level)}`}>
                                {member.policy.risk_level.toUpperCase()}
                              </span>
                            )}
                            <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
                              {formatSimilarity(member.similarity_to_group)} match
                            </span>
                          </div>
                        </div>

                        {selectedGroup.status === "detected" && (
                          <button
                            onClick={() => consolidateGroup(selectedGroup.id, member.policy_id)}
                            className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
                          >
                            Use as Centralized Policy
                          </button>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600 dark:text-gray-400">Subject:</span>
                          <span className="ml-2 text-gray-900 dark:text-gray-50">{member.policy.subject}</span>
                        </div>
                        <div>
                          <span className="text-gray-600 dark:text-gray-400">Resource:</span>
                          <span className="ml-2 text-gray-900 dark:text-gray-50">{member.policy.resource}</span>
                        </div>
                        <div>
                          <span className="text-gray-600 dark:text-gray-400">Action:</span>
                          <span className="ml-2 text-gray-900 dark:text-gray-50">{member.policy.action}</span>
                        </div>
                        {member.policy.conditions && (
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Conditions:</span>
                            <span className="ml-2 text-gray-900 dark:text-gray-50">{member.policy.conditions}</span>
                          </div>
                        )}
                      </div>

                      {member.policy.description && (
                        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
                          {member.policy.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {/* Actions */}
                {selectedGroup.status === "detected" && (
                  <div className="mt-6 flex items-center justify-end gap-3 pt-6 border-t border-gray-200 dark:border-gray-800">
                    <button
                      onClick={() => dismissGroup(selectedGroup.id)}
                      className="px-4 py-2 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      Dismiss as False Positive
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
