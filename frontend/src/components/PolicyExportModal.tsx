import { useState } from 'react'
import { X, Download, Copy, Check } from 'lucide-react'
import logger from '../lib/logger'

interface PolicyExportModalProps {
  policyId: number
  onClose: () => void
}

type ExportFormat = 'rego' | 'cedar' | 'json'

export default function PolicyExportModal({ policyId, onClose }: PolicyExportModalProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('rego')
  const [exportedPolicy, setExportedPolicy] = useState<string | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleExport = async () => {
    try {
      setIsExporting(true)
      setError(null)
      setCopied(false)

      const response = await fetch(`/api/v1/policies/${policyId}/export/${selectedFormat}`)

      if (!response.ok) {
        throw new Error(`Failed to export policy as ${selectedFormat}`)
      }

      const data = await response.json()
      setExportedPolicy(data.policy)
      logger.info('Policy exported', { policyId, format: selectedFormat })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to export policy', { error: errorMessage, policyId, format: selectedFormat })
      setError(errorMessage)
    } finally {
      setIsExporting(false)
    }
  }

  const handleCopy = async () => {
    if (exportedPolicy) {
      try {
        await navigator.clipboard.writeText(exportedPolicy)
        setCopied(true)
        logger.info('Policy copied to clipboard', { policyId, format: selectedFormat })
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        logger.error('Failed to copy to clipboard', { error: err })
      }
    }
  }

  const handleDownload = () => {
    if (exportedPolicy) {
      const blob = new Blob([exportedPolicy], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `policy_${policyId}.${selectedFormat}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      logger.info('Policy downloaded', { policyId, format: selectedFormat })
    }
  }

  const getLanguage = () => {
    switch (selectedFormat) {
      case 'rego':
        return 'rego'
      case 'cedar':
        return 'cedar'
      case 'json':
        return 'json'
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface border border-gray-200 dark:border-dark-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <h3 className="text-xl font-semibold">Export Policy</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-4 flex-1 overflow-auto">
          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Export Format
            </label>
            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setSelectedFormat('rego')
                  setExportedPolicy(null)
                  setError(null)
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  selectedFormat === 'rego'
                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                OPA Rego
              </button>
              <button
                onClick={() => {
                  setSelectedFormat('cedar')
                  setExportedPolicy(null)
                  setError(null)
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  selectedFormat === 'cedar'
                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                AWS Cedar
              </button>
              <button
                onClick={() => {
                  setSelectedFormat('json')
                  setExportedPolicy(null)
                  setError(null)
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  selectedFormat === 'json'
                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                Custom JSON
              </button>
            </div>
          </div>

          {/* Export Button */}
          {!exportedPolicy && (
            <div>
              <button
                onClick={handleExport}
                disabled={isExporting}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                {isExporting ? 'Exporting...' : `Export as ${selectedFormat.toUpperCase()}`}
              </button>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200 text-sm">
              {error}
            </div>
          )}

          {/* Exported Policy Display */}
          {exportedPolicy && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Exported {selectedFormat.toUpperCase()} Policy
                </label>
                <div className="flex space-x-2">
                  <button
                    onClick={handleCopy}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 text-sm"
                  >
                    {copied ? (
                      <>
                        <Check size={14} />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={14} />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 text-sm"
                  >
                    <Download size={14} />
                    <span>Download</span>
                  </button>
                </div>
              </div>
              <pre className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 overflow-x-auto text-sm">
                <code className={`language-${getLanguage()}`}>{exportedPolicy}</code>
              </pre>
              <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                {selectedFormat === 'rego' && (
                  <p>
                    This OPA Rego policy can be tested in the{' '}
                    <a
                      href="https://play.openpolicyagent.org/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      OPA Playground
                    </a>
                    .
                  </p>
                )}
                {selectedFormat === 'cedar' && (
                  <p>This AWS Cedar policy can be deployed to AWS Verified Permissions.</p>
                )}
                {selectedFormat === 'json' && (
                  <p>This JSON policy can be used with custom PBAC platforms.</p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-dark-border">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
