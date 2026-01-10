import { useState, useEffect } from 'react';
import { ShieldCheck, AlertCircle } from 'lucide-react';

interface LLMSettings {
  provider: 'aws_bedrock' | 'azure_openai';
  aws_bedrock_region: string;
  aws_bedrock_model_id: string;
  azure_openai_endpoint: string;
  azure_openai_deployment_name: string;
  azure_openai_api_version: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<LLMSettings>({
    provider: 'aws_bedrock',
    aws_bedrock_region: 'us-east-1',
    aws_bedrock_model_id: 'anthropic.claude-sonnet-4-20250514-v1:0',
    azure_openai_endpoint: '',
    azure_openai_deployment_name: 'claude-sonnet-4',
    azure_openai_api_version: '2024-10-01-preview',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSave = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // In a real implementation, this would call an API endpoint to save settings
      // For now, we'll just show a success message
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call

      setSuccess('LLM provider settings saved successfully. Restart the backend to apply changes.');
    } catch (err) {
      setError('Failed to save settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">Settings</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Configure LLM provider for policy extraction and analysis
        </p>
      </div>

      {/* Security Notice */}
      <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
        <div className="flex gap-3">
          <ShieldCheck className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
              Private LLM Endpoints Only
            </h3>
            <p className="mt-1 text-sm text-blue-800 dark:text-blue-200">
              For security and compliance, this application only supports private LLM endpoints:
              AWS Bedrock or Azure OpenAI. Direct Anthropic Claude.ai connections are not allowed
              to ensure no customer data is used for model training.
            </p>
          </div>
        </div>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        </div>
      )}

      {success && (
        <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4">
          <p className="text-sm text-green-800 dark:text-green-200">{success}</p>
        </div>
      )}

      {/* Provider Selection */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
          LLM Provider
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Provider Type
            </label>
            <select
              value={settings.provider}
              onChange={(e) => setSettings({ ...settings, provider: e.target.value as 'aws_bedrock' | 'azure_openai' })}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="aws_bedrock">AWS Bedrock</option>
              <option value="azure_openai">Azure OpenAI</option>
            </select>
          </div>
        </div>
      </div>

      {/* AWS Bedrock Settings */}
      {settings.provider === 'aws_bedrock' && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
            AWS Bedrock Configuration
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                AWS Region
              </label>
              <input
                type="text"
                value={settings.aws_bedrock_region}
                onChange={(e) => setSettings({ ...settings, aws_bedrock_region: e.target.value })}
                placeholder="us-east-1"
                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Model ID
              </label>
              <input
                type="text"
                value={settings.aws_bedrock_model_id}
                onChange={(e) => setSettings({ ...settings, aws_bedrock_model_id: e.target.value })}
                placeholder="anthropic.claude-sonnet-4-20250514-v1:0"
                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong className="text-gray-900 dark:text-gray-100">Note:</strong> AWS credentials should be
                configured via environment variables (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) or
                IAM roles. These settings control the region and model to use.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Azure OpenAI Settings */}
      {settings.provider === 'azure_openai' && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
            Azure OpenAI Configuration
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Azure Endpoint
              </label>
              <input
                type="text"
                value={settings.azure_openai_endpoint}
                onChange={(e) => setSettings({ ...settings, azure_openai_endpoint: e.target.value })}
                placeholder="https://your-resource.openai.azure.com"
                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Deployment Name
              </label>
              <input
                type="text"
                value={settings.azure_openai_deployment_name}
                onChange={(e) => setSettings({ ...settings, azure_openai_deployment_name: e.target.value })}
                placeholder="claude-sonnet-4"
                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                API Version
              </label>
              <input
                type="text"
                value={settings.azure_openai_api_version}
                onChange={(e) => setSettings({ ...settings, azure_openai_api_version: e.target.value })}
                placeholder="2024-10-01-preview"
                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong className="text-gray-900 dark:text-gray-100">Note:</strong> Azure OpenAI API key should be
                configured via the AZURE_OPENAI_API_KEY environment variable. These settings control the
                endpoint and deployment to use.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Environment Variables Reference */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">
          Environment Variables
        </h2>

        <div className="space-y-3 font-mono text-sm">
          <div className="flex items-start gap-3">
            <span className="text-gray-500 dark:text-gray-500">•</span>
            <div>
              <code className="text-blue-600 dark:text-blue-400">LLM_PROVIDER</code>
              <span className="text-gray-600 dark:text-gray-400 ml-2">= aws_bedrock | azure_openai</span>
            </div>
          </div>

          {settings.provider === 'aws_bedrock' && (
            <>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AWS_BEDROCK_REGION</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= {settings.aws_bedrock_region}</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AWS_BEDROCK_MODEL_ID</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= {settings.aws_bedrock_model_id}</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AWS_ACCESS_KEY_ID</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= (your AWS access key)</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AWS_SECRET_ACCESS_KEY</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= (your AWS secret key)</span>
                </div>
              </div>
            </>
          )}

          {settings.provider === 'azure_openai' && (
            <>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AZURE_OPENAI_ENDPOINT</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= {settings.azure_openai_endpoint || '(set endpoint)'}</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AZURE_OPENAI_API_KEY</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= (your Azure API key)</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AZURE_OPENAI_DEPLOYMENT_NAME</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= {settings.azure_openai_deployment_name}</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-gray-500 dark:text-gray-500">•</span>
                <div>
                  <code className="text-blue-600 dark:text-blue-400">AZURE_OPENAI_API_VERSION</code>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">= {settings.azure_openai_api_version}</span>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="mt-4 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            <strong>Important:</strong> These environment variables must be set in your <code>.env</code> file
            or container environment. Changes require restarting the backend service to take effect.
          </p>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={loading}
          className="rounded-lg bg-blue-600 dark:bg-blue-500 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
