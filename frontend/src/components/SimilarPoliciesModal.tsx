import { X, Shield, AlertCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import logger from '../lib/logger'

interface Evidence {
  id: number
  file_path: string
  line_start: number
  line_end: number
  code_snippet: string
}

type SourceType = 'frontend' | 'backend' | 'database' | 'unknown'

interface Policy {
  id: number
  repository_id: number
  subject: string
  resource: string
  action: string
  conditions: string | null
  description: string | null
  risk_score: number | null
  risk_level: 'low' | 'medium' | 'high' | null
  status: 'pending' | 'approved' | 'rejected'
  source_type: SourceType
  evidence: Evidence[]
  created_at: string
}

interface SimilarPolicy {
  policy: Policy
  similarity_score: number
}

interface Props {
  policyId: number
  onClose: () => void
}

export default function SimilarPoliciesModal({ policyId, onClose }: Props) {
  const [similarPolicies, setSimilarPolicies] = useState<SimilarPolicy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [minSimilarity, setMinSimilarity] = useState(0.7)

  useEffect(() => {
    fetchSimilarPolicies()
  }, [policyId, minSimilarity])

  const fetchSimilarPolicies = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(
        `/api/v1/policies/${policyId}/similar?limit=10&min_similarity=${minSimilarity}`
      )

      if (!response.ok) {
        throw new Error('Failed to fetch similar policies')
      }

      const data = await response.json()
      setSimilarPolicies(data)
      logger.info('Similar policies fetched', { count: data.length, policyId })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to fetch similar policies', { error: errorMessage, policyId })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const getRiskBadge = (riskLevel: 'low' | 'medium' | 'high' | null) => {
    if (!riskLevel) return null
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (riskLevel) {
      case 'low':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Low</span>
      case 'medium':
        return <span className={`${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400`}>Medium</span>
      case 'high':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>High</span>
    }
  }

  const getSourceTypeBadge = (sourceType: SourceType) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (sourceType) {
      case 'frontend':
        return <span className={`${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400`}>Frontend</span>
      case 'backend':
        return <span className={`${baseClasses} bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400`}>Backend</span>
      case 'database':
        return <span className={`${baseClasses} bg-cyan-100 text-cyan-800 dark:bg-cyan-900/20 dark:text-cyan-400`}>Database</span>
      default:
        return <span className={`${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400`}>Unknown</span>
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface rounded-lg w-full max-w-5xl max-h-[90vh] flex flex-col border border-gray-200 dark:border-dark-border">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <div className="flex items-center space-x-3">
            <Shield size={24} className="text-blue-600 dark:text-blue-400" />
            <h2 className="text-xl font-semibold">Similar Policies</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X size={24} />
          </button>
        </div>

        {/* Similarity Threshold Control */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-border">
          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Minimum Similarity:
            </label>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.05"
              value={minSimilarity}
              onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
              className="flex-1"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-16">
              {Math.round(minSimilarity * 100)}%
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-dark-text-secondary">Loading similar policies...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start space-x-3">
              <AlertCircle size={20} className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-800 dark:text-red-200 font-medium">Error Loading Similar Policies</p>
                <p className="text-red-600 dark:text-red-300 text-sm mt-1">{error}</p>
              </div>
            </div>
          ) : similarPolicies.length === 0 ? (
            <div className="text-center py-12">
              <Shield size={48} className="mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600 dark:text-dark-text-secondary">
                No similar policies found with {Math.round(minSimilarity * 100)}% similarity or higher.
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Try lowering the similarity threshold to find more matches.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Found {similarPolicies.length} similar {similarPolicies.length === 1 ? 'policy' : 'policies'}
              </p>

              {similarPolicies.map(({ policy, similarity_score }) => (
                <div
                  key={policy.id}
                  className="border border-gray-200 dark:border-dark-border rounded-lg bg-gray-50 dark:bg-gray-900 p-4"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="text-base font-semibold">
                          {policy.subject} → {policy.action} → {policy.resource}
                        </h3>
                      </div>
                      {policy.description && (
                        <p className="text-sm text-gray-600 dark:text-dark-text-secondary mb-2">
                          {policy.description}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end space-y-2 ml-4">
                      <div className="px-3 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-400 rounded font-semibold text-sm">
                        {Math.round(similarity_score * 100)}% Match
                      </div>
                      <div className="flex items-center space-x-2">
                        {getSourceTypeBadge(policy.source_type)}
                        {getRiskBadge(policy.risk_level)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Subject:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.subject}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Resource:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.resource}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Action:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.action}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Conditions:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">
                        {policy.conditions || 'None'}
                      </span>
                    </div>
                  </div>

                  {policy.evidence.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-700">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Evidence: {policy.evidence.length} snippet{policy.evidence.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-dark-border">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 dark:bg-gray-500 dark:hover:bg-gray-600 text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
