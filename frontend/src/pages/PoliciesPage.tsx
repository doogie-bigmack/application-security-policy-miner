import { useEffect, useState } from 'react'
import { Shield, FileCode, CheckCircle, XCircle, Clock, Filter } from 'lucide-react'
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
  complexity_score: number | null
  impact_score: number | null
  confidence_score: number | null
  status: 'pending' | 'approved' | 'rejected'
  source_type: SourceType
  evidence: Evidence[]
  created_at: string
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)
  const [sourceTypeFilter, setSourceTypeFilter] = useState<SourceType | 'all'>('all')

  const fetchPolicies = async (sourceType?: SourceType | 'all') => {
    try {
      setIsLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (sourceType && sourceType !== 'all') {
        params.append('source_type', sourceType)
      }

      const url = `/api/v1/policies/${params.toString() ? `?${params.toString()}` : ''}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error('Failed to fetch policies')
      }

      const data = await response.json()
      setPolicies(data.policies)
      logger.info('Policies fetched', { count: data.total, sourceType })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to fetch policies', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    logger.info('PoliciesPage mounted')
    fetchPolicies(sourceTypeFilter)
  }, [sourceTypeFilter])

  const handleSourceTypeFilterChange = (newFilter: SourceType | 'all') => {
    setSourceTypeFilter(newFilter)
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

  const getRiskBadge = (riskLevel: string | null) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (riskLevel) {
      case 'high':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>High Risk</span>
      case 'medium':
        return <span className={`${baseClasses} bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-400`}>Medium Risk</span>
      case 'low':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Low Risk</span>
      default:
        return <span className={`${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400`}>Unknown</span>
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle size={16} className="text-green-600 dark:text-green-400" />
      case 'rejected':
        return <XCircle size={16} className="text-red-600 dark:text-red-400" />
      case 'pending':
      default:
        return <Clock size={16} className="text-gray-600 dark:text-gray-400" />
    }
  }

  const handleApprove = async (policyId: number) => {
    try {
      const response = await fetch(`/api/v1/policies/${policyId}/approve`, {
        method: 'PUT',
      })

      if (!response.ok) {
        throw new Error('Failed to approve policy')
      }

      logger.info('Policy approved', { policyId })
      await fetchPolicies()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to approve policy', { error: errorMessage })
      alert(`Failed to approve policy: ${errorMessage}`)
    }
  }

  const handleReject = async (policyId: number) => {
    try {
      const response = await fetch(`/api/v1/policies/${policyId}/reject`, {
        method: 'PUT',
      })

      if (!response.ok) {
        throw new Error('Failed to reject policy')
      }

      logger.info('Policy rejected', { policyId })
      await fetchPolicies()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to reject policy', { error: errorMessage })
      alert(`Failed to reject policy: ${errorMessage}`)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-semibold">Extracted Policies</h2>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
            Review and approve authorization policies extracted from your code
          </p>
        </div>
      </div>

      {/* Source Type Filter */}
      <div className="flex items-center space-x-3">
        <Filter size={20} className="text-gray-600 dark:text-gray-400" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter by Source:</span>
        <div className="flex space-x-2">
          {(['all', 'frontend', 'backend', 'database', 'unknown'] as const).map((type) => (
            <button
              key={type}
              onClick={() => handleSourceTypeFilterChange(type)}
              className={`px-3 py-1 rounded text-sm font-medium transition ${
                sourceTypeFilter === type
                  ? 'bg-blue-600 text-white dark:bg-blue-500'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-8 text-center">
          <p className="text-gray-600 dark:text-dark-text-secondary">Loading policies...</p>
        </div>
      ) : policies.length === 0 ? (
        <div className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-8 text-center">
          <Shield size={48} className="mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600 dark:text-dark-text-secondary">
            No policies extracted yet. Scan a repository to get started.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {policies.map((policy) => (
            <div
              key={policy.id}
              className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-6 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start space-x-3 flex-1">
                  <Shield size={20} className="text-blue-600 dark:text-blue-400 mt-1" />
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      {getStatusIcon(policy.status)}
                      <h3 className="text-lg font-semibold">
                        {policy.subject} → {policy.action} → {policy.resource}
                      </h3>
                    </div>
                    {policy.description && (
                      <p className="text-sm text-gray-600 dark:text-dark-text-secondary mb-3">
                        {policy.description}
                      </p>
                    )}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700 dark:text-gray-300">Who (Subject):</span>
                        <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.subject}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700 dark:text-gray-300">What (Resource):</span>
                        <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.resource}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700 dark:text-gray-300">How (Action):</span>
                        <span className="ml-2 text-gray-600 dark:text-gray-400">{policy.action}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700 dark:text-gray-300">When (Conditions):</span>
                        <span className="ml-2 text-gray-600 dark:text-gray-400">
                          {policy.conditions || 'None'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end space-y-2">
                  <div className="flex items-center space-x-2">
                    {getSourceTypeBadge(policy.source_type)}
                  </div>
                  <div className="flex items-center space-x-2">
                    {getRiskBadge(policy.risk_level)}
                    {policy.risk_score !== null && (
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Score: {Math.round(policy.risk_score)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {policy.evidence.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-border">
                  <button
                    onClick={() => setSelectedPolicy(selectedPolicy?.id === policy.id ? null : policy)}
                    className="inline-flex items-center space-x-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <FileCode size={16} />
                    <span>
                      {selectedPolicy?.id === policy.id ? 'Hide' : 'Show'} Evidence ({policy.evidence.length} snippet
                      {policy.evidence.length !== 1 ? 's' : ''})
                    </span>
                  </button>

                  {selectedPolicy?.id === policy.id && (
                    <div className="mt-4 space-y-3">
                      {policy.evidence.map((ev) => (
                        <div
                          key={ev.id}
                          className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-800"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              {ev.file_path}
                            </span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              Lines {ev.line_start}-{ev.line_end}
                            </span>
                          </div>
                          <pre className="text-xs bg-white dark:bg-gray-950 p-3 rounded border border-gray-200 dark:border-gray-800 overflow-x-auto">
                            <code>{ev.code_snippet}</code>
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {policy.status === 'pending' && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-border flex items-center space-x-3">
                  <button
                    onClick={() => handleApprove(policy.id)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 text-sm"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(policy.id)}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 text-sm"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
