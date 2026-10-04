import type { Metadata } from "next";
import { Arbutus_Slab, Fraunces, Outfit } from "next/font/google";

import { AuthProvider } from "@/components/AuthProvider";
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

const display = Arbutus_Slab({
  subsets: ["latin"],
  variable: "--font-display",
  weight: "400",
});

export const metadata: Metadata = {
  title: "Nomly",
  description: "Stop arguing. Let the group decide where to eat.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${fraunces.variable} ${outfit.variable} font-sans antialiased`}>
        <AuthProvider>
          <Header />
          <main className="mx-auto w-full max-w-6xl px-5 pb-16">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
