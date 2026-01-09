import React, { useEffect, useState } from "react";
import { FileCode, Download, CheckCircle, XCircle, Clock, AlertCircle } from "lucide-react";
import { CodeAdvisory, AdvisoryStatus } from "../types/codeAdvisory";

const API_BASE = "/api/v1";

export default function CodeAdvisoriesPage() {
  const [advisories, setAdvisories] = useState<CodeAdvisory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<AdvisoryStatus | "all">("all");
  const [selectedAdvisory, setSelectedAdvisory] = useState<CodeAdvisory | null>(null);

  useEffect(() => {
    fetchAdvisories();
  }, [filterStatus]);

  const fetchAdvisories = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== "all") {
        params.append("status", filterStatus);
      }
      const response = await fetch(`${API_BASE}/code-advisories/?${params}`);
      const data = await response.json();
      setAdvisories(data);
    } catch (error) {
      console.error("Failed to fetch advisories:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (advisoryId: number, status: AdvisoryStatus) => {
    try {
      await fetch(`${API_BASE}/code-advisories/${advisoryId}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      fetchAdvisories();
      setSelectedAdvisory(null);
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  const downloadRefactoredCode = (advisory: CodeAdvisory) => {
    const blob = new Blob([advisory.refactored_code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const fileName = advisory.file_path.split("/").pop() || "refactored_code.txt";
    a.download = `refactored_${fileName}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getStatusBadge = (status: AdvisoryStatus) => {
    const badges = {
      pending: { bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-800 dark:text-amber-200", label: "Pending" },
      reviewed: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-800 dark:text-blue-200", label: "Reviewed" },
      applied: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-800 dark:text-green-200", label: "Applied" },
      rejected: { bg: "bg-red-100 dark:bg-red-900/30", text: "text-red-800 dark:text-red-200", label: "Rejected" },
    };
    const badge = badges[status];
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium ${badge.bg} ${badge.text}`}>
        {status === "pending" && <Clock className="w-3 h-3" />}
        {status === "reviewed" && <AlertCircle className="w-3 h-3" />}
        {status === "applied" && <CheckCircle className="w-3 h-3" />}
        {status === "rejected" && <XCircle className="w-3 h-3" />}
        {badge.label}
      </span>
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Code Change Advisories</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          AI-generated refactoring suggestions to externalize inline authorization to PBAC platforms
        </p>
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2">
        {[
          { value: "all", label: "All" },
          { value: "pending", label: "Pending" },
          { value: "reviewed", label: "Reviewed" },
          { value: "applied", label: "Applied" },
          { value: "rejected", label: "Rejected" },
        ].map((filter) => (
          <button
            key={filter.value}
            onClick={() => setFilterStatus(filter.value as AdvisoryStatus | "all")}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              filterStatus === filter.value
                ? "bg-blue-600 text-white"
                : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Advisories List */}
      {loading ? (
        <div className="text-center py-12 text-gray-600 dark:text-gray-400">Loading advisories...</div>
      ) : advisories.length === 0 ? (
        <div className="text-center py-12">
          <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-50">No code advisories</h3>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Generate advisories from the Policies page to see refactoring suggestions here
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {advisories.map((advisory) => (
            <div
              key={advisory.id}
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer"
              onClick={() => setSelectedAdvisory(advisory)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <FileCode className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-gray-50">{advisory.file_path}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Lines {advisory.line_start}-{advisory.line_end}
                    </p>
                  </div>
                </div>
                {getStatusBadge(advisory.status)}
              </div>

              <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">{advisory.explanation}</p>

              <div className="mt-4 flex gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedAdvisory(advisory);
                  }}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  View Details
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    downloadRefactoredCode(advisory);
                  }}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  <Download className="w-3 h-3" />
                  Download
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Advisory Detail Modal */}
      {selectedAdvisory && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedAdvisory(null)}
        >
          <div
            className="bg-white dark:bg-gray-950 rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 p-6 z-10">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50">Code Change Advisory</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{selectedAdvisory.file_path}</p>
                </div>
                <button
                  onClick={() => setSelectedAdvisory(null)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Explanation */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-50 mb-2">Explanation</h3>
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  {selectedAdvisory.explanation}
                </p>
              </div>

              {/* Side-by-side diff */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-50 mb-2">Original Code</h3>
                  <pre className="text-xs bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg overflow-x-auto">
                    <code className="text-gray-900 dark:text-gray-50">{selectedAdvisory.original_code}</code>
                  </pre>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-50 mb-2">Refactored Code</h3>
                  <pre className="text-xs bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4 rounded-lg overflow-x-auto">
                    <code className="text-gray-900 dark:text-gray-50">{selectedAdvisory.refactored_code}</code>
                  </pre>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-800">
                <button
                  onClick={() => downloadRefactoredCode(selectedAdvisory)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download Code
                </button>
                {selectedAdvisory.status === "pending" && (
                  <>
                    <button
                      onClick={() => updateStatus(selectedAdvisory.id, "reviewed")}
                      className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
                    >
                      Mark as Reviewed
                    </button>
                    <button
                      onClick={() => updateStatus(selectedAdvisory.id, "applied")}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      Mark as Applied
                    </button>
                    <button
                      onClick={() => updateStatus(selectedAdvisory.id, "rejected")}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                    >
                      Reject
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
