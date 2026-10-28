import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {
  onRequest,
  sanitizePath,
  buildForwardHeaders,
  validateBackendOrigin,
  ALLOWED_BACKEND_ORIGIN,
} from '../functions/api/[[path]].ts';

describe('Cloudflare Pages Functions Proxy Suite (/api/*)', () => {
  let mockServer: http.Server;
  let mockServerPort: number;
  let receivedRequests: Array<{
    method: string;
    url: string;
    headers: http.IncomingHttpHeaders;
    body: string;
  }> = [];

  before(async () => {
    // Start local mock backend server to test proxy routing, headers, and security
    await new Promise<void>((resolve) => {
      mockServer = http.createServer((req, res) => {
        let body = '';
        req.on('data', (chunk) => {
          body += chunk;
        });
        req.on('end', () => {
          receivedRequests.push({
            method: req.method || 'GET',
            url: req.url || '/',
            headers: req.headers,
            body,
          });

          if (req.url === '/health') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'ok', app: 'AstraForge', version: '0.1.0' }));
          } else if (req.url === '/simulate-401') {
            res.writeHead(401, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ detail: 'Invalid or missing AstraForge API key' }));
          } else if (req.url === '/simulate-500') {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ detail: 'Internal Server Error' }));
          } else if (req.url?.startsWith('/projects/build')) {
            if (!req.headers['x-astraforge-key']) {
              res.writeHead(401, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ detail: 'Invalid or missing AstraForge API key' }));
            } else {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ project_id: 'proj-123', run_id: 1, status: 'queued' }));
            }
          } else if (req.url?.includes('/events')) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ project_id: 'proj-123', events: [] }));
          } else {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ detail: 'Not Found' }));
          }
        });
      });

      mockServer.listen(0, '127.0.0.1', () => {
        const address = mockServer.address() as any;
        mockServerPort = address.port;
        resolve();
      });
    });
  });

  after(() => {
    mockServer?.close();
  });

  const getMockEnv = (overrides = {}) => ({
    ASTRAFORGE_BACKEND_URL: `http://127.0.0.1:${mockServerPort}`,
    ASTRAFORGE_API_KEY: 'test-secret-key-123',
    ALLOW_TEST_ORIGIN: 'true',
    ...overrides,
  });

  // Test 1: GET /api/health
  it('1. should transmit GET /api/health to backend /health and strip /api prefix', async () => {
    receivedRequests = [];
    const request = new Request('http://localhost:3000/api/health', {
      method: 'GET',
    });

    const response = await onRequest({
      request,
      env: getMockEnv(),
      params: { path: 'health' },
    });

    assert.equal(response.status, 200);
    const data = (await response.json()) as any;
    assert.equal(data.status, 'ok');
    assert.equal(data.app, 'AstraForge');
    assert.equal(receivedRequests.length, 1);
    assert.equal(receivedRequests[0].url, '/health');
  });

  // Test 2: Methods & Query parameters transmission
  it('2. should transmit GET & POST methods and query parameters faithfully', async () => {
    receivedRequests = [];
    const request = new Request('http://localhost:3000/api/projects/build?publish=false&deploy=true', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Test App' }),
    });

    const response = await onRequest({
      request,
      env: getMockEnv(),
      params: { path: ['projects', 'build'] },
    });

    assert.equal(response.status, 200);
    assert.equal(receivedRequests.length, 1);
    assert.equal(receivedRequests[0].method, 'POST');
    assert.equal(receivedRequests[0].url, '/projects/build?publish=false&deploy=true');
  });

  // Test 3: JSON body transmission
  it('3. should correctly transmit JSON request body', async () => {
    receivedRequests = [];
    const payload = { id: 'p-1', name: 'SaaS App', requirements: ['Auth', 'DB'] };
    const request = new Request('http://localhost:3000/api/projects/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    await onRequest({
      request,
      env: getMockEnv(),
      params: { path: ['projects', 'build'] },
    });

    assert.equal(receivedRequests.length, 1);
    const parsedBody = JSON.parse(receivedRequests[0].body);
    assert.deepEqual(parsedBody, payload);
  });

  // Test 4: Injection of X-AstraForge-Key server-side and stripping hop-by-hop headers
  it('4. should inject X-AstraForge-Key server-side and strip hop-by-hop and client spoofing headers', async () => {
    const clientHeaders = new Headers({
      'Content-Type': 'application/json',
      'X-Custom-Client-Header': 'ok',
      'X-AstraForge-Key': 'attacker-client-key',
      Connection: 'keep-alive',
      'Keep-Alive': 'timeout=5',
      'Transfer-Encoding': 'chunked',
    });

    const forwardHeaders = buildForwardHeaders(clientHeaders, 'server-verified-secret');

    // Must be the server secret, not the client spoofed secret
    assert.equal(forwardHeaders.get('x-astraforge-key'), 'server-verified-secret');
    assert.equal(forwardHeaders.get('x-custom-client-header'), 'ok');
    // Hop-by-hop headers must be stripped
    assert.equal(forwardHeaders.get('connection'), null);
    assert.equal(forwardHeaders.get('keep-alive'), null);
    assert.equal(forwardHeaders.get('transfer-encoding'), null);
  });

  // Test 5: Missing secret handling (503 on protected routes, 200 on public /health)
  it('5. should keep /health accessible but return 503 on protected routes when secret is missing', async () => {
    // 5a. GET /api/health must remain accessible without secret
    const healthReq = new Request('http://localhost:3000/api/health', { method: 'GET' });
    const healthRes = await onRequest({
      request: healthReq,
      env: getMockEnv({ ASTRAFORGE_API_KEY: undefined }),
      params: { path: 'health' },
    });
    assert.equal(healthRes.status, 200);

    // 5b. POST /api/projects/build must return 503 Service Unavailable when secret is missing
    const buildReq = new Request('http://localhost:3000/api/projects/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'No Secret App' }),
    });
    const buildRes = await onRequest({
      request: buildReq,
      env: getMockEnv({ ASTRAFORGE_API_KEY: undefined }),
      params: { path: ['projects', 'build'] },
    });
    assert.equal(buildRes.status, 503);
    const errorBody = (await buildRes.json()) as any;
    assert.equal(errorBody.error, 'missing_server_secret');
  });

  // Test 6: No secret leakage in responses or logs
  it('6. should never leak the API key in response headers or response body', async () => {
    const SECRET = 'SUPER_SECRET_VALUE_999';
    const request = new Request('http://localhost:3000/api/health', {
      method: 'GET',
    });

    const response = await onRequest({
      request,
      env: getMockEnv({ ASTRAFORGE_API_KEY: SECRET }),
      params: { path: 'health' },
    });

    assert.equal(response.headers.get('x-astraforge-key'), null);
    const text = await response.text();
    assert.equal(text.includes(SECRET), false);
  });

  // Test 7: Handling HTTP 401, 404, 500 and network errors
  it('7. should pass through 401, 404, 500 response codes faithfully and return 502 on network down', async () => {
    const res401 = await onRequest({
      request: new Request('http://localhost:3000/api/simulate-401'),
      env: getMockEnv(),
      params: { path: 'simulate-401' },
    });
    assert.equal(res401.status, 401);

    const res404 = await onRequest({
      request: new Request('http://localhost:3000/api/simulate-404-nonexistent'),
      env: getMockEnv(),
      params: { path: 'simulate-404-nonexistent' },
    });
    assert.equal(res404.status, 404);

    const res500 = await onRequest({
      request: new Request('http://localhost:3000/api/simulate-500'),
      env: getMockEnv(),
      params: { path: 'simulate-500' },
    });
    assert.equal(res500.status, 500);

    const resNetError = await onRequest({
      request: new Request('http://localhost:3000/api/health'),
      env: getMockEnv({ ASTRAFORGE_BACKEND_URL: 'http://127.0.0.1:59999' }),
      params: { path: 'health' },
    });
    assert.equal(resNetError.status, 502);
  });

  // Test 8: Protection against path traversal, null bytes, backslashes, and double encodings
  it('8. should reject path traversal, null bytes, backslashes, and double encodings with 400 Bad Request', async () => {
    // Unit tests on sanitizePath
    assert.throws(() => sanitizePath('../admin'), /Invalid path traversal sequence/);
    assert.throws(() => sanitizePath('projects/../../etc/passwd'), /Invalid path traversal sequence/);
    assert.throws(() => sanitizePath('projects/%2e%2e/test'), /Invalid path traversal sequence/);
    assert.throws(() => sanitizePath('projects/%252e%252e/test'), /Invalid path traversal sequence/);
    assert.throws(() => sanitizePath('projects\\build'), /Invalid backslash in path/);
    assert.throws(() => sanitizePath('projects%5cbuild'), /Invalid backslash in path/);
    assert.throws(() => sanitizePath('projects\0build'), /Invalid null byte in path/);
    assert.throws(() => sanitizePath('projects%00build'), /Invalid null byte in path/);

    // Legitimate paths must be preserved cleanly
    assert.equal(sanitizePath('/health'), 'health');
    assert.equal(sanitizePath('/projects/build'), 'projects/build');
    assert.equal(sanitizePath('/projects/123/events'), 'projects/123/events');

    // Request with backslash traversal must return 400
    const reqBackslash = new Request('http://localhost:3000/api/%5c..%5csecrets', { method: 'GET' });
    const resBackslash = await onRequest({
      request: reqBackslash,
      env: getMockEnv(),
      params: { path: '%5c..%5csecrets' },
    });
    assert.equal(resBackslash.status, 400);

    // Request not starting with /api must return 404
    const reqNonApi = new Request('http://localhost:3000/other/path', { method: 'GET' });
    const resNonApi = await onRequest({
      request: reqNonApi,
      env: getMockEnv(),
      params: { path: 'path' },
    });
    assert.equal(resNonApi.status, 404);
  });

  // Test 9: Strict restriction of backend origin
  it('9. should strictly restrict backend origin to ALLOWED_BACKEND_ORIGIN and reject unauthorized targets', async () => {
    // 9a. Authorized origin matches Render target
    assert.equal(ALLOWED_BACKEND_ORIGIN, 'https://astraforge-backend-7t9l.onrender.com');
    const validOrigin = validateBackendOrigin(ALLOWED_BACKEND_ORIGIN);
    assert.equal(validOrigin.origin, 'https://astraforge-backend-7t9l.onrender.com');

    // 9b. Arbitrary target must be rejected
    assert.throws(
      () => validateBackendOrigin('https://evil-attacker-site.com'),
      /Unauthorized backend origin/
    );

    // 9c. Request targeting unauthorized backend returns 500 configuration error
    const resForbidden = await onRequest({
      request: new Request('http://localhost:3000/api/health', { method: 'GET' }),
      env: {
        ASTRAFORGE_BACKEND_URL: 'https://malicious-external-proxy.com',
        ALLOW_TEST_ORIGIN: 'false',
      },
      params: { path: 'health' },
    });
    assert.equal(resForbidden.status, 500);
    const errBody = (await resForbidden.json()) as any;
    assert.equal(errBody.detail, 'Configuration error: unauthorized backend origin');
  });

  // Test 10: Event polling & WebSocket headers
  it('10. should support HTTP event polling with after_id and build WebSocket headers securely', async () => {
    receivedRequests = [];
    const request = new Request('http://localhost:3000/api/projects/proj-123/events?after_id=42', {
      method: 'GET',
    });

    const response = await onRequest({
      request,
      env: getMockEnv(),
      params: { path: ['projects', 'proj-123', 'events'] },
    });

    assert.equal(response.status, 200);
    assert.equal(receivedRequests.length, 1);
    assert.equal(receivedRequests[0].url, '/projects/proj-123/events?after_id=42');

    // WebSocket headers construction unit test
    const wsHeaders = new Headers({
      Upgrade: 'websocket',
      Connection: 'Upgrade',
    });

    const forwarded = buildForwardHeaders(wsHeaders, 'secret-key-xyz', true);
    assert.equal(forwarded.get('upgrade'), 'websocket');
    assert.equal(forwarded.get('x-astraforge-key'), 'secret-key-xyz');
    assert.equal(forwarded.get('connection'), null); // hop-by-hop stripped
  });
});
