import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SOURCE_INDICATORS } from "@/app/(app)/discover/_data/source-status";
import { cn } from "@/lib/utils";

/**
 * Barra inferior tipo bandeja de avisos de terminal. Cada fuente es un
 * dot con bloom radial; el operador sabe de un vistazo qué está vivo.
 */
export function StatusBar() {
  const okCount = SOURCE_INDICATORS.filter((s) => s.state === "ok").length;

  return (
    <footer className="relative z-20 flex h-9 shrink-0 items-center justify-between border-t border-border/60 bg-background/90 px-4 backdrop-blur">
      <div className="flex items-center gap-2 text-[10px] tracking-wider text-muted-foreground">
        <span className="label-eyebrow text-[9px]">live</span>
        <span className="tabular-nums">
          {okCount.toString().padStart(2, "0")}/
          {SOURCE_INDICATORS.length.toString().padStart(2, "0")} fuentes
        </span>
      </div>

      <TooltipProvider delay={80}>
        <ul className="flex items-center gap-4">
          {SOURCE_INDICATORS.map((src) => (
            <Tooltip key={src.key}>
              <TooltipTrigger
                render={
                  <li className="flex cursor-default items-center gap-1.5 text-[10px] tracking-wider text-muted-foreground">
                    <span
                      aria-hidden
                      className={cn(
                        "h-[7px] w-[7px] rounded-full",
                        src.state === "ok" && "bg-primary dot-bloom",
                        src.state === "stub" &&
                          "bg-[var(--warning)] dot-bloom-orange",
                        src.state === "down" && "bg-muted-foreground/40"
                      )}
                    />
                    <span
                      className={cn(
                        "font-medium",
                        src.state === "ok" && "text-foreground/80"
                      )}
                    >
                      {src.label}
                    </span>
                  </li>
                }
              />
              <TooltipContent
                side="top"
                sideOffset={8}
                className="rounded-none border border-border bg-background text-xs"
              >
                <div className="max-w-[220px]">
                  <div className="label-eyebrow mb-0.5">{src.state}</div>
                  <div className="font-medium">{src.label}</div>
                  <div className="text-muted-foreground">{src.hint}</div>
                </div>
              </TooltipContent>
            </Tooltip>
          ))}
        </ul>
      </TooltipProvider>

      <div className="hidden items-center gap-2 text-[10px] tracking-wider text-muted-foreground md:flex">
        <span className="tabular-nums">SVQ · 2026</span>
        <span className="h-3 w-px bg-border" />
        <span className="label-eyebrow text-[9px]">snapshot</span>
      </div>
    </footer>
  );
}
