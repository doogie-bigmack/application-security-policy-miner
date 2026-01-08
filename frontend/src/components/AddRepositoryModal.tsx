import { FormEvent, useState } from 'react'
import { X } from 'lucide-react'
import logger from '../lib/logger'

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

  if (!isOpen) return null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    logger.info('Submitting repository', { name, sourceType, gitUrl })

    try {
      const connectionConfig: Record<string, string> = {}
      if (authType === 'token' && token) {
        connectionConfig.token = token
      } else if (authType === 'usernamepassword' && username && password) {
        connectionConfig.username = username
        connectionConfig.password = password
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

          {/* Database-specific placeholder */}
          {sourceType === 'database' && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-amber-800 dark:text-amber-200">
              Database connection configuration will be available in a future update.
            </div>
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
    </div>
  )
}
