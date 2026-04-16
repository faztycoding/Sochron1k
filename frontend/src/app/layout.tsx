import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sochron1k — ระบบวิเคราะห์ Forex อัจฉริยะ",
  description: "วิเคราะห์ EUR/USD, USD/JPY, EUR/JPY ด้วย AI และ Technical Indicators",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Thai:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased min-h-screen">{children}</body>
    </html>
  );
}
