import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  TrendingUp,
  Shield,
  BarChart3,
  Filter,
  Download,
  Settings,
  FileText,
} from 'lucide-react'
import logger from '../lib/logger'

interface RiskDistribution {
  high: number
  medium: number
  low: number
  unscored: number
}

interface RiskMetrics {
  total_policies: number
  average_risk_score: number
  average_complexity: number
  average_impact: number
  average_confidence: number
  distribution: RiskDistribution
}

interface Policy {
  id: number
  subject: string
  resource: string
  action: string
  risk_score: number | null
  risk_level: 'low' | 'medium' | 'high' | null
  complexity_score: number | null
  impact_score: number | null
  confidence_score: number | null
  historical_score: number | null
  status: string
  repository_id: number
}

interface RiskThresholds {
  high_threshold: number
  medium_threshold: number
}

export default function RiskDashboardPage() {
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<
    'high' | 'medium' | 'low' | 'unscored' | null
  >(null)
  const [filteredPolicies, setFilteredPolicies] = useState<Policy[]>([])
  const [thresholds, setThresholds] = useState<RiskThresholds>({
    high_threshold: 70.0,
    medium_threshold: 40.0,
  })
  const [showThresholdSettings, setShowThresholdSettings] = useState(false)
  const [tempThresholds, setTempThresholds] = useState<RiskThresholds>({
    high_threshold: 70.0,
    medium_threshold: 40.0,
  })

  const fetchMetrics = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch('/api/v1/risk/metrics')

      if (!response.ok) {
        throw new Error('Failed to fetch risk metrics')
      }

      const data = await response.json()
      setMetrics(data)
      logger.info('Risk metrics fetched', { data })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      logger.error('Failed to fetch risk metrics', { error: errorMessage })
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchThresholds = async () => {
    try {
      const response = await fetch('/api/v1/risk/thresholds')
      if (response.ok) {
        const data = await response.json()
        setThresholds(data)
        setTempThresholds(data)
      }
    } catch (err) {
      logger.error('Failed to fetch risk thresholds', { error: err })
    }
  }

  const fetchPoliciesByRiskLevel = async (level: 'high' | 'medium' | 'low' | 'unscored') => {
    try {
      const response = await fetch(`/api/v1/risk/policies/by-level/${level}`)

      if (!response.ok) {
        throw new Error('Failed to fetch policies')
      }

      const data = await response.json()
      setFilteredPolicies(data.policies)
      logger.info('Policies by risk level fetched', { level, count: data.total })
    } catch (err) {
      logger.error('Failed to fetch policies by risk level', { error: err })
    }
  }

  useEffect(() => {
    logger.info('RiskDashboardPage mounted')
    fetchMetrics()
    fetchThresholds()
  }, [])

  useEffect(() => {
    if (selectedRiskLevel) {
      fetchPoliciesByRiskLevel(selectedRiskLevel)
    } else {
      setFilteredPolicies([])
    }
  }, [selectedRiskLevel])

  const handleUpdateThresholds = async () => {
    try {
      const response = await fetch('/api/v1/risk/thresholds', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(tempThresholds),
      })

      if (!response.ok) {
        throw new Error('Failed to update thresholds')
      }

      const data = await response.json()
      setThresholds(data)
      setShowThresholdSettings(false)
      logger.info('Risk thresholds updated', { thresholds: data })
    } catch (err) {
      logger.error('Failed to update risk thresholds', { error: err })
    }
  }

  const getRiskLevelBadge = (level: 'low' | 'medium' | 'high' | null) => {
    if (!level) {
      return (
        <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">
          Unscored
        </span>
      )
    }
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium'
    switch (level) {
      case 'high':
        return (
          <span
            className={`${baseClasses} bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`}
          >
            High Risk
          </span>
        )
      case 'medium':
        return (
          <span
            className={`${baseClasses} bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-400`}
          >
            Medium Risk
          </span>
        )
      case 'low':
        return (
          <span
            className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`}
          >
            Low Risk
          </span>
        )
    }
  }

  const exportRiskReport = () => {
    if (!metrics) return

    const reportData = {
      generated_at: new Date().toISOString(),
      metrics,
      thresholds,
    }

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `risk-report-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)

    logger.info('Risk report exported')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-600 dark:text-gray-400">Loading risk metrics...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-red-600 dark:text-red-400">Error: {error}</div>
      </div>
    )
  }

  if (!metrics) {
    return null
  }

  const totalScored =
    metrics.distribution.high + metrics.distribution.medium + metrics.distribution.low
  const highPercent = totalScored > 0 ? (metrics.distribution.high / totalScored) * 100 : 0
  const mediumPercent = totalScored > 0 ? (metrics.distribution.medium / totalScored) * 100 : 0
  const lowPercent = totalScored > 0 ? (metrics.distribution.low / totalScored) * 100 : 0

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
            Risk Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Policy risk analysis and distribution
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowThresholdSettings(!showThresholdSettings)}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <Settings size={16} />
            <span>Thresholds</span>
          </button>
          <button
            onClick={exportRiskReport}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Download size={16} />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* Threshold Settings */}
      {showThresholdSettings && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Risk Thresholds</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                High Risk Threshold (≥ this value)
              </label>
              <input
                type="number"
                value={tempThresholds.high_threshold}
                onChange={(e) =>
                  setTempThresholds({ ...tempThresholds, high_threshold: parseFloat(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950"
                min="0"
                max="100"
                step="0.1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Medium Risk Threshold (≥ this value)
              </label>
              <input
                type="number"
                value={tempThresholds.medium_threshold}
                onChange={(e) =>
                  setTempThresholds({
                    ...tempThresholds,
                    medium_threshold: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-950"
                min="0"
                max="100"
                step="0.1"
              />
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setTempThresholds(thresholds)
                  setShowThresholdSettings(false)
                }}
                className="px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateThresholds}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Policies</p>
              <p className="text-3xl font-semibold mt-1">{metrics.total_policies}</p>
            </div>
            <Shield className="text-blue-600" size={32} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg Risk Score</p>
              <p className="text-3xl font-semibold mt-1">{metrics.average_risk_score}</p>
            </div>
            <TrendingUp className="text-amber-500" size={32} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg Complexity</p>
              <p className="text-3xl font-semibold mt-1">{metrics.average_complexity}</p>
            </div>
            <BarChart3 className="text-purple-600" size={32} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg Impact</p>
              <p className="text-3xl font-semibold mt-1">{metrics.average_impact}</p>
            </div>
            <AlertTriangle className="text-red-600" size={32} />
          </div>
        </div>
      </div>

      {/* Risk Distribution Chart */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-6">Risk Distribution</h2>

        {/* Bar Chart */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">High Risk</span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {metrics.distribution.high} ({highPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-4">
              <div
                className="bg-red-600 h-4 rounded-full transition-all duration-500"
                style={{ width: `${highPercent}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Medium Risk</span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {metrics.distribution.medium} ({mediumPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-4">
              <div
                className="bg-amber-500 h-4 rounded-full transition-all duration-500"
                style={{ width: `${mediumPercent}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Low Risk</span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {metrics.distribution.low} ({lowPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-4">
              <div
                className="bg-green-600 h-4 rounded-full transition-all duration-500"
                style={{ width: `${lowPercent}%` }}
              />
            </div>
          </div>

          {metrics.distribution.unscored > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Unscored</span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {metrics.distribution.unscored}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-4">
                <div className="bg-gray-400 h-4 rounded-full w-full" />
              </div>
            </div>
          )}
        </div>

        {/* Filter Buttons */}
        <div className="mt-6 flex items-center space-x-3">
          <Filter size={16} className="text-gray-600 dark:text-gray-400" />
          <button
            onClick={() => setSelectedRiskLevel('high')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              selectedRiskLevel === 'high'
                ? 'bg-red-600 text-white'
                : 'border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            High ({metrics.distribution.high})
          </button>
          <button
            onClick={() => setSelectedRiskLevel('medium')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              selectedRiskLevel === 'medium'
                ? 'bg-amber-500 text-white'
                : 'border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            Medium ({metrics.distribution.medium})
          </button>
          <button
            onClick={() => setSelectedRiskLevel('low')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              selectedRiskLevel === 'low'
                ? 'bg-green-600 text-white'
                : 'border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            Low ({metrics.distribution.low})
          </button>
          {metrics.distribution.unscored > 0 && (
            <button
              onClick={() => setSelectedRiskLevel('unscored')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                selectedRiskLevel === 'unscored'
                  ? 'bg-gray-600 text-white'
                  : 'border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
            >
              Unscored ({metrics.distribution.unscored})
            </button>
          )}
          {selectedRiskLevel && (
            <button
              onClick={() => setSelectedRiskLevel(null)}
              className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Clear Filter
            </button>
          )}
        </div>
      </div>

      {/* Filtered Policies */}
      {selectedRiskLevel && filteredPolicies.length > 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-6">
            {selectedRiskLevel.charAt(0).toUpperCase() + selectedRiskLevel.slice(1)} Risk Policies
          </h2>
          <div className="space-y-4">
            {filteredPolicies.map((policy) => (
              <div
                key={policy.id}
                className="border border-gray-200 dark:border-gray-800 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="font-medium">
                        {policy.subject} → {policy.action} → {policy.resource}
                      </h3>
                      {getRiskLevelBadge(policy.risk_level)}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Risk Score:</span>
                        <span className="ml-2 font-medium">
                          {policy.risk_score?.toFixed(1) ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Complexity:</span>
                        <span className="ml-2 font-medium">
                          {policy.complexity_score?.toFixed(1) ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Impact:</span>
                        <span className="ml-2 font-medium">
                          {policy.impact_score?.toFixed(1) ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Confidence:</span>
                        <span className="ml-2 font-medium">
                          {policy.confidence_score?.toFixed(1) ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Historical:</span>
                        <span className="ml-2 font-medium">
                          {policy.historical_score?.toFixed(1) ?? 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedRiskLevel && filteredPolicies.length === 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 text-center text-gray-600 dark:text-gray-400">
          No policies found for this risk level.
        </div>
      )}
    </div>
  )
}
