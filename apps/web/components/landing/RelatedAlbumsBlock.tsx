"use client";

import { useState } from "react";
import { StyleGridClient } from "@/components/landing/StyleGridClient";
import { getPresetAlbumsByCategory } from "@/lib/api";

interface AlbumSummary {
  id: string;
  name: string | null;
}

export function RelatedAlbumsBlock({ categoryKey }: { categoryKey: string }) {
  const [albums, setAlbums] = useState<AlbumSummary[] | null>(null);
  const [hasContent, setHasContent] = useState<boolean | null>(null); // null = unknown
  const [loading, setLoading] = useState(false);
  const [openAlbumId, setOpenAlbumId] = useState<string | null>(null);
  const [listVisible, setListVisible] = useState(false);

  async function handleOpen() {
    if (listVisible) {
      setListVisible(false);
      setOpenAlbumId(null);
      return;
    }

    if (albums !== null) {
      setListVisible(true);
      return;
    }

    setLoading(true);
    try {
      const data = (await getPresetAlbumsByCategory(categoryKey)) as AlbumSummary[];
      if (!data || data.length === 0) {
        setHasContent(false);
        return;
      }
      setAlbums(data);
      setHasContent(true);
      setListVisible(true);
    } catch {
      setHasContent(false);
    } finally {
      setLoading(false);
    }
  }

  function handleAlbumClick(id: string) {
    setOpenAlbumId((prev) => (prev === id ? null : id));
  }

  // Hide permanently once we know there is no content
  if (hasContent === false) return null;

  return (
    <section className="px-4 pb-6">
      {/* Trigger pill */}
      <button
        type="button"
        onClick={handleOpen}
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-100 px-4 py-1.5 text-sm text-amber-900 hover:bg-amber-200 transition-colors disabled:opacity-50"
      >
        {loading ? "Загрузка..." : "Посмотреть похожие съёмки"}
        {listVisible ? (
          <span className="text-xs">↑</span>
        ) : (
          <span className="text-xs">↓</span>
        )}
      </button>

      {/* Album list */}
      {listVisible && albums && albums.length > 0 && (
        <div className="mt-3 space-y-2">
          {albums.map((album) => (
            <div key={album.id}>
              {/* Album title pill */}
              <button
                type="button"
                onClick={() => handleAlbumClick(album.id)}
                className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 px-4 py-1.5 text-sm text-gray-700 hover:border-gray-400 hover:text-gray-900 transition-colors"
              >
                {album.name ?? album.id}
                {openAlbumId === album.id ? (
                  <span className="text-xs">↑</span>
                ) : (
                  <span className="text-xs">↓</span>
                )}
              </button>

              {/* Album gallery — opens below the pill */}
              {openAlbumId === album.id && (
                <div className="mt-2">
                  <StyleGridClient photoSetId={album.id} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}