import { useEffect, useState } from 'react';
import { ShieldAlert, AlertTriangle, FileText, MapPin } from 'lucide-react';
import type { SecretDetectionLog } from '../types/secret';

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretDetectionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSecrets();
  }, []);

  const fetchSecrets = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:7777/api/v1/secrets/');
      if (!response.ok) {
        throw new Error('Failed to fetch secret detection logs');
      }
      const data = await response.json();
      setSecrets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getSecretTypeColor = (type: string): string => {
    if (type.includes('aws') || type.includes('private_key')) return 'text-red-600 dark:text-red-400';
    if (type.includes('password') || type.includes('database')) return 'text-orange-600 dark:text-orange-400';
    return 'text-yellow-600 dark:text-yellow-400';
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600 dark:text-gray-400">Loading secret detection logs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-800 dark:text-red-200">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Secret Detection Logs
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Secrets detected in scanned repositories (redacted before sending to LLM)
          </p>
        </div>
      </div>

      {secrets.length === 0 ? (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-8 text-center">
          <ShieldAlert className="w-12 h-12 text-green-600 dark:text-green-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-green-900 dark:text-green-100 mb-1">
            No Secrets Detected
          </h3>
          <p className="text-green-700 dark:text-green-300">
            All scanned repositories are clean - no credentials found.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-amber-900 dark:text-amber-100">
                  {secrets.length} secret{secrets.length !== 1 ? 's' : ''} detected
                </p>
                <p className="text-amber-700 dark:text-amber-300 mt-1">
                  All secrets were redacted before sending code to the LLM. Review the logs below.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg divide-y divide-gray-200 dark:divide-gray-800">
            {secrets.map((secret) => (
              <div key={secret.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-sm font-medium ${getSecretTypeColor(secret.secret_type)}`}>
                        {secret.description}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ({secret.secret_type})
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex items-center gap-1.5">
                        <FileText className="w-4 h-4" />
                        <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">
                          {secret.file_path}
                        </code>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-4 h-4" />
                        <span>Line {secret.line_number}</span>
                      </div>
                    </div>

                    <div className="bg-gray-50 dark:bg-gray-800 rounded p-2 border border-gray-200 dark:border-gray-700">
                      <code className="text-xs text-gray-700 dark:text-gray-300 font-mono">
                        {secret.preview}
                      </code>
                    </div>
                  </div>

                  <div className="text-right text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                    {formatDate(secret.detected_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
