export type AdvisoryStatus = "pending" | "reviewed" | "applied" | "rejected";

export interface TestCase {
  name: string;
  scenario: string;
  setup: string;
  input: Record<string, unknown>;
  expected_original: string;
  expected_refactored: string;
  assertion: string;
}

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
  test_cases: string | null;  // JSON string of TestCase[]
  status: AdvisoryStatus;
  created_at: string;
  reviewed_at: string | null;
}

export interface GenerateAdvisoryRequest {
  policy_id: number;
  target_platform?: string;
}
