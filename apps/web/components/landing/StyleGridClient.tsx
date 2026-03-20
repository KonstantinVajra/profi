"use client";

import { useEffect, useState, useCallback } from "react";

interface PhotoItem {
  id: string;
  photo_url: string;
  display_order: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function StyleGridClient({ photoSetId }: { photoSetId: string }) {
  const [items, setItems] = useState<PhotoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/public/photo-sets/${photoSetId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.items) setItems(data.items);
      })
      .catch((err) => console.error("StyleGrid fetch failed:", err))
      .finally(() => setLoading(false));
  }, [photoSetId]);

  const close = useCallback(() => setSelectedIndex(null), []);

  const prev = useCallback(() => {
    if (items.length === 0) return;
    setSelectedIndex((i) => (i === null ? null : (i - 1 + items.length) % items.length));
  }, [items.length]);

  const next = useCallback(() => {
    if (items.length === 0) return;
    setSelectedIndex((i) => (i === null ? null : (i + 1) % items.length));
  }, [items.length]);

  useEffect(() => {
    if (selectedIndex === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedIndex, close, prev, next]);

  if (loading) {
    return (
      <section className="pb-6">
        <div className="rounded-2xl bg-gray-100 h-48 flex items-center justify-center">
          <span className="text-xs text-gray-400">Загрузка фото...</span>
        </div>
      </section>
    );
  }

  if (items.length === 0) {
    return (
      <section className="pb-6">
        <div className="rounded-2xl bg-gray-100 h-48 flex items-center justify-center">
          <span className="text-xs text-gray-400">Примеры работ</span>
        </div>
      </section>
    );
  }

  return (
    <section className="pb-6">
      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {items.map((item, i) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSelectedIndex(i)}
            className="focus:outline-none rounded-xl overflow-hidden"
            aria-label={`Открыть фото ${i + 1}`}
          >
            <img
              src={item.photo_url}
              alt=""
              className="w-full h-40 object-cover rounded-xl"
            />
          </button>
        ))}
      </div>

      {/* Lightbox */}
      {selectedIndex !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ backgroundColor: "rgba(0,0,0,0.9)" }}
          onClick={close}
        >
          <div
            className="relative flex items-center justify-center w-full h-full"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Photo */}
            <img
              src={items[selectedIndex].photo_url}
              alt=""
              className="max-h-screen max-w-full object-contain px-16"
            />

            {/* Close */}
            <button
              type="button"
              onClick={close}
              className="absolute top-4 right-4 text-white text-2xl leading-none w-10 h-10 flex items-center justify-center rounded-full"
              style={{ background: "rgba(0,0,0,0.5)" }}
              aria-label="Закрыть"
            >
              ×
            </button>

            {/* Counter */}
            <div
              className="absolute top-4 left-1/2 text-white text-sm px-3 py-1 rounded-full"
              style={{ transform: "translateX(-50%)", background: "rgba(0,0,0,0.5)" }}
            >
              {selectedIndex + 1} / {items.length}
            </div>

            {/* Prev */}
            {items.length > 1 && (
              <button
                type="button"
                onClick={prev}
                className="absolute left-2 text-white text-3xl w-10 h-10 flex items-center justify-center rounded-full"
                style={{ background: "rgba(0,0,0,0.5)" }}
                aria-label="Предыдущее"
              >
                ‹
              </button>
            )}

            {/* Next */}
            {items.length > 1 && (
              <button
                type="button"
                onClick={next}
                className="absolute right-2 text-white text-3xl w-10 h-10 flex items-center justify-center rounded-full"
                style={{ background: "rgba(0,0,0,0.5)" }}
                aria-label="Следующее"
              >
                ›
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
