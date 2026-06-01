"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";

/** Left navigation. Active item uses the Lime accent marker. */
export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-0.5 p-3">
      {NAV_ITEMS.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "relative rounded-card px-3 py-2 text-sm transition-colors",
              active
                ? "bg-grey-light font-semibold text-ink"
                : "text-grey-text hover:bg-grey-light hover:text-ink",
            )}
          >
            {active && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-full bg-lime" />
            )}
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
