import { useEffect, useState } from 'react';
import { Shield, CheckCircle, AlertCircle, Info } from 'lucide-react';

interface EncryptionCheck {
  enabled?: boolean;
  configured?: boolean;
  recommendation?: string;
  method?: string;
  notes?: string;
  algorithm?: string;
}

interface ComponentAudit {
  status: string;
  ssl_tls_in_transit?: EncryptionCheck;
  tls_in_transit?: EncryptionCheck;
  https_tls?: EncryptionCheck;
  encryption_at_rest?: EncryptionCheck;
  encrypted_fields?: Record<string, string>;
  encryption_key?: EncryptionCheck;
  encrypted_secrets?: string[];
  api_security?: string[];
  notes?: string[];
}

interface SecurityAudit {
  database: ComponentAudit;
  redis: ComponentAudit;
  object_storage: ComponentAudit;
  secrets: ComponentAudit;
  api: ComponentAudit;
  overall_status: string;
  failed_components?: string[];
}

export function SecurityAuditPage() {
  const [audit, setAudit] = useState<SecurityAudit | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAudit();
  }, []);

  const fetchAudit = async () => {
    try {
      const response = await fetch('/api/v1/security/audit');
      const data = await response.json();
      setAudit(data);
    } catch (error) {
      console.error('Failed to fetch security audit:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500 dark:text-gray-400">Loading security audit...</div>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-600 dark:text-red-400">Failed to load security audit</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass':
        return 'text-green-600 dark:text-green-400';
      case 'partial':
        return 'text-amber-600 dark:text-amber-400';
      case 'fail':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="w-5 h-5" />;
      case 'partial':
        return <AlertCircle className="w-5 h-5" />;
      case 'fail':
        return <AlertCircle className="w-5 h-5" />;
      default:
        return <Info className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">Security Audit</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Encryption at rest and in transit verification
          </p>
        </div>
        <button
          onClick={fetchAudit}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          Refresh Audit
        </button>
      </div>

      {/* Overall Status */}
      <div className="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg">
        <div className="flex items-center space-x-3">
          <Shield className="w-8 h-8 text-blue-600 dark:text-blue-500" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">Overall Security Status</h2>
            <div className={`flex items-center space-x-2 mt-1 ${getStatusColor(audit.overall_status)}`}>
              {getStatusIcon(audit.overall_status)}
              <span className="font-medium uppercase">{audit.overall_status}</span>
            </div>
          </div>
        </div>
        {audit.failed_components && audit.failed_components.length > 0 && (
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <p className="text-sm text-amber-800 dark:text-amber-300">
              Failed components: {audit.failed_components.join(', ')}
            </p>
          </div>
        )}
      </div>

      {/* Component Audits */}
      <div className="space-y-6">
        {/* Database */}
        <ComponentCard title="Database" component={audit.database} />

        {/* Redis */}
        <ComponentCard title="Redis" component={audit.redis} />

        {/* Object Storage */}
        <ComponentCard title="Object Storage (MinIO/S3)" component={audit.object_storage} />

        {/* Secrets */}
        <ComponentCard title="Secrets Encryption" component={audit.secrets} />

        {/* API */}
        <ComponentCard title="API Security" component={audit.api} />
      </div>
    </div>
  );
}

interface ComponentCardProps {
  title: string;
  component: ComponentAudit;
}

function ComponentCard({ title, component }: ComponentCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
      case 'partial':
        return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20';
      case 'fail':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  return (
    <div className="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">{title}</h3>
        <span className={`px-3 py-1 text-xs font-medium rounded-full uppercase ${getStatusColor(component.status)}`}>
          {component.status}
        </span>
      </div>

      <div className="space-y-4">
        {/* Encryption in Transit */}
        {(component.ssl_tls_in_transit || component.tls_in_transit || component.https_tls) && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Encryption in Transit</h4>
            {component.ssl_tls_in_transit && (
              <div className="pl-4 text-sm text-gray-600 dark:text-gray-400">
                <p className="mb-1">
                  <span className="font-medium">SSL/TLS:</span>{' '}
                  {component.ssl_tls_in_transit.enabled ? '✓ Enabled' : '⚠ Disabled'}
                </p>
                {component.ssl_tls_in_transit.recommendation && (
                  <p className="text-xs text-gray-500 dark:text-gray-500">{component.ssl_tls_in_transit.recommendation}</p>
                )}
              </div>
            )}
            {component.tls_in_transit && (
              <div className="pl-4 text-sm text-gray-600 dark:text-gray-400">
                <p className="mb-1">
                  <span className="font-medium">TLS:</span>{' '}
                  {component.tls_in_transit.enabled ? '✓ Enabled' : '⚠ Disabled'}
                </p>
                {component.tls_in_transit.recommendation && (
                  <p className="text-xs text-gray-500 dark:text-gray-500">{component.tls_in_transit.recommendation}</p>
                )}
              </div>
            )}
            {component.https_tls && (
              <div className="pl-4 text-sm text-gray-600 dark:text-gray-400">
                <p className="mb-1">
                  <span className="font-medium">HTTPS/TLS:</span>{' '}
                  {component.https_tls.configured ? '✓ Configured' : '⚠ Not Configured'}
                </p>
                {component.https_tls.recommendation && (
                  <p className="text-xs text-gray-500 dark:text-gray-500">{component.https_tls.recommendation}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Encryption at Rest */}
        {component.encryption_at_rest && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Encryption at Rest</h4>
            <div className="pl-4 text-sm text-gray-600 dark:text-gray-400">
              <p className="mb-1">
                <span className="font-medium">Status:</span>{' '}
                {component.encryption_at_rest.configured ? '✓ Configured' : '✗ Not Configured'}
              </p>
              {component.encryption_at_rest.method && (
                <p className="mb-1">
                  <span className="font-medium">Method:</span> {component.encryption_at_rest.method}
                </p>
              )}
              {component.encryption_at_rest.notes && (
                <p className="text-xs text-gray-500 dark:text-gray-500">{component.encryption_at_rest.notes}</p>
              )}
            </div>
          </div>
        )}

        {/* Encrypted Fields */}
        {component.encrypted_fields && Object.keys(component.encrypted_fields).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Encrypted Fields</h4>
            <div className="pl-4 space-y-1">
              {Object.entries(component.encrypted_fields).map(([field, description]) => (
                <div key={field} className="text-sm text-gray-600 dark:text-gray-400">
                  <span className="font-mono text-xs">{field}</span>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Encryption Key */}
        {component.encryption_key && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Encryption Key</h4>
            <div className="pl-4 text-sm text-gray-600 dark:text-gray-400">
              <p className="mb-1">
                <span className="font-medium">Configured:</span>{' '}
                {component.encryption_key.configured ? '✓ Yes' : '✗ No'}
              </p>
              {component.encryption_key.algorithm && (
                <p className="mb-1">
                  <span className="font-medium">Algorithm:</span> {component.encryption_key.algorithm}
                </p>
              )}
              {component.encryption_key.recommendation && (
                <p className="text-xs text-gray-500 dark:text-gray-500">{component.encryption_key.recommendation}</p>
              )}
            </div>
          </div>
        )}

        {/* Encrypted Secrets */}
        {component.encrypted_secrets && component.encrypted_secrets.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Encrypted Secrets</h4>
            <ul className="pl-4 space-y-1">
              {component.encrypted_secrets.map((secret, index) => (
                <li key={index} className="text-sm text-gray-600 dark:text-gray-400">
                  • {secret}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* API Security */}
        {component.api_security && component.api_security.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Security Features</h4>
            <ul className="pl-4 space-y-1">
              {component.api_security.map((feature, index) => (
                <li key={index} className="text-sm text-gray-600 dark:text-gray-400">
                  • {feature}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Notes */}
        {component.notes && component.notes.length > 0 && (
          <div className="pt-4 mt-4 border-t border-gray-200 dark:border-gray-800">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Notes</h4>
            <ul className="pl-4 space-y-1">
              {component.notes.map((note, index) => (
                <li key={index} className="text-xs text-gray-500 dark:text-gray-500">
                  • {note}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
