import { useEffect, useState } from 'react'
import { Shield, FileCode, AlertCircle } from 'lucide-react'
import logger from '../lib/logger'

interface PolicyEvidence {
  id: number
  file_path: string
  start_line: number
  end_line: number
  code_snippet: string
}

interface Policy {
  id: number
  repository_id: number
  subject: string
  resource: string
  action: string
  conditions: string | null
  description: string | null
  status: 'extracted' | 'approved' | 'rejected' | 'pending_review'
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number
  created_at: string
  evidence: PolicyEvidence[]
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)

  const fetchPolicies = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await fetch('/api/v1/policies/')

      if (!response.ok) {
        throw new Error('Failed to fetch policies')
      }

      const data = await response.json()
      setPolicies(data.policies)
      logger.info('Policies fetched', { count: data.total })
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
    fetchPolicies()
  }, [])

  const getRiskBadge = (riskLevel: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (riskLevel) {
      case 'low':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Low Risk</span>
      case 'medium':
        return <span className={`${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400`}>Medium Risk</span>
      case 'high':
        return <span className={`${baseClasses} bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400`}>High Risk</span>
      case 'critical':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>Critical Risk</span>
      default:
        return null
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (status) {
      case 'approved':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Approved</span>
      case 'rejected':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>Rejected</span>
      case 'pending_review':
        return <span className={`${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400`}>Pending Review</span>
      case 'extracted':
      default:
        return <span className={`${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400`}>Extracted</span>
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-semibold">Policies</h2>
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
          <Shield className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600 dark:text-dark-text-secondary">
            No policies found. Start scanning a repository to extract policies.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {policies.map((policy) => (
            <div
              key={policy.id}
              className="border border-gray-200 dark:border-dark-border rounded-lg bg-white dark:bg-dark-surface p-6 hover:shadow-md transition cursor-pointer"
              onClick={() => setSelectedPolicy(policy)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start space-x-3 flex-1">
                  <Shield className="text-blue-600 dark:text-blue-400 mt-1" size={20} />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-2">{policy.description || 'Policy'}</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-dark-text-secondary">WHO (Subject):</span>
                        <p className="font-medium mt-1">{policy.subject}</p>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-dark-text-secondary">WHAT (Resource):</span>
                        <p className="font-medium mt-1">{policy.resource}</p>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-dark-text-secondary">HOW (Action):</span>
                        <p className="font-medium mt-1">{policy.action}</p>
                      </div>
                      {policy.conditions && (
                        <div>
                          <span className="text-gray-600 dark:text-dark-text-secondary">WHEN (Conditions):</span>
                          <p className="font-medium mt-1">{policy.conditions}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col space-y-2 items-end">
                  {getRiskBadge(policy.risk_level)}
                  {getStatusBadge(policy.status)}
                </div>
              </div>

              {policy.evidence.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-dark-text-secondary">
                    <FileCode size={16} />
                    <span>{policy.evidence.length} evidence item{policy.evidence.length !== 1 ? 's' : ''}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {selectedPolicy && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedPolicy(null)}
        >
          <div
            className="bg-white dark:bg-dark-surface rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-2xl font-semibold mb-2">Policy Details</h3>
                  <p className="text-gray-600 dark:text-dark-text-secondary">
                    {selectedPolicy.description || 'Policy'}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedPolicy(null)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary mb-2">WHO (Subject)</h4>
                  <p className="font-medium">{selectedPolicy.subject}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary mb-2">WHAT (Resource)</h4>
                  <p className="font-medium">{selectedPolicy.resource}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary mb-2">HOW (Action)</h4>
                  <p className="font-medium">{selectedPolicy.action}</p>
                </div>
                {selectedPolicy.conditions && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary mb-2">WHEN (Conditions)</h4>
                    <p className="font-medium">{selectedPolicy.conditions}</p>
                  </div>
                )}
              </div>

              <div className="flex items-center space-x-4">
                {getRiskBadge(selectedPolicy.risk_level)}
                {getStatusBadge(selectedPolicy.status)}
                <span className="text-sm text-gray-600 dark:text-dark-text-secondary">
                  Risk Score: {selectedPolicy.risk_score}/100
                </span>
              </div>

              {selectedPolicy.evidence.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                    <FileCode size={20} />
                    <span>Evidence ({selectedPolicy.evidence.length})</span>
                  </h4>
                  <div className="space-y-4">
                    {selectedPolicy.evidence.map((evidence) => (
                      <div
                        key={evidence.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                      >
                        <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-dark-text-secondary mb-2">
                          <span className="font-mono">{evidence.file_path}</span>
                          <span>•</span>
                          <span>Lines {evidence.start_line}-{evidence.end_line}</span>
                        </div>
                        <pre className="bg-gray-50 dark:bg-gray-900 p-4 rounded text-sm overflow-x-auto">
                          <code>{evidence.code_snippet}</code>
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
