import { apiClient } from './client';
import {
  BackendProjectSpec,
  BackendBuildResponse,
  BackendRun,
  BackendFilesResponse,
  BackendFileContentResponse,
  BackendTestsResponse,
  BackendEvent,
} from './types';

export class ProjectsApi {
  /**
   * Save a project specification in FastAPI state_store
   */
  static async createProject(project: BackendProjectSpec): Promise<{ project: BackendProjectSpec }> {
    return apiClient.request<{ project: BackendProjectSpec }>('/projects', {
      method: 'POST',
      body: JSON.stringify(project),
    });
  }

  /**
   * Save project and queue a build in the backend durable worker
   */
  static async buildProject(
    project: BackendProjectSpec,
    publish = false,
    deploy = false
  ): Promise<BackendBuildResponse> {
    const params = new URLSearchParams({
      publish: String(publish),
      deploy: String(deploy),
    });
    return apiClient.request<BackendBuildResponse>(`/projects/build?${params.toString()}`, {
      method: 'POST',
      body: JSON.stringify(project),
    });
  }

  /**
   * Queue a new build on an existing project
   */
  static async buildExistingProject(
    projectId: string,
    publish = false,
    deploy = false
  ): Promise<BackendBuildResponse> {
    const params = new URLSearchParams({
      publish: String(publish),
      deploy: String(deploy),
    });
    return apiClient.request<BackendBuildResponse>(
      `/projects/${encodeURIComponent(projectId)}/build?${params.toString()}`,
      {
        method: 'POST',
      }
    );
  }

  /**
   * Retrieve project status and latest run metadata
   */
  static async getProject(
    projectId: string
  ): Promise<{ project: BackendProjectSpec; latest_run: BackendRun | null }> {
    return apiClient.request<{ project: BackendProjectSpec; latest_run: BackendRun | null }>(
      `/projects/${encodeURIComponent(projectId)}`
    );
  }

  /**
   * List runs for a project
   */
  static async listRuns(projectId: string, limit = 50): Promise<{ project_id: string; runs: BackendRun[] }> {
    return apiClient.request<{ project_id: string; runs: BackendRun[] }>(
      `/projects/${encodeURIComponent(projectId)}/runs?limit=${limit}`
    );
  }

  /**
   * Request cancellation of an active run
   */
  static async cancelRun(
    projectId: string,
    runId: number
  ): Promise<{ run_id: number; status: string }> {
    return apiClient.request<{ run_id: number; status: string }>(
      `/projects/${encodeURIComponent(projectId)}/runs/${runId}/cancel`,
      {
        method: 'POST',
      }
    );
  }

  /**
   * Resume a cancelled run
   */
  static async resumeRun(
    projectId: string,
    publish = false,
    deploy = false
  ): Promise<BackendBuildResponse> {
    const params = new URLSearchParams({
      publish: String(publish),
      deploy: String(deploy),
    });
    return apiClient.request<BackendBuildResponse>(
      `/projects/${encodeURIComponent(projectId)}/resume?${params.toString()}`,
      {
        method: 'POST',
      }
    );
  }

  /**
   * List files generated in the project workspace
   */
  static async getFiles(projectId: string): Promise<BackendFilesResponse> {
    return apiClient.request<BackendFilesResponse>(
      `/projects/${encodeURIComponent(projectId)}/files`
    );
  }

  /**
   * Read the real content of a generated file in the workspace
   */
  static async getFileContent(projectId: string, filePath: string): Promise<BackendFileContentResponse> {
    return apiClient.request<BackendFileContentResponse>(
      `/projects/${encodeURIComponent(projectId)}/files?path=${encodeURIComponent(filePath)}`
    );
  }

  /**
   * Fetch real sandbox test results, tester findings and reviewer findings
   */
  static async getTests(projectId: string): Promise<BackendTestsResponse> {
    return apiClient.request<BackendTestsResponse>(
      `/projects/${encodeURIComponent(projectId)}/tests`
    );
  }

  /**
   * Polling fallback for build events
   */
  static async getEvents(
    projectId: string,
    afterId = 0
  ): Promise<{ project_id: string; events: BackendEvent[] }> {
    return apiClient.request<{ project_id: string; events: BackendEvent[] }>(
      `/projects/${encodeURIComponent(projectId)}/events?after_id=${afterId}`
    );
  }
}
