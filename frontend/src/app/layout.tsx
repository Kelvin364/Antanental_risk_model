import type { Metadata } from "next";
import { Host_Grotesk, IBM_Plex_Mono } from "next/font/google";

import { AppHeader } from "@/components/AppHeader";
import { ServiceStatus } from "@/components/ServiceStatus";
import { SessionProvider } from "@/lib/session";

import "./globals.css";

// The design's typefaces, fetched at build time and served from this site.
const host = Host_Grotesk({ subsets: ["latin"], variable: "--font-host", display: "swap" });
const plex = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Antenatal Caseload Prototype",
  description: "Research prototype. Synthetic cases only. Not for clinical use.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${host.variable} ${plex.variable}`}>
      <body className="font-sans leading-normal">
        <SessionProvider>
          <AppHeader />
          {children}
          <footer className="mx-auto max-w-[1000px] px-4 pb-10 text-xs text-muted">
            <ServiceStatus />
          </footer>
        </SessionProvider>
      </body>
    </html>
  );
}
