import { useState } from 'react'
import { Search, RefreshCw, ExternalLink, Lock, Globe, Check } from 'lucide-react'
import logger from '../lib/logger'

interface GitHubRepo {
  id: number
  name: string
  full_name: string
  description: string | null
  clone_url: string
  ssh_url: string
  html_url: string
  private: boolean
  language: string | null
  updated_at: string
  default_branch: string
}

interface GitHubRepositoryBrowserProps {
  onSelectRepository: (repo: GitHubRepo, token: string) => void
  onClose: () => void
}

export default function GitHubRepositoryBrowser({ onSelectRepository, onClose }: GitHubRepositoryBrowserProps) {
  const [token, setToken] = useState('')
  const [repositories, setRepositories] = useState<GitHubRepo[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null)

  const verifyToken = async () => {
    if (!token.trim()) {
      setError('Please enter a GitHub access token')
      return
    }

    setIsVerifying(true)
    setError(null)
    logger.info('Verifying GitHub token')

    try {
      const response = await fetch(`/api/v1/repositories/github/verify?access_token=${encodeURIComponent(token)}`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('Invalid GitHub access token')
      }

      const data = await response.json()
      setUserInfo(data)
      logger.info('GitHub token verified', { user: data.login })

      // Automatically fetch repositories after verification
      await fetchRepositories()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to verify token'
      logger.error('Token verification failed', { error: errorMessage })
      setError(errorMessage)
      setUserInfo(null)
    } finally {
      setIsVerifying(false)
    }
  }

  const fetchRepositories = async () => {
    if (!token.trim()) {
      setError('Please enter a GitHub access token')
      return
    }

    setIsLoading(true)
    setError(null)
    logger.info('Fetching GitHub repositories')

    try {
      const response = await fetch(
        `/api/v1/repositories/github/list?access_token=${encodeURIComponent(token)}&per_page=100&page=1`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error('Failed to fetch GitHub repositories')
      }

      const data = await response.json()
      setRepositories(data.repositories)
      logger.info('GitHub repositories fetched', { count: data.repositories.length })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch repositories'
      logger.error('Failed to fetch GitHub repositories', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectRepository = () => {
    if (selectedRepo && token) {
      logger.info('Repository selected', { repo: selectedRepo.full_name })
      onSelectRepository(selectedRepo, token)
    }
  }

  const filteredRepos = repositories.filter(
    (repo) =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (repo.description && repo.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-border">
          <div>
            <h3 className="text-xl font-semibold">Import from GitHub</h3>
            {userInfo && (
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                Authenticated as {userInfo.login}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        {/* Token Input */}
        {!userInfo && (
          <div className="p-6 border-b border-gray-200 dark:border-dark-border">
            <label className="block text-sm font-medium mb-2">GitHub Personal Access Token</label>
            <div className="flex space-x-3">
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && verifyToken()}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="ghp_xxxxxxxxxxxx"
              />
              <button
                onClick={verifyToken}
                disabled={isVerifying || !token.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isVerifying ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <span>Connect</span>
                )}
              </button>
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-dark-text-secondary">
              Generate a token at{' '}
              <a
                href="https://github.com/settings/tokens/new"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                github.com/settings/tokens
              </a>{' '}
              with <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">repo</code> scope
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mx-6 mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        {/* Repository List */}
        {userInfo && (
          <>
            {/* Search */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-border">
              <div className="relative">
                <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Search repositories..."
                />
              </div>
            </div>

            {/* Loading State */}
            {isLoading && (
              <div className="flex-1 flex items-center justify-center py-12">
                <div className="flex items-center space-x-3 text-gray-600 dark:text-dark-text-secondary">
                  <RefreshCw size={20} className="animate-spin" />
                  <span>Loading repositories...</span>
                </div>
              </div>
            )}

            {/* Repository List */}
            {!isLoading && repositories.length > 0 && (
              <div className="flex-1 overflow-y-auto p-6 space-y-2">
                {filteredRepos.length === 0 ? (
                  <div className="text-center py-12 text-gray-600 dark:text-dark-text-secondary">
                    No repositories match your search
                  </div>
                ) : (
                  filteredRepos.map((repo) => (
                    <button
                      key={repo.id}
                      onClick={() => setSelectedRepo(repo)}
                      className={`w-full text-left p-4 rounded-lg border transition ${
                        selectedRepo?.id === repo.id
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            {repo.private ? (
                              <Lock size={16} className="text-gray-400 flex-shrink-0" />
                            ) : (
                              <Globe size={16} className="text-gray-400 flex-shrink-0" />
                            )}
                            <span className="font-medium truncate">{repo.full_name}</span>
                            {selectedRepo?.id === repo.id && (
                              <Check size={16} className="text-blue-600 dark:text-blue-400 flex-shrink-0" />
                            )}
                          </div>
                          {repo.description && (
                            <p className="mt-1 text-sm text-gray-600 dark:text-dark-text-secondary line-clamp-2">
                              {repo.description}
                            </p>
                          )}
                          <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                            {repo.language && (
                              <span className="flex items-center space-x-1">
                                <span className="w-2 h-2 rounded-full bg-blue-500" />
                                <span>{repo.language}</span>
                              </span>
                            )}
                            <span>Updated {new Date(repo.updated_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <a
                          href={repo.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="ml-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                          <ExternalLink size={16} />
                        </a>
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}

            {!isLoading && repositories.length === 0 && (
              <div className="flex-1 flex items-center justify-center py-12">
                <div className="text-center text-gray-600 dark:text-dark-text-secondary">
                  <p>No repositories found</p>
                  <button
                    onClick={fetchRepositories}
                    className="mt-4 text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Refresh
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-200 dark:border-dark-border">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          {userInfo && (
            <button
              onClick={handleSelectRepository}
              disabled={!selectedRepo}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Import Repository
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
