"use client";

import { useState, useEffect } from "react";
import {
  createProject,
  getProject,
  extractOrder,
  extractOrderFromImage,
  extractOrderFromImages,
  updateProjectContacts,
  generateLanding,
  getLandingDraft,
  generateReplies,
  getPhotoSets,
  uploadPhotos,
  createPresetAlbum,
} from "@/lib/api";
import type { PhotoSet } from "@/types/photo";
import type { ContactInfo } from "@/lib/api";
import type { LandingPublicResponse } from "@/types/landing";
import { selectExtractionMethod } from "@/lib/extractionUtils";
import { buildLandingUrl } from "@/lib/landingUrl";

// ── Types ─────────────────────────────────────────────────────────────────

interface ParsedOrderData {
  client_name: string | null;
  event_type: string | null;
  city: string | null;
  date_text: string | null;
  budget_max: number | null;
}

interface ReplyVariantData {
  id: string;
  variant_type: string;
  message_text: string;
}

// ── Component ─────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  // localStorage key for project lifecycle persistence
  const LS_KEY = "landingReply_projectId";

  // true while we are checking localStorage on mount — hides Contacts block briefly
  const [projectLoading, setProjectLoading] = useState(true);

  // state
  const [orderText, setOrderText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projectId, setProjectId] = useState<string | null>(null);
  const [parsedOrder, setParsedOrder] = useState<ParsedOrderData | null>(null);
  const [landing, setLanding] = useState<LandingPublicResponse | null>(null);
  const [replies, setReplies] = useState<ReplyVariantData[]>([]);

  // Draft review state — populated after getLandingDraft(), cleared after handleConfirmDraft()
  const [draftReview, setDraftReview] = useState<{ final_text: string; entry_message: string } | null>(null);
  const [editHeroTitle, setEditHeroTitle] = useState("");
  const [editFinalText, setEditFinalText] = useState("");
  const [editEntryMessage, setEditEntryMessage] = useState("");
  // Local editable drafts keyed by ReplyVariant id.
  // Initialized from message_text on generation; never persisted to backend.
  const [draftTexts, setDraftTexts] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // photo state
  const [photoSets, setPhotoSets] = useState<PhotoSet[]>([]);
  const [selectedPhotoSetId, setSelectedPhotoSetId] = useState<string | null>(null);
  const [relatedCategoryKey, setRelatedCategoryKey] = useState("");
  const [manualFiles, setManualFiles] = useState<File[]>([]);
  const [photoSetsLoaded, setPhotoSetsLoaded] = useState(false);
  // preset album creation
  const [newAlbumName, setNewAlbumName] = useState("");
  const [newAlbumCategory, setNewAlbumCategory] = useState("");
  const [newAlbumFiles, setNewAlbumFiles] = useState<File[]>([]);
  const [albumCreating, setAlbumCreating] = useState(false);

  // screenshot state — for order extraction via image (1–5 files)
  const [screenshotFiles, setScreenshotFiles] = useState<File[]>([]);

  // contacts state — photographer contact links for CTA buttons
  const [contacts, setContacts] = useState<ContactInfo>({});
  const [contactsSaved, setContactsSaved] = useState(false);
  const [contactsSaving, setContactsSaving] = useState(false);

  // ── Host guard ───────────────────────────────────────────────────────────
  // Secondary guard: redirect workspace away from the public domain.
  // Primary enforcement is nginx (location /workspace { return 404; }).
  // This catches direct URL entry in browsers before nginx can act.
  // Triggers only for evflow.ru and www.evflow.ru — IP and workspace.evflow.ru are unaffected.
  useEffect(() => {
    const h = window.location.hostname;
    if (h === "evflow.ru" || h === "www.evflow.ru") {
      window.location.replace(
        "https://workspace.evflow.ru" + window.location.pathname + window.location.search
      );
    }
  }, []);

  // ── Project lifecycle ────────────────────────────────────────────────────
  // On mount: restore projectId from localStorage and preload contact_info.
  // Project is NOT created here — only restored if it already exists in DB.
  useEffect(() => {
    const stored = localStorage.getItem(LS_KEY);
    if (!stored) {
      setProjectLoading(false);
      return;
    }
    (getProject(stored) as Promise<{ id: string; contact_info?: ContactInfo | null }>)
      .then((project) => {
        setProjectId(project.id);
        if (project.contact_info) {
          setContacts(project.contact_info);
        }
      })
      .catch(() => {
        // Project not found or network error — clear stale id, start fresh.
        localStorage.removeItem(LS_KEY);
      })
      .finally(() => {
        setProjectLoading(false);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Create a new project or return the current one if already set.
  // handleGenerate() resets projectId before calling this, so it always
  // creates a fresh Project for each generate action.
  // handleSaveContacts() calls this without resetting — preserves current project.
  async function ensureProject(): Promise<string> {
    if (projectId) return projectId;
    const project = await createProject() as { id: string };
    localStorage.setItem(LS_KEY, project.id);
    setProjectId(project.id);
    return project.id;
  }

  // ── Contacts ─────────────────────────────────────────────────────────────

  async function handleSaveContacts() {
    setContactsSaving(true);
    setError(null);
    try {
      // Create project on first save if not yet created.
      const pid = await ensureProject();
      await updateProjectContacts(pid, contacts);
      setContactsSaved(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save contacts");
    } finally {
      setContactsSaving(false);
    }
  }

  async function copyToClipboard(text: string, id: string) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for HTTP (non-localhost IP addresses)
        const el = document.createElement("textarea");
        el.value = text;
        el.style.position = "fixed";
        el.style.opacity = "0";
        document.body.appendChild(el);
        el.focus();
        el.select();
        document.execCommand("copy");
        document.body.removeChild(el);
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1500);
    } catch {
      // Silent fail — do not show red error to user
    }
  }

  // ── Photo helpers ────────────────────────────────────────────────────────

  async function loadPhotoSets() {
    if (photoSetsLoaded) return;
    try {
      const sets = await getPhotoSets() as PhotoSet[];
      setPhotoSets(sets);
      setPhotoSetsLoaded(true);
    } catch {
      // non-critical — workspace still usable without photo sets
    }
  }

  async function handleCreateAlbum() {
    if (!newAlbumName.trim() || newAlbumFiles.length === 0 || !newAlbumCategory) return;
    setAlbumCreating(true);
    try {
      await createPresetAlbum(newAlbumName.trim(), newAlbumFiles, newAlbumCategory);
      setNewAlbumName("");
      setNewAlbumCategory("");
      setNewAlbumFiles([]);
      setPhotoSetsLoaded(false);
      await loadPhotoSets();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Album creation failed");
    } finally {
      setAlbumCreating(false);
    }
  }

  // ── New Reply: explicit project reset ────────────────────────────────────
  // Clears project context and all generation state so the next
  // "Сгенерировать" click creates a fresh Project.
  // Contacts are preserved — they belong to the photographer, not the client.

  function handleNewReply() {
    // Clear project identity
    setProjectId(null);
    localStorage.removeItem(LS_KEY);

    // Clear generation state
    setParsedOrder(null);
    setLanding(null);
    setReplies([]);
    setDraftTexts({});
    setDraftReview(null);
    setEditHeroTitle("");
    setEditFinalText("");
    setEditEntryMessage("");

    // Clear order input
    setOrderText("");
    setScreenshotFiles([]);
    setRelatedCategoryKey("");

    // Clear per-reply photo selection
    setSelectedPhotoSetId(null);
    setManualFiles([]);

    // Clear album creation form (per-reply transient input)
    setNewAlbumName("");
    setNewAlbumCategory("");
    setNewAlbumFiles([]);

    // photoSets (photographer's preset catalog) is NOT reset — it is global / reusable.

    // Clear error
    setError(null);
  }

  // ── Step 1-4: generate everything ───────────────────────────────────────

  async function handleGenerate() {
    // text has priority over screenshot; at least one must be present
    const extractionMethod = selectExtractionMethod(orderText, screenshotFiles.length > 0 ? screenshotFiles[0] : null);
    if (!extractionMethod) return;
    setLoading(true);
    setError(null);
    setParsedOrder(null);
    setLanding(null);
    setReplies([]);
    setDraftTexts({});
    setDraftReview(null);

    try {
      // 1. Always create a new Project for each generate action.
      // Do NOT call ensureProject() here — it reads projectId from React state
      // which may not have flushed yet. Call createProject() directly to guarantee
      // a fresh project regardless of current state.
      const project = await createProject() as { id: string };
      localStorage.setItem(LS_KEY, project.id);
      setProjectId(project.id);
      const pid = project.id;

      // 2. extract order — single file uses /extract/image, multiple uses /extract/images
      const parsed = (
        extractionMethod === "text"
          ? await extractOrder(pid, orderText)
          : screenshotFiles.length === 1
            ? await extractOrderFromImage(pid, screenshotFiles[0])
            : await extractOrderFromImages(pid, screenshotFiles)
      ) as ParsedOrderData;
      setParsedOrder(parsed);

      // 3. run Step 1 only — get editable draft (no landing saved yet)
      const draft = await getLandingDraft(pid);
      setDraftReview(draft);
      setEditFinalText(draft.final_text);
      setEditEntryMessage(draft.entry_message);
      // hero_title: prefer existing override, fall back to hero.title, then empty
      setEditHeroTitle(
        landing?.landing_content?.hero_title_override ??
        landing?.landing_content?.hero?.title ??
        ""
      );

    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmDraft() {
    const pid = projectId;
    if (!pid || !draftReview) return;
    setLoading(true);
    setError(null);

    try {
      // resolve photo set (same as before)
      let resolvedPhotoSetId: string | undefined = selectedPhotoSetId ?? undefined;
      if (!resolvedPhotoSetId && manualFiles.length > 0) {
        const uploadResult = await uploadPhotos(pid, manualFiles);
        resolvedPhotoSetId = uploadResult.photo_set_id;
      }

      // generate landing with user-edited overrides
      // always send current edit state; empty hero title → undefined (not sent as override)
      const landingResult = await generateLanding(
        pid,
        resolvedPhotoSetId,
        relatedCategoryKey ? { category_key: relatedCategoryKey } : undefined,
        {
          hero_title_override: editHeroTitle.trim() || undefined,
          final_text_override: editFinalText || undefined,
          entry_message_override: editEntryMessage || undefined,
        },
      ) as LandingPublicResponse;
      setLanding(landingResult);
      setDraftReview(null);

      // generate replies with real landing URL (only after landing is saved)
      const slug = landingResult.landing_page.slug;
      const landingUrl = buildLandingUrl(slug);
      const repliesResult = await generateReplies(pid, landingUrl) as { reply_variants: ReplyVariantData[] };
      setReplies(repliesResult.reply_variants);
      setDraftTexts(
        repliesResult.reply_variants.reduce<Record<string, string>>(
          (acc, r) => ({ ...acc, [r.id]: r.message_text }),
          {}
        )
      );

      // reset after success
      setScreenshotFiles([]);
      setRelatedCategoryKey("");

    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const landingUrl = landing ? buildLandingUrl(landing.landing_page.slug) : null;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-6">

        <h1 className="text-xl font-bold">Landing Reply — Workspace</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {/* Block Photos — Album selector */}
        <section className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-semibold mb-3">Фото для лендинга</h2>

          {/* Preset albums */}
          <div className="mb-4">
            <button
              onClick={loadPhotoSets}
              className="text-sm text-blue-600 underline mb-2 block"
            >
              Загрузить альбомы
            </button>
            {photoSets.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-gray-400 mb-1">Выберите альбом:</p>
                {photoSets.map((ps) => (
                  <label key={ps.id} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name="photoSet"
                      value={ps.id}
                      checked={selectedPhotoSetId === ps.id}
                      onChange={() => { setSelectedPhotoSetId(ps.id); setManualFiles([]); }}
                    />
                    {ps.name ?? ps.id}
                    <span className="text-xs text-gray-400">({ps.items.length} фото)</span>
                  </label>
                ))}
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="radio"
                    name="photoSet"
                    value=""
                    checked={selectedPhotoSetId === null}
                    onChange={() => setSelectedPhotoSetId(null)}
                  />
                  Без альбома
                </label>
              </div>
            )}

            {/* Related photo series category */}
            <div className="mt-3">
              <p className="text-xs text-gray-400 mb-1">Похожие фотосерии (категория):</p>
              <select
                value={relatedCategoryKey}
                onChange={(e) => setRelatedCategoryKey(e.target.value)}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                <option value="">— без похожих серий —</option>
                <option value="wedding">wedding</option>
                <option value="love_story">love_story</option>
                <option value="family">family</option>
                <option value="kids">kids</option>
                <option value="portrait">portrait</option>
                <option value="maternity">maternity</option>
                <option value="business">business</option>
                <option value="events">events</option>
                <option value="catalog">catalog</option>
                <option value="interior">interior</option>
                <option value="food">food</option>
                <option value="art">art</option>
              </select>
            </div>
          </div>

          {/* Manual upload */}
          {selectedPhotoSetId === null && (
            <div className="mb-4">
              <p className="text-xs text-gray-400 mb-1">Или загрузите фото вручную:</p>
              <input
                type="file"
                multiple
                accept="image/*"
                className="text-sm"
                onChange={(e) => setManualFiles(Array.from(e.target.files ?? []))}
              />
              {manualFiles.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">{manualFiles.length} файл(ов) выбрано</p>
              )}
            </div>
          )}

          {/* Create preset album */}
          <details className="mt-2">
            <summary className="text-xs text-gray-400 cursor-pointer">Добавить новый альбом</summary>
            <div className="mt-2 space-y-2">
              <input
                type="text"
                placeholder="Название альбома"
                value={newAlbumName}
                onChange={(e) => setNewAlbumName(e.target.value)}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
              <select
                value={newAlbumCategory}
                onChange={(e) => setNewAlbumCategory(e.target.value)}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                <option value="">Выберите категорию</option>
                <option value="wedding">wedding</option>
                <option value="love_story">love_story</option>
                <option value="family">family</option>
                <option value="kids">kids</option>
                <option value="portrait">portrait</option>
                <option value="maternity">maternity</option>
                <option value="business">business</option>
                <option value="events">events</option>
                <option value="catalog">catalog</option>
                <option value="interior">interior</option>
                <option value="food">food</option>
                <option value="art">art</option>
              </select>
              <input
                type="file"
                multiple
                accept="image/*"
                className="text-sm"
                onChange={(e) => setNewAlbumFiles(Array.from(e.target.files ?? []))}
              />
              <button
                onClick={handleCreateAlbum}
                disabled={albumCreating || !newAlbumName.trim() || newAlbumFiles.length === 0 || !newAlbumCategory}
                className="bg-gray-800 text-white rounded-lg px-4 py-1.5 text-sm disabled:opacity-40"
              >
                {albumCreating ? "Сохраняем..." : "Создать альбом"}
              </button>
            </div>
          </details>
        </section>

        {/* Block A — Order Input */}
        <section className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-semibold mb-3">Заказ</h2>
          <textarea
            className="w-full border rounded-xl p-3 text-sm resize-none h-28"
            placeholder="Вставьте текст заказа..."
            value={orderText}
            onChange={(e) => {
              setOrderText(e.target.value);
              // clear screenshots when user types text to avoid ambiguous state
              if (e.target.value.trim()) {
                setScreenshotFiles([]);
              }
            }}
          />
          <div className="mt-3">
            <p className="text-xs text-gray-400 mb-1">или загрузите скриншот(ы) заказа (до 5):</p>
            <input
              type="file"
              accept="image/*"
              multiple
              className="text-sm"
              onChange={(e) => {
                const files = Array.from(e.target.files ?? []);
                if (files.length > 5) {
                  setError("Можно загрузить не более 5 скриншотов");
                  e.target.value = "";
                  return;
                }
                setScreenshotFiles(files);
              }}
            />
            {screenshotFiles.length > 0 && (
              <p className="text-xs text-gray-500 mt-1">{screenshotFiles.length} файл(ов) выбрано</p>
            )}
          </div>
          <button
            onClick={handleGenerate}
            disabled={projectLoading || loading || (!orderText.trim() && screenshotFiles.length === 0)}
            className="mt-3 bg-black text-white rounded-xl px-5 py-2 text-sm disabled:opacity-40"
          >
            {loading ? "Генерируем..." : "Сгенерировать"}
          </button>
        </section>

        {/* Draft Review Block — shown after Step 1, before final generate */}
        {draftReview && (
          <section className="bg-white rounded-2xl p-6 shadow-sm border border-amber-200">
            <h2 className="text-base font-semibold mb-1">Проверьте черновик</h2>
            <p className="text-xs text-gray-400 mb-4">
              Отредактируйте текст при необходимости и нажмите «Создать лендинг»
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Заголовок страницы (необязательно)
                </label>
                <input
                  type="text"
                  value={editHeroTitle}
                  onChange={(e) => setEditHeroTitle(e.target.value)}
                  placeholder="Оставьте пустым — будет сгенерирован автоматически"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Сообщение-подводка
                </label>
                <textarea
                  value={editEntryMessage}
                  onChange={(e) => setEditEntryMessage(e.target.value)}
                  rows={3}
                  className="w-full border rounded-lg px-3 py-2 text-sm resize-y"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Основной текст
                </label>
                <textarea
                  value={editFinalText}
                  onChange={(e) => setEditFinalText(e.target.value)}
                  rows={6}
                  className="w-full border rounded-lg px-3 py-2 text-sm resize-y"
                />
              </div>
              <button
                onClick={handleConfirmDraft}
                disabled={loading}
                className="bg-black text-white rounded-xl px-5 py-2 text-sm disabled:opacity-40"
              >
                {loading ? "Создаём..." : "Создать лендинг →"}
              </button>
            </div>
          </section>
        )}

        {/* Block B — Parsed Order */}
        {parsedOrder && (
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-base font-semibold mb-3">Данные заказа</h2>
            <dl className="text-sm space-y-1">
              {[
                ["Клиент", parsedOrder.client_name],
                ["Событие", parsedOrder.event_type],
                ["Город", parsedOrder.city],
                ["Дата", parsedOrder.date_text],
                ["Бюджет", parsedOrder.budget_max ? `${parsedOrder.budget_max} ₽` : null],
              ].map(([label, value]) =>
                value ? (
                  <div key={label as string} className="flex gap-2">
                    <dt className="text-gray-400 w-24 flex-shrink-0">{label}</dt>
                    <dd className="font-medium">{value as string}</dd>
                  </div>
                ) : null
              )}
            </dl>
          </section>
        )}

        {/* Block C — Landing */}
        {landing && landingUrl && (() => {
          // Prefer entry_message (short hook). Fall back to final_text, then to "[entry]".
          const entryText =
            landing.landing_content.entry_message?.trim() ||
            landing.landing_content.final_text?.trim() ||
            "[entry]";
          return (
            <section className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex justify-between items-start gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-800 whitespace-pre-line mb-3">{entryText}</p>
                  <a
                    href={landingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 underline break-all"
                  >
                    {landingUrl}
                  </a>
                </div>
                <button
                  onClick={() => copyToClipboard(`${entryText}
${landingUrl}`, "landing-entry")}
                  className="text-xs text-gray-400 hover:text-black flex-shrink-0"
                >
                  {copiedId === "landing-entry" ? "✓ Скопировано" : "Копировать"}
                </button>
              </div>
            </section>
          );
        })()}

        {/* Block Contacts — visible from page load; project created lazily on first save */}
        {landing && (
          <div className="flex justify-end">
            <button
              onClick={handleNewReply}
              className="text-sm text-gray-400 hover:text-black underline"
            >
              Новый отклик →
            </button>
          </div>
        )}

        {/* Block Contacts — visible from page load; project created lazily on first save */}
        {!projectLoading && (
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-base font-semibold mb-4">Контакты для лендинга</h2>
            <div className="space-y-3">
              {(["whatsapp", "telegram", "phone", "instagram", "vk"] as const).map((key) => {
                const labels: Record<string, string> = {
                  whatsapp:  "WhatsApp (номер, напр. 79161234567)",
                  telegram:  "Telegram (username без @)",
                  phone:     "Телефон",
                  instagram: "Instagram (username без @)",
                  vk:        "VK (username или id)",
                };
                return (
                  <div key={key}>
                    <label className="text-xs text-gray-400 block mb-1">{labels[key]}</label>
                    <input
                      type="text"
                      className="w-full border rounded-xl px-3 py-2 text-sm"
                      value={contacts[key] ?? ""}
                      onChange={(e) => {
                        setContacts((prev) => ({ ...prev, [key]: e.target.value || null }));
                        setContactsSaved(false);
                      }}
                    />
                  </div>
                );
              })}
            </div>
            <button
              onClick={handleSaveContacts}
              disabled={projectLoading || contactsSaving}
              className="mt-4 bg-black text-white rounded-xl px-5 py-2 text-sm disabled:opacity-40"
            >
              {contactsSaving ? "Сохраняем..." : "Сохранить контакты"}
            </button>
            {contactsSaved && (
              <p className="text-xs text-green-600 mt-2">✓ Сохранено</p>
            )}
          </section>
        )}

        {replies.length > 0 && (
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-base font-semibold mb-3">Варианты отклика</h2>
            <div className="space-y-4">
              {replies.map((r) => (
                <div key={r.id} className="border rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-medium uppercase text-gray-400">{r.variant_type}</span>
                    <button
                      onClick={() => copyToClipboard(draftTexts[r.id] ?? "", r.id)}
                      className="text-xs text-gray-400 hover:text-black"
                    >
                      {copiedId === r.id ? "✓ Скопировано" : "Копировать"}
                    </button>
                  </div>
                  <textarea
                    className="w-full text-sm bg-transparent outline-none resize-none min-h-[7rem] overflow-auto"
                    value={draftTexts[r.id] ?? ""}
                    onChange={(e) =>
                      setDraftTexts((prev) => ({ ...prev, [r.id]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          </section>
        )}


      </div>
    </main>
  );
}