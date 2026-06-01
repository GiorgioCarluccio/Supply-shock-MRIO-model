import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Roboto_Mono } from "next/font/google";

import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { Providers } from "@/app/providers";
import { APP_SUBTITLE, APP_TITLE } from "@/lib/constants";

const atkinson = Atkinson_Hyperlegible({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-atkinson",
  display: "swap",
});

const mono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: `${APP_TITLE} — OpenEconomics`,
  description: APP_SUBTITLE,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${atkinson.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      {/* suppressHydrationWarning: browser extensions (e.g. Grammarly) inject
          attributes into <body> before React hydrates, which would otherwise
          trigger a spurious hydration-mismatch warning. */}
      <body suppressHydrationWarning>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
