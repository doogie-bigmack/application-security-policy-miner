import { useState, useEffect } from 'react';
import {
  Play,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  Package,
  Zap,
  Activity,
} from 'lucide-react';

interface Repository {
  id: number;
  name: string;
  repository_type: string;
  status: string;
  source_url: string | null;
}

interface TaskInfo {
  repository_id: number;
  task_id: string;
  status?: string;
  state?: string;
}

interface BulkScanResult {
  total_repositories: number;
  total_batches: number;
  batch_size: number;
  spawned_tasks: number;
  task_ids: TaskInfo[];
  status: string;
  bulk_task_id: string;
}

interface TaskStatus {
  task_id: string;
  state: string;
  result: any;
  meta: any;
}

interface WorkerStats {
  worker_name: string;
  status: string;
  active_tasks: number;
  processed_tasks: number;
  pool_size: number;
}

interface QueueStats {
  total_workers: number;
  active_workers: number;
  total_tasks_active: number;
  total_tasks_reserved: number;
  queue_depth: number;
  workers: WorkerStats[];
}

interface BulkProgress {
  task_id: string;
  state: string;
  result: any;
  meta: {
    total_repositories: number;
    total_batches: number;
    current_batch?: number;
    batch_size: number;
    spawned_so_far?: number;
    status: string;
  } | null;
}

