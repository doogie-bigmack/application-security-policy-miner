import { useEffect, useState } from "react";
import { Calendar, User, FileCode, AlertCircle, Check, X } from "lucide-react";

interface AuditLog {
  id: number;
  event_type: string;
  event_description: string;
  user_email: string | null;
  repository_id: number | null;
  policy_id: number | null;
  conflict_id: number | null;
  ai_model: string | null;
  ai_provider: string | null;
  ai_prompt: string | null;
  ai_response: string | null;
  request_metadata: Record<string, any> | null;
  response_metadata: Record<string, any> | null;
  additional_data: Record<string, any> | null;
  created_at: string;
}

type EventTypeFilter = "all" | "ai_prompt" | "ai_response" | "policy_approval" | "policy_rejection" | "provisioning";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<EventTypeFilter>("all");
  const [expandedLog, setExpandedLog] = useState<number | null>(null);

  useEffect(() => {
    fetchAuditLogs();
  }, [filter]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter !== "all") {
        params.append("event_type", filter);
      }
      params.append("limit", "50");

      const response = await fetch(`/api/v1/audit-logs/?${params.toString()}`);
      const data = await response.json();
      setLogs(data.items || []);
    } catch (error) {
      console.error("Failed to fetch audit logs:", error);
    } finally {
      setLoading(false);
    }
  };

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case "ai_prompt":
      case "ai_response":
        return "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950";
      case "policy_approval":
        return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950";
      case "policy_rejection":
        return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950";
      case "provisioning":
        return "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950";
      default:
        return "text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900";
    }
  };

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType) {
      case "policy_approval":
        return <Check className="w-4 h-4" />;
      case "policy_rejection":
        return <X className="w-4 h-4" />;
      default:
        return <FileCode className="w-4 h-4" />;
    }
  };

  const formatEventType = (eventType: string) => {
    return eventType
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">Audit Logs</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Complete audit trail of all system operations, AI prompts, and user decisions
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === "all"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          All Events
        </button>
        <button
          onClick={() => setFilter("ai_prompt")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === "ai_prompt"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          AI Prompts
        </button>
        <button
          onClick={() => setFilter("ai_response")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === "ai_response"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          AI Responses
        </button>
        <button
          onClick={() => setFilter("policy_approval")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === "policy_approval"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          Approvals
        </button>
        <button
          onClick={() => setFilter("policy_rejection")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === "policy_rejection"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          Rejections
        </button>
      </div>

      {/* Audit Logs List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading audit logs...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-50">No audit logs</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            No audit log entries found for the selected filter.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {logs.map((log) => (
            <div
              key={log.id}
              className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${getEventTypeColor(
                        log.event_type
                      )}`}
                    >
                      {getEventTypeIcon(log.event_type)}
                      {formatEventType(log.event_type)}
                    </span>
                    {log.ai_model && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Model: {log.ai_model}
                      </span>
                    )}
                    {log.ai_provider && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Provider: {log.ai_provider}
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm text-gray-900 dark:text-gray-50">{log.event_description}</p>

                  <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    {log.user_email && (
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        <span>{log.user_email}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(log.created_at)}</span>
                    </div>
                    {log.repository_id && <span>Repo ID: {log.repository_id}</span>}
                    {log.policy_id && <span>Policy ID: {log.policy_id}</span>}
                  </div>

                  {/* Expandable details */}
                  {(log.ai_prompt || log.ai_response || log.additional_data) && (
                    <div className="mt-3">
                      <button
                        onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                        className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                      >
                        {expandedLog === log.id ? "Hide details" : "Show details"}
                      </button>

                      {expandedLog === log.id && (
                        <div className="mt-3 space-y-3">
                          {log.ai_prompt && (
                            <div>
                              <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                                AI Prompt:
                              </h4>
                              <pre className="text-xs bg-gray-50 dark:bg-gray-950 p-3 rounded border border-gray-200 dark:border-gray-800 overflow-x-auto">
                                {truncateText(log.ai_prompt, 1000)}
                              </pre>
                            </div>
                          )}

                          {log.ai_response && (
                            <div>
                              <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                                AI Response:
                              </h4>
                              <pre className="text-xs bg-gray-50 dark:bg-gray-950 p-3 rounded border border-gray-200 dark:border-gray-800 overflow-x-auto">
                                {truncateText(log.ai_response, 1000)}
                              </pre>
                            </div>
                          )}

                          {log.additional_data && (
                            <div>
                              <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Additional Data:
                              </h4>
                              <pre className="text-xs bg-gray-50 dark:bg-gray-950 p-3 rounded border border-gray-200 dark:border-gray-800 overflow-x-auto">
                                {JSON.stringify(log.additional_data, null, 2)}
                              </pre>
                            </div>
                          )}

                          {log.response_metadata && (
                            <div>
                              <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Response Metadata:
                              </h4>
                              <pre className="text-xs bg-gray-50 dark:bg-gray-950 p-3 rounded border border-gray-200 dark:border-gray-800 overflow-x-auto">
                                {JSON.stringify(log.response_metadata, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
