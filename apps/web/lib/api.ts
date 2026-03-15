/**
 * API client for Landing Reply backend.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API ${res.status}: ${error}`);
  }
  return res.json();
}

// ── Projects ──────────────────────────────────────────────────────────────
export const createProject = (title?: string) =>
  request("/projects", {
    method: "POST",
    body: JSON.stringify({ title }),
  });

// ── Orders ────────────────────────────────────────────────────────────────
export const extractOrder = (projectId: string, rawText: string) =>
  request("/orders/extract", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, raw_text: rawText }),
  });

// ── Replies ───────────────────────────────────────────────────────────────
export const generateReplies = (projectId: string, landingUrl?: string) =>
  request(`/projects/${projectId}/replies/generate`, {
    method: "POST",
    body: JSON.stringify({ landing_url: landingUrl ?? null }),
  });

// ── Landing ───────────────────────────────────────────────────────────────
export const generateLanding = (projectId: string) =>
  request(`/projects/${projectId}/landing/generate`, {
    method: "POST",
    body: JSON.stringify({}),
  });

export const getLandingBySlug = (slug: string) =>
  request(`/public/landings/${slug}`);

// ── Dialogue ──────────────────────────────────────────────────────────────
export const suggestDialogueReply = (projectId: string, messageText: string) =>
  request(`/projects/${projectId}/dialogue/reply`, {
    method: "POST",
    body: JSON.stringify({ message_text: messageText, source_channel: "profi" }),
  });
