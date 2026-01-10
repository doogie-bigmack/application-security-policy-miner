import React, { useEffect, useState, useRef } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingDown,
  TrendingUp,
  XCircle,
  Code2,
  GitBranch,
  Shield,
} from 'lucide-react';
import logger from '../lib/logger';
import { ToastContainer } from '../components/Toast';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7777/api/v1';

interface WorkItem {
  id: number;
  policy_change_id: number;
  repository_id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assigned_to: string | null;
  is_spaghetti_detection: number;
  refactoring_suggestion: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  tenant_id: string | null;
}

interface SpaghettiMetrics {
  total_detections: number;
  open_detections: number;
  resolved_detections: number;
  detection_rate: number;
  avg_resolution_time_hours: number | null;
  detections_by_repository: Array<{
    repository_id: number;
    total: number;
    open: number;
    resolved: number;
  }>;
  recent_detections: WorkItem[];
}

const GovernancePage: React.FC = () => {
  const [metrics, setMetrics] = useState<SpaghettiMetrics | null>(null);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWorkItem, setSelectedWorkItem] = useState<WorkItem | null>(null);
  const [days, setDays] = useState(30);
  const [toasts, setToasts] = useState<Array<{ id: string; type: 'success' | 'error' | 'warning' | 'info'; title: string; message?: string }>>([]);
  const previousOpenCount = useRef<number>(0);

  useEffect(() => {
    fetchMetrics();
    fetchWorkItems();
  }, [days]);

  // Poll for new detections every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchMetrics();
      fetchWorkItems();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, []);

  // Check for new detections and show notification
  useEffect(() => {
    if (metrics && previousOpenCount.current > 0 && metrics.open_detections > previousOpenCount.current) {
      const newDetections = metrics.open_detections - previousOpenCount.current;
      addToast({
        type: 'warning',
        title: '⚠️ NEW SPAGHETTI DETECTED',
        message: `${newDetections} new inline authorization check${newDetections > 1 ? 's' : ''} detected. Use centralized PBAC instead.`,
      });
    }
    if (metrics) {
      previousOpenCount.current = metrics.open_detections;
    }
  }, [metrics]);

  const addToast = (toast: { type: 'success' | 'error' | 'warning' | 'info'; title: string; message?: string }) => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, ...toast }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      logger.info('Fetching spaghetti metrics', { days });
      const response = await fetch(`${API_BASE_URL}/work-items/metrics/spaghetti?days=${days}`);
      if (!response.ok) {
        throw new Error('Failed to fetch metrics');
      }
      const data = await response.json();
      setMetrics(data);
      logger.info('Fetched spaghetti metrics', { total_detections: data.total_detections });
    } catch (err) {
      logger.error('Failed to fetch metrics', { error: err });
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchWorkItems = async () => {
    try {
      logger.info('Fetching work items');
      const response = await fetch(`${API_BASE_URL}/work-items/?spaghetti_only=true&limit=50`);
      if (!response.ok) {
        throw new Error('Failed to fetch work items');
      }
      const data = await response.json();
      setWorkItems(data);
      logger.info('Fetched work items', { count: data.length });
    } catch (err) {
      logger.error('Failed to fetch work items', { error: err });
    }
  };

  const updateWorkItemStatus = async (workItemId: number, status: string) => {
    try {
      logger.info('Updating work item status', { workItemId, status });
      const response = await fetch(`${API_BASE_URL}/work-items/${workItemId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        throw new Error('Failed to update work item');
      }
      logger.info('Updated work item status', { workItemId, status });
      // Refresh data
      await fetchMetrics();
      await fetchWorkItems();
      setSelectedWorkItem(null);
    } catch (err) {
      logger.error('Failed to update work item', { error: err, workItemId });
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950';
      case 'high':
        return 'text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-950';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950';
      case 'low':
        return 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-950';
      default:
        return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950';
      case 'in_progress':
        return 'text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950';
      case 'resolved':
        return 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950';
      case 'closed':
        return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900';
      default:
        return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading governance metrics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 dark:bg-red-950 p-6">
        <div className="flex items-center gap-3 text-red-800 dark:text-red-200">
          <XCircle size={20} />
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">Continuous Governance</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Track and prevent new spaghetti code from being added to your applications
        </p>
      </div>

      {/* Time Range Selector */}
      <div className="flex gap-2">
        {[7, 30, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              days === d
                ? 'bg-blue-600 text-white'
                : 'bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Last {d} days
          </button>
        ))}
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Total Detections */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Detections</p>
                <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-gray-50">
                  {metrics.total_detections}
                </p>
              </div>
              <AlertTriangle className="text-orange-600 dark:text-orange-400" size={32} />
            </div>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
              {metrics.detection_rate.toFixed(1)} per day
            </p>
          </div>

          {/* Open Issues */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Open Issues</p>
                <p className="mt-2 text-3xl font-semibold text-red-600 dark:text-red-400">
                  {metrics.open_detections}
                </p>
              </div>
              <XCircle className="text-red-600 dark:text-red-400" size={32} />
            </div>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">Require attention</p>
          </div>

          {/* Resolved */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Resolved</p>
                <p className="mt-2 text-3xl font-semibold text-green-600 dark:text-green-400">
                  {metrics.resolved_detections}
                </p>
              </div>
              <CheckCircle className="text-green-600 dark:text-green-400" size={32} />
            </div>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
              {metrics.total_detections > 0
                ? `${((metrics.resolved_detections / metrics.total_detections) * 100).toFixed(1)}% resolution rate`
                : 'No detections'}
            </p>
          </div>

          {/* Avg Resolution Time */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg Resolution Time</p>
                <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-gray-50">
                  {metrics.avg_resolution_time_hours
                    ? `${metrics.avg_resolution_time_hours.toFixed(1)}h`
                    : 'N/A'}
                </p>
              </div>
              <Clock className="text-blue-600 dark:text-blue-400" size={32} />
            </div>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">Time to fix</p>
          </div>
        </div>
      )}

      {/* Work Items List */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <div className="border-b border-gray-200 dark:border-gray-800 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
            Spaghetti Code Detections
          </h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            New inline authorization checks detected by continuous monitoring
          </p>
        </div>

        <div className="divide-y divide-gray-200 dark:divide-gray-800">
          {workItems.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Shield className="mx-auto text-gray-400 dark:text-gray-600" size={48} />
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                No spaghetti code detected - great job!
              </p>
            </div>
          ) : (
            workItems.map((item) => (
              <div
                key={item.id}
                className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-900 cursor-pointer transition-colors"
                onClick={() => setSelectedWorkItem(item)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <Code2 className="text-orange-600 dark:text-orange-400 flex-shrink-0" size={20} />
                      <h3 className="text-sm font-medium text-gray-900 dark:text-gray-50 truncate">
                        {item.title}
                      </h3>
                    </div>
                    {item.description && (
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {item.description}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                      <span>Repo ID: {item.repository_id}</span>
                      <span>•</span>
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getPriorityColor(
                        item.priority
                      )}`}
                    >
                      {item.priority}
                    </span>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(
                        item.status
                      )}`}
                    >
                      {item.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Work Item Detail Modal */}
      {selectedWorkItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800 max-w-3xl w-full max-h-[80vh] overflow-y-auto">
            <div className="border-b border-gray-200 dark:border-gray-800 px-6 py-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                    {selectedWorkItem.title}
                  </h3>
                  <div className="mt-2 flex items-center gap-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getPriorityColor(
                        selectedWorkItem.priority
                      )}`}
                    >
                      {selectedWorkItem.priority}
                    </span>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(
                        selectedWorkItem.status
                      )}`}
                    >
                      {selectedWorkItem.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedWorkItem(null)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <XCircle size={24} />
                </button>
              </div>
            </div>

            <div className="px-6 py-4 space-y-6">
              {/* Description */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2">Description</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedWorkItem.description || 'No description available'}
                </p>
              </div>

              {/* Refactoring Suggestion */}
              {selectedWorkItem.refactoring_suggestion && (
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2">
                    Refactoring Suggestion
                  </h4>
                  <div className="rounded-lg bg-gray-50 dark:bg-gray-900 p-4">
                    <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono">
                      {selectedWorkItem.refactoring_suggestion}
                    </pre>
                  </div>
                </div>
              )}

              {/* Metadata */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-50 mb-2">Details</h4>
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-gray-600 dark:text-gray-400">Repository ID</dt>
                    <dd className="mt-1 text-gray-900 dark:text-gray-50">{selectedWorkItem.repository_id}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-600 dark:text-gray-400">Created</dt>
                    <dd className="mt-1 text-gray-900 dark:text-gray-50">
                      {formatDate(selectedWorkItem.created_at)}
                    </dd>
                  </div>
                  {selectedWorkItem.assigned_to && (
                    <div>
                      <dt className="text-gray-600 dark:text-gray-400">Assigned To</dt>
                      <dd className="mt-1 text-gray-900 dark:text-gray-50">{selectedWorkItem.assigned_to}</dd>
                    </div>
                  )}
                  {selectedWorkItem.resolved_at && (
                    <div>
                      <dt className="text-gray-600 dark:text-gray-400">Resolved</dt>
                      <dd className="mt-1 text-gray-900 dark:text-gray-50">
                        {formatDate(selectedWorkItem.resolved_at)}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                {selectedWorkItem.status === 'open' && (
                  <button
                    onClick={() => updateWorkItemStatus(selectedWorkItem.id, 'in_progress')}
                    className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    Start Work
                  </button>
                )}
                {selectedWorkItem.status === 'in_progress' && (
                  <button
                    onClick={() => updateWorkItemStatus(selectedWorkItem.id, 'resolved')}
                    className="flex-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                  >
                    Mark Resolved
                  </button>
                )}
                {selectedWorkItem.status === 'resolved' && (
                  <button
                    onClick={() => updateWorkItemStatus(selectedWorkItem.id, 'closed')}
                    className="flex-1 rounded-lg bg-gray-600 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
                  >
                    Close
                  </button>
                )}
                <button
                  onClick={() => setSelectedWorkItem(null)}
                  className="flex-1 rounded-lg border border-gray-300 dark:border-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </div>
  );
};

export default GovernancePage;
