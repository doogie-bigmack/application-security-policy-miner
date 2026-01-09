export interface SecretDetectionLog {
  id: number;
  repository_id: number;
  tenant_id: string | null;
  file_path: string;
  secret_type: string;
  description: string;
  line_number: number;
  preview: string;
  detected_at: string;
}
