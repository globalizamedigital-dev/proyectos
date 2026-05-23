"use client";

import { useEffect, useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  SOURCE_INDICATORS,
  type SourceIndicator,
  type SourceState,
} from "@/app/(app)/discover/_data/source-status";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/**
 * Barra inferior tipo bandeja de avisos de terminal. Cada fuente es un
 * dot con bloom radial. El operador sabe de un vistazo qué está vivo.
 *
 * Estrategia de datos: hace polling cada 30s a `/health/sources`. Si el
 * API no responde, se queda con los indicadores mock para no romper la
 * UI (mejor un dato estimado que un vacío).
 */
export function StatusBar() {
  const [sources, setSources] = useState<readonly SourceIndicator[]>(SOURCE_INDICATORS);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const live = await apiClient.sources();
        if (cancelled || !Array.isArray(live) || live.length === 0) return;
        setSources(
          live.map((s) => ({
            key: s.source,
            label: s.source,
            state: normalizeState(s.state),
            hint: s.detail ?? `Estado: ${s.state}`,
          })),
        );
      } catch {
        // API offline → mantener los mocks. Silencioso a propósito.
      }
    };

    poll();
    const id = window.setInterval(poll, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const okCount = sources.filter((s) => s.state === "ok").length;

  // Helper local: normaliza cualquier estado del backend a los 3 buckets
  // visuales (ok / stub / down). No es exhaustivo a propósito: cualquier
  // estado desconocido se pinta como "down".
  function normalizeState(raw: string): SourceState {
    if (raw === "ok") return "ok";
    if (raw === "stub" || raw === "js-spa" || raw === "requires-cert" || raw === "blocked") {
      return "stub";
    }
    return "down";
  }

  return (
    <footer className="relative z-20 flex h-9 shrink-0 items-center justify-between border-t border-border/60 bg-background/90 px-4 backdrop-blur">
      <div className="flex items-center gap-2 text-[10px] tracking-wider text-muted-foreground">
        <span className="label-eyebrow text-[9px]">live</span>
        <span className="tabular-nums">
          {okCount.toString().padStart(2, "0")}/
          {sources.length.toString().padStart(2, "0")} fuentes
        </span>
      </div>

      <TooltipProvider delay={80}>
        <ul className="flex items-center gap-4">
          {sources.map((src) => (
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
