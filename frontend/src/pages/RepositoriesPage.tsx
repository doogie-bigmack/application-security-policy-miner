import { useEffect, useState } from 'react'
import { GitBranch, Database, Server, ExternalLink, Play, Webhook, Copy, Check, Filter, ArrowUpDown, Eye, Edit2, Trash2, ChevronDown, Zap } from 'lucide-react'
import logger from '../lib/logger'
import AddRepositoryModal from '../components/AddRepositoryModal'

interface Repository {
  id: number
  name: string
  description: string | null
  repository_type: 'git' | 'database' | 'mainframe'
  source_url: string | null
  status: 'pending' | 'connected' | 'failed' | 'scanning'
  created_at: string
  last_scan_at: string | null
  webhook_secret: string | null
  webhook_enabled: boolean
}

interface ScanProgress {
  id: number
  repository_id: number
  status: 'queued' | 'processing' | 'completed' | 'failed'
  total_files: number
  processed_files: number
  current_batch: number
  total_batches: number
  policies_extracted: number
  errors_count: number
  error_message: string | null
}

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scanningRepoId, setScanningRepoId] = useState<number | null>(null)
  const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null)
  const [webhookModalOpen, setWebhookModalOpen] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [webhookSecret, setWebhookSecret] = useState<string | null>(null)
  const [copied, setCopied] = useState<'secret' | 'url' | null>(null)

  // Filtering and sorting
  const [typeFilter, setTypeFilter] = useState<'all' | 'git' | 'database' | 'mainframe'>('all')
  const [sortBy, setSortBy] = useState<'created_at' | 'last_scan_at' | 'name'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Details modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false)
  const [detailsRepo, setDetailsRepo] = useState<Repository | null>(null)
  const [scanHistory, setScanHistory] = useState<ScanProgress[]>([])

  // Edit modal
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editRepo, setEditRepo] = useState<Repository | null>(null)

  // Delete confirmation
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleteRepo, setDeleteRepo] = useState<Repository | null>(null)

  // Scan type dropdown
  const [scanMenuOpen, setScanMenuOpen] = useState<number | null>(null)

  const fetchRepositories = async () => {
    try {
      setIsLoading(true)
      setError(null)
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

  useEffect(() => {
    logger.info('RepositoriesPage mounted')
    fetchRepositories()
  }, [])

  // Close scan menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setScanMenuOpen(null)
    if (scanMenuOpen !== null) {
      document.addEventListener('click', handleClickOutside)
    }
    return () => document.removeEventListener('click', handleClickOutside)
  }, [scanMenuOpen])

  const handleSuccess = () => {
    fetchRepositories()
  }

  const pollScanProgress = async (repositoryId: number, scanId: number) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/scan-progress/${scanId}`)

        if (!response.ok) {
          clearInterval(pollInterval)
          setScanningRepoId(null)
          setScanProgress(null)
          return
        }

        const progress: ScanProgress = await response.json()
        setScanProgress(progress)

        if (progress.status === 'completed' || progress.status === 'failed') {
          clearInterval(pollInterval)
          setScanningRepoId(null)

          // Refresh repositories
          await fetchRepositories()

          if (progress.status === 'completed') {
            alert(
              `Scan complete! Processed ${progress.total_files} files in ${progress.total_batches} batches.\n` +
              `Extracted ${progress.policies_extracted} policies.\n` +
              `${progress.errors_count} errors encountered.`
            )
          } else {
            alert(`Scan failed: ${progress.error_message}`)
          }

          setScanProgress(null)
        }
      } catch (err) {
        logger.error('Failed to fetch scan progress', { error: err })
        clearInterval(pollInterval)
        setScanningRepoId(null)
        setScanProgress(null)
      }
    }, 2000) // Poll every 2 seconds
  }

  const handleScan = async (repositoryId: number, incremental: boolean = false) => {
    try {
      const scanType = incremental ? 'incremental' : 'full'
      logger.info('Starting scan', { repositoryId, scanType })
      setScanningRepoId(repositoryId)
      setScanProgress(null)

      const url = `/api/v1/repositories/${repositoryId}/scan${incremental ? '?incremental=true' : ''}`
      const response = await fetch(url, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to start scan')
      }

      const result = await response.json()
      logger.info('Scan started', { result })

      // Start polling for progress
      if (result.scan_id) {
        await pollScanProgress(repositoryId, result.scan_id)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Scan failed', { error: errorMessage })
      alert(`Scan failed: ${errorMessage}`)
      setScanningRepoId(null)
      setScanProgress(null)
    }
  }

  const handleConfigureWebhook = async (repo: Repository) => {
    setSelectedRepo(repo)
    if (repo.webhook_secret) {
      setWebhookSecret(repo.webhook_secret)
      setWebhookModalOpen(true)
    } else {
      // Generate new webhook secret
      try {
        const response = await fetch(`/api/v1/webhooks/${repo.id}/generate-secret`, {
          method: 'POST',
        })

        if (!response.ok) {
          throw new Error('Failed to generate webhook secret')
        }

        const data = await response.json()
        setWebhookSecret(data.webhook_secret)
        setWebhookModalOpen(true)

        // Refresh repositories to get updated webhook_secret and webhook_enabled
        await fetchRepositories()
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
        logger.error('Failed to generate webhook secret', { error: errorMessage })
        alert(`Failed to generate webhook secret: ${errorMessage}`)
      }
    }
  }

  const handleCopy = (text: string, type: 'secret' | 'url') => {
    navigator.clipboard.writeText(text)
    setCopied(type)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleToggleWebhook = async (repo: Repository) => {
    try {
      const response = await fetch(`/api/v1/repositories/${repo.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          webhook_enabled: !repo.webhook_enabled,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to toggle webhook')
      }

      await fetchRepositories()
      logger.info('Webhook toggled', { repositoryId: repo.id, enabled: !repo.webhook_enabled })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to toggle webhook', { error: errorMessage })
      alert(`Failed to toggle webhook: ${errorMessage}`)
    }
  }

  const handleViewDetails = async (repo: Repository) => {
    setDetailsRepo(repo)
    setDetailsModalOpen(true)

    // Fetch scan history
    try {
      const response = await fetch(`/api/v1/repositories/${repo.id}/scans`)
      if (response.ok) {
        const scans = await response.json()
        setScanHistory(scans)
      }
    } catch (err) {
      logger.error('Failed to fetch scan history', { error: err })
    }
  }

  const handleEdit = (repo: Repository) => {
    setEditRepo(repo)
    setEditModalOpen(true)
  }

  const handleSaveEdit = async () => {
    if (!editRepo) return

    try {
      const response = await fetch(`/api/v1/repositories/${editRepo.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editRepo.name,
          description: editRepo.description,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to update repository')
      }

      await fetchRepositories()
      setEditModalOpen(false)
      setEditRepo(null)
      logger.info('Repository updated', { repositoryId: editRepo.id })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to update repository', { error: errorMessage })
      alert(`Failed to update repository: ${errorMessage}`)
    }
  }

  const handleDelete = (repo: Repository) => {
    setDeleteRepo(repo)
    setDeleteModalOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!deleteRepo) return

    try {
      const response = await fetch(`/api/v1/repositories/${deleteRepo.id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete repository')
      }

      await fetchRepositories()
      setDeleteModalOpen(false)
      setDeleteRepo(null)
      logger.info('Repository deleted', { repositoryId: deleteRepo.id })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to delete repository', { error: errorMessage })
      alert(`Failed to delete repository: ${errorMessage}`)
    }
  }

  // Filter and sort repositories
  const filteredAndSortedRepositories = repositories
    .filter((repo) => {
      if (typeFilter === 'all') return true
      return repo.repository_type === typeFilter
    })
    .sort((a, b) => {
      let aValue: string | number | null
      let bValue: string | number | null

      if (sortBy === 'name') {
        aValue = a.name
        bValue = b.name
      } else if (sortBy === 'last_scan_at') {
        aValue = a.last_scan_at || ''
        bValue = b.last_scan_at || ''
      } else {
        aValue = a.created_at
        bValue = b.created_at
      }

      if (aValue === null || aValue === '') return sortOrder === 'asc' ? -1 : 1
      if (bValue === null || bValue === '') return sortOrder === 'asc' ? 1 : -1

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'git':
        return <GitBranch size={20} />
      case 'database':
        return <Database size={20} />
      case 'mainframe':
        return <Server size={20} />
      default:
        return null
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (status) {
      case 'connected':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Connected</span>
      case 'failed':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>Failed</span>
      case 'scanning':
        return <span className={`${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400`}>Scanning</span>
      case 'pending':
      default:
        return <span className={`${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400`}>Pending</span>
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-semibold">Repositories</h2>
        <button
          data-testid="repositories-btn-add"
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          Add Repository
        </button>
      </div>

      {/* Filters and Sorting */}
      <div className="flex items-center space-x-4 border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-4">
        <div className="flex items-center space-x-2">
          <Filter size={16} className="text-gray-600 dark:text-gray-400" />
          <span className="text-sm font-medium">Filter:</span>
          <select
            data-testid="repositories-filter-type"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as 'all' | 'git' | 'database' | 'mainframe')}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm"
          >
            <option value="all">All Types</option>
            <option value="git">Git</option>
            <option value="database">Database</option>
            <option value="mainframe">Mainframe</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <ArrowUpDown size={16} className="text-gray-600 dark:text-gray-400" />
          <span className="text-sm font-medium">Sort by:</span>
          <select
            data-testid="repositories-sort-by"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'created_at' | 'last_scan_at' | 'name')}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm"
          >
            <option value="created_at">Date Added</option>
            <option value="last_scan_at">Last Scan</option>
            <option value="name">Name</option>
          </select>
          <button
            data-testid="repositories-sort-order"
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-sm"
          >
            {sortOrder === 'asc' ? '↑' : '↓'}
          </button>
        </div>

        <div className="text-sm text-gray-600 dark:text-dark-text-secondary ml-auto">
          {filteredAndSortedRepositories.length} of {repositories.length} repositories
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-8 text-center">
          <p className="text-gray-600 dark:text-dark-text-secondary">Loading repositories...</p>
        </div>
      ) : filteredAndSortedRepositories.length === 0 ? (
        <div className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-8 text-center">
          <p className="text-gray-600 dark:text-dark-text-secondary">
            {repositories.length === 0 ? 'No repositories yet. Click "Add Repository" to get started.' : 'No repositories match the current filter.'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4" data-testid="repositories-list">
          {filteredAndSortedRepositories.map((repo) => (
            <div
              key={repo.id}
              data-testid="repository-row"
              className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-6 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="text-gray-600 dark:text-gray-400 mt-1">
                    {getTypeIcon(repo.repository_type)}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold" data-testid="repository-name">{repo.name}</h3>
                    {repo.description && (
                      <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                        {repo.description}
                      </p>
                    )}
                    {repo.source_url && (
                      <a
                        href={repo.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1 text-sm text-blue-600 dark:text-blue-400 hover:underline mt-2"
                      >
                        <span>{repo.source_url}</span>
                        <ExternalLink size={14} />
                      </a>
                    )}
                    <div className="flex items-center space-x-4 mt-3 text-sm text-gray-600 dark:text-dark-text-secondary">
                      <span className="capitalize" data-testid="repository-type">{repo.repository_type}</span>
                      <span>•</span>
                      <span>Added {new Date(repo.created_at).toLocaleDateString()}</span>
                      {repo.last_scan_at && (
                        <>
                          <span>•</span>
                          <span>Last scanned {new Date(repo.last_scan_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span data-testid="repository-status">{getStatusBadge(repo.status)}</span>
                  <button
                    data-testid="repository-btn-view-details"
                    onClick={() => handleViewDetails(repo)}
                    className="inline-flex items-center space-x-1 px-2 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-sm"
                    title="View details"
                  >
                    <Eye size={16} />
                  </button>
                  <button
                    data-testid="repository-btn-edit"
                    onClick={() => handleEdit(repo)}
                    className="inline-flex items-center space-x-1 px-2 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-sm"
                    title="Edit repository"
                  >
                    <Edit2 size={16} />
                  </button>
                  <button
                    data-testid="repository-btn-delete"
                    onClick={() => handleDelete(repo)}
                    className="inline-flex items-center space-x-1 px-2 py-1.5 border border-red-300 dark:border-red-600 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-sm"
                    title="Delete repository"
                  >
                    <Trash2 size={16} />
                  </button>
                  {repo.repository_type === 'git' && repo.status === 'connected' && (
                    <>
                      <button
                        data-testid="repository-btn-webhook"
                        onClick={() => handleConfigureWebhook(repo)}
                        className="inline-flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-sm"
                        title="Configure webhook"
                      >
                        <Webhook size={16} />
                        <span>Webhook</span>
                        {repo.webhook_enabled && (
                          <span className="ml-1 w-2 h-2 bg-green-500 rounded-full" title="Webhook enabled" />
                        )}
                      </button>
                      {scanningRepoId !== repo.id && (
                        <div className="relative">
                          <button
                            data-testid="repository-btn-scan"
                            onClick={(e) => {
                              e.stopPropagation()
                              setScanMenuOpen(scanMenuOpen === repo.id ? null : repo.id)
                            }}
                            className="inline-flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-sm"
                          >
                            <Play size={16} />
                            <span>Start Scan</span>
                            <ChevronDown size={14} />
                          </button>
                          {scanMenuOpen === repo.id && (
                            <div
                              onClick={(e) => e.stopPropagation()}
                              className="absolute right-0 mt-1 w-56 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10"
                            >
                              <button
                                data-testid="repository-btn-scan-full"
                                onClick={() => {
                                  handleScan(repo.id, false)
                                  setScanMenuOpen(null)
                                }}
                                className="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-start space-x-3 border-b border-gray-200 dark:border-gray-700"
                              >
                                <Play size={16} className="mt-0.5 flex-shrink-0" />
                                <div>
                                  <div className="font-medium text-sm">Full Scan</div>
                                  <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                                    Scan all files in the repository
                                  </div>
                                </div>
                              </button>
                              <button
                                data-testid="repository-btn-scan-incremental"
                                onClick={() => {
                                  handleScan(repo.id, true)
                                  setScanMenuOpen(null)
                                }}
                                className="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-start space-x-3 rounded-b-lg"
                              >
                                <Zap size={16} className="mt-0.5 flex-shrink-0 text-yellow-500" />
                                <div>
                                  <div className="font-medium text-sm">Incremental Scan</div>
                                  <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                                    Only scan changed files since last scan
                                  </div>
                                </div>
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Scan Progress */}
              {scanningRepoId === repo.id && scanProgress && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-border" data-testid="repository-scan-progress">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600 dark:text-dark-text-secondary">
                        Batch {scanProgress.current_batch} of {scanProgress.total_batches}
                      </span>
                      <span className="text-gray-900 dark:text-dark-text-primary font-medium">
                        {scanProgress.processed_files} / {scanProgress.total_files} files
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${scanProgress.total_files > 0 ? (scanProgress.processed_files / scanProgress.total_files) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs text-gray-600 dark:text-dark-text-secondary">
                      <span>{scanProgress.policies_extracted} policies extracted</span>
                      {scanProgress.errors_count > 0 && (
                        <span className="text-red-600 dark:text-red-400">{scanProgress.errors_count} errors</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <AddRepositoryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleSuccess}
      />

      {/* Webhook Configuration Modal */}
      {webhookModalOpen && selectedRepo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Configure Webhook</h3>
              <button
                onClick={() => {
                  setWebhookModalOpen(false)
                  setSelectedRepo(null)
                  setWebhookSecret(null)
                }}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 dark:text-dark-text-secondary mb-4">
                  Configure your Git provider to send webhook events to trigger automatic scans when you push code changes.
                </p>
              </div>

              {/* Webhook URL */}
              <div>
                <label className="block text-sm font-medium mb-2">Webhook URL</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={`${window.location.origin}/api/v1/webhooks/github`}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm"
                  />
                  <button
                    onClick={() => handleCopy(`${window.location.origin}/api/v1/webhooks/github`, 'url')}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                    title="Copy URL"
                  >
                    {copied === 'url' ? <Check size={16} className="text-green-600" /> : <Copy size={16} />}
                  </button>
                </div>
              </div>

              {/* Webhook Secret */}
              <div>
                <label className="block text-sm font-medium mb-2">Webhook Secret</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={webhookSecret || ''}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm font-mono"
                  />
                  <button
                    onClick={() => webhookSecret && handleCopy(webhookSecret, 'secret')}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                    title="Copy secret"
                  >
                    {copied === 'secret' ? <Check size={16} className="text-green-600" /> : <Copy size={16} />}
                  </button>
                </div>
              </div>

              {/* Enable/Disable Toggle */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <div>
                  <p className="font-medium">Webhook Status</p>
                  <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
                    {selectedRepo.webhook_enabled ? 'Webhooks are enabled' : 'Webhooks are disabled'}
                  </p>
                </div>
                <button
                  onClick={() => handleToggleWebhook(selectedRepo)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    selectedRepo.webhook_enabled
                      ? 'bg-red-600 text-white hover:bg-red-700'
                      : 'bg-green-600 text-white hover:bg-green-700'
                  }`}
                >
                  {selectedRepo.webhook_enabled ? 'Disable' : 'Enable'}
                </button>
              </div>

              {/* Instructions */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <h4 className="font-medium text-sm mb-2">GitHub Setup Instructions</h4>
                <ol className="text-sm text-gray-700 dark:text-gray-300 space-y-1 list-decimal list-inside">
                  <li>Go to your GitHub repository settings</li>
                  <li>Navigate to Webhooks → Add webhook</li>
                  <li>Paste the webhook URL above</li>
                  <li>Set Content type to "application/json"</li>
                  <li>Paste the webhook secret above</li>
                  <li>Select "Just the push event"</li>
                  <li>Click "Add webhook"</li>
                </ol>
              </div>
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => {
                  setWebhookModalOpen(false)
                  setSelectedRepo(null)
                  setWebhookSecret(null)
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Details Modal */}
      {detailsModalOpen && detailsRepo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-4xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Repository Details</h3>
              <button
                onClick={() => {
                  setDetailsModalOpen(false)
                  setDetailsRepo(null)
                  setScanHistory([])
                }}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>

            <div className="space-y-6">
              {/* Basic Info */}
              <div className="border border-gray-200 dark:border-dark-border rounded-lg p-4">
                <h4 className="font-medium mb-3">Basic Information</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-dark-text-secondary">Name:</span>
                    <p className="font-medium mt-1">{detailsRepo.name}</p>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-dark-text-secondary">Type:</span>
                    <p className="font-medium mt-1 capitalize">{detailsRepo.repository_type}</p>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-dark-text-secondary">Status:</span>
                    <div className="mt-1">{getStatusBadge(detailsRepo.status)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-dark-text-secondary">Created:</span>
                    <p className="font-medium mt-1">{new Date(detailsRepo.created_at).toLocaleString()}</p>
                  </div>
                  {detailsRepo.description && (
                    <div className="col-span-2">
                      <span className="text-gray-600 dark:text-dark-text-secondary">Description:</span>
                      <p className="font-medium mt-1">{detailsRepo.description}</p>
                    </div>
                  )}
                  {detailsRepo.source_url && (
                    <div className="col-span-2">
                      <span className="text-gray-600 dark:text-dark-text-secondary">Source URL:</span>
                      <a
                        href={detailsRepo.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1 text-blue-600 dark:text-blue-400 hover:underline mt-1"
                      >
                        <span>{detailsRepo.source_url}</span>
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Scan History */}
              <div className="border border-gray-200 dark:border-dark-border rounded-lg p-4">
                <h4 className="font-medium mb-3">Scan History</h4>
                {scanHistory.length === 0 ? (
                  <p className="text-sm text-gray-600 dark:text-dark-text-secondary">No scans yet</p>
                ) : (
                  <div className="space-y-2">
                    {scanHistory.map((scan) => (
                      <div
                        key={scan.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-sm"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">
                            {scan.status === 'completed' ? '✓' : scan.status === 'failed' ? '✗' : '⋯'}{' '}
                            Scan #{scan.id}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-xs ${
                              scan.status === 'completed'
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                                : scan.status === 'failed'
                                  ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                                  : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                            }`}
                          >
                            {scan.status}
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs text-gray-600 dark:text-dark-text-secondary">
                          <div>Files: {scan.total_files}</div>
                          <div>Policies: {scan.policies_extracted}</div>
                          <div>Errors: {scan.errors_count}</div>
                        </div>
                        {scan.error_message && (
                          <p className="text-xs text-red-600 dark:text-red-400 mt-2">{scan.error_message}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => {
                  setDetailsModalOpen(false)
                  setDetailsRepo(null)
                  setScanHistory([])
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editModalOpen && editRepo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Edit Repository</h3>
              <button
                onClick={() => {
                  setEditModalOpen(false)
                  setEditRepo(null)
                }}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Name</label>
                <input
                  type="text"
                  value={editRepo.name}
                  onChange={(e) => setEditRepo({ ...editRepo, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Description</label>
                <textarea
                  value={editRepo.description || ''}
                  onChange={(e) => setEditRepo({ ...editRepo, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setEditModalOpen(false)
                  setEditRepo(null)
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && deleteRepo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-red-600 dark:text-red-400">Delete Repository</h3>
              <button
                onClick={() => {
                  setDeleteModalOpen(false)
                  setDeleteRepo(null)
                }}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <p className="text-gray-700 dark:text-gray-300">
                Are you sure you want to delete <strong>{deleteRepo.name}</strong>?
              </p>
              <p className="text-sm text-red-600 dark:text-red-400">
                This will permanently delete the repository and all associated policies. This action cannot be undone.
              </p>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setDeleteModalOpen(false)
                  setDeleteRepo(null)
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600"
              >
                Delete Repository
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
