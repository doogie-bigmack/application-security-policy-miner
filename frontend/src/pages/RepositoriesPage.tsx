import { useEffect } from 'react'
import logger from '../lib/logger'

export default function RepositoriesPage() {
  useEffect(() => {
    logger.info('RepositoriesPage mounted')
  }, [])

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-semibold">Repositories</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600">
          Add Repository
        </button>
      </div>

      <div className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-8 text-center">
        <p className="text-gray-600 dark:text-dark-text-secondary">
          No repositories yet. Click "Add Repository" to get started.
        </p>
      </div>
    </div>
  )
}
