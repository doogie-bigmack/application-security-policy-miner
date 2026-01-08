import { useEffect } from 'react'
import logger from '../lib/logger'

export default function HomePage() {
  useEffect(() => {
    logger.info('HomePage mounted')
  }, [])

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-semibold mb-4">Welcome to Policy Miner</h2>
        <p className="text-gray-600 dark:text-dark-text-secondary">
          Discover, analyze, and manage security policies across your applications.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 border border-gray-200 dark:border-dark-border rounded-lg bg-gray-50 dark:bg-dark-surface">
          <h3 className="text-lg font-semibold mb-2">AI-Powered Discovery</h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
            Automatically extract security policies from code, databases, and mainframes.
          </p>
        </div>

        <div className="p-6 border border-gray-200 dark:border-dark-border rounded-lg bg-gray-50 dark:bg-dark-surface">
          <h3 className="text-lg font-semibold mb-2">Multi-Tenancy</h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
            Full tenant isolation with enterprise-scale support for thousands of applications.
          </p>
        </div>

        <div className="p-6 border border-gray-200 dark:border-dark-border rounded-lg bg-gray-50 dark:bg-dark-surface">
          <h3 className="text-lg font-semibold mb-2">PBAC Integration</h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
            Provision to OPA, AWS Verified Permissions, Axiomatics, and more.
          </p>
        </div>
      </div>
    </div>
  )
}
