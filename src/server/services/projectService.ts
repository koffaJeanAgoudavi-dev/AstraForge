import { desc, eq, and, gt } from 'drizzle-orm';
import { db } from '../../db/index.ts';
import { projects, runs, events, projectFiles, testReports } from '../../db/schema.ts';

export class ProjectDatabaseService {
  /**
   * Create or update project spec
   */
  static async upsertProject(data: {
    id: string;
    name: string;
    description: string;
    requirements: string[];
    status?: string;
    type?: string;
    userId?: number;
  }) {
    const requirementsJson = JSON.stringify(data.requirements || []);
    const existing = await db
      .select()
      .from(projects)
      .where(eq(projects.id, data.id))
      .limit(1);

    if (existing.length > 0) {
      const [updated] = await db
        .update(projects)
        .set({
          name: data.name,
          description: data.description,
          requirements: requirementsJson,
          status: data.status || existing[0].status,
          type: data.type || existing[0].type,
          updatedAt: new Date(),
        })
        .where(eq(projects.id, data.id))
        .returning();
      return {
        ...updated,
        requirements: JSON.parse(updated.requirements),
      };
    }

    const [created] = await db
      .insert(projects)
      .values({
        id: data.id,
        name: data.name,
        description: data.description,
        requirements: requirementsJson,
        status: data.status || 'created',
        type: data.type || 'web',
        userId: data.userId || null,
      })
      .returning();

    return {
      ...created,
      requirements: JSON.parse(created.requirements),
    };
  }

  /**
   * Get project by ID and latest run
   */
  static async getProjectWithLatestRun(projectId: string) {
    const projectList = await db
      .select()
      .from(projects)
      .where(eq(projects.id, projectId))
      .limit(1);

    if (projectList.length === 0) {
      return null;
    }

    const proj = projectList[0];
    const latestRuns = await db
      .select()
      .from(runs)
      .where(eq(runs.projectId, projectId))
      .orderBy(desc(runs.id))
      .limit(1);

    const latestRun = latestRuns[0] || null;

    return {
      project: {
        id: proj.id,
        name: proj.name,
        description: proj.description,
        requirements: JSON.parse(proj.requirements || '[]'),
        status: proj.status,
        created_at: proj.createdAt?.toISOString() || new Date().toISOString(),
      },
      latest_run: latestRun
        ? {
            id: latestRun.id,
            project_id: latestRun.projectId,
            stage: latestRun.stage,
            status: latestRun.status,
            attempts: latestRun.attempts,
            error: latestRun.error,
            updated_at: latestRun.updatedAt?.toISOString() || new Date().toISOString(),
            started_at: latestRun.startedAt?.toISOString() || null,
            cancel_requested: latestRun.cancelRequested,
            publish: latestRun.publish,
            deploy: latestRun.deploy,
          }
        : null,
    };
  }

  /**
   * List runs for a project
   */
  static async listRuns(projectId: string, limit = 50) {
    const rows = await db
      .select()
      .from(runs)
      .where(eq(runs.projectId, projectId))
      .orderBy(desc(runs.id))
      .limit(limit);

    return rows.map((r) => ({
      id: r.id,
      project_id: r.projectId,
      stage: r.stage,
      status: r.status,
      attempts: r.attempts,
      error: r.error,
      updated_at: r.updatedAt?.toISOString() || new Date().toISOString(),
      started_at: r.startedAt?.toISOString() || null,
      cancel_requested: r.cancelRequested,
      publish: r.publish,
      deploy: r.deploy,
    }));
  }

  /**
   * Create a new run
   */
  static async createRun(projectId: string, publish = false, deploy = false) {
    const [run] = await db
      .insert(runs)
      .values({
        projectId,
        stage: 'architect',
        status: 'queued',
        attempts: 1,
        publish,
        deploy,
        cancelRequested: false,
      })
      .returning();

    await db
      .update(projects)
      .set({ status: 'building', updatedAt: new Date() })
      .where(eq(projects.id, projectId));

    return run;
  }

  /**
   * Request run cancellation
   */
  static async cancelRun(projectId: string, runId: number) {
    const [run] = await db
      .update(runs)
      .set({
        cancelRequested: true,
        status: 'cancelled',
        updatedAt: new Date(),
      })
      .where(and(eq(runs.id, runId), eq(runs.projectId, projectId)))
      .returning();

    await db
      .update(projects)
      .set({ status: 'created', updatedAt: new Date() })
      .where(eq(projects.id, projectId));

    return run;
  }

