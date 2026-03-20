"use client";

import { useEffect, useState, useRef } from "react";

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
  // Determined once at open time, not recalculated on resize
  const [isMobile, setIsMobile] = useState(false);

  // Mobile feed refs
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const photoRowRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/public/photo-sets/${photoSetId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data?.items) setItems(data.items); })
      .catch((err) => console.error("StyleGrid fetch failed:", err))
      .finally(() => setLoading(false));
  }, [photoSetId]);

  function open(index: number) {
    setIsMobile(window.innerWidth < 640);
    setSelectedIndex(index);
  }

  function close() { setSelectedIndex(null); }

  // ── Mobile: scroll to tapped photo ───────────────────────────────────────
  // Step 1: initial scroll as soon as viewer mounts (catches cached images)
  // Step 2: repeated scroll after target image loads (catches slow images)
  useEffect(() => {
    if (selectedIndex === null || !isMobile) return;

    function scrollToTarget() {
      const target = photoRowRefs.current[selectedIndex!];
      const container = scrollContainerRef.current;
      if (target && container) {
        container.scrollTop = target.offsetTop;
      }
    }

    // Step 1 — initial scroll after paint
    const id = requestAnimationFrame(scrollToTarget);

    // Step 2 — re-scroll after target image load (cleanup symmetric: only if listener was added)
    const targetEl = photoRowRefs.current[selectedIndex];
    const img = targetEl?.querySelector("img");
    let listenerAdded = false;
    if (img && !img.complete) {
      img.addEventListener("load", scrollToTarget, { once: true });
      listenerAdded = true;
    }

    return () => {
      cancelAnimationFrame(id);
      if (listenerAdded && img) img.removeEventListener("load", scrollToTarget);
    };
  }, [selectedIndex, isMobile]);

  // ── Desktop: keyboard navigation ─────────────────────────────────────────
  useEffect(() => {
    if (selectedIndex === null || isMobile) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") setSelectedIndex((i) =>
        i === null || items.length === 0 ? null : (i - 1 + items.length) % items.length
      );
      if (e.key === "ArrowRight") setSelectedIndex((i) =>
        i === null || items.length === 0 ? null : (i + 1) % items.length
      );
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedIndex, isMobile, items.length]);

  // ── Mobile: Esc close ─────────────────────────────────────────────────────
  useEffect(() => {
    if (selectedIndex === null || !isMobile) return;
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") close(); }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedIndex, isMobile]);

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
      {/* Thumbnail grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {items.map((item, i) => (
          <button
            key={item.id}
            type="button"
            onClick={() => open(i)}
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

      {selectedIndex !== null && (
        <>
          {/* ── Mobile viewer: fullscreen vertical feed ─────────────────── */}
          {isMobile && (
            <div
              style={{
                position: "fixed", top: 0, left: 0,
                width: "100%", height: "100%",
                zIndex: 50,
                backgroundColor: "rgba(0,0,0,0.95)",
              }}
            >
              {/* Close — always on top */}
              <button
                type="button"
                onClick={close}
                aria-label="Закрыть"
                style={{
                  position: "absolute", top: 16, right: 16, zIndex: 60,
                  width: 40, height: 40, borderRadius: "50%",
                  background: "rgba(0,0,0,0.6)", color: "#fff",
                  fontSize: 24, lineHeight: "1",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: "none", cursor: "pointer",
                }}
              >×</button>

              {/* Scrollable feed — Safari-safe: overflow on inner absolute div */}
              <div
                ref={scrollContainerRef}
                style={{
                  position: "absolute", top: 0, left: 0,
                  width: "100%", height: "100%",
                  overflowY: "scroll",
                  WebkitOverflowScrolling: "touch",
                } as React.CSSProperties & { WebkitOverflowScrolling: string }}
              >
                <div style={{ height: 64 }} />
                {items.map((item, i) => (
                  <div
                    key={item.id}
                    ref={(el) => { photoRowRefs.current[i] = el; }}
                    style={{ width: "100%", marginBottom: 8 }}
                  >
                    <img
                      src={item.photo_url}
                      alt=""
                      style={{ width: "100%", height: "auto", display: "block" }}
                    />
                    <div style={{
                      textAlign: "center", color: "rgba(255,255,255,0.4)",
                      fontSize: 12, padding: "4px 0 8px",
                    }}>
                      {i + 1} / {items.length}
                    </div>
                  </div>
                ))}
                <div style={{ height: 80 }} />
              </div>
            </div>
          )}

          {/* ── Desktop viewer: centered lightbox/slideshow ──────────────── */}
          {!isMobile && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center"
              style={{ backgroundColor: "rgba(0,0,0,0.9)" }}
              onClick={close}
            >
              <div
                className="relative flex items-center justify-center w-full h-full"
                onClick={(e) => e.stopPropagation()}
              >
                {items[selectedIndex] && (
                  <img
                    src={items[selectedIndex].photo_url}
                    alt=""
                    className="max-h-screen max-w-full object-contain px-16"
                  />
                )}

                {/* Close */}
                <button
                  type="button" onClick={close} aria-label="Закрыть"
                  className="absolute top-4 right-4 text-white text-2xl w-10 h-10 flex items-center justify-center rounded-full"
                  style={{ background: "rgba(0,0,0,0.5)" }}
                >×</button>

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
                    type="button" aria-label="Предыдущее"
                    onClick={() => setSelectedIndex((i) =>
                      i === null ? null : (i - 1 + items.length) % items.length
                    )}
                    className="absolute left-2 text-white text-3xl w-10 h-10 flex items-center justify-center rounded-full"
                    style={{ background: "rgba(0,0,0,0.5)" }}
                  >‹</button>
                )}

                {/* Next */}
                {items.length > 1 && (
                  <button
                    type="button" aria-label="Следующее"
                    onClick={() => setSelectedIndex((i) =>
                      i === null ? null : (i + 1) % items.length
                    )}
                    className="absolute right-2 text-white text-3xl w-10 h-10 flex items-center justify-center rounded-full"
                    style={{ background: "rgba(0,0,0,0.5)" }}
                  >›</button>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
