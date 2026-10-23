import type { Metadata } from "next";

import { AppHeader } from "@/components/AppHeader";
import { ServiceStatus } from "@/components/ServiceStatus";
import { SessionProvider } from "@/lib/session";

import "./globals.css";

export const metadata: Metadata = {
  title: "Antenatal Caseload Prototype",
  description: "Research prototype. Synthetic cases only. Not for clinical use.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans leading-normal">
        <SessionProvider>
          <AppHeader />
          {children}
          <footer className="mx-auto max-w-[980px] px-4 pb-10 text-xs text-muted">
            <ServiceStatus />
          </footer>
        </SessionProvider>
      </body>
    </html>
  );
}
