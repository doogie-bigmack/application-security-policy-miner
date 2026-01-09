import { useState } from 'react'
import { Search, RefreshCw, ExternalLink, FolderGit2, Check } from 'lucide-react'
import logger from '../lib/logger'

interface AzureDevOpsRepo {
  id: string
  name: string
  full_name: string
  description: string | null
  clone_url: string
  ssh_url: string | null
  html_url: string
  private: boolean
  language: string | null
  updated_at: string | null
  default_branch: string
  project: string
  project_id: string
}

interface AzureDevOpsProject {
  id: string
  name: string
  description: string | null
  url: string
  state: string
  visibility: string
}

interface AzureDevOpsRepositoryBrowserProps {
  onSelectRepository: (repo: AzureDevOpsRepo, organization: string, token: string) => void
  onClose: () => void
}

export default function AzureDevOpsRepositoryBrowser({
  onSelectRepository,
  onClose,
}: AzureDevOpsRepositoryBrowserProps) {
  const [organization, setOrganization] = useState('')
  const [token, setToken] = useState('')
  const [repositories, setRepositories] = useState<AzureDevOpsRepo[]>([])
  const [projects, setProjects] = useState<AzureDevOpsProject[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingProjects, setIsLoadingProjects] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRepo, setSelectedRepo] = useState<AzureDevOpsRepo | null>(null)

  const verifyToken = async () => {
    if (!organization.trim() || !token.trim()) {
      setError('Please enter both organization and access token')
      return
    }

    setIsVerifying(true)
    setError(null)
    logger.info('Verifying Azure DevOps token')

    try {
      const response = await fetch(
        `/api/v1/repositories/azure-devops/verify?organization=${encodeURIComponent(organization)}&access_token=${encodeURIComponent(token)}`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error('Invalid Azure DevOps access token or organization')
      }

      const data = await response.json()
      setUserInfo(data)
      logger.info('Azure DevOps token verified', { user: data.name })

      // Automatically fetch projects after verification
      await fetchProjects()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to verify token'
      logger.error('Token verification failed', { error: errorMessage })
      setError(errorMessage)
      setUserInfo(null)
    } finally {
      setIsVerifying(false)
    }
  }

  const fetchProjects = async () => {
    if (!organization.trim() || !token.trim()) {
      setError('Please enter both organization and access token')
      return
    }

    setIsLoadingProjects(true)
    setError(null)
    logger.info('Fetching Azure DevOps projects')

    try {
      const response = await fetch(
        `/api/v1/repositories/azure-devops/projects?organization=${encodeURIComponent(organization)}&access_token=${encodeURIComponent(token)}`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error('Failed to fetch Azure DevOps projects')
      }

      const data = await response.json()
      setProjects(data.projects)
      logger.info('Azure DevOps projects fetched', { count: data.projects.length })

      // Automatically fetch all repositories (no project filter)
      await fetchRepositories()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch projects'
      logger.error('Failed to fetch Azure DevOps projects', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoadingProjects(false)
    }
  }

  const fetchRepositories = async (project?: string) => {
    if (!organization.trim() || !token.trim()) {
      setError('Please enter both organization and access token')
      return
    }

    setIsLoading(true)
    setError(null)
    logger.info('Fetching Azure DevOps repositories', { project })

    try {
      const projectParam = project ? `&project=${encodeURIComponent(project)}` : ''
      const response = await fetch(
        `/api/v1/repositories/azure-devops/list?organization=${encodeURIComponent(organization)}&access_token=${encodeURIComponent(token)}${projectParam}&per_page=100&page=1`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error('Failed to fetch Azure DevOps repositories')
      }

      const data = await response.json()
      setRepositories(data.repositories)
      logger.info('Azure DevOps repositories fetched', { count: data.repositories.length })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch repositories'
      logger.error('Failed to fetch Azure DevOps repositories', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleProjectChange = (projectName: string) => {
    setSelectedProject(projectName)
    if (projectName) {
      fetchRepositories(projectName)
    } else {
      fetchRepositories()
    }
  }

  const handleSelectRepository = () => {
    if (selectedRepo && organization && token) {
      logger.info('Repository selected', { repo: selectedRepo.full_name })
      onSelectRepository(selectedRepo, organization, token)
    }
  }

  const filteredRepos = repositories.filter(
    (repo) =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.project.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (repo.description && repo.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-border">
          <div>
            <h3 className="text-xl font-semibold">Import from Azure DevOps</h3>
            {userInfo && (
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                Authenticated as {userInfo.name} ({organization})
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

        {/* Credentials Input */}
        {!userInfo && (
          <div className="p-6 border-b border-gray-200 dark:border-dark-border space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Organization Name</label>
              <input
                type="text"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="myorganization"
              />
              <p className="mt-1 text-xs text-gray-600 dark:text-dark-text-secondary">
                From dev.azure.com/<strong>myorganization</strong>
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Personal Access Token</label>
              <div className="flex space-x-3">
                <input
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && verifyToken()}
                  className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                />
                <button
                  onClick={verifyToken}
                  disabled={isVerifying || !organization.trim() || !token.trim()}
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
                Create a PAT at{' '}
                <span className="font-mono text-xs">
                  dev.azure.com/{'{'}organization{'}'}/_usersSettings/tokens
                </span>{' '}
                with <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">Code (Read)</code> scope
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

        {/* Project Filter & Repository List */}
        {userInfo && (
          <>
            {/* Project Filter */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-border">
              <label className="block text-sm font-medium mb-2">Filter by Project (Optional)</label>
              <select
                value={selectedProject}
                onChange={(e) => handleProjectChange(e.target.value)}
                disabled={isLoadingProjects}
                className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Projects</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.name}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

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
                            <FolderGit2 size={16} className="text-gray-400 flex-shrink-0" />
                            <span className="font-medium truncate">{repo.full_name}</span>
                            {selectedRepo?.id === repo.id && (
                              <Check size={16} className="text-blue-600 dark:text-blue-400 flex-shrink-0" />
                            )}
                          </div>
                          <div className="mt-1 flex items-center space-x-3 text-sm">
                            <span className="text-gray-600 dark:text-dark-text-secondary">
                              Project: {repo.project}
                            </span>
                            {repo.default_branch && (
                              <span className="text-gray-500 dark:text-gray-400">
                                Default: {repo.default_branch}
                              </span>
                            )}
                          </div>
                        </div>
                        <a
                          href={repo.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="ml-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                        >
                          <ExternalLink size={16} />
                        </a>
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}

            {/* Empty State */}
            {!isLoading && repositories.length === 0 && (
              <div className="flex-1 flex items-center justify-center py-12">
                <div className="text-center text-gray-600 dark:text-dark-text-secondary">
                  <FolderGit2 size={48} className="mx-auto mb-4 text-gray-400" />
                  <p>No repositories found</p>
                  <p className="text-sm mt-2">
                    {selectedProject ? `No repositories in project "${selectedProject}"` : 'No repositories in this organization'}
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Footer */}
        {userInfo && (
          <div className="px-6 py-4 border-t border-gray-200 dark:border-dark-border flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-dark-text-secondary">
              {repositories.length} {repositories.length === 1 ? 'repository' : 'repositories'}
              {selectedProject && ` in ${selectedProject}`}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleSelectRepository}
                disabled={!selectedRepo}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Import Repository
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
