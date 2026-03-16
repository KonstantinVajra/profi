"use client";

import { useState } from "react";
import {
  createProject,
  extractOrder,
  generateLanding,
  generateReplies,
  suggestDialogueReply,
} from "@/lib/api";

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

interface LandingData {
  landing_page: { slug: string; status: string };
  landing_content: { hero: { title: string } };
}

interface SuggestionData {
  detected_intent: string;
  detected_stage: string;
  suggestions: Array<{ type: string; text: string }>;
  next_best_question: string;
}

// ── Component ─────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const siteUrl = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";

  // state
  const [orderText, setOrderText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projectId, setProjectId] = useState<string | null>(null);
  const [parsedOrder, setParsedOrder] = useState<ParsedOrderData | null>(null);
  const [landing, setLanding] = useState<LandingData | null>(null);
  const [replies, setReplies] = useState<ReplyVariantData[]>([]);
  const [clientMsg, setClientMsg] = useState("");
  const [suggestion, setSuggestion] = useState<SuggestionData | null>(null);

  // ── Step 1-4: generate everything ───────────────────────────────────────

  async function handleGenerate() {
    if (!orderText.trim()) return;
    setLoading(true);
    setError(null);
    setParsedOrder(null);
    setLanding(null);
    setReplies([]);
    setSuggestion(null);

    try {
      // 1. create project
      const project = await createProject() as { id: string };
      setProjectId(project.id);

      // 2. extract order
      const parsed = await extractOrder(project.id, orderText) as ParsedOrderData;
      setParsedOrder(parsed);

      // 3. generate landing
      const landingResult = await generateLanding(project.id) as LandingData;
      setLanding(landingResult);

      // 4. generate replies with real landing URL
      const slug = landingResult.landing_page.slug;
      const landingUrl = `${siteUrl}/r/${slug}`;
      const repliesResult = await generateReplies(project.id, landingUrl) as { reply_variants: ReplyVariantData[] };
      setReplies(repliesResult.reply_variants);

    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  // ── Step 5: dialogue ─────────────────────────────────────────────────────

  async function handleDialogue() {
    if (!projectId || !clientMsg.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await suggestDialogueReply(projectId, clientMsg) as SuggestionData;
      setSuggestion(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const landingUrl = landing ? `${siteUrl}/r/${landing.landing_page.slug}` : null;

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

        {/* Block A — Order Input */}
        <section className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-semibold mb-3">Заказ</h2>
          <textarea
            className="w-full border rounded-xl p-3 text-sm resize-none h-28"
            placeholder="Вставьте текст заказа..."
            value={orderText}
            onChange={(e) => setOrderText(e.target.value)}
          />
          <button
            onClick={handleGenerate}
            disabled={loading || !orderText.trim()}
            className="mt-3 bg-black text-white rounded-xl px-5 py-2 text-sm disabled:opacity-40"
          >
            {loading ? "Генерируем..." : "Сгенерировать"}
          </button>
        </section>

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
        {landing && landingUrl && (
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-base font-semibold mb-3">Лендинг</h2>
            <p className="text-sm text-gray-500 mb-1">{landing.landing_content.hero.title}</p>
            <a
              href={landingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 underline break-all"
            >
              {landingUrl}
            </a>
          </section>
        )}

        {/* Block D — Reply Variants */}
        {replies.length > 0 && (
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-base font-semibold mb-3">Варианты отклика</h2>
            <div className="space-y-4">
              {replies.map((r) => (
                <div key={r.id} className="border rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-medium uppercase text-gray-400">{r.variant_type}</span>
                    <button
                      onClick={() => navigator.clipboard.writeText(r.message_text)}
                      className="text-xs text-gray-400 hover:text-black"
                    >
                      Копировать
                    </button>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{r.message_text}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Block E — Dialogue Copilot */}
        {projectId && (
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-base font-semibold mb-3">Диалог с клиентом</h2>
            <textarea
              className="w-full border rounded-xl p-3 text-sm resize-none h-20"
              placeholder="Вставьте ответ клиента..."
              value={clientMsg}
              onChange={(e) => setClientMsg(e.target.value)}
            />
            <button
              onClick={handleDialogue}
              disabled={loading || !clientMsg.trim()}
              className="mt-3 bg-black text-white rounded-xl px-5 py-2 text-sm disabled:opacity-40"
            >
              {loading ? "Анализируем..." : "Предложить ответ"}
            </button>

            {suggestion && (
              <div className="mt-4 space-y-3">
                <div className="text-xs text-gray-400">
                  <span className="font-medium text-gray-600">Интент:</span> {suggestion.detected_intent}
                  {" · "}
                  <span className="font-medium text-gray-600">Стадия:</span> {suggestion.detected_stage}
                </div>
                {suggestion.suggestions.map((s, i) => (
                  <div key={i} className="border rounded-xl p-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium uppercase text-gray-400">{s.type}</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(s.text)}
                        className="text-xs text-gray-400 hover:text-black"
                      >
                        Копировать
                      </button>
                    </div>
                    <p className="text-sm">{s.text}</p>
                  </div>
                ))}
                <p className="text-xs text-gray-500">
                  <span className="font-medium">Следующий вопрос:</span> {suggestion.next_best_question}
                </p>
              </div>
            )}
          </section>
        )}

      </div>
    </main>
  );
}