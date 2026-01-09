import { useEffect, useState } from 'react'
import { X, FileCode, AlertCircle } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import logger from '../lib/logger'

interface SourceFileViewerProps {
  evidenceId: number
  onClose: () => void
}

interface SourceFileData {
  file_path: string
  content: string
  total_lines: number
  line_start: number
  line_end: number
}

export default function SourceFileViewer({ evidenceId, onClose }: SourceFileViewerProps) {
  const [sourceFile, setSourceFile] = useState<SourceFileData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isDarkMode, setIsDarkMode] = useState(false)

  useEffect(() => {
    // Check if dark mode is enabled
    setIsDarkMode(window.matchMedia('(prefers-color-scheme: dark)').matches)

    const fetchSourceFile = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const response = await fetch(`/api/v1/policies/evidence/${evidenceId}/source`)

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Failed to fetch source file')
        }

        const data = await response.json()
        setSourceFile(data)
        logger.info('Source file fetched', { evidenceId, filePath: data.file_path })
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
        logger.error('Failed to fetch source file', { error: errorMessage, evidenceId })
        setError(errorMessage)
      } finally {
        setIsLoading(false)
      }
    }

    fetchSourceFile()
  }, [evidenceId])

  const getLanguage = (filePath: string): string => {
    const extension = filePath.split('.').pop()?.toLowerCase()
    const languageMap: Record<string, string> = {
      js: 'javascript',
      jsx: 'jsx',
      ts: 'typescript',
      tsx: 'tsx',
      py: 'python',
      java: 'java',
      cs: 'csharp',
      go: 'go',
      rb: 'ruby',
      php: 'php',
      scala: 'scala',
      kt: 'kotlin',
      rs: 'rust',
      swift: 'swift',
      c: 'c',
      cpp: 'cpp',
      h: 'c',
      hpp: 'cpp',
      html: 'html',
      css: 'css',
      json: 'json',
      yaml: 'yaml',
      yml: 'yaml',
      xml: 'xml',
      sql: 'sql',
      sh: 'bash',
      bash: 'bash',
      md: 'markdown',
    }
    return languageMap[extension || ''] || 'text'
  }

  const customLineProps = (lineNumber: number) => {
    if (sourceFile && lineNumber >= sourceFile.line_start && lineNumber <= sourceFile.line_end) {
      return {
        style: {
          backgroundColor: isDarkMode ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
          display: 'block',
          width: '100%',
        },
      }
    }
    return {}
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <div className="flex items-center space-x-3">
            <FileCode size={24} className="text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-xl font-semibold">Source File Viewer</h2>
              {sourceFile && (
                <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                  {sourceFile.file_path}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-dark-text-secondary">Loading source file...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertCircle size={20} className="text-red-600 dark:text-red-400 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-red-800 dark:text-red-200">Error Loading Source File</h3>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
                </div>
              </div>
            </div>
          ) : sourceFile ? (
            <div className="space-y-4">
              {/* File Info */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-800">
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Total Lines:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">{sourceFile.total_lines}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Evidence Lines:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {sourceFile.line_start}-{sourceFile.line_end}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Language:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {getLanguage(sourceFile.file_path)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Source Code */}
              <div className="border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
                <SyntaxHighlighter
                  language={getLanguage(sourceFile.file_path)}
                  style={isDarkMode ? vscDarkPlus : oneLight}
                  showLineNumbers={true}
                  wrapLines={true}
                  lineProps={customLineProps}
                  customStyle={{
                    margin: 0,
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem',
                    lineHeight: '1.5',
                  }}
                >
                  {sourceFile.content}
                </SyntaxHighlighter>
              </div>

              {/* Legend */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-center space-x-2 text-sm">
                  <div
                    className="w-4 h-4 rounded"
                    style={{
                      backgroundColor: isDarkMode ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
                    }}
                  />
                  <span className="text-blue-800 dark:text-blue-200">
                    Highlighted lines indicate the exact code evidence supporting this policy
                  </span>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
