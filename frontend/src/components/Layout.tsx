import { Link } from 'react-router-dom'
import { Moon, Sun } from 'lucide-react'
import logger from '../lib/logger'

interface LayoutProps {
  children: React.ReactNode
  darkMode: boolean
  setDarkMode: (value: boolean) => void
}

export default function Layout({ children, darkMode, setDarkMode }: LayoutProps) {
  const toggleDarkMode = () => {
    logger.info({ darkMode: !darkMode }, 'Toggling dark mode')
    setDarkMode(!darkMode)
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-dark-border bg-white dark:bg-dark-surface">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center space-x-2">
              <h1 className="text-xl font-semibold">Policy Miner</h1>
            </Link>
            <nav className="flex items-center space-x-8">
              <Link
                to="/repositories"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Repositories
              </Link>
              <Link
                to="/bulk-scan"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Bulk Scan
              </Link>
              <Link
                to="/policies"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Policies
              </Link>
              <Link
                to="/conflicts"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Conflicts
              </Link>
              <Link
                to="/changes"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Changes
              </Link>
              <Link
                to="/secrets"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Secrets
              </Link>
              <Link
                to="/provisioning"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Provisioning
              </Link>
              <Link
                to="/code-advisories"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Advisories
              </Link>
              <Link
                to="/policy-fixes"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Fixes
              </Link>
              <Link
                to="/auto-approval"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Auto-Approval
              </Link>
              <Link
                to="/risk"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Risk
              </Link>
              <Link
                to="/organizations"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Organizations
              </Link>
              <Link
                to="/applications"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Applications
              </Link>
              <Link
                to="/normalization"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Normalization
              </Link>
              <Link
                to="/inconsistent-enforcement"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Inconsistencies
              </Link>
              <Link
                to="/duplicates"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Duplicates
              </Link>
              <Link
                to="/cross-application-conflicts"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Cross-App Conflicts
              </Link>
              <Link
                to="/audit-logs"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Audit Logs
              </Link>
              <Link
                to="/security"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Security
              </Link>
              <Link
                to="/settings"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary"
              >
                Settings
              </Link>
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Toggle dark mode"
              >
                {darkMode ? <Sun size={20} /> : <Moon size={20} />}
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
