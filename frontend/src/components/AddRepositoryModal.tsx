import { FormEvent, useState } from 'react'
import { X, Github, GitlabIcon } from 'lucide-react'
import logger from '../lib/logger'
import GitHubRepositoryBrowser from './GitHubRepositoryBrowser'
import GitLabRepositoryBrowser from './GitLabRepositoryBrowser'
import BitbucketRepositoryBrowser from './BitbucketRepositoryBrowser'

interface AddRepositoryModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddRepositoryModal({ isOpen, onClose, onSuccess }: AddRepositoryModalProps) {
  const [sourceType, setSourceType] = useState<'git' | 'database' | 'mainframe'>('git')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [gitUrl, setGitUrl] = useState('')
  const [authType, setAuthType] = useState<'none' | 'token' | 'usernamepassword'>('none')
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Database-specific fields
  const [databaseType, setDatabaseType] = useState<'postgresql' | 'sqlserver' | 'oracle' | 'mysql'>('postgresql')
  const [dbHost, setDbHost] = useState('')
  const [dbPort, setDbPort] = useState('')
  const [dbName, setDbName] = useState('')
  const [dbUsername, setDbUsername] = useState('')
  const [dbPassword, setDbPassword] = useState('')

  // GitHub browser state
  const [showGitHubBrowser, setShowGitHubBrowser] = useState(false)

  // GitLab browser state
  const [showGitLabBrowser, setShowGitLabBrowser] = useState(false)

  // Bitbucket browser state
  const [showBitbucketBrowser, setShowBitbucketBrowser] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    logger.info('Submitting repository', { name, sourceType, gitUrl })

    try {
      let connectionConfig: Record<string, string | number> = {}

      if (sourceType === 'git') {
        if (authType === 'token' && token) {
          connectionConfig.token = token
        } else if (authType === 'usernamepassword' && username && password) {
          connectionConfig.username = username
          connectionConfig.password = password
        }
      } else if (sourceType === 'database') {
        connectionConfig = {
          database_type: databaseType,
          host: dbHost,
          port: dbPort ? parseInt(dbPort, 10) : 0,
          database: dbName,
          username: dbUsername,
          password: dbPassword,
        }
      }

      const response = await fetch('/api/v1/repositories/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          description,
          repository_type: sourceType,
          git_provider: sourceType === 'git' ? 'generic' : null,
          source_url: sourceType === 'git' ? gitUrl : null,
          connection_config: Object.keys(connectionConfig).length > 0 ? connectionConfig : null,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create repository')
      }

      const data = await response.json()
      logger.info('Repository created successfully', { repositoryId: data.id })

      // Reset form
      setName('')
      setDescription('')
      setGitUrl('')
      setAuthType('none')
      setToken('')
      setUsername('')
      setPassword('')
      setSourceType('git')
      setDatabaseType('postgresql')
      setDbHost('')
      setDbPort('')
      setDbName('')
      setDbUsername('')
      setDbPassword('')

      onSuccess()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to create repository', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGitHubRepositorySelect = async (repo: any, accessToken: string) => {
    logger.info('GitHub repository selected', { repo: repo.full_name })

    setShowGitHubBrowser(false)

    // Pre-fill the form with GitHub repository data
    setName(repo.name)
    setDescription(repo.description || '')
    setGitUrl(repo.clone_url)
    setAuthType('token')
    setToken(accessToken)
    setSourceType('git')

    // Auto-submit the form
    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/repositories/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: repo.name,
          description: repo.description || '',
          repository_type: 'git',
          git_provider: 'github',
          source_url: repo.clone_url,
          connection_config: {
            token: accessToken,
          },
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create repository')
      }

      const data = await response.json()
      logger.info('GitHub repository imported successfully', { repositoryId: data.id })

      // Reset form
      setName('')
      setDescription('')
      setGitUrl('')
      setAuthType('none')
      setToken('')

      onSuccess()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to import GitHub repository', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGitLabRepositorySelect = async (repo: any, accessToken: string, baseUrl: string) => {
    logger.info('GitLab repository selected', { repo: repo.full_name })

    setShowGitLabBrowser(false)

    // Pre-fill the form with GitLab repository data
    setName(repo.name)
    setDescription(repo.description || '')
    setGitUrl(repo.clone_url)
    setAuthType('token')
    setToken(accessToken)
    setSourceType('git')

