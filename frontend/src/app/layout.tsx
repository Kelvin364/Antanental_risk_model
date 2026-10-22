import type { Metadata } from "next";

import { ServiceStatus } from "@/components/ServiceStatus";

import "./globals.css";

export const metadata: Metadata = {
  title: "Antenatal Caseload Prototype",
  description: "Research prototype. Synthetic cases only. Not for clinical use.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans leading-normal">
        <header className="border-b border-line bg-surface">
          <div className="mx-auto max-w-[980px] px-4 py-3.5">
            <b className="text-[17px]">Antenatal Caseload</b>
          </div>
        </header>
        {children}
        <footer className="mx-auto max-w-[980px] px-4 pb-10 text-xs text-muted">
          <ServiceStatus />
        </footer>
      </body>
    </html>
  );
}
