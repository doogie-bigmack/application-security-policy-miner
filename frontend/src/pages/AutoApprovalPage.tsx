import { useEffect, useState } from 'react';
import { Brain, CheckCircle2, TrendingUp, Settings as SettingsIcon } from 'lucide-react';
import logger from '../lib/logger';
import {
  autoApprovalApi,
  AutoApprovalSettings,
  AutoApprovalDecision,
} from '../services/autoApprovalApi';

export default function AutoApprovalPage() {
  const [settings, setSettings] = useState<AutoApprovalSettings | null>(null);
  const [decisions, setDecisions] = useState<AutoApprovalDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [enabled, setEnabled] = useState(false);
  const [riskThreshold, setRiskThreshold] = useState(30);
  const [minHistoricalApprovals, setMinHistoricalApprovals] = useState(3);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [settingsData, decisionsData] = await Promise.all([
        autoApprovalApi.getSettings(),
        autoApprovalApi.getDecisions(50),
      ]);

      setSettings(settingsData);
      setEnabled(settingsData.enabled);
      setRiskThreshold(settingsData.risk_threshold);
      setMinHistoricalApprovals(settingsData.min_historical_approvals);
      setDecisions(decisionsData);

      logger.info('Auto-approval data loaded');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load auto-approval data';
      setError(message);
      logger.error('Error loading auto-approval data', { error: err });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      setError(null);

      const updated = await autoApprovalApi.updateSettings({
        enabled,
        risk_threshold: riskThreshold,
        min_historical_approvals: minHistoricalApprovals,
      });

      setSettings(updated);
      logger.info('Auto-approval settings updated');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save settings';
      setError(message);
      logger.error('Error saving settings', { error: err });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-950 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Brain className="w-8 h-8 text-blue-600 dark:text-blue-500" />
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
              Auto-Approval Settings
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Configure AI-powered automatic approval of low-risk policies based on historical patterns
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-red-800 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Metrics Overview */}
        {settings && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Auto-Approval Rate
                </span>
                <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-500" />
              </div>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                {settings.auto_approval_rate.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                Target: &gt;30%
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Auto-Approved Policies
                </span>
                <CheckCircle2 className="w-5 h-5 text-blue-600 dark:text-blue-500" />
              </div>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                {settings.total_auto_approvals}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                of {settings.total_policies_scanned} scanned
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
                <SettingsIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </div>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                {settings.enabled ? 'Enabled' : 'Disabled'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                AI learning mode
              </p>
            </div>
          </div>
        )}

        {/* Settings Form */}
        <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-6">
            Configuration
          </h2>

          <div className="space-y-6">
            {/* Enable/Disable */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-900 dark:text-gray-50">
                  Enable AI Learning Mode
                </label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Automatically approve low-risk policies based on historical patterns
                </p>
              </div>
              <button
                onClick={() => setEnabled(!enabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  enabled
                    ? 'bg-blue-600 dark:bg-blue-500'
                    : 'bg-gray-200 dark:bg-gray-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Risk Threshold */}
            <div>
              <label className="text-sm font-medium text-gray-900 dark:text-gray-50 block mb-2">
                Risk Threshold: {riskThreshold}
              </label>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Maximum risk score (0-100) for auto-approval
              </p>
              <input
                type="range"
                min="0"
                max="100"
                value={riskThreshold}
                onChange={(e) => setRiskThreshold(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-500 mt-1">
                <span>0 (Low Risk)</span>
                <span>100 (High Risk)</span>
              </div>
            </div>

            {/* Min Historical Approvals */}
            <div>
              <label className="text-sm font-medium text-gray-900 dark:text-gray-50 block mb-2">
                Minimum Historical Approvals: {minHistoricalApprovals}
              </label>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Minimum number of similar approved policies required
              </p>
              <input
                type="range"
                min="1"
                max="10"
                value={minHistoricalApprovals}
                onChange={(e) => setMinHistoricalApprovals(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-500 mt-1">
                <span>1</span>
                <span>10</span>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-800">
            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>

        {/* Recent Decisions */}
        <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-6">
            Recent Auto-Approval Decisions
          </h2>

          {decisions.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              No auto-approval decisions yet. Enable AI learning mode and run a scan to see results.
            </p>
          ) : (
            <div className="space-y-3">
              {decisions.map((decision) => (
                <div
                  key={decision.id}
                  className="bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {decision.auto_approved ? (
                        <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-500" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-700" />
                      )}
                      <span className="font-medium text-gray-900 dark:text-gray-50">
                        Policy #{decision.policy_id}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-500">
                      {new Date(decision.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {decision.reasoning}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                    <span>Risk Score: {decision.risk_score.toFixed(1)}</span>
                    <span>Similar Policies: {decision.similar_policies_count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
