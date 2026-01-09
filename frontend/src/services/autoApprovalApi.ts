import { logger } from '../utils/logger';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:7777';
const API_V1 = `${API_BASE_URL}/api/v1`;

export interface AutoApprovalSettings {
  id: number;
  tenant_id: string;
  enabled: boolean;
  risk_threshold: number;
  min_historical_approvals: number;
  total_auto_approvals: number;
  total_policies_scanned: number;
  auto_approval_rate: number;
  created_at: string;
  updated_at: string;
}

export interface AutoApprovalSettingsUpdate {
  enabled?: boolean;
  risk_threshold?: number;
  min_historical_approvals?: number;
}

export interface AutoApprovalDecision {
  id: number;
  tenant_id: string;
  policy_id: number;
  auto_approved: boolean;
  reasoning: string;
  risk_score: number;
  similar_policies_count: number;
  matched_patterns: string | null;
  created_at: string;
}

export interface AutoApprovalMetrics {
  total_auto_approvals: number;
  total_policies_scanned: number;
  auto_approval_rate: number;
  enabled: boolean;
  risk_threshold: number;
  min_historical_approvals: number;
}

export const autoApprovalApi = {
  async getSettings(): Promise<AutoApprovalSettings> {
    try {
      const response = await fetch(`${API_V1}/auto-approval/settings`, {
        headers: {
          'x-tenant-id': 'default-tenant',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get auto-approval settings: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Error fetching auto-approval settings', { error });
      throw error;
    }
  },

  async updateSettings(update: AutoApprovalSettingsUpdate): Promise<AutoApprovalSettings> {
    try {
      const response = await fetch(`${API_V1}/auto-approval/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'x-tenant-id': 'default-tenant',
        },
        body: JSON.stringify(update),
      });

      if (!response.ok) {
        throw new Error(`Failed to update auto-approval settings: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Error updating auto-approval settings', { error });
      throw error;
    }
  },

  async getMetrics(): Promise<AutoApprovalMetrics> {
    try {
      const response = await fetch(`${API_V1}/auto-approval/metrics`, {
        headers: {
          'x-tenant-id': 'default-tenant',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get auto-approval metrics: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Error fetching auto-approval metrics', { error });
      throw error;
    }
  },

  async getDecisions(limit = 100): Promise<AutoApprovalDecision[]> {
    try {
      const response = await fetch(`${API_V1}/auto-approval/decisions?limit=${limit}`, {
        headers: {
          'x-tenant-id': 'default-tenant',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get auto-approval decisions: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Error fetching auto-approval decisions', { error });
      throw error;
    }
  },
};
