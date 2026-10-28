/**
 * Cloudflare Pages Functions: Reverse Proxy for AstraForge API
 * Route: /api/*
 *
 * Transmits /api/* requests to the FastAPI backend on Render while keeping
 * ASTRAFORGE_API_KEY secure on the server side (injected into X-AstraForge-Key).
 *
 * Production reference: HTTP Event Polling via GET /api/projects/{id}/events?after_id=
 * is the official, guaranteed delivery channel for build events on Cloudflare Pages.
 */

export interface Env {
  ASTRAFORGE_BACKEND_URL?: string;
  ASTRAFORGE_API_KEY?: string;
  ALLOW_TEST_ORIGIN?: string;
}

export interface PagesContext {
  request: Request;
  env: Env;
  params: {
    path?: string | string[];
  };
}

export const ALLOWED_BACKEND_ORIGIN = "https://astraforge-backend-7t9l.onrender.com";

// Standard HTTP hop-by-hop headers to strip
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "host",
]);

/**
 * Validates and strictly restricts backend URL to the authorized Render origin
 */
export function validateBackendOrigin(urlStr: string, allowTestOrigin = false): URL {
  const parsed = new URL(urlStr);

  if (parsed.origin !== ALLOWED_BACKEND_ORIGIN) {
    if (allowTestOrigin && (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost")) {
      return parsed;
    }
    throw new Error(`Unauthorized backend origin: ${parsed.origin}`);
  }

  return parsed;
}

/**
 * Validates and sanitizes relative subpaths to prevent path traversal,
 * double encodings, backslashes, null bytes, and ambiguous sequences.
 */
export function sanitizePath(rawPath: string): string {
  // Reject raw null bytes or encoded null bytes
  if (rawPath.includes("\0") || rawPath.includes("%00")) {
    throw new Error("Invalid null byte in path");
  }

  // Reject backslashes and encoded backslashes
  if (rawPath.includes("\\") || rawPath.toLowerCase().includes("%5c")) {
    throw new Error("Invalid backslash in path");
  }

  // Decode URI component defensively (recursively handling double-encoding like %252e)
  let decoded = rawPath;
  for (let i = 0; i < 3; i++) {
    try {
      const next = decodeURIComponent(decoded);
      if (next === decoded) break;
      decoded = next;
    } catch {
      throw new Error("Malformed URI encoding in path");
    }
  }

  // Reject null bytes or backslashes if revealed after decoding
  if (decoded.includes("\0") || decoded.includes("\\")) {
    throw new Error("Invalid character sequence after decode");
  }

  const segments = decoded.trim().split("/").filter(Boolean);

  // Validate each segment
  for (const seg of segments) {
    const lower = seg.toLowerCase();
    if (seg === ".." || seg === "." || lower.includes("%2e") || lower.includes("..")) {
      throw new Error("Invalid path traversal sequence");
    }
  }

  return segments.join("/");
}

/**
 * Filter headers: removes hop-by-hop headers and strips any client-provided x-astraforge-key
 */
export function buildForwardHeaders(
  incomingHeaders: Headers,
  apiKey?: string,
  isWebSocket = false
): Headers {
  const headers = new Headers();

  for (const [key, value] of incomingHeaders.entries()) {
    const lowerKey = key.toLowerCase();

    // Skip hop-by-hop headers (unless Upgrade for websocket)
    if (HOP_BY_HOP_HEADERS.has(lowerKey)) {
      continue;
    }

    // Strip client-supplied secret to avoid spoofing
    if (lowerKey === "x-astraforge-key") {
      continue;
    }

    headers.set(key, value);
  }

  // Inject backend authorization key server-side
  if (apiKey) {
    headers.set("X-AstraForge-Key", apiKey);
  }

  if (isWebSocket) {
    headers.set("Upgrade", "websocket");
  }

  return headers;
}

/**
 * Main Cloudflare Pages Function entry point for /api/*
 */
export async function onRequest(context: PagesContext): Promise<Response> {
  const { request, env } = context;

  // 1. Strict validation of backend origin (anti-open proxy)
  const rawBackendUrl = env.ASTRAFORGE_BACKEND_URL || ALLOWED_BACKEND_ORIGIN;
  const allowTestOrigin =
    env.ALLOW_TEST_ORIGIN === "true" ||
    (typeof globalThis !== "undefined" && (globalThis as any).process?.env?.NODE_ENV === "test");
  let backendOrigin: URL;
  try {
    backendOrigin = validateBackendOrigin(rawBackendUrl, allowTestOrigin);
  } catch {
    return new Response(
      JSON.stringify({
        detail: "Configuration error: unauthorized backend origin",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 2. Parse and sanitize incoming URL and path
  const incomingUrl = new URL(request.url);
  const pathname = incomingUrl.pathname;

  // Strip leading /api prefix
  if (!pathname.startsWith("/api")) {
    return new Response(
      JSON.stringify({
        detail: "Not Found: Path must begin with /api",
      }),
      {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  const subPath = pathname.substring(4); // remove '/api'
  let cleanSubPath = "";
  try {
    cleanSubPath = sanitizePath(subPath);
  } catch {
    return new Response(
      JSON.stringify({
        detail: "Bad Request: Malformed or disallowed path",
      }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 3. Security: Check if ASTRAFORGE_API_KEY is missing on protected routes
  const isPublicRoute = cleanSubPath === "health";
  if (!isPublicRoute && !env.ASTRAFORGE_API_KEY) {
    return new Response(
      JSON.stringify({
        detail: "Service Unavailable: ASTRAFORGE_API_KEY is not configured in Cloudflare environment secrets",
        error: "missing_server_secret",
      }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 4. Construct target destination URL
  const targetUrl = new URL(
    cleanSubPath ? `${backendOrigin.pathname.replace(/\/+$/, "")}/${cleanSubPath}` : backendOrigin.pathname,
    backendOrigin.origin
  );

  // Copy query parameters
  targetUrl.search = incomingUrl.search;

  // 5. Check for WebSocket upgrade
  // NOTE: WebSocket relay on Pages Functions to third-party hosts is best-effort.
  // The client automatically falls back to HTTP event polling (/events?after_id=).
  const isWebSocket = request.headers.get("Upgrade")?.toLowerCase() === "websocket";

  if (isWebSocket && env.ASTRAFORGE_API_KEY && cleanSubPath.includes("events")) {
    targetUrl.searchParams.set("token", env.ASTRAFORGE_API_KEY);
  }

  // 6. Build forwarded headers with secure X-AstraForge-Key injection
  const forwardHeaders = buildForwardHeaders(request.headers, env.ASTRAFORGE_API_KEY, isWebSocket);

  // 7. Prepare fetch options with 30s timeout
  const isBodyAllowed = request.method !== "GET" && request.method !== "HEAD";
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const fetchInit: RequestInit & { duplex?: string } = {
      method: request.method,
      headers: forwardHeaders,
      body: isBodyAllowed ? request.body : undefined,
      redirect: "manual",
      signal: controller.signal,
      duplex: isBodyAllowed && request.body ? "half" : undefined,
    };

    const backendResponse = await fetch(targetUrl.toString(), fetchInit);
    clearTimeout(timeoutId);

    // If WebSocket upgrade response
    if (isWebSocket && backendResponse.status === 101) {
      return backendResponse;
    }

    // Build response headers, removing any potential leaked internal headers
    const responseHeaders = new Headers(backendResponse.headers);
    responseHeaders.delete("x-astraforge-key");

    return new Response(backendResponse.body, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: responseHeaders,
    });
  } catch (err: any) {
    clearTimeout(timeoutId);

    if (err.name === "AbortError") {
      return new Response(
        JSON.stringify({
          detail: "Gateway Timeout: Backend did not respond within 30s",
        }),
        {
          status: 504,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response(
      JSON.stringify({
        detail: "Bad Gateway: Failed to reach backend service",
      }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
