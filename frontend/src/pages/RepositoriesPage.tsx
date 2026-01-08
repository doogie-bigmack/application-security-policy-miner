import { useEffect, useState } from 'react'
import { GitBranch, Database, Server, ExternalLink, Play } from 'lucide-react'
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
}

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const handleSuccess = () => {
    fetchRepositories()
  }

  const handleScan = async (repositoryId: number) => {
    try {
      logger.info('Starting scan', { repositoryId })
      const response = await fetch(`/api/v1/repositories/${repositoryId}/scan`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to start scan')
      }

      const result = await response.json()
      logger.info('Scan completed', { result })

      // Refresh repositories to show updated status
      await fetchRepositories()

      alert(`Scan complete! Extracted ${result.policies_extracted} policies from ${result.files_scanned} files.`)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Scan failed', { error: errorMessage })
      alert(`Scan failed: ${errorMessage}`)
    }
  }

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
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          Add Repository
        </button>
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
      ) : repositories.length === 0 ? (
        <div className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-8 text-center">
          <p className="text-gray-600 dark:text-dark-text-secondary">
            No repositories yet. Click "Add Repository" to get started.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {repositories.map((repo) => (
            <div
              key={repo.id}
              className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-6 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="text-gray-600 dark:text-gray-400 mt-1">
                    {getTypeIcon(repo.repository_type)}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold">{repo.name}</h3>
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
                      <span className="capitalize">{repo.repository_type}</span>
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
                <div className="flex items-center space-x-3">
                  {getStatusBadge(repo.status)}
                  {repo.repository_type === 'git' && repo.status === 'connected' && (
                    <button
                      onClick={() => handleScan(repo.id)}
                      className="inline-flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-sm"
                    >
                      <Play size={16} />
                      <span>Start Scan</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <AddRepositoryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleSuccess}
      />
    </div>
  )
}
