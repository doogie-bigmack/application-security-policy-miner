import { useState, useEffect } from 'react';
import { AlertCircle, Activity, Server, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

interface AutoscalerConfig {
  min_workers: number;
  max_workers: number;
  scale_up_threshold: number;
  scale_down_threshold: number;
  check_interval: number;
}

interface AutoscalerMetrics {
  config: AutoscalerConfig;
  current_state: {
    total_workers: number;
    running_containers: number;
    queue_depth: number;
    active_tasks: number;
  };
  status: string;
}

export default function AutoscalerPage() {
  const [metrics, setMetrics] = useState<AutoscalerMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scaleTarget, setScaleTarget] = useState('');
  const [scaling, setScaling] = useState(false);
  const [restarting, setRestarting] = useState(false);

  const fetchMetrics = async () => {
    try {
      const response = await fetch('http://localhost:7777/api/v1/monitoring/autoscaler/metrics/');
      if (!response.ok) {
        throw new Error('Failed to fetch autoscaler metrics');
      }
      const data = await response.json();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleManualScale = async () => {
    if (!scaleTarget || isNaN(Number(scaleTarget))) {
      alert('Please enter a valid number');
      return;
    }

    setScaling(true);
    try {
      const response = await fetch('http://localhost:7777/api/v1/monitoring/autoscaler/scale/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ target_count: Number(scaleTarget) }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to scale workers');
      }

      alert(`Successfully initiated scaling to ${scaleTarget} workers`);
      setScaleTarget('');
      await fetchMetrics();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setScaling(false);
    }
  };

  const handleRestartFailed = async () => {
    setRestarting(true);
    try {
      const response = await fetch('http://localhost:7777/api/v1/monitoring/workers/restart-failed/', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to restart workers');
      }

      alert('Successfully triggered restart of failed workers');
      await fetchMetrics();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setRestarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">Worker Autoscaler</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Monitor and manage distributed worker auto-scaling
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Status Card */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${metrics.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-50">
              Autoscaler Status: {metrics.status === 'running' ? 'Active' : 'Stopped'}
            </span>
          </div>
        </div>
      </div>

      {/* Current State Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Server className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Workers</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {metrics.current_state.total_workers}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <Activity className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Running Containers</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {metrics.current_state.running_containers}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
              <TrendingUp className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Queue Depth</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {metrics.current_state.queue_depth}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Activity className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Active Tasks</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
                {metrics.current_state.active_tasks}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Min Workers</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">{metrics.config.min_workers}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Max Workers</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">{metrics.config.max_workers}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Scale Up Threshold</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">{metrics.config.scale_up_threshold}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Scale Down Threshold</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">{metrics.config.scale_down_threshold}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Check Interval</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">{metrics.config.check_interval}s</p>
          </div>
        </div>
      </div>

      {/* Manual Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">Manual Scaling</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Manually scale workers to a specific count (between {metrics.config.min_workers} and {metrics.config.max_workers})
          </p>
          <div className="flex gap-3">
            <input
              type="number"
              value={scaleTarget}
              onChange={(e) => setScaleTarget(e.target.value)}
              placeholder="Target worker count"
              min={metrics.config.min_workers}
              max={metrics.config.max_workers}
              className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleManualScale}
              disabled={scaling}
              className="px-6 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {scaling ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Scaling...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4" />
                  Scale
                </>
              )}
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">Worker Management</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Restart any failed or unhealthy workers automatically
          </p>
          <button
            onClick={handleRestartFailed}
            disabled={restarting}
            className="w-full px-6 py-2 bg-amber-600 dark:bg-amber-500 text-white rounded-lg hover:bg-amber-700 dark:hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {restarting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Restarting...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Restart Failed Workers
              </>
            )}
          </button>
        </div>
      </div>

      {/* Scaling Logic Info */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-6">
        <h2 className="text-xl font-semibold text-blue-900 dark:text-blue-200 mb-4">How Autoscaling Works</h2>
        <div className="space-y-3 text-sm text-blue-800 dark:text-blue-300">
          <div className="flex items-start gap-3">
            <TrendingUp className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <p>
              <strong>Scale Up:</strong> When queue depth exceeds {metrics.config.scale_up_threshold} tasks per worker,
              the autoscaler increases worker count by 50% or adds at least 5 workers.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <TrendingDown className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <p>
              <strong>Scale Down:</strong> When queue depth falls below {metrics.config.scale_down_threshold} tasks
              and worker count exceeds the minimum, the autoscaler reduces worker count by 25%.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Activity className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <p>
              <strong>Health Checks:</strong> Failed workers are automatically detected and restarted every {metrics.config.check_interval} seconds.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
