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

export default function BulkScanPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepos, setSelectedRepos] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [bulkScanResult, setBulkScanResult] = useState<BulkScanResult | null>(null);
  const [taskStatuses, setTaskStatuses] = useState<Map<string, TaskStatus>>(new Map());
  const [incremental, setIncremental] = useState(false);

  useEffect(() => {
    fetchRepositories();
  }, []);

  useEffect(() => {
    // Poll task statuses if we have a bulk scan running
    if (bulkScanResult && bulkScanResult.task_ids.length > 0) {
      const interval = setInterval(() => {
        updateTaskStatuses();
      }, 3000); // Poll every 3 seconds

      return () => clearInterval(interval);
    }
  }, [bulkScanResult]);

  const fetchRepositories = async () => {
    try {
      const response = await fetch('/api/v1/repositories/');
      if (!response.ok) throw new Error('Failed to fetch repositories');
      const data = await response.json();
      setRepositories(data);
    } catch (err: any) {
      console.error('Failed to fetch repositories:', err);
    } finally {
      setLoading(false);
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
            Parallel Scanning
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Scan multiple repositories in parallel using distributed workers
          </p>
        </div>
      </div>

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
