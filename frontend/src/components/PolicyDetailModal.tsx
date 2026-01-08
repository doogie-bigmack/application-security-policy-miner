import { useEffect, useState } from 'react'
import { X, Save, FileCode } from 'lucide-react'
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-surface rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <div>
            <h2 className="text-2xl font-semibold">Edit Policy</h2>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
              Policy ID: {policy.id} | Status: {policy.status}
            </p>
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
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-dark-border">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition text-sm"
            disabled={isSaving}
          >
            Cancel
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
  )
}
