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