  /**
   * Log an event
   */
  static async addEvent(data: {
    projectId: string;
    runId: number;
    type: string;
    stage: string;
    status: string;
    message: string;
    metadata?: any;
  }) {
    const [ev] = await db
      .insert(events)
      .values({
        projectId: data.projectId,
        runId: data.runId,
        type: data.type,
        stage: data.stage,
        status: data.status,
        message: data.message,
        metadata: data.metadata ? JSON.stringify(data.metadata) : null,
      })
      .returning();

    return {
      id: ev.id,
      type: ev.type,
      project_id: ev.projectId,
      run_id: ev.runId,
      timestamp: ev.createdAt?.toISOString() || new Date().toISOString(),
      stage: ev.stage,
      status: ev.status,
      message: ev.message,
      metadata: ev.metadata ? JSON.parse(ev.metadata) : undefined,
    };
  }

  /**
   * Get events after an ID
   */
  static async getEvents(projectId: string, afterId = 0) {
    const condition =
      afterId > 0
        ? and(eq(events.projectId, projectId), gt(events.id, afterId))
        : eq(events.projectId, projectId);

    const rows = await db
      .select()
      .from(events)
      .where(condition)
      .orderBy(events.id)
      .limit(100);

    return rows.map((ev) => ({
      id: ev.id,
      type: ev.type,
      project_id: ev.projectId,
      run_id: ev.runId,
      timestamp: ev.createdAt?.toISOString() || new Date().toISOString(),
      stage: ev.stage,
      status: ev.status,
      message: ev.message,
      metadata: ev.metadata ? JSON.parse(ev.metadata) : undefined,
    }));
  }

  /**
   * Save or update project files
   */
  static async saveProjectFile(projectId: string, path: string, content: string) {
    const existing = await db
      .select()
      .from(projectFiles)
      .where(and(eq(projectFiles.projectId, projectId), eq(projectFiles.path, path)))
      .limit(1);

    if (existing.length > 0) {
      const [updated] = await db
        .update(projectFiles)
        .set({ content, updatedAt: new Date() })
        .where(eq(projectFiles.id, existing[0].id))
        .returning();
      return updated;
    }

    const [created] = await db
      .insert(projectFiles)
      .values({
        projectId,
        path,
        content,
      })
      .returning();

    return created;
  }

  /**
   * List files for a project
   */
  static async getFiles(projectId: string) {
    const rows = await db
      .select({ path: projectFiles.path })
      .from(projectFiles)
      .where(eq(projectFiles.projectId, projectId));

    return rows.map((r) => r.path);
  }

  /**
   * Get specific file content
   */
  static async getFileContent(projectId: string, filePath: string) {
    const rows = await db
      .select()
      .from(projectFiles)
      .where(and(eq(projectFiles.projectId, projectId), eq(projectFiles.path, filePath)))
      .limit(1);

    if (rows.length === 0) {
      return null;
    }

    return rows[0].content;
  }

  /**
   * Save test report
   */
  static async saveTestReport(data: {
    projectId: string;
    runId: number;
    tests: any[];
    testerFindings: string[];
    reviewerFindings: string[];
    repairs?: any[];
  }) {
    const [report] = await db
      .insert(testReports)
      .values({
        projectId: data.projectId,
        runId: data.runId,
        testsJson: JSON.stringify(data.tests),
        testerFindings: JSON.stringify(data.testerFindings),
        reviewerFindings: JSON.stringify(data.reviewerFindings),
        repairsJson: JSON.stringify(data.repairs || []),
      })
      .returning();

    return report;
  }

  /**
   * Get tests report for project
   */
  static async getTests(projectId: string) {
    const rows = await db
      .select()
      .from(testReports)
      .where(eq(testReports.projectId, projectId))
      .orderBy(desc(testReports.id))
      .limit(1);

    if (rows.length === 0) {
      return {
        project_id: projectId,
        run_id: null,
        tests: [],
        tester_findings: [],
        reviewer_findings: [],
        repairs: [],
      };
    }

    const r = rows[0];
    return {
      project_id: r.projectId,
      run_id: r.runId,
      tests: JSON.parse(r.testsJson || '[]'),
      tester_findings: JSON.parse(r.testerFindings || '[]'),
      reviewer_findings: JSON.parse(r.reviewerFindings || '[]'),
      repairs: JSON.parse(r.repairsJson || '[]'),
    };
  }
}
