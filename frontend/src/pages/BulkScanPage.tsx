import { useEffect, useState } from 'react'
import { Zap, CheckCircle, XCircle, Clock, Package, Loader, AlertTriangle } from 'lucide-react'
import logger from '../lib/logger'

interface Repository {
  id: number
  name: string
  repository_type: 'git' | 'database' | 'mainframe'
}

interface BulkScanJob {
  repository_id: number
  repository_name: string
  job_id: string
  status: string
}

interface BulkScanProgress {
  bulk_scan_id: number
  status: string
  total_applications: number
  completed_applications: number
  failed_applications: number
  total_policies_extracted: number
  total_files_scanned: number
  average_scan_duration_seconds: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export default function BulkScanPage() {
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [selectedRepoIds, setSelectedRepoIds] = useState<Set<number>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [isScanningInProgress, setIsScanningInProgress] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bulkScans, setBulkScans] = useState<BulkScanProgress[]>([])
  const [currentBulkScan, setCurrentBulkScan] = useState<BulkScanProgress | null>(null)
  const [maxWorkers, setMaxWorkers] = useState<number>(10)

  const fetchRepositories = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/v1/repositories/')

      if (!response.ok) {
        throw new Error('Failed to fetch repositories')
      }

      const data = await response.json()
      setRepositories(data.repositories)
      logger.info('Repositories fetched', { count: data.total })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to fetch repositories', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchBulkScans = async () => {
    try {
      const response = await fetch('/api/v1/bulk-scan/')
      if (!response.ok) {
        throw new Error('Failed to fetch bulk scans')
      }

      const data = await response.json()
      setBulkScans(data)
      logger.info('Bulk scans fetched', { count: data.length })
    } catch (err) {
      logger.error('Failed to fetch bulk scans', { error: err })
    }
  }

  const fetchBulkScanProgress = async (bulkScanId: number) => {
    try {
      const response = await fetch(`/api/v1/bulk-scan/${bulkScanId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch bulk scan progress')
      }

      const data = await response.json()
      setCurrentBulkScan(data)

      // If scan is complete, stop polling
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        setIsScanningInProgress(false)
        fetchBulkScans() // Refresh list
      }
    } catch (err) {
      logger.error('Failed to fetch bulk scan progress', { error: err })
    }
  }

  useEffect(() => {
    logger.info('BulkScanPage mounted')
    fetchRepositories()
    fetchBulkScans()
  }, [])

  // Poll for progress if scanning in progress
  useEffect(() => {
    if (isScanningInProgress && currentBulkScan) {
      const interval = setInterval(() => {
        fetchBulkScanProgress(currentBulkScan.bulk_scan_id)
      }, 2000) // Poll every 2 seconds

      return () => clearInterval(interval)
    }
  }, [isScanningInProgress, currentBulkScan])

  const toggleRepoSelection = (repoId: number) => {
    const newSelected = new Set(selectedRepoIds)
    if (newSelected.has(repoId)) {
      newSelected.delete(repoId)
    } else {
      newSelected.add(repoId)
    }
    setSelectedRepoIds(newSelected)
  }

  const selectAll = () => {
    if (selectedRepoIds.size === repositories.length) {
      setSelectedRepoIds(new Set())
    } else {
      setSelectedRepoIds(new Set(repositories.map(r => r.id)))
    }
  }

  const startBulkScan = async () => {
    if (selectedRepoIds.size === 0) {
      setError('Please select at least one repository to scan')
      return
    }

    try {
      setError(null)
      setIsScanningInProgress(true)

      const response = await fetch('/api/v1/bulk-scan/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_ids: Array.from(selectedRepoIds),
          incremental: false,
          max_parallel_workers: maxWorkers,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start bulk scan')
      }

      const data = await response.json()
      logger.info('Bulk scan initiated', { bulkScanId: data.bulk_scan_id })

      // Start polling for progress
      setCurrentBulkScan({
        bulk_scan_id: data.bulk_scan_id,
        status: 'processing',
        total_applications: data.total_applications,
        completed_applications: 0,
        failed_applications: 0,
        total_policies_extracted: 0,
        total_files_scanned: 0,
        average_scan_duration_seconds: null,
        started_at: new Date().toISOString(),
        completed_at: null,
        created_at: new Date().toISOString(),
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to start bulk scan', { error: errorMessage })
      setError(errorMessage)
      setIsScanningInProgress(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />
      case 'processing':
      case 'queued':
        return <Loader className="w-5 h-5 text-blue-600 animate-spin" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'queued':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">Bulk Scan</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Scan multiple repositories in parallel for faster policy extraction
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 mr-2" />
            <div className="flex-1">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Current Bulk Scan Progress */}
      {currentBulkScan && isScanningInProgress && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
              Scan in Progress
            </h2>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadge(currentBulkScan.status)}`}>
              {currentBulkScan.status.toUpperCase()}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
              <span>
                {currentBulkScan.completed_applications + currentBulkScan.failed_applications} / {currentBulkScan.total_applications} applications
              </span>
              <span>
                {Math.round(((currentBulkScan.completed_applications + currentBulkScan.failed_applications) / currentBulkScan.total_applications) * 100)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${((currentBulkScan.completed_applications + currentBulkScan.failed_applications) / currentBulkScan.total_applications) * 100}%`,
                }}
              />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">Completed</div>
              <div className="text-2xl font-semibold text-green-600 dark:text-green-400">
                {currentBulkScan.completed_applications}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">Failed</div>
              <div className="text-2xl font-semibold text-red-600 dark:text-red-400">
                {currentBulkScan.failed_applications}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">Policies</div>
              <div className="text-2xl font-semibold text-blue-600 dark:text-blue-400">
                {currentBulkScan.total_policies_extracted}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">Files Scanned</div>
              <div className="text-2xl font-semibold text-purple-600 dark:text-purple-400">
                {currentBulkScan.total_files_scanned}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Card */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
          Select Repositories
        </h2>

        {/* Max Workers Config */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Maximum Parallel Workers
          </label>
          <input
            type="number"
            min="1"
            max="100"
            value={maxWorkers}
            onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 10)}
            className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-50"
            disabled={isScanningInProgress}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Number of repositories to scan simultaneously (1-100)
          </p>
        </div>

        {/* Select All Button */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={selectAll}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
            disabled={isScanningInProgress}
          >
            {selectedRepoIds.size === repositories.length ? 'Deselect All' : 'Select All'}
          </button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {selectedRepoIds.size} selected
          </span>
        </div>

        {/* Repository List */}
        {isLoading ? (
          <div className="text-center py-8">
            <Loader className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading repositories...</p>
          </div>
        ) : repositories.length === 0 ? (
          <div className="text-center py-8">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600 dark:text-gray-400">No repositories found</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {repositories.map((repo) => (
              <label
                key={repo.id}
                className={`flex items-center p-3 rounded-lg border transition-colors cursor-pointer ${
                  selectedRepoIds.has(repo.id)
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'
                } ${isScanningInProgress ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={selectedRepoIds.has(repo.id)}
                  onChange={() => toggleRepoSelection(repo.id)}
                  disabled={isScanningInProgress}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <div className="ml-3 flex-1">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-50">
                    {repo.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {repo.repository_type}
                  </div>
                </div>
              </label>
            ))}
          </div>
        )}

        {/* Start Scan Button */}
        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {selectedRepoIds.size > 0 && (
              <span>
                Will scan {selectedRepoIds.size} {selectedRepoIds.size === 1 ? 'repository' : 'repositories'} with up to {maxWorkers} parallel workers
              </span>
            )}
          </div>
          <button
            onClick={startBulkScan}
            disabled={selectedRepoIds.size === 0 || isScanningInProgress}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Zap className="w-4 h-4 mr-2" />
            Start Bulk Scan
          </button>
        </div>
      </div>

      {/* Recent Bulk Scans */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
          Recent Bulk Scans
        </h2>

        {bulkScans.length === 0 ? (
          <div className="text-center py-8">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600 dark:text-gray-400">No bulk scans yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {bulkScans.map((scan) => (
              <div
                key={scan.bulk_scan_id}
                className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-800 rounded-lg"
              >
                <div className="flex items-start space-x-4">
                  {getStatusIcon(scan.status)}
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-50">
                      Bulk Scan #{scan.bulk_scan_id}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      {scan.total_applications} applications • {scan.completed_applications} completed • {scan.failed_applications} failed
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      Started: {new Date(scan.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-gray-900 dark:text-gray-50">
                    {scan.total_policies_extracted}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">policies</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
