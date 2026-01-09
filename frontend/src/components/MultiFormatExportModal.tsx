import { useState } from 'react'
import { X, Download, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import logger from '../lib/logger'

interface MultiFormatExportModalProps {
  policyId: number
  onClose: () => void
}

interface ExportResult {
  rego: string
  cedar: string
  json: string
  semantic_equivalence: {
    rego: boolean
    cedar: boolean
    json: boolean
  }
}

export default function MultiFormatExportModal({
  policyId,
  onClose,
}: MultiFormatExportModalProps) {
  const [exportResult, setExportResult] = useState<ExportResult | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verifyEquivalence, setVerifyEquivalence] = useState(true)

  const handleExport = async () => {
    try {
      setIsExporting(true)
      setError(null)

      const response = await fetch(
        `/api/v1/policies/${policyId}/export/all?verify_equivalence=${verifyEquivalence}`
      )

      if (!response.ok) {
        throw new Error('Failed to export policy to all formats')
      }

      const data = await response.json()
      setExportResult(data)
      logger.info('Policy exported to all formats', {
        policyId,
        verifyEquivalence,
      })
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to export policy to all formats', {
        error: errorMessage,
        policyId,
      })
      setError(errorMessage)
    } finally {
      setIsExporting(false)
    }
  }

  const handleDownloadAll = () => {
    if (!exportResult) return

    // Create a combined file with all formats
    const content = `# Policy Export - Multiple Formats

## OPA Rego
\`\`\`rego
${exportResult.rego}
\`\`\`

## AWS Cedar
\`\`\`cedar
${exportResult.cedar}
\`\`\`

## Custom JSON
\`\`\`json
${exportResult.json}
\`\`\`

## Semantic Equivalence Verification
- Rego: ${exportResult.semantic_equivalence.rego ? '✓ Verified' : '✗ Not Verified'}
- Cedar: ${exportResult.semantic_equivalence.cedar ? '✓ Verified' : '✗ Not Verified'}
- JSON: ${exportResult.semantic_equivalence.json ? '✓ Verified' : '✗ Not Verified'}
`

    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `policy_${policyId}_all_formats.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    logger.info('All policies downloaded', { policyId })
  }

  const EquivalenceIndicator = ({ verified }: { verified: boolean }) => {
    return verified ? (
      <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
        <CheckCircle size={16} />
        <span className="text-sm">Verified Equivalent</span>
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
        <XCircle size={16} />
        <span className="text-sm">Not Verified</span>
      </span>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface border border-gray-200 dark:border-dark-border rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <h3 className="text-xl font-semibold">
            Export Policy to All Formats
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-6 flex-1 overflow-auto">
          {/* Verification Toggle */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={verifyEquivalence}
                onChange={(e) => setVerifyEquivalence(e.target.checked)}
                disabled={isExporting || !!exportResult}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Verify Semantic Equivalence
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Use Claude AI to verify that all translations preserve the same
                  authorization logic
                </div>
              </div>
            </label>
          </div>

          {/* Export Button */}
          {!exportResult && (
            <div>
              <button
                onClick={handleExport}
                disabled={isExporting}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isExporting ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Exporting...</span>
                  </>
                ) : (
                  <span>Export to All Formats</span>
                )}
              </button>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-800 dark:text-red-200">
              {error}
            </div>
          )}

          {/* Export Results */}
          {exportResult && (
            <div className="space-y-6">
              {/* Overall Status */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                <h4 className="font-medium mb-3">Semantic Equivalence Status</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Rego:
                    </span>
                    <EquivalenceIndicator
                      verified={exportResult.semantic_equivalence.rego}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Cedar:
                    </span>
                    <EquivalenceIndicator
                      verified={exportResult.semantic_equivalence.cedar}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      JSON:
                    </span>
                    <EquivalenceIndicator
                      verified={exportResult.semantic_equivalence.json}
                    />
                  </div>
                </div>
              </div>

              {/* OPA Rego */}
              <div className="border border-gray-200 dark:border-dark-border rounded-lg overflow-hidden">
                <div className="bg-gray-50 dark:bg-gray-800/50 px-4 py-2 border-b border-gray-200 dark:border-dark-border">
                  <h4 className="font-medium">OPA Rego</h4>
                </div>
                <pre className="p-4 bg-gray-900 text-gray-100 overflow-x-auto text-sm">
                  <code>{exportResult.rego}</code>
                </pre>
              </div>

              {/* AWS Cedar */}
              <div className="border border-gray-200 dark:border-dark-border rounded-lg overflow-hidden">
                <div className="bg-gray-50 dark:bg-gray-800/50 px-4 py-2 border-b border-gray-200 dark:border-dark-border">
                  <h4 className="font-medium">AWS Cedar</h4>
                </div>
                <pre className="p-4 bg-gray-900 text-gray-100 overflow-x-auto text-sm">
                  <code>{exportResult.cedar}</code>
                </pre>
              </div>

              {/* Custom JSON */}
              <div className="border border-gray-200 dark:border-dark-border rounded-lg overflow-hidden">
                <div className="bg-gray-50 dark:bg-gray-800/50 px-4 py-2 border-b border-gray-200 dark:border-dark-border">
                  <h4 className="font-medium">Custom JSON</h4>
                </div>
                <pre className="p-4 bg-gray-900 text-gray-100 overflow-x-auto text-sm">
                  <code>{exportResult.json}</code>
                </pre>
              </div>

              {/* Download All Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleDownloadAll}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2"
                >
                  <Download size={20} />
                  <span>Download All Formats</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
