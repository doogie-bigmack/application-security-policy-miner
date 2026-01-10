import { useState } from 'react'
import { Search, RefreshCw, ExternalLink, Lock, Globe, Check } from 'lucide-react'
import logger from '../lib/logger'

interface GitLabRepo {
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
  visibility: string
  namespace: string
}

interface GitLabRepositoryBrowserProps {
  onSelectRepository: (repo: GitLabRepo, token: string, baseUrl: string) => void
  onClose: () => void
}

export default function GitLabRepositoryBrowser({ onSelectRepository, onClose }: GitLabRepositoryBrowserProps) {
  const [token, setToken] = useState('')
  const [baseUrl, setBaseUrl] = useState('https://gitlab.com')
  const [repositories, setRepositories] = useState<GitLabRepo[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRepo, setSelectedRepo] = useState<GitLabRepo | null>(null)

  const verifyToken = async () => {
    if (!token.trim()) {
      setError('Please enter a GitLab access token')
      return
    }

    if (!baseUrl.trim()) {
      setError('Please enter a GitLab instance URL')
      return
    }

    setIsVerifying(true)
    setError(null)
    logger.info('Verifying GitLab token', { baseUrl })

    try {
      const response = await fetch(
        `/api/v1/repositories/gitlab/verify?access_token=${encodeURIComponent(token)}&base_url=${encodeURIComponent(
          baseUrl
        )}`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error('Invalid GitLab access token')
      }

      const data = await response.json()
      setUserInfo(data)
      logger.info('GitLab token verified', { user: data.username })

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
      setError('Please enter a GitLab access token')
      return
    }

    setIsLoading(true)
    setError(null)
    logger.info('Fetching GitLab repositories', { baseUrl })

    try {
      const response = await fetch(
        `/api/v1/repositories/gitlab/list?access_token=${encodeURIComponent(token)}&base_url=${encodeURIComponent(
          baseUrl
        )}&per_page=100&page=1`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error('Failed to fetch GitLab repositories')
      }

      const data = await response.json()
      setRepositories(data.repositories)
      logger.info('GitLab repositories fetched', { count: data.repositories.length })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch repositories'
      logger.error('Failed to fetch GitLab repositories', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectRepository = () => {
    if (selectedRepo && token) {
      logger.info('Repository selected', { repo: selectedRepo.full_name })
      onSelectRepository(selectedRepo, token, baseUrl)
    }
  }

  const filteredRepos = repositories.filter(
    (repo) =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (repo.description && repo.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const getVisibilityIcon = (visibility: string) => {
    if (visibility === 'public') {
      return <Globe size={16} className="text-green-500 flex-shrink-0" />
    } else if (visibility === 'internal') {
      return <Lock size={16} className="text-yellow-500 flex-shrink-0" />
    } else {
      return <Lock size={16} className="text-red-500 flex-shrink-0" />
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-border">
          <div>
            <h3 className="text-xl font-semibold">Import from GitLab</h3>
            {userInfo && (
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                Authenticated as {userInfo.username} on {new URL(baseUrl).hostname}
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
          <div className="p-6 border-b border-gray-200 dark:border-dark-border space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">GitLab Instance URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="https://gitlab.com"
              />
              <p className="mt-1 text-xs text-gray-600 dark:text-dark-text-secondary">
                Use https://gitlab.com for GitLab.com or your self-hosted instance URL
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">GitLab Personal Access Token</label>
              <div className="flex space-x-3">
                <input
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && verifyToken()}
                  className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="glpat-xxxxxxxxxxxx"
                />
                <button
                  onClick={verifyToken}
                  disabled={isVerifying || !token.trim() || !baseUrl.trim()}
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
                  href={`${baseUrl}/-/user_settings/personal_access_tokens`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {new URL(baseUrl).hostname}/user_settings/tokens
                </a>{' '}
                with <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">api</code> or{' '}
                <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">read_api</code> scope
              </p>
            </div>
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
                  placeholder="Search projects..."
                />
              </div>
            </div>

            {/* Loading State */}
            {isLoading && (
              <div className="flex-1 flex items-center justify-center py-12">
                <div className="flex items-center space-x-3 text-gray-600 dark:text-dark-text-secondary">
                  <RefreshCw size={20} className="animate-spin" />
                  <span>Loading projects...</span>
                </div>
              </div>
            )}

            {/* Repository List */}
            {!isLoading && repositories.length > 0 && (
              <div className="flex-1 overflow-y-auto p-6 space-y-2">
                {filteredRepos.length === 0 ? (
                  <div className="text-center py-12 text-gray-600 dark:text-dark-text-secondary">
                    No projects match your search
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
                            {getVisibilityIcon(repo.visibility)}
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
                            <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded-full capitalize">
                              {repo.visibility}
                            </span>
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
                  <p>No projects found</p>
                  <button onClick={fetchRepositories} className="mt-4 text-blue-600 dark:text-blue-400 hover:underline">
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
              Import Project
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
