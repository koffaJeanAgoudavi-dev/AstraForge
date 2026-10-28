import { BackendHealthStatus } from './types';

const STORAGE_KEY_BACKEND_URL = 'astraforge_backend_url';

export class ApiClient {
  private static instance: ApiClient;
  private baseUrl: string;

  private constructor() {
    // Default to the same-origin Vite proxy path '/api'
    const savedUrl = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY_BACKEND_URL) : null;
    this.baseUrl = savedUrl || '/api';
  }

  public static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      ApiClient.instance = new ApiClient();
    }
    return ApiClient.instance;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public setBaseUrl(url: string): void {
    const trimmed = url.trim().replace(/\/+$/, '');
    this.baseUrl = trimmed || '/api';
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY_BACKEND_URL, this.baseUrl);
    }
  }

  public async checkHealth(): Promise<BackendHealthStatus> {
    const start = performance.now();
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const res = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const latencyMs = Math.round(performance.now() - start);

      if (res.ok) {
        try {
          const data = await res.json();
          if (data && data.status === 'ok') {
            return {
              isAvailable: true,
              url: this.baseUrl,
              latencyMs,
            };
          }
          return {
            isAvailable: false,
            url: this.baseUrl,
            error: `Réponse inattendue de /health: statut non "ok"`,
            latencyMs,
          };
        } catch {
          return {
            isAvailable: false,
            url: this.baseUrl,
            error: 'Réponse JSON invalide reçue de /health',
            latencyMs,
          };
        }
      }

      // Explicitly reject HTTP 401 or any non-2xx as NOT available
      return {
        isAvailable: false,
        url: this.baseUrl,
        error: `Erreur HTTP ${res.status}: ${res.statusText}`,
        latencyMs,
      };
    } catch (err: any) {
      const latencyMs = Math.round(performance.now() - start);
      return {
        isAvailable: false,
        url: this.baseUrl,
        error: err.name === 'AbortError' ? 'Délai d’attente dépassé (timeout 4s)' : 'Serveur FastAPI injoignable',
        latencyMs,
      };
    }
  }

  public async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${this.baseUrl}${cleanEndpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errorBody = await response.json();
        detail = errorBody.detail || errorBody.message || errorBody.error || detail;
      } catch {
        // ignore json parse error
      }
      throw new Error(detail);
    }

    return response.json() as Promise<T>;
  }
}

export const apiClient = ApiClient.getInstance();
