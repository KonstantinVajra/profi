export interface PhotoSetItem {
  id: string;
  photo_url: string;
  display_order: number;
}

export interface PhotoSet {
  id: string;
  name: string | null;
  category_key: string | null;
  items: PhotoSetItem[];
}

export interface PresetAlbumSummary {
  id: string;
  name: string | null;
}