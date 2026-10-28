import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { WebSocketServer } from 'ws';
import { optionalAuth, AuthRequest } from './src/middleware/auth.ts';
import { ProjectDatabaseService } from './src/server/services/projectService.ts';
import { BuildOrchestrator, wsClients } from './src/server/services/orchestrator.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);
const PORT = Number(process.env.PORT) || 3000;
const isProduction = process.env.NODE_ENV === 'production';

// Body parsers
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Optional Firebase authentication middleware
app.use('/api', optionalAuth);

// -----------------------------------------------------------------------------
// REST API Routes
// -----------------------------------------------------------------------------

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    app: 'AstraForge',
    version: '0.1.0',
    database: 'postgresql',
    mode: 'fullstack-service',
  });
});

// Create / update project
app.post('/api/projects', async (req, res) => {
  try {
    const { id, name, description, requirements, status, type } = req.body;
    if (!id || !name) {
      return res.status(400).json({ error: 'id and name are required' });
    }

    const project = await ProjectDatabaseService.upsertProject({
      id,
      name,
      description: description || '',
      requirements: requirements || [],
      status: status || 'created',
      type: type || 'web',
      userId: (req as AuthRequest).user?.dbUserId,
    });

    res.json({ project });
  } catch (err: any) {
    console.error('Failed to create project:', err);
    res.status(500).json({ error: err.message || 'Failed to create project' });
  }
});

// Build project (upsert spec & start run)
app.post('/api/projects/build', async (req, res) => {
  try {
    const { id, name, description, requirements, status, type } = req.body;
    if (!id || !name) {
      return res.status(400).json({ error: 'id and name are required' });
    }

    const publish = req.query.publish === 'true';
    const deploy = req.query.deploy === 'true';

    // 1. Upsert project
    await ProjectDatabaseService.upsertProject({
      id,
      name,
      description: description || '',
      requirements: requirements || [],
      status: 'building',
      type: type || 'web',
      userId: (req as AuthRequest).user?.dbUserId,
    });

    // 2. Create run
    const run = await ProjectDatabaseService.createRun(id, publish, deploy);

    // 3. Start orchestrator
    BuildOrchestrator.startPipeline(id, run.id, { publish, deploy });

    res.json({
      project_id: id,
      run_id: run.id,
      status: 'queued',
      message: 'Build queued successfully in database orchestrator',
    });
  } catch (err: any) {
    console.error('Failed to start build:', err);
    res.status(500).json({ error: err.message || 'Failed to queue build' });
  }
});

// Build existing project
app.post('/api/projects/:projectId/build', async (req, res) => {
  try {
    const { projectId } = req.params;
    const publish = req.query.publish === 'true';
    const deploy = req.query.deploy === 'true';

    const projData = await ProjectDatabaseService.getProjectWithLatestRun(projectId);
    if (!projData) {
      return res.status(404).json({ error: 'Project not found' });
    }

    const run = await ProjectDatabaseService.createRun(projectId, publish, deploy);
    BuildOrchestrator.startPipeline(projectId, run.id, { publish, deploy });

    res.json({
      project_id: projectId,
      run_id: run.id,
      status: 'queued',
      message: 'Build queued successfully',
    });
  } catch (err: any) {
    console.error('Failed to build project:', err);
    res.status(500).json({ error: err.message || 'Failed to trigger build' });
  }
});

// Get project details + latest run
app.get('/api/projects/:projectId', async (req, res) => {
  try {
    const { projectId } = req.params;
    const result = await ProjectDatabaseService.getProjectWithLatestRun(projectId);
    if (!result) {
      return res.status(404).json({ error: 'Project not found' });
    }
    res.json(result);
  } catch (err: any) {
    console.error('Failed to get project:', err);
    res.status(500).json({ error: err.message || 'Failed to retrieve project' });
  }
});

// List runs for a project
app.get('/api/projects/:projectId/runs', async (req, res) => {
  try {
    const { projectId } = req.params;
    const limit = Number(req.query.limit) || 50;
    const runsList = await ProjectDatabaseService.listRuns(projectId, limit);
    res.json({ project_id: projectId, runs: runsList });
  } catch (err: any) {
    console.error('Failed to list runs:', err);
    res.status(500).json({ error: err.message || 'Failed to list runs' });
  }
});

