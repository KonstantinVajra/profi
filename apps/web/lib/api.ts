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

// ── Contacts (shared type, mirrors backend ContactInfo schema) ───────────
// telegram / instagram stored without @ (backend validator strips it).
export interface ContactInfo {
  whatsapp?: string | null;
  telegram?: string | null;
  phone?: string | null;
  instagram?: string | null;
  vk?: string | null;
}

// ── Projects (extended) ──────────────────────────────────────────────────
export const getProject = (projectId: string) =>
  request<{ id: string; contact_info?: ContactInfo | null }>(`/projects/${projectId}`);

export const updateProjectContacts = (projectId: string, contactInfo: ContactInfo) =>
  request<{ contact_info?: ContactInfo | null }>(`/projects/${projectId}/contacts`, {
    method: "PATCH",
    body: JSON.stringify({ contact_info: contactInfo }),
  });

// ── Orders ────────────────────────────────────────────────────────────────
export const extractOrder = (projectId: string, rawText: string) =>
  request("/orders/extract", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, raw_text: rawText }),
  });

// ── Orders (screenshot) ──────────────────────────────────────────────────
// Uses fetch directly (not request()) to avoid Content-Type: application/json
// overriding the multipart/form-data boundary set by the browser.
export const extractOrderFromImage = (projectId: string, file: File) => {
  const form = new FormData();
  form.append("project_id", projectId);
  form.append("screenshot", file);
  const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return fetch(`${BASE}/orders/extract/image`, {
    method: "POST",
    body: form,
  }).then((res) => {
    if (!res.ok) throw new Error(`Screenshot extraction failed: ${res.status}`);
    return res.json();
  });
};

// Multi-screenshot variant: sends 1–5 files to POST /orders/extract/images.
// Backend enforces the 5-file limit; frontend validates before calling.
export const extractOrderFromImages = (projectId: string, files: File[]) => {
  const form = new FormData();
  form.append("project_id", projectId);
  files.forEach((f) => form.append("screenshots", f));
  const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return fetch(`${BASE}/orders/extract/images`, {
    method: "POST",
    body: form,
  }).then((res) => {
    if (!res.ok) throw new Error(`Multi-screenshot extraction failed: ${res.status}`);
    return res.json();
  });
};

// ── Replies ───────────────────────────────────────────────────────────────
export const generateReplies = (projectId: string, landingUrl?: string) =>
  request(`/projects/${projectId}/replies/generate`, {
    method: "POST",
    body: JSON.stringify({ landing_url: landingUrl ?? null }),
  });

// ── Landing ───────────────────────────────────────────────────────────────
export const getLandingDraft = (projectId: string) =>
  request<{ final_text: string; entry_message: string }>(
    `/projects/${projectId}/landing/draft`,
    { method: "POST" },
  );

export const generateLanding = (
  projectId: string,
  photoSetId?: string,
  relatedBlock?: { category_key: string },
  overrides?: {
    hero_title_override?: string;
    final_text_override?: string;
    entry_message_override?: string;
  },
) =>
  request(`/projects/${projectId}/landing/generate`, {
    method: "POST",
    body: JSON.stringify({
      photo_set_id: photoSetId ?? null,
      related_block: relatedBlock ?? null,
      hero_title_override: overrides?.hero_title_override ?? null,
      final_text_override: overrides?.final_text_override ?? null,
      entry_message_override: overrides?.entry_message_override ?? null,
    }),
  });

export const getLandingBySlug = (slug: string) =>
  request(`/public/landings/${slug}`);

// ── Dialogue ──────────────────────────────────────────────────────────────
export const suggestDialogueReply = (projectId: string, messageText: string) =>
  request(`/projects/${projectId}/dialogue/reply`, {
    method: "POST",
    body: JSON.stringify({ message_text: messageText, source_channel: "profi" }),
  });

// ── Photos ────────────────────────────────────────────────────────────────
export const getPhotoSets = () =>
  request("/photo-sets");

export const getPhotoSet = (photoSetId: string) =>
  request(`/photo-sets/${photoSetId}`);

export const uploadPhotos = (projectId: string, files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return fetch(`${BASE}/projects/${projectId}/photos/upload`, {
    method: "POST",
    body: form,
  }).then((res) => {
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json() as Promise<{ photo_set_id: string }>;
  });
};

export const createPresetAlbum = (name: string, files: File[], category: string) => {
  const form = new FormData();
  form.append("name", name);
  form.append("category", category);
  files.forEach((f) => form.append("files", f));
  const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return fetch(`${BASE}/photo-sets/preset`, {
    method: "POST",
    body: form,
  }).then((res) => {
    if (!res.ok) throw new Error(`Create album failed: ${res.status}`);
    return res.json() as Promise<{ photo_set_id: string; name: string }>;
  });
};

export const getPresetAlbumsByCategory = (category: string) =>
  request(`/public/photo-sets?category=${encodeURIComponent(category)}`);