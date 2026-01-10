import React, { useEffect, useState } from "react";
import { FileCode, Download, CheckCircle, XCircle, Clock, AlertCircle, TestTube, FileText } from "lucide-react";
import { CodeAdvisory, AdvisoryStatus, TestCase } from "../types/codeAdvisory";
import DiffViewer from "../components/DiffViewer";

const API_BASE = "/api/v1";

export default function CodeAdvisoriesPage() {
  const [advisories, setAdvisories] = useState<CodeAdvisory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<AdvisoryStatus | "all">("all");
  const [selectedAdvisory, setSelectedAdvisory] = useState<CodeAdvisory | null>(null);
  const [generatingTests, setGeneratingTests] = useState<number | null>(null);

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

  const generateTestCases = async (advisoryId: number) => {
    try {
      setGeneratingTests(advisoryId);
      const response = await fetch(`${API_BASE}/code-advisories/${advisoryId}/generate-tests/`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to generate test cases");
      const updatedAdvisory = await response.json();

      // Update the advisory in the list
      setAdvisories((prev) =>
        prev.map((a) => (a.id === advisoryId ? updatedAdvisory : a))
      );

      // Update selected advisory if it's the one being updated
      if (selectedAdvisory?.id === advisoryId) {
        setSelectedAdvisory(updatedAdvisory);
      }
    } catch (error) {
      console.error("Failed to generate test cases:", error);
      alert("Failed to generate test cases. Please try again.");
    } finally {
      setGeneratingTests(null);
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

  const downloadPatchFile = (advisory: CodeAdvisory) => {
    // Generate unified diff format patch
    const fileName = advisory.file_path.split("/").pop() || "file";
    const now = new Date().toISOString();

    const patch = `--- a/${advisory.file_path}\t${now}
+++ b/${advisory.file_path}\t${now}
@@ -${advisory.line_start},${advisory.line_end - advisory.line_start + 1} +${advisory.line_start},${advisory.line_end - advisory.line_start + 1} @@
${advisory.original_code.split('\n').map(line => `-${line}`).join('\n')}
${advisory.refactored_code.split('\n').map(line => `+${line}`).join('\n')}
`;

    const blob = new Blob([patch], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileName}.patch`;
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

              {/* Side-by-side diff with highlighting */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-50 mb-3">Code Diff</h3>
                <DiffViewer
                  originalCode={selectedAdvisory.original_code}
                  refactoredCode={selectedAdvisory.refactored_code}
                  fileName={selectedAdvisory.file_path.split("/").pop()}
                  language="javascript"
                />
              </div>

              {/* Test Cases */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-50">Generated Test Cases</h3>
                  {!selectedAdvisory.test_cases && (
                    <button
                      onClick={() => generateTestCases(selectedAdvisory.id)}
                      disabled={generatingTests === selectedAdvisory.id}
                      className="px-3 py-1 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-1 disabled:opacity-50"
                    >
                      <TestTube className="w-3 h-3" />
                      {generatingTests === selectedAdvisory.id ? "Generating..." : "Generate Test Cases"}
                    </button>
                  )}
                </div>

                {selectedAdvisory.test_cases ? (
                  (() => {
                    try {
                      const testCases: TestCase[] = JSON.parse(selectedAdvisory.test_cases);
                      if (testCases.length === 0 || testCases[0]?.error) {
                        return (
                          <div className="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg">
                            Failed to generate test cases. Please try again.
                          </div>
                        );
                      }
                      return (
                        <div className="space-y-3">
                          {testCases.map((testCase, index) => (
                            <div
                              key={index}
                              className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4 rounded-lg"
                            >
                              <div className="flex items-start justify-between mb-2">
                                <h4 className="font-medium text-sm text-gray-900 dark:text-gray-50">
                                  {index + 1}. {testCase.name}
                                </h4>
                              </div>
                              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{testCase.scenario}</p>
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Setup:</span>
                                  <p className="text-gray-600 dark:text-gray-400 mt-1">{testCase.setup}</p>
                                </div>
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Expected Result:</span>
                                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                                    Original: {testCase.expected_original} | Refactored: {testCase.expected_refactored}
                                  </p>
                                </div>
                              </div>
                              <div className="mt-2 text-xs">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Assertion:</span>
                                <p className="text-gray-600 dark:text-gray-400 mt-1">{testCase.assertion}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    } catch (e) {
                      return (
                        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                          Error parsing test cases
                        </div>
                      );
                    }
                  })()
                ) : (
                  <div className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    No test cases generated yet. Click the button above to generate comprehensive test cases for this
                    advisory.
                  </div>
                )}
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
                <button
                  onClick={() => downloadPatchFile(selectedAdvisory)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Download Patch
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
