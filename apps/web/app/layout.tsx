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
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-gray-50 font-sans antialiased text-gray-900">
        {children}
      </body>
    </html>
  );
}
