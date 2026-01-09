import { useEffect, useState } from 'react';
import { FileEdit, AlertCircle, CheckCircle2, Plus, Minus, ChevronDown, ChevronUp } from 'lucide-react';

interface PolicyChange {
  id: number;
  repository_id: number;
  change_type: 'added' | 'modified' | 'deleted';
  before_subject?: string;
  before_resource?: string;
  before_action?: string;
  before_conditions?: string;
  after_subject?: string;
  after_resource?: string;
  after_action?: string;
  after_conditions?: string;
  description?: string;
  diff_summary?: string;
  detected_at: string;
}

interface WorkItem {
  id: number;
  policy_change_id: number;
  repository_id: number;
  title: string;
  description?: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_to?: string;
  created_at: string;
  is_spaghetti_detection: number;
  refactoring_suggestion?: string;
}

interface SpaghettiMetrics {
  total_spaghetti_detected: number;
  spaghetti_resolved: number;
  spaghetti_open: number;
  spaghetti_in_progress: number;
  prevention_rate: number;
  total_work_items: number;
}

export default function ChangesPage() {
  const [changes, setChanges] = useState<PolicyChange[]>([]);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedChanges, setExpandedChanges] = useState<Set<number>>(new Set());
  const [spaghettiMetrics, setSpaghettiMetrics] = useState<SpaghettiMetrics | null>(null);

  useEffect(() => {
    fetchChanges();
    fetchWorkItems();
    fetchSpaghettiMetrics();
  }, []);

  const fetchChanges = async () => {
    try {
      const response = await fetch('/api/v1/changes/');
      if (response.ok) {
        const data = await response.json();
        setChanges(data);
      }
    } catch (error) {
      console.error('Error fetching changes:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchWorkItems = async () => {
    try {
      const response = await fetch('/api/v1/changes/work-items/');
      if (response.ok) {
        const data = await response.json();
        setWorkItems(data);
      }
    } catch (error) {
      console.error('Error fetching work items:', error);
    }
  };

  const fetchSpaghettiMetrics = async () => {
    try {
      const response = await fetch('/api/v1/changes/spaghetti-metrics');
      if (response.ok) {
        const data = await response.json();
        setSpaghettiMetrics(data);
      }
    } catch (error) {
      console.error('Error fetching spaghetti metrics:', error);
    }
  };

  const toggleExpanded = (changeId: number) => {
    const newExpanded = new Set(expandedChanges);
    if (newExpanded.has(changeId)) {
      newExpanded.delete(changeId);
    } else {
      newExpanded.add(changeId);
    }
    setExpandedChanges(newExpanded);
  };

  const getChangeIcon = (changeType: string) => {
    switch (changeType) {
      case 'added':
        return <Plus className="h-5 w-5 text-green-600 dark:text-green-400" />;
      case 'modified':
        return <FileEdit className="h-5 w-5 text-blue-600 dark:text-blue-400" />;
      case 'deleted':
        return <Minus className="h-5 w-5 text-red-600 dark:text-red-400" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-600 dark:text-gray-400" />;
    }
  };

  const getChangeTypeBadge = (changeType: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium';
    switch (changeType) {
      case 'added':
        return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`;
      case 'modified':
        return `${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`;
      case 'deleted':
        return `${baseClasses} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200`;
    }
  };

  const getPriorityBadge = (priority: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium';
    switch (priority) {
      case 'critical':
        return `${baseClasses} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200`;
      case 'high':
        return `${baseClasses} bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200`;
      case 'medium':
        return `${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200`;
      case 'low':
        return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200`;
    }
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = 'px-2 py-1 rounded text-xs font-medium';
    switch (status) {
      case 'open':
        return `${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`;
      case 'in_progress':
        return `${baseClasses} bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200`;
      case 'resolved':
        return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`;
      case 'closed':
        return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200`;
    }
  };

  const renderDiffLines = (diffSummary: string) => {
    return diffSummary.split('\n').map((line, idx) => {
      if (line.startsWith('- ')) {
        return (
          <div key={idx} className="bg-red-50 dark:bg-red-900/20 text-red-900 dark:text-red-200 px-4 py-1 font-mono text-sm">
            {line}
          </div>
        );
      } else if (line.startsWith('+ ')) {
        return (
          <div key={idx} className="bg-green-50 dark:bg-green-900/20 text-green-900 dark:text-green-200 px-4 py-1 font-mono text-sm">
            {line}
          </div>
        );
      } else {
        return (
          <div key={idx} className="text-gray-900 dark:text-gray-100 px-4 py-1 font-mono text-sm">
            {line}
          </div>
        );
      }
    });
  };

  const getWorkItemsForChange = (changeId: number) => {
    return workItems.filter(item => item.policy_change_id === changeId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600 dark:text-gray-400">Loading changes...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">Policy Changes</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Review detected changes to authorization policies and associated work items
        </p>
      </div>

      {/* Spaghetti Prevention Metrics */}
      {spaghettiMetrics && spaghettiMetrics.total_spaghetti_detected > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            <h2 className="text-lg font-semibold text-amber-900 dark:text-amber-100">
              Spaghetti Code Prevention Dashboard
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
              <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                {spaghettiMetrics.total_spaghetti_detected}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Detected</div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {spaghettiMetrics.spaghetti_open}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Open</div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {spaghettiMetrics.spaghetti_in_progress}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">In Progress</div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {spaghettiMetrics.spaghetti_resolved}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Resolved</div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {spaghettiMetrics.prevention_rate}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Prevention Rate</div>
            </div>
          </div>
        </div>
      )}

      {changes.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-12 text-center">
          <CheckCircle2 className="h-16 w-16 text-green-600 dark:text-green-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-2">No Changes Detected</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Run a scan on a repository to detect policy changes
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {changes.map((change) => {
            const isExpanded = expandedChanges.has(change.id);
            const changeWorkItems = getWorkItemsForChange(change.id);

            return (
              <div
                key={change.id}
                className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      {getChangeIcon(change.change_type)}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={getChangeTypeBadge(change.change_type)}>
                            {change.change_type.toUpperCase()}
                          </span>
                          <span className="text-sm text-gray-500 dark:text-gray-400">
                            {new Date(change.detected_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-gray-900 dark:text-gray-50 font-medium mb-2">
                          {change.description || 'Policy change detected'}
                        </p>

                        {/* Policy summary */}
                        <div className="space-y-2 text-sm">
                          {change.change_type === 'deleted' && (
                            <div className="text-gray-600 dark:text-gray-400">
                              <span className="font-medium">Deleted: </span>
                              {change.before_subject} → {change.before_action} → {change.before_resource}
                            </div>
                          )}
                          {change.change_type === 'added' && (
                            <div className="text-gray-600 dark:text-gray-400">
                              <span className="font-medium">Added: </span>
                              {change.after_subject} → {change.after_action} → {change.after_resource}
                            </div>
                          )}
                          {change.change_type === 'modified' && (
                            <div className="space-y-1">
                              <div className="text-red-600 dark:text-red-400">
                                <span className="font-medium">Before: </span>
                                {change.before_subject} → {change.before_action} → {change.before_resource}
                              </div>
                              <div className="text-green-600 dark:text-green-400">
                                <span className="font-medium">After: </span>
                                {change.after_subject} → {change.after_action} → {change.after_resource}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Work items */}
                        {changeWorkItems.length > 0 && (
                          <div className="mt-4 space-y-2">
                            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              Work Items ({changeWorkItems.length})
                            </div>
                            {changeWorkItems.map((workItem) => (
                              <div
                                key={workItem.id}
                                className={`p-3 rounded border ${workItem.is_spaghetti_detection === 1 ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700' : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'}`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      {workItem.is_spaghetti_detection === 1 && (
                                        <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                                      )}
                                      <div className="text-sm font-medium text-gray-900 dark:text-gray-50">
                                        {workItem.title}
                                      </div>
                                    </div>
                                    {workItem.assigned_to && (
                                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                        Assigned to: {workItem.assigned_to}
                                      </div>
                                    )}
                                    {workItem.is_spaghetti_detection === 1 && (
                                      <div className="mt-2 p-2 bg-white dark:bg-gray-900 rounded border border-amber-200 dark:border-amber-800">
                                        <div className="text-xs font-medium text-amber-900 dark:text-amber-100 mb-1">
                                          ⚡ Use centralized PBAC instead
                                        </div>
                                        {workItem.refactoring_suggestion && (
                                          <div className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                            {workItem.refactoring_suggestion.substring(0, 500)}
                                            {workItem.refactoring_suggestion.length > 500 && '...'}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2 ml-4">
                                    <span className={getPriorityBadge(workItem.priority)}>
                                      {workItem.priority}
                                    </span>
                                    <span className={getStatusBadge(workItem.status)}>
                                      {workItem.status.replace('_', ' ')}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {change.diff_summary && (
                      <button
                        onClick={() => toggleExpanded(change.id)}
                        className="ml-4 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Diff visualization */}
                  {isExpanded && change.diff_summary && (
                    <div className="mt-6 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                      <div className="bg-gray-50 dark:bg-gray-800 px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Detailed Changes
                        </span>
                      </div>
                      <div className="bg-white dark:bg-gray-900">
                        {renderDiffLines(change.diff_summary)}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
