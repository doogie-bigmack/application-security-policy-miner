import { X, Shield, Link as LinkIcon } from 'lucide-react'
import { useState, useEffect } from 'react'
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
}

interface SimilarPolicy {
  policy: Policy
  similarity_score: number
}

interface SimilarPoliciesModalProps {
  policyId: number
  onClose: () => void
}

export default function SimilarPoliciesModal({ policyId, onClose }: SimilarPoliciesModalProps) {
  const [similarPolicies, setSimilarPolicies] = useState<SimilarPolicy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSimilarPolicies()
  }, [policyId])

  const fetchSimilarPolicies = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`/api/v1/similarity/policies/${policyId}/similar?limit=10&min_similarity=0.5`)

      if (!response.ok) {
        throw new Error('Failed to fetch similar policies')
      }

      const data = await response.json()
      setSimilarPolicies(data.similar_policies)
      logger.info('Similar policies fetched', { count: data.count, policyId })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to fetch similar policies', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
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

  const getRiskBadge = (riskLevel: 'low' | 'medium' | 'high' | null) => {
    if (!riskLevel) return null
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (riskLevel) {
      case 'low':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Low Risk</span>
      case 'medium':
        return <span className={`${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400`}>Medium Risk</span>
      case 'high':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>High Risk</span>
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-dark-border px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <LinkIcon size={24} className="text-blue-600 dark:text-blue-400" />
            <h2 className="text-xl font-semibold">Similar Policies</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-gray-400">Finding similar policies...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200">
              {error}
            </div>
          ) : similarPolicies.length === 0 ? (
            <div className="text-center py-12">
              <Shield size={48} className="mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600 dark:text-gray-400">
                No similar policies found. This policy appears to be unique.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Found {similarPolicies.length} similar {similarPolicies.length === 1 ? 'policy' : 'policies'} across all applications.
              </p>
              {similarPolicies.map(({ policy, similarity_score }) => (
                <div
                  key={policy.id}
                  className="border border-gray-200 dark:border-dark-border rounded-lg bg-gray-50 dark:bg-gray-900/20 p-4 hover:shadow-md transition"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start space-x-3 flex-1">
                      <Shield size={16} className="text-blue-600 dark:text-blue-400 mt-1" />
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm mb-1">
                          {policy.subject} → {policy.action} → {policy.resource}
                        </h4>
                        {policy.description && (
                          <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                            {policy.description}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-1">
                      <span className="px-2 py-1 rounded text-xs font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                        {Math.round(similarity_score)}% Similar
                      </span>
                      {getSourceTypeBadge(policy.source_type)}
                      {getRiskBadge(policy.risk_level)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Who:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.subject}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">What:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.resource}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">How:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.action}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">When:</span>
                      <span className="ml-2 text-gray-600 dark:text-gray-400">
                        {policy.conditions || 'None'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-dark-border px-6 py-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
