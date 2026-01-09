import { useEffect, useState } from 'react'
import { X, Save, FileCode, CheckCircle, XCircle, Clock, History } from 'lucide-react'
import Editor from '@monaco-editor/react'
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
  approval_comment?: string | null
  reviewed_by?: string | null
  reviewed_at?: string | null
}

interface PolicyChange {
  id: number
  change_type: 'added' | 'modified' | 'deleted'
  before: {
    subject: string | null
    resource: string | null
    action: string | null
    conditions: string | null
  }
  after: {
    subject: string | null
    resource: string | null
    action: string | null
    conditions: string | null
  }
  description: string | null
  diff_summary: string | null
  detected_at: string | null
}

interface PolicyDetailModalProps {
  policy: Policy
  onClose: () => void
  onSave: () => void
}

export default function PolicyDetailModal({ policy, onClose, onSave }: PolicyDetailModalProps) {
  const [editedPolicy, setEditedPolicy] = useState<string>('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [approvalComment, setApprovalComment] = useState<string>('')
  const [showHistory, setShowHistory] = useState(false)
  const [policyHistory, setPolicyHistory] = useState<PolicyChange[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)

  useEffect(() => {
    // Check if dark mode is enabled
    const darkMode = document.documentElement.classList.contains('dark')
    setIsDarkMode(darkMode)

    // Format policy as JSON for editing
    const policyData = {
      subject: policy.subject,
      resource: policy.resource,
      action: policy.action,
      conditions: policy.conditions,
      description: policy.description,
      source_type: policy.source_type,
    }
    setEditedPolicy(JSON.stringify(policyData, null, 2))
  }, [policy])

  const handleSave = async () => {
    try {
      setIsSaving(true)
      setError(null)

      // Parse the edited JSON
      const updatedData = JSON.parse(editedPolicy)

      // Validate required fields
      if (!updatedData.subject || !updatedData.resource || !updatedData.action) {
        throw new Error('Subject, resource, and action are required fields')
      }

      const response = await fetch(`/api/v1/policies/${policy.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update policy')
      }

      logger.info('Policy updated successfully', { policyId: policy.id })
      onSave()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to update policy', { error: errorMessage, policyId: policy.id })
      setError(errorMessage)
    } finally {
      setIsSaving(false)
    }
  }

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setEditedPolicy(value)
    }
  }

  const fetchPolicyHistory = async () => {
    try {
      setIsLoadingHistory(true)
      const response = await fetch(`/api/v1/policies/${policy.id}/history`)

      if (!response.ok) {
        throw new Error('Failed to fetch policy history')
      }

      const data = await response.json()
      setPolicyHistory(data.changes || [])
      logger.info('Policy history fetched', { policyId: policy.id, count: data.total })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to fetch policy history', { error: errorMessage })
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleApprove = async () => {
    try {
      setIsSaving(true)
      setError(null)

      const response = await fetch(`/api/v1/policies/${policy.id}/approve`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: approvalComment || null }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to approve policy')
      }

      logger.info('Policy approved', { policyId: policy.id })
      onSave()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to approve policy', { error: errorMessage, policyId: policy.id })
      setError(errorMessage)
    } finally {
      setIsSaving(false)
    }
  }

  const handleReject = async () => {
    try {
      setIsSaving(true)
      setError(null)

      const response = await fetch(`/api/v1/policies/${policy.id}/reject`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: approvalComment || null }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to reject policy')
      }

      logger.info('Policy rejected', { policyId: policy.id })
      onSave()
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to reject policy', { error: errorMessage, policyId: policy.id })
      setError(errorMessage)
    } finally {
      setIsSaving(false)
    }
  }

  const toggleHistory = () => {
    if (!showHistory && policyHistory.length === 0) {
      fetchPolicyHistory()
    }
    setShowHistory(!showHistory)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle size={20} className="text-green-600 dark:text-green-400" />
      case 'rejected':
        return <XCircle size={20} className="text-red-600 dark:text-red-400" />
      case 'pending':
      default:
        return <Clock size={20} className="text-gray-600 dark:text-gray-400" />
    }
  }

  const getChangeTypeBadge = (changeType: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (changeType) {
      case 'added':
        return <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}>Added</span>
      case 'modified':
        return <span className={`${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400`}>Modified</span>
      case 'deleted':
        return <span className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}>Deleted</span>
      default:
        return <span className={`${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400`}>Unknown</span>
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <div className="flex items-center space-x-3">
            {getStatusIcon(policy.status)}
            <div>
              <h2 className="text-2xl font-semibold">Policy Review</h2>
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                Policy ID: {policy.id} | Status: {policy.status}
              </p>
              {policy.reviewed_by && policy.reviewed_at && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Reviewed by {policy.reviewed_by} on {new Date(policy.reviewed_at).toLocaleString()}
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
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-800 dark:text-red-200 text-sm">
              {error}
            </div>
          )}

          {/* Monaco Editor */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Policy Definition (JSON)
            </label>
            <div className="border border-gray-200 dark:border-dark-border rounded-lg overflow-hidden">
              <Editor
                height="300px"
                defaultLanguage="json"
                value={editedPolicy}
                onChange={handleEditorChange}
                theme={isDarkMode ? 'vs-dark' : 'light'}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  renderWhitespace: 'selection',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 2,
                }}
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Edit the policy details using JSON format. Required fields: subject, resource, action
            </p>
          </div>

          {/* Evidence Section (Read-only) */}
          {policy.evidence.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <FileCode size={20} className="text-blue-600 dark:text-blue-400" />
                <h3 className="text-lg font-semibold">Evidence ({policy.evidence.length})</h3>
              </div>
              <div className="space-y-3">
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
            </div>
          )}

          {/* Risk Scores (Read-only) */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Risk Score
              </div>
              <div className="text-2xl font-semibold">
                {policy.risk_score !== null ? Math.round(policy.risk_score) : 'N/A'}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Level: {policy.risk_level || 'Unknown'}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Complexity Score
              </div>
              <div className="text-2xl font-semibold">
                {policy.complexity_score !== null ? Math.round(policy.complexity_score) : 'N/A'}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Impact Score
              </div>
              <div className="text-2xl font-semibold">
                {policy.impact_score !== null ? Math.round(policy.impact_score) : 'N/A'}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Confidence Score
              </div>
              <div className="text-2xl font-semibold">
                {policy.confidence_score !== null ? Math.round(policy.confidence_score) : 'N/A'}
              </div>
            </div>
          </div>

          {/* Existing Review Comment (if any) */}
          {policy.approval_comment && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Review Comment</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">{policy.approval_comment}</p>
            </div>
          )}

          {/* Approval/Rejection Section (only for pending policies) */}
          {policy.status === 'pending' && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Review Decision</h4>
              <textarea
                value={approvalComment}
                onChange={(e) => setApprovalComment(e.target.value)}
                placeholder="Add a comment (optional)"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent resize-none"
                rows={3}
              />
            </div>
          )}

          {/* Change History */}
          <div className="space-y-3">
            <button
              onClick={toggleHistory}
              className="inline-flex items-center space-x-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              <History size={16} />
              <span>{showHistory ? 'Hide' : 'Show'} Change History</span>
            </button>

            {showHistory && (
              <div className="space-y-3">
                {isLoadingHistory ? (
                  <p className="text-sm text-gray-600 dark:text-gray-400">Loading history...</p>
                ) : policyHistory.length === 0 ? (
                  <p className="text-sm text-gray-600 dark:text-gray-400">No change history available</p>
                ) : (
                  policyHistory.map((change) => (
                    <div
                      key={change.id}
                      className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-800"
                    >
                      <div className="flex items-center justify-between mb-2">
                        {getChangeTypeBadge(change.change_type)}
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {change.detected_at ? new Date(change.detected_at).toLocaleString() : 'Unknown'}
                        </span>
                      </div>
                      {change.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{change.description}</p>
                      )}
                      {change.diff_summary && (
                        <pre className="text-xs bg-white dark:bg-gray-950 p-3 rounded border border-gray-200 dark:border-gray-800 overflow-x-auto">
                          {change.diff_summary}
                        </pre>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-dark-border">
          <div className="flex items-center space-x-3">
            {policy.status === 'pending' && (
              <>
                <button
                  onClick={handleApprove}
                  disabled={isSaving}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 transition text-sm inline-flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircle size={16} />
                  <span>{isSaving ? 'Approving...' : 'Approve'}</span>
                </button>
                <button
                  onClick={handleReject}
                  disabled={isSaving}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 transition text-sm inline-flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <XCircle size={16} />
                  <span>{isSaving ? 'Rejecting...' : 'Reject'}</span>
                </button>
              </>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition text-sm"
              disabled={isSaving}
            >
              Close
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition text-sm inline-flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save size={16} />
              <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
