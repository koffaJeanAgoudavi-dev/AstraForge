export interface BackendProjectSpec {
  id: string;
  name: string;
  description: string;
  requirements: string[];
  status: string;
  created_at: string;
}

export interface BackendRun {
  id: number;
  project_id: string;
  stage: string;
  status: string;
  attempts: number;
  error: string | null;
  updated_at: string;
  started_at: string | null;
  cancel_requested: boolean;
  publish: boolean;
  deploy: boolean;
}

export interface BackendEvent {
  id: number;
  type: string;
  project_id: string;
  run_id: number | null;
  timestamp: string;
  stage: string;
  status: string;
  message: string | null;
  metadata?: Record<string, any>;
}

export interface BackendFilesResponse {
  project_id: string;
  files: string[];
}

export interface BackendFileContentResponse {
  project_id: string;
  path: string;
  content: string;
}

export interface BackendTestsResponse {
  project_id: string;
  run_id: number | null;
  tests: any[];
  tester_findings: string[];
  reviewer_findings: string[];
  repairs: any[];
}

export interface BackendBuildResponse {
  project_id: string;
  run_id: number;
  status: string;
  message?: string;
}

export interface BackendHealthStatus {
  isAvailable: boolean;
  url: string;
  error?: string;
  latencyMs?: number;
}
