import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";

import { Header } from "@/components/Header";

import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-serif",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "DineOff",
  description: "Stop arguing. Let the group decide where to eat.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${fraunces.variable} ${outfit.variable} font-sans antialiased`}>
        <Header />
        <main className="mx-auto w-full max-w-6xl px-5 pb-16">{children}</main>
      </body>
    </html>
  );
}
