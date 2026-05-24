"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  Microscope,
  Database,
  SlidersHorizontal,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: typeof Compass;
  shortcut: string;
}

// Cazador MVP: solo descubrir + cualificar + persistir. Outreach (email,
// WhatsApp) queda fuera del MVP. Si vuelve al producto, se reañade Outreach
// como item 04 entre Leads y Config.
const NAV: readonly NavItem[] = [
  { label: "Discover", href: "/discover", icon: Compass, shortcut: "01" },
  { label: "Analizar", href: "/analizar", icon: Microscope, shortcut: "02" },
  { label: "Leads", href: "/leads", icon: Database, shortcut: "03" },
  { label: "Config", href: "/config", icon: SlidersHorizontal, shortcut: "04" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="relative z-10 flex w-16 shrink-0 flex-col border-r border-border/60 bg-background">
      {/* índice ministerial arriba */}
      <div className="flex h-12 items-center justify-center border-b border-border/60">
        <span className="label-eyebrow text-[9px]">idx</span>
      </div>

      <TooltipProvider delay={120}>
        <ul className="flex flex-1 flex-col gap-1 py-3">
          {NAV.map((item) => {
            const active = pathname?.startsWith(item.href) ?? false;
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Tooltip>
                  <TooltipTrigger
                    render={
                      <Link
                        href={item.href}
                        className={cn(
                          "group relative mx-2 flex h-11 flex-col items-center justify-center gap-0.5 rounded-none border-l-2 border-transparent transition-colors",
                          active
                            ? "border-l-primary bg-primary/[0.06] text-primary"
                            : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-[18px] w-[18px] stroke-[1.5]",
                            active && "text-primary"
                          )}
                        />
                        <span className="text-[9px] font-medium tabular-nums tracking-wider opacity-60">
                          {item.shortcut}
                        </span>
                      </Link>
                    }
                  />
                  <TooltipContent
                    side="right"
                    sideOffset={8}
                    className="rounded-none border border-border bg-background font-sans text-xs"
                  >
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              </li>
            );
          })}
        </ul>
      </TooltipProvider>

      {/* Cuño inferior: aporta peso visual, referencia a documentos oficiales */}
      <div className="border-t border-border/60 py-3 text-center">
        <div
          className="mx-auto mb-1 h-1 w-1 rounded-full bg-primary"
          aria-hidden
        />
        <span className="label-eyebrow text-[8px]">ES · 2026</span>
      </div>
    </nav>
  );
}