    // Auto-submit the form
    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/repositories/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: repo.name,
          description: repo.description || '',
          repository_type: 'git',
          git_provider: 'gitlab',
          source_url: repo.clone_url,
          connection_config: {
            token: accessToken,
            base_url: baseUrl,
          },
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create repository')
      }

      const data = await response.json()
      logger.info('GitLab repository imported successfully', { repositoryId: data.id })

      // Reset form
      setName('')
      setDescription('')
      setGitUrl('')
      setAuthType('none')
      setToken('')

      onSuccess()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to import GitLab repository', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleBitbucketRepositorySelect = async (repo: any, bbUsername: string, appPassword: string) => {
    logger.info('Bitbucket repository selected', { repo: repo.full_name })

    setShowBitbucketBrowser(false)

    // Pre-fill the form with Bitbucket repository data
    setName(repo.name)
    setDescription(repo.description || '')
    setGitUrl(repo.clone_url)
    setAuthType('usernamepassword')
    setUsername(bbUsername)
    setPassword(appPassword)
    setSourceType('git')

    // Auto-submit the form
    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/repositories/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: repo.name,
          description: repo.description || '',
          repository_type: 'git',
          git_provider: 'bitbucket',
          source_url: repo.clone_url,
          connection_config: {
            username: bbUsername,
            password: appPassword,
          },
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create repository')
      }

      const data = await response.json()
      logger.info('Bitbucket repository imported successfully', { repositoryId: data.id })

      // Reset form
      setName('')
      setDescription('')
      setGitUrl('')
      setAuthType('none')
      setUsername('')
      setPassword('')

      onSuccess()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to import Bitbucket repository', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl w-full max-w-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-border">
          <h3 className="text-xl font-semibold">Add Repository</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200">
              {error}
            </div>
          )}

          {/* Source Type */}
          <div>
            <label className="block text-sm font-medium mb-2">Source Type</label>
            <div className="grid grid-cols-3 gap-3">
              {['git', 'database', 'mainframe'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSourceType(type as 'git' | 'database' | 'mainframe')}
                  className={`px-4 py-2 rounded-lg border text-sm font-medium capitalize transition ${
                    sourceType === type
                      ? 'bg-blue-600 text-white border-blue-600 dark:bg-blue-500 dark:border-blue-500'
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400'
                  }`}
                >
                  {type === 'git' ? 'Git Repository' : type === 'database' ? 'Database' : 'Mainframe'}
                </button>
              ))}
            </div>
          </div>

          {/* Repository Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-2">
              Repository Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="my-application-repo"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Optional description of the repository"
            />
          </div>

          {/* Git-specific fields */}
          {sourceType === 'git' && (
            <>
              {/* Git Integration Buttons */}
              <div>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => setShowGitHubBrowser(true)}
                    className="px-4 py-3 bg-gray-900 dark:bg-gray-800 text-white rounded-lg hover:bg-gray-800 dark:hover:bg-gray-700 flex items-center justify-center space-x-2 transition"
                  >
                    <Github size={20} />
                    <span>GitHub</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowGitLabBrowser(true)}
                    className="px-4 py-3 bg-orange-600 dark:bg-orange-700 text-white rounded-lg hover:bg-orange-700 dark:hover:bg-orange-600 flex items-center justify-center space-x-2 transition"
                  >
                    <GitlabIcon size={20} />
                    <span>GitLab</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowBitbucketBrowser(true)}
                    className="px-4 py-3 bg-blue-700 dark:bg-blue-600 text-white rounded-lg hover:bg-blue-800 dark:hover:bg-blue-700 flex items-center justify-center space-x-2 transition"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M.778 1.211a.768.768 0 00-.768.892l3.263 19.81c.084.5.515.868 1.022.873H19.95a.772.772 0 00.77-.646l3.27-20.03a.768.768 0 00-.768-.891zM14.52 15.528H9.522L8.17 8.464h7.561z"/>
                    </svg>
                    <span>Bitbucket</span>
                  </button>
                </div>
                <p className="mt-2 text-sm text-gray-600 dark:text-dark-text-secondary text-center">
                  Or manually enter repository details below
                </p>
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white dark:bg-dark-surface text-gray-500">or</span>
                </div>
              </div>

              {/* Git URL */}
              <div>
                <label htmlFor="gitUrl" className="block text-sm font-medium mb-2">
                  Git Repository URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  id="gitUrl"
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  required
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://github.com/username/repo.git"
                />
                <p className="mt-1 text-sm text-gray-600 dark:text-dark-text-secondary">
                  Supports GitHub, GitLab, Bitbucket, and Azure DevOps
                </p>
              </div>

              {/* Authentication */}
              <div>
                <label className="block text-sm font-medium mb-2">Authentication</label>
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <input
                      type="radio"
                      id="auth-none"
                      name="auth"
                      checked={authType === 'none'}
                      onChange={() => setAuthType('none')}
                      className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="auth-none" className="text-sm">
                      None (Public repository)
                    </label>
                  </div>

                  <div className="flex items-center space-x-3">
                    <input
                      type="radio"
                      id="auth-token"
                      name="auth"
                      checked={authType === 'token'}
                      onChange={() => setAuthType('token')}
                      className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="auth-token" className="text-sm">
                      Access Token (Recommended)
                    </label>
                  </div>

                  {authType === 'token' && (
                    <div className="ml-7">
                      <input
                        type="password"
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="ghp_xxxxxxxxxxxx"
                      />
                    </div>
                  )}

                  <div className="flex items-center space-x-3">
                    <input
                      type="radio"
                      id="auth-usernamepassword"
                      name="auth"
                      checked={authType === 'usernamepassword'}
                      onChange={() => setAuthType('usernamepassword')}
                      className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="auth-usernamepassword" className="text-sm">
                      Username & Password
                    </label>
                  </div>

                  {authType === 'usernamepassword' && (
                    <div className="ml-7 space-y-3">
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Username"
                      />
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Password"
                      />
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Database-specific fields */}
          {sourceType === 'database' && (
            <>
              {/* Database Type */}
              <div>
                <label className="block text-sm font-medium mb-2">Database Type</label>
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { value: 'postgresql', label: 'PostgreSQL' },
                    { value: 'sqlserver', label: 'SQL Server' },
                    { value: 'oracle', label: 'Oracle' },
                    { value: 'mysql', label: 'MySQL' },
                  ].map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => setDatabaseType(type.value as typeof databaseType)}
                      className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                        databaseType === type.value
                          ? 'bg-blue-600 text-white border-blue-600 dark:bg-blue-500 dark:border-blue-500'
                          : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400'
                      }`}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Host and Port */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label htmlFor="dbHost" className="block text-sm font-medium mb-2">
                    Host <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    id="dbHost"
                    value={dbHost}
                    onChange={(e) => setDbHost(e.target.value)}
                    required
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="localhost or db.example.com"
                  />
                </div>
                <div>
                  <label htmlFor="dbPort" className="block text-sm font-medium mb-2">
                    Port
                  </label>
                  <input
                    type="number"
                    id="dbPort"
                    value={dbPort}
                    onChange={(e) => setDbPort(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder={
                      databaseType === 'postgresql'
                        ? '5432'
                        : databaseType === 'mysql'
                          ? '3306'
                          : databaseType === 'sqlserver'
                            ? '1433'
                            : '1521'
                    }
                  />
                </div>
              </div>

              {/* Database Name */}
              <div>
                <label htmlFor="dbName" className="block text-sm font-medium mb-2">
                  Database Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="dbName"
                  value={dbName}
                  onChange={(e) => setDbName(e.target.value)}
                  required
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="myapp_db"
                />
              </div>

              {/* Username */}
              <div>
                <label htmlFor="dbUsername" className="block text-sm font-medium mb-2">
                  Username <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="dbUsername"
                  value={dbUsername}
                  onChange={(e) => setDbUsername(e.target.value)}
                  required
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="db_user"
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="dbPassword" className="block text-sm font-medium mb-2">
                  Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  id="dbPassword"
                  value={dbPassword}
                  onChange={(e) => setDbPassword(e.target.value)}
                  required
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="••••••••"
                />
              </div>
            </>
          )}

          {/* Mainframe-specific placeholder */}
          {sourceType === 'mainframe' && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-amber-800 dark:text-amber-200">
              Mainframe connection configuration will be available in a future update.
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-dark-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Adding...' : 'Add Repository'}
            </button>
          </div>
        </form>
      </div>

      {/* GitHub Repository Browser */}
      {showGitHubBrowser && (
        <GitHubRepositoryBrowser
          onSelectRepository={handleGitHubRepositorySelect}
          onClose={() => setShowGitHubBrowser(false)}
        />
      )}

      {/* GitLab Repository Browser */}
      {showGitLabBrowser && (
        <GitLabRepositoryBrowser
          onSelectRepository={handleGitLabRepositorySelect}
          onClose={() => setShowGitLabBrowser(false)}
        />
      )}

      {/* Bitbucket Repository Browser */}
      {showBitbucketBrowser && (
        <BitbucketRepositoryBrowser
          onSelectRepository={handleBitbucketRepositorySelect}
          onClose={() => setShowBitbucketBrowser(false)}
        />
      )}
    </div>
  )
}
