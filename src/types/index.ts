export type ProjectType = 'web' | 'saas' | 'app';

export type ProjectStatus =
  | 'created'
  | 'planning'
  | 'building'
  | 'testing'
  | 'reviewing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ProjectSpec {
  id: string;
  name: string;
  description: string;
  requirements: string[];
  status: ProjectStatus;
  type: ProjectType;
  createdAt: string;
}

export type AgentRole = 'architect' | 'developer' | 'tester' | 'reviewer';

export interface AgentStageInfo {
  id: number;
  role: AgentRole;
  title: string;
  subtitle: string;
  status: 'idle' | 'queued' | 'running' | 'done' | 'failed';
  stateLabel: string;
  provider: string;
  durationMs?: number;
  details?: string;
  findings?: string;
}

export interface GeneratedFile {
  name: string;
  path: string;
  language: string;
  content: string;
  status: 'generated' | 'modified' | 'tested' | 'approved';
  sizeBytes: number;
}

export interface BuildLogEntry {
  id: string;
  timestamp: string;
  stage: string;
  role?: AgentRole;
  kind: 'cyan' | 'green' | 'amber' | 'red' | 'info';
  text: string;
  details?: string;
}

export interface TestResult {
  passed: boolean;
  attempts: number;
  stdout: string;
  stderr: string;
  testCount: number;
  failedCount: number;
  durationMs: number;
  findings: string[];
}

export interface ReviewFindings {
  approved: boolean;
  score: number;
  findings: string[];
  repairsApplied: number;
}

export interface DeploymentConfig {
  publishGithub: boolean;
  deployCloudflare: boolean;
  githubRepo?: string;
  cloudflareProject?: string;
  deploymentUrl?: string;
}

export interface ProviderProfile {
  role: AgentRole | 'general';
  preferredProviders: string[];
  temperature: number;
  model: string;
}
