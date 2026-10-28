import { BackendEvent } from './types';
import { apiClient } from './client';
import { ProjectsApi } from './projects';

export interface EventSubscriptionOptions {
  projectId: string;
  onEvent: (event: BackendEvent) => void;
  onError?: (err: any) => void;
  onComplete?: () => void;
}

/**
 * EventsService: Realtime build events subscriber
 *
 * PRODUCTION NOTE:
 * On Cloudflare Pages, WebSocket connections to third-party endpoints (Render)
 * are best-effort. The automatic HTTP event polling mechanism (/events?after_id=)
 * implemented below serves as the production reference delivery channel,
 * ensuring zero dropped events and reliable streaming during builds.
 */
export class EventsService {
  /**
   * Subscribe to live events for a project via WebSocket with automatic HTTP polling fallback
   */
  static subscribe({
    projectId,
    onEvent,
    onError,
    onComplete,
  }: EventSubscriptionOptions): () => void {
    let isCancelled = false;
    let socket: WebSocket | null = null;
    let pollingTimer: any = null;
    let lastEventId = 0;

    // Convert HTTP baseUrl to WS url
    const baseUrl = apiClient.getBaseUrl();
    let wsUrl = '';

    if (baseUrl.startsWith('http://')) {
      wsUrl = baseUrl.replace('http://', 'ws://');
    } else if (baseUrl.startsWith('https://')) {
      wsUrl = baseUrl.replace('https://', 'wss://');
    } else {
      // Relative path like '/api'
      const loc = window.location;
      const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${proto}//${loc.host}${baseUrl}`;
    }

    const wsFullUrl = `${wsUrl}/projects/${encodeURIComponent(projectId)}/events`;

    const startPolling = () => {
      if (isCancelled) return;

      const poll = async () => {
        if (isCancelled) return;
        try {
          const res = await ProjectsApi.getEvents(projectId, lastEventId);
          for (const ev of res.events) {
            lastEventId = Math.max(lastEventId, ev.id);
            onEvent(ev);
            if (['completed', 'failed', 'cancelled'].includes(ev.status)) {
              onComplete?.();
              return;
            }
          }
        } catch (e) {
          onError?.(e);
        }
        if (!isCancelled) {
          pollingTimer = setTimeout(poll, 1200);
        }
      };

      poll();
    };

    try {
      socket = new WebSocket(wsFullUrl);

      socket.onmessage = (event) => {
        if (isCancelled) return;
        try {
          const data = JSON.parse(event.data);
          if (data.id) {
            lastEventId = Math.max(lastEventId, Number(data.id));
          }
          onEvent(data);
          if (['completed', 'failed', 'cancelled'].includes(data.status)) {
            onComplete?.();
          }
        } catch (e) {
          // ignore parsing error
        }
      };

      socket.onerror = () => {
        // Fall back to polling if WebSocket fails
        if (!isCancelled) {
          startPolling();
        }
      };

      socket.onclose = (event) => {
        if (!isCancelled && event.code !== 1000) {
          startPolling();
        }
      };
    } catch {
      startPolling();
    }

    return () => {
      isCancelled = true;
      if (socket) {
        socket.close();
      }
      if (pollingTimer) {
        clearTimeout(pollingTimer);
      }
    };
  }
}
