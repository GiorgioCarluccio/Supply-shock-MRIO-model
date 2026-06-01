"use client";

import Image from "next/image";

import { APP_SUBTITLE, APP_TITLE } from "@/lib/constants";

/** Top bar: OpenEconomics logo (black on light) + project title. */
export function TopBar() {
  return (
    <header className="flex h-16 items-center gap-4 border-b border-grey-mid bg-paper px-5">
      <div className="flex items-center gap-3">
        <Image
          src="/logos/openeconomics-logo-black.png"
          alt="OpenEconomics"
          width={150}
          height={32}
          priority
          className="h-7 w-auto"
        />
        <span className="h-7 w-px bg-grey-mid" />
        <div className="leading-tight">
          <div className="text-sm font-semibold text-ink">{APP_TITLE}</div>
          <div className="text-[11px] text-grey-text">{APP_SUBTITLE}</div>
        </div>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span className="rounded-full border border-grey-mid px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-grey-text">
          Static demo
        </span>
      </div>
    </header>
  );
}
