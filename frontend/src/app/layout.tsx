import type { Metadata } from "next";
import "./globals.css";
import "./app.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = { title: "ФСП Оренбургская область", description: "Платформа спортивного программирования Оренбургской области" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><head><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" /><link href="https://fonts.googleapis.com/css2?family=Rubik:wght@500;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet" /></head><body><AppShell>{children}</AppShell></body></html>;
}
