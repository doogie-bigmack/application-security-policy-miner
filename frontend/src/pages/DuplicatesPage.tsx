import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Copy,
  Trash2,
  TrendingDown,
} from "lucide-react";

interface ApplicationSummary {
  id: number;
  name: string;
  business_unit_id: number | null;
}

interface SamplePolicy {
  subject: string;
  resource: string;
  action: string;
  conditions: string | null;
}

interface DuplicateGroup {
  policy_ids: number[];
  similarity_score: number;
  application_count: number;
  potential_savings: number;
  sample_policy: SamplePolicy;
  applications: ApplicationSummary[];
}

interface Statistics {
  total_policies: number;
  total_duplicates: number;
  duplicate_groups: number;
  potential_savings_count: number;
  potential_savings_percentage: number;
}

export default function DuplicatesPage() {
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [minSimilarity, setMinSimilarity] = useState(95);
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchData();
  }, [minSimilarity]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch statistics
      const statsRes = await fetch(
        `/api/v1/duplicates/statistics?min_similarity=${minSimilarity / 100}`
      );
      if (statsRes.ok) {
        const stats = await statsRes.json();
        setStatistics(stats);
      }

      // Fetch duplicates
      const dupRes = await fetch(
        `/api/v1/duplicates/?min_similarity=${minSimilarity / 100}`
      );
      if (dupRes.ok) {
        const data = await dupRes.json();
        setDuplicates(data);
      }
    } catch (error) {
      console.error("Error fetching duplicates:", error);
    } finally {
      setLoading(false);
    }
  };

  const detectDuplicates = async () => {
    setDetecting(true);
    try {
      await fetchData();
      alert("Duplicate detection complete!");
    } catch (error) {
      console.error("Error detecting duplicates:", error);
      alert("Failed to detect duplicates");
    } finally {
      setDetecting(false);
    }
  };

  const consolidateGroup = async (group: DuplicateGroup) => {
    if (!confirm(
      `Consolidate ${group.policy_ids.length} duplicate policies? This will keep 1 and remove ${group.potential_savings} duplicates.`
    )) {
      return;
    }

    // Keep the first policy by default
    const keepPolicyId = group.policy_ids[0];

    try {
      const res = await fetch("/api/v1/duplicates/consolidate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          policy_ids: group.policy_ids,
          keep_policy_id: keepPolicyId,
        }),
      });

      if (res.ok) {
        alert(`Successfully consolidated duplicates! Removed ${group.potential_savings} policies.`);
        fetchData();
      } else {
        const error = await res.text();
        alert(`Failed to consolidate: ${error}`);
      }
    } catch (error) {
      console.error("Error consolidating:", error);
      alert("Failed to consolidate duplicates");
    }
  };

  const toggleGroupExpansion = (index: number) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedGroups(newExpanded);
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500 dark:text-gray-400">
            Loading duplicates...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50 mb-2">
          Duplicate Policies Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Detect and consolidate duplicate authorization policies across applications
        </p>
      </div>

      {/* Statistics Cards */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Total Policies
            </div>
            <div className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
              {statistics.total_policies}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Duplicate Policies
            </div>
            <div className="text-3xl font-semibold text-amber-600">
              {statistics.total_duplicates}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Duplicate Groups
            </div>
            <div className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
              {statistics.duplicate_groups}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Potential Savings
            </div>
            <div className="text-3xl font-semibold text-green-600">
              {statistics.potential_savings_count}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Reduction %
            </div>
            <div className="text-3xl font-semibold text-green-600 flex items-center gap-2">
              <TrendingDown className="w-6 h-6" />
              {statistics.potential_savings_percentage}%
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={detectDuplicates}
          disabled={detecting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Copy className="w-4 h-4" />
          {detecting ? "Detecting..." : "Detect Duplicates"}
        </button>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-400">
            Min Similarity:
          </label>
          <input
            type="range"
            min="80"
            max="100"
            value={minSimilarity}
            onChange={(e) => setMinSimilarity(parseInt(e.target.value))}
            className="w-32"
          />
          <span className="text-sm font-medium text-gray-900 dark:text-gray-50 w-12">
            {minSimilarity}%
          </span>
        </div>
      </div>

      {/* Duplicate Groups */}
      {duplicates.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <CheckCircle className="w-16 h-16 text-green-600 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-2">
              No Duplicate Policies Found
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              All policies are unique across applications. Great job maintaining clean authorization logic!
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {duplicates.map((group, index) => (
            <div
              key={index}
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6"
            >
              {/* Group Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                      Duplicate Group #{index + 1}
                    </h3>
                    <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs font-medium rounded">
                      {Math.round(group.similarity_score * 100)}% Similar
                    </span>
                  </div>

                  <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <div>
                      <span className="font-medium">{group.policy_ids.length}</span> duplicate policies across{" "}
                      <span className="font-medium">{group.application_count}</span> applications
                    </div>
                    <div className="text-green-600 dark:text-green-400">
                      Potential savings: <span className="font-medium">{group.potential_savings}</span> policies
                      ({Math.round((group.potential_savings / group.policy_ids.length) * 100)}% reduction)
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => toggleGroupExpansion(index)}
                    className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    {expandedGroups.has(index) ? "Hide Details" : "Show Details"}
                  </button>
                  <button
                    onClick={() => consolidateGroup(group)}
                    className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    Consolidate
                  </button>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedGroups.has(index) && (
                <div className="border-t border-gray-200 dark:border-gray-800 pt-4 space-y-4">
                  {/* Sample Policy */}
                  <div>
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Sample Policy:
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-800 rounded p-3 space-y-1 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Subject:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{group.sample_policy.subject}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Resource:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{group.sample_policy.resource}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Action:</span>{" "}
                        <span className="text-gray-900 dark:text-gray-50">{group.sample_policy.action}</span>
                      </div>
                      {group.sample_policy.conditions && (
                        <div>
                          <span className="text-gray-600 dark:text-gray-400">Conditions:</span>{" "}
                          <span className="text-gray-900 dark:text-gray-50">{group.sample_policy.conditions}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Applications */}
                  <div>
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Affected Applications:
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {group.applications.map((app) => (
                        <span
                          key={app.id}
                          className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-sm rounded"
                        >
                          {app.name}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Policy IDs */}
                  <div>
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Policy IDs:
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 font-mono">
                      {group.policy_ids.join(", ")}
                    </div>
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
