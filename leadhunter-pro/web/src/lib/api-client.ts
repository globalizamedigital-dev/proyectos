/**
 * Cliente HTTP del API Cazador.
 * Centraliza:
 *   - URL base (NEXT_PUBLIC_API_BASE_URL).
 *   - Authorization: Bearer <session_token> obtenido de Supabase Auth.
 *   - Manejo de errores con shape estable {error, detail, trace_id}.
 *
 * Uso desde un client component:
 *
 *   import { apiClient } from "@/lib/api-client";
 *   const result = await apiClient.discover({ geo, sector, max, enrich });
 */
import { getSupabaseBrowserClient } from "@/lib/supabase-browser";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly detail?: string;
  readonly traceId?: string;

  constructor(status: number, message: string, opts?: { detail?: string; traceId?: string }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = opts?.detail;
    this.traceId = opts?.traceId;
  }
}

interface RequestOpts {
  signal?: AbortSignal;
  /** Si true (default), añade Authorization Bearer desde Supabase Auth. */
  auth?: boolean;
}

type HttpMethod = "GET" | "POST" | "DELETE";

async function request<T>(
  path: string,
  body: unknown,
  { signal, auth = true, method }: RequestOpts & { method?: HttpMethod } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (auth) {
    const sb = getSupabaseBrowserClient();
    const { data } = await sb.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      throw new ApiError(401, "No hay sesión activa. Inicia sesión.");
    }
    headers.Authorization = `Bearer ${token}`;
  }

  const finalMethod: HttpMethod =
    method ?? (body === undefined ? "GET" : "POST");

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: finalMethod,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
      cache: "no-store",
    });
  } catch (err) {
    throw new ApiError(
      0,
      "No se pudo contactar con el API",
      { detail: err instanceof Error ? err.message : String(err) }
    );
  }

  const traceId = res.headers.get("X-Trace-Id") ?? undefined;

  if (!res.ok) {
    let detail: string | undefined;
    try {
      const data = (await res.json()) as { detail?: string; error?: string };
      detail = data.detail ?? data.error;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail ?? res.statusText, { detail, traceId });
  }

  return (await res.json()) as T;
}

// ─── Tipos espejo del backend (subset esencial) ────────────────────
export interface DiscoverRequest {
  geo: string;
  sector: string;
  max: number;
  enrich: boolean;
}

export interface DiscoverLead {
  razonSocial: string;
  nif?: string;
  score: number;
  grade: "A" | "B" | "C" | "D";
  decisor?: string;
  decisor_role?: string;
  email?: string;
  email_confidence?: "high" | "medium" | "low";
  phone?: string;
  domain?: string;
  cnae?: string;
  sector?: string;
  provincia?: string;
  city?: string;
  sourcesHit?: string[];
  decisionMakers?: { name: string; role?: string; email?: string }[];
  // El backend tolera extras (model_config extra='allow').
  [key: string]: unknown;
}

export interface DiscoverResponse {
  schema_version: string;
  query: Record<string, unknown>;
  candidates: DiscoverLead[];
  totalCandidates: number;
  totalUnresolvedDomain: number;
  sourcesAvailability: { source: string; state: string; detail?: string }[];
  leadsPersisted: number;
}

export interface AnalyzeRequest {
  input: string;
  premium?: boolean;
  user_claims?: Record<string, unknown>;
}

export interface SourceState {
  source: string;
  state: string;
  detail?: string;
}

export interface PrivacySubject {
  kind: "email" | "phone" | "nif";
  value: string;
}

export const apiClient = {
  discover(req: DiscoverRequest, signal?: AbortSignal): Promise<DiscoverResponse> {
    return request<DiscoverResponse>("/discover", req, { signal });
  },
  analyze(req: AnalyzeRequest, signal?: AbortSignal) {
    return request("/analyze", req, { signal });
  },
  health(signal?: AbortSignal) {
    return request<{ status: string; db: string; sources: SourceState[] }>(
      "/health",
      undefined,
      { signal, auth: false }
    );
  },
  sources(signal?: AbortSignal) {
    return request<SourceState[]>("/health/sources", undefined, { signal, auth: false });
  },
  /** Genérico — wrap fino para endpoints menos comunes (privacy). */
  request<T = unknown>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, body);
  },
  /** DELETE con cuerpo JSON — para /privacy/erase. */
  requestDelete<T = unknown>(path: string, body: unknown): Promise<T> {
    return request<T>(path, body, { method: "DELETE" });
  },
};