// Cancel run
app.post('/api/projects/:projectId/runs/:runId/cancel', async (req, res) => {
  try {
    const { projectId, runId } = req.params;
    const run = await ProjectDatabaseService.cancelRun(projectId, Number(runId));
    if (!run) {
      return res.status(404).json({ error: 'Run not found' });
    }
    res.json({ run_id: run.id, status: 'cancelled' });
  } catch (err: any) {
    console.error('Failed to cancel run:', err);
    res.status(500).json({ error: err.message || 'Failed to cancel run' });
  }
});

// Resume run
app.post('/api/projects/:projectId/resume', async (req, res) => {
  try {
    const { projectId } = req.params;
    const publish = req.query.publish === 'true';
    const deploy = req.query.deploy === 'true';

    const run = await ProjectDatabaseService.createRun(projectId, publish, deploy);
    BuildOrchestrator.startPipeline(projectId, run.id, { publish, deploy });

    res.json({
      project_id: projectId,
      run_id: run.id,
      status: 'queued',
      message: 'Run resumed successfully',
    });
  } catch (err: any) {
    console.error('Failed to resume run:', err);
    res.status(500).json({ error: err.message || 'Failed to resume run' });
  }
});

// Get files or specific file content
app.get('/api/projects/:projectId/files', async (req, res) => {
  try {
    const { projectId } = req.params;
    const filePath = req.query.path as string | undefined;

    if (filePath) {
      const content = await ProjectDatabaseService.getFileContent(projectId, filePath);
      if (content === null) {
        return res.status(404).json({ error: 'File not found' });
      }
      return res.json({ project_id: projectId, path: filePath, content });
    }

    const files = await ProjectDatabaseService.getFiles(projectId);
    res.json({ project_id: projectId, files });
  } catch (err: any) {
    console.error('Failed to get files:', err);
    res.status(500).json({ error: err.message || 'Failed to get files' });
  }
});

// Get test results
app.get('/api/projects/:projectId/tests', async (req, res) => {
  try {
    const { projectId } = req.params;
    const tests = await ProjectDatabaseService.getTests(projectId);
    res.json(tests);
  } catch (err: any) {
    console.error('Failed to get tests:', err);
    res.status(500).json({ error: err.message || 'Failed to get tests' });
  }
});

// Get events (polling fallback)
app.get('/api/projects/:projectId/events', async (req, res) => {
  try {
    const { projectId } = req.params;
    const afterId = Number(req.query.after_id) || 0;
    const eventsList = await ProjectDatabaseService.getEvents(projectId, afterId);
    res.json({ project_id: projectId, events: eventsList });
  } catch (err: any) {
    console.error('Failed to get events:', err);
    res.status(500).json({ error: err.message || 'Failed to get events' });
  }
});

// -----------------------------------------------------------------------------
// WebSocket Server for Live Event Streaming
// -----------------------------------------------------------------------------
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const url = new URL(request.url || '', `http://${request.headers.host}`);
  // Match /projects/:id/events or /api/projects/:id/events
  const match = url.pathname.match(/^(?:\/api)?\/projects\/([^/]+)\/events/);
  if (match) {
    const projectId = decodeURIComponent(match[1]);
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request, projectId);
    });
  } else {
    socket.destroy();
  }
});

wss.on('connection', (ws: any, request: any, projectId: string) => {
  if (!wsClients.has(projectId)) {
    wsClients.set(projectId, new Set());
  }
  const set = wsClients.get(projectId)!;
  set.add(ws);

  ws.on('close', () => {
    set.delete(ws);
    if (set.size === 0) {
      wsClients.delete(projectId);
    }
  });

  ws.on('error', (err: any) => {
    console.warn(`WebSocket error for project ${projectId}:`, err);
  });
});

// -----------------------------------------------------------------------------
// Vite Frontend Integration
// -----------------------------------------------------------------------------
async function setupFrontend() {
  if (!isProduction) {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(distPath, 'index.html'));
    });
  }
}

setupFrontend().then(() => {
  server.listen(PORT, '0.0.0.0', () => {
    console.log(`[AstraForge Server] Listening on http://0.0.0.0:${PORT}`);
  });
});
