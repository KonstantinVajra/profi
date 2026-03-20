"use client";

import { useEffect, useState } from "react";

interface PhotoItem {
  id: string;
  photo_url: string;
  display_order: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function StyleGridClient({ photoSetId }: { photoSetId: string }) {
  const [items, setItems] = useState<PhotoItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/public/photo-sets/${photoSetId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.items) setItems(data.items);
      })
      .catch((err) => console.error("StyleGrid fetch failed:", err))
      .finally(() => setLoading(false));
  }, [photoSetId]);

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
      <div className="grid grid-cols-3 gap-2">
        {items.map((item) => (
          <img
            key={item.id}
            src={item.photo_url}
            alt=""
            className="w-full h-32 object-cover rounded-xl"
          />
        ))}
      </div>
    </section>
  );
}
