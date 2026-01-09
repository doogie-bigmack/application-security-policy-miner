export type AdvisoryStatus = "pending" | "reviewed" | "applied" | "rejected";

export interface CodeAdvisory {
  id: number;
  policy_id: number;
  tenant_id: string;
  file_path: string;
  original_code: string;
  line_start: number;
  line_end: number;
  refactored_code: string;
  explanation: string;
  status: AdvisoryStatus;
  created_at: string;
  reviewed_at: string | null;
}

export interface GenerateAdvisoryRequest {
  policy_id: number;
  target_platform?: string;
}
