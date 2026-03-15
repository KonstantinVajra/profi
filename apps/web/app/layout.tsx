import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Landing Reply",
  description: "AI-powered freelance reply generator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