export default function BulkScanPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepos, setSelectedRepos] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [bulkScanResult, setBulkScanResult] = useState<BulkScanResult | null>(null);
  const [taskStatuses, setTaskStatuses] = useState<Map<string, TaskStatus>>(new Map());
  const [incremental, setIncremental] = useState(false);
  const [batchSize, setBatchSize] = useState(50);
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [bulkProgress, setBulkProgress] = useState<BulkProgress | null>(null);

  useEffect(() => {
    fetchRepositories();
    fetchQueueStats();

    // Poll queue stats every 5 seconds
    const interval = setInterval(fetchQueueStats, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Poll task statuses and bulk progress if we have a bulk scan running
    if (bulkScanResult && bulkScanResult.task_ids.length > 0) {
      const interval = setInterval(() => {
        updateTaskStatuses();
        if (bulkScanResult.bulk_task_id) {
          fetchBulkProgress(bulkScanResult.bulk_task_id);
        }
      }, 3000); // Poll every 3 seconds

      return () => clearInterval(interval);
    }
  }, [bulkScanResult]);

  const fetchRepositories = async () => {
    try {
      const response = await fetch('/api/v1/repositories/');
      if (!response.ok) throw new Error('Failed to fetch repositories');
      const data = await response.json();
      setRepositories(data.repositories || data);
    } catch (err: any) {
      console.error('Failed to fetch repositories:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchQueueStats = async () => {
    try {
      const response = await fetch('/api/v1/monitoring/queue-stats/');
      if (!response.ok) return;
      const data = await response.json();
      setQueueStats(data);
    } catch (err) {
      // Silently fail to avoid spamming errors
    }
  };

  const fetchBulkProgress = async (taskId: string) => {
    try {
      const response = await fetch(`/api/v1/monitoring/bulk-task/${taskId}/progress/`);
      if (!response.ok) return;
      const data = await response.json();
      setBulkProgress(data);
    } catch (err) {
      // Silently fail
    }
  };

  const updateTaskStatuses = async () => {
    if (!bulkScanResult) return;

    const newStatuses = new Map<string, TaskStatus>();

    for (const taskInfo of bulkScanResult.task_ids) {
      try {
        const response = await fetch(`/api/v1/bulk-scan/task/${taskInfo.task_id}/status/`);
        if (response.ok) {
          const status: TaskStatus = await response.json();
          newStatuses.set(taskInfo.task_id, status);
        }
      } catch (err) {
        console.error(`Failed to fetch status for task ${taskInfo.task_id}:`, err);
      }
    }

    setTaskStatuses(newStatuses);

    // Check if all tasks are done
    const allDone = Array.from(newStatuses.values()).every(
      (status) => status.state === 'SUCCESS' || status.state === 'FAILURE'
    );

    if (allDone) {
      setScanning(false);
    }
  };

  const toggleRepo = (repoId: number) => {
    const newSelected = new Set(selectedRepos);
    if (newSelected.has(repoId)) {
      newSelected.delete(repoId);
    } else {
      newSelected.add(repoId);
    }
    setSelectedRepos(newSelected);
  };

  const toggleAll = () => {
    if (selectedRepos.size === repositories.length) {
      setSelectedRepos(new Set());
    } else {
      setSelectedRepos(new Set(repositories.map((r) => r.id)));
    }
  };

  const startBulkScan = async () => {
    if (selectedRepos.size === 0) {
      alert('Please select at least one repository');
      return;
    }

    setScanning(true);

    try {
      const response = await fetch('/api/v1/bulk-scan/bulk-scan/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_ids: Array.from(selectedRepos),
          incremental,
          batch_size: batchSize,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start bulk scan');
      }

      const result: BulkScanResult = await response.json();
      setBulkScanResult(result);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
      setScanning(false);
    }
  };

  const getRepositoryName = (repoId: number) => {
    return repositories.find((r) => r.id === repoId)?.name || `Repo ${repoId}`;
  };

  const getTaskState = (taskId: string): string => {
    const status = taskStatuses.get(taskId);
    return status?.state || 'PENDING';
  };

  const getTaskStateColor = (state: string): string => {
    switch (state) {
      case 'SUCCESS':
        return 'text-green-600 dark:text-green-400';
      case 'FAILURE':
        return 'text-red-600 dark:text-red-400';
      case 'STARTED':
      case 'PROGRESS':
        return 'text-blue-600 dark:text-blue-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getTaskStateIcon = (state: string) => {
    switch (state) {
      case 'SUCCESS':
        return <CheckCircle className="w-5 h-5" />;
      case 'FAILURE':
        return <AlertCircle className="w-5 h-5" />;
      case 'STARTED':
      case 'PROGRESS':
        return <Loader2 className="w-5 h-5 animate-spin" />;
      default:
        return <Clock className="w-5 h-5" />;
    }
  };

  const completedCount = bulkScanResult
    ? bulkScanResult.task_ids.filter(
        (t) => getTaskState(t.task_id) === 'SUCCESS' || getTaskState(t.task_id) === 'FAILURE'
      ).length
    : 0;

  const successCount = bulkScanResult
    ? bulkScanResult.task_ids.filter((t) => getTaskState(t.task_id) === 'SUCCESS').length
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
            Enterprise-Scale Parallel Scanning
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Scan hundreds or thousands of repositories in parallel with batch processing
          </p>
        </div>
      </div>

      {/* Queue Stats Dashboard */}
      {queueStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Workers</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                  {queueStats.active_workers}/{queueStats.total_workers}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  {queueStats.active_workers} active
                </p>
              </div>
              <Activity className="w-8 h-8 text-blue-600" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Active Tasks</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                  {queueStats.total_tasks_active}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  Running now
                </p>
              </div>
              <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Queue Depth</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                  {queueStats.queue_depth}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  Tasks waiting
                </p>
              </div>
              <Clock className="w-8 h-8 text-amber-600" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">System Status</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                  {scanning ? 'Scanning' : 'Ready'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  {scanning ? 'In progress' : 'Idle'}
                </p>
              </div>
              {scanning ? (
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              ) : (
                <CheckCircle className="w-8 h-8 text-green-600" />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Bulk Progress */}
      {bulkProgress && bulkProgress.meta && (
        <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Loader2 className="w-5 h-5 animate-spin text-blue-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900 dark:text-blue-50 mb-1">
                Batch Processing in Progress
              </h3>
              <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                {bulkProgress.meta.status}
              </p>
              {bulkProgress.meta.current_batch && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm text-blue-800 dark:text-blue-200">
                    <span>Batch {bulkProgress.meta.current_batch} of {bulkProgress.meta.total_batches}</span>
                    <span>{bulkProgress.meta.spawned_so_far}/{bulkProgress.meta.total_repositories} tasks spawned</span>
                  </div>
                  <div className="w-full bg-blue-200 dark:bg-blue-900 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${((bulkProgress.meta.current_batch || 0) / bulkProgress.meta.total_batches) * 100}%`
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Control Panel */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedRepos.size === repositories.length && repositories.length > 0}
                onChange={toggleAll}
                className="rounded border-gray-300 dark:border-gray-700"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Select All ({repositories.length} repositories)
              </span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={incremental}
                onChange={(e) => setIncremental(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-700"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">
                <Zap className="w-4 h-4 text-yellow-500" />
                Incremental Scan
              </span>
            </label>

            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-700 dark:text-gray-300">
                Batch Size:
              </label>
              <input
                type="number"
                value={batchSize}
                onChange={(e) => setBatchSize(parseInt(e.target.value) || 50)}
                min="1"
                max="100"
                className="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
              />
              <span className="text-xs text-gray-500 dark:text-gray-500">
                (repos/batch)
              </span>
            </div>
          </div>

          <button
            onClick={startBulkScan}
            disabled={scanning || selectedRepos.size === 0}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {scanning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Parallel Scan ({selectedRepos.size})
              </>
            )}
          </button>
        </div>

        {/* Selected count */}
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {selectedRepos.size} of {repositories.length} repositories selected
        </div>
      </div>

      {/* Progress Dashboard */}
      {bulkScanResult && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-600" />
              Scan Progress
              {bulkScanResult.total_batches > 1 && (
                <span className="text-sm font-normal text-gray-600 dark:text-gray-400">
                  ({bulkScanResult.total_batches} batches × {bulkScanResult.batch_size} repos/batch)
                </span>
              )}
            </h2>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {completedCount} / {bulkScanResult.total_repositories} completed
            </div>
          </div>

          {/* Progress bar */}
          <div className="mb-6">
            <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${(completedCount / bulkScanResult.total_repositories) * 100}%`,
                }}
              />
            </div>
            <div className="mt-2 flex justify-between text-xs text-gray-600 dark:text-gray-400">
              <span>{successCount} successful</span>
              <span>{completedCount - successCount} failed</span>
            </div>
          </div>

          {/* Task list */}
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {bulkScanResult.task_ids.map((taskInfo) => {
              const state = getTaskState(taskInfo.task_id);
              const status = taskStatuses.get(taskInfo.task_id);

              return (
                <div
                  key={taskInfo.task_id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className={getTaskStateColor(state)}>{getTaskStateIcon(state)}</div>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-50">
                        {getRepositoryName(taskInfo.repository_id)}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-500">
                        Task ID: {taskInfo.task_id.substring(0, 8)}...
                      </div>
                    </div>
                  </div>
                  <div className="text-sm">
                    <span className={`font-medium ${getTaskStateColor(state)}`}>{state}</span>
                    {status?.meta && (
                      <div className="text-xs text-gray-500 dark:text-gray-500">
                        {status.meta.status}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Repository List */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
            Available Repositories
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-800">
          {repositories.map((repo) => (
            <div
              key={repo.id}
              className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
              onClick={() => toggleRepo(repo.id)}
            >
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={selectedRepos.has(repo.id)}
                  onChange={() => toggleRepo(repo.id)}
                  onClick={(e) => e.stopPropagation()}
                  className="rounded border-gray-300 dark:border-gray-700"
                />
                <Package className="w-5 h-5 text-gray-400" />
                <div className="flex-1">
                  <div className="font-medium text-gray-900 dark:text-gray-50">{repo.name}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {repo.repository_type} • {repo.status}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
