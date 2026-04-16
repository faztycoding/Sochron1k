import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/layout/navbar";

export const metadata: Metadata = {
  title: "Sochron1k — ระบบวิเคราะห์ Forex อัจฉริยะ",
  description: "วิเคราะห์ EUR/USD, USD/JPY, EUR/JPY, GBP/USD, AUD/USD ด้วย AI + Technical Indicators + ข่าวเรียลไทม์",
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
      <body className="antialiased min-h-screen">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
