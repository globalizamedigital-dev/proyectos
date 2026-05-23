"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ExternalLink } from "lucide-react";
import { ScoreChip } from "@/components/score-chip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Lead } from "@/app/(app)/discover/_data/mock-leads";

interface ResultsTableProps {
  leads: Lead[];
  onSelect(lead: Lead): void;
}

type SortKey =
  | "score"
  | "razonSocial"
  | "decisor"
  | "email"
  | "phone"
  | "domain";
type SortDir = "asc" | "desc";

const COLUMNS: readonly {
  key: SortKey;
  label: string;
  width: string;
  align?: "left" | "right";
}[] = [
  { key: "score", label: "Score", width: "w-[88px]" },
  { key: "razonSocial", label: "Empresa", width: "min-w-[220px]" },
  { key: "decisor", label: "Decisor", width: "min-w-[160px]" },
  { key: "email", label: "Email", width: "min-w-[220px]" },
  { key: "phone", label: "Teléfono", width: "w-[150px]" },
  { key: "domain", label: "Dominio", width: "min-w-[160px]" },
];

export function ResultsTable({ leads, onSelect }: ResultsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const out = [...leads];
    out.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "score") return (a.score - b.score) * dir;
      const av = String((a as unknown as Record<string, unknown>)[sortKey] ?? "");
      const bv = String((b as unknown as Record<string, unknown>)[sortKey] ?? "");
      return av.localeCompare(bv, "es", { sensitivity: "base" }) * dir;
    });
    return out;
  }, [leads, sortKey, sortDir]);

  const toggleSort = (k: SortKey) => {
    if (k === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      setSortDir(k === "score" ? "desc" : "asc");
    }
  };

  return (
    <div className="relative overflow-hidden border border-border/60 bg-card">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border/80 bg-background/40">
              {COLUMNS.map((col) => {
                const active = sortKey === col.key;
                const Icon = !active
                  ? ArrowUpDown
                  : sortDir === "asc"
                    ? ArrowUp
                    : ArrowDown;
                return (
                  <th
                    key={col.key}
                    className={cn(
                      "h-10 px-4 text-left",
                      col.width
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(col.key)}
                      className={cn(
                        "label-eyebrow flex items-center gap-1.5 transition-colors",
                        active
                          ? "text-primary"
                          : "hover:text-foreground"
                      )}
                    >
                      {col.label}
                      <Icon className="h-3 w-3" />
                    </button>
                  </th>
                );
              })}
              <th className="h-10 w-[160px] px-4 text-left">
                <span className="label-eyebrow">Fuentes</span>
              </th>
              <th className="w-12" aria-hidden />
            </tr>
          </thead>
          <tbody>
            {sorted.map((lead, idx) => (
              <tr
                key={lead.id}
                onClick={() => onSelect(lead)}
                className="row-accent row-in cursor-pointer border-b border-border/40 transition-colors hover:bg-muted/30"
                style={{ animationDelay: `${idx * 18}ms` }}
              >
                <td className="px-4 py-3 align-middle">
                  <ScoreChip score={lead.score} grade={lead.grade} size="sm" />
                </td>
                <td className="px-4 py-3 align-middle">
                  <div className="flex flex-col">
                    <span className="font-medium leading-tight">
                      {lead.razonSocial}
                    </span>
                    <span className="mt-0.5 text-[11px] tracking-wide text-muted-foreground">
                      {lead.city}
                      {lead.nif ? ` · ${lead.nif}` : ""}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 align-middle">
                  {lead.decisor ? (
                    <div className="flex flex-col">
                      <span className="text-sm">{lead.decisor}</span>
                      {lead.decisorRole && (
                        <span className="text-[11px] tracking-wide text-muted-foreground">
                          {lead.decisorRole}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground/60">—</span>
                  )}
                </td>
                <td className="px-4 py-3 align-middle">
                  {lead.email ? (
                    <span className="font-mono text-[12.5px] text-foreground/90">
                      {lead.email}
                    </span>
                  ) : (
                    <span className="text-muted-foreground/60">—</span>
                  )}
                </td>
                <td className="px-4 py-3 align-middle font-mono tabular-nums text-[12.5px] text-foreground/80">
                  {lead.phone ?? <span className="text-muted-foreground/60">—</span>}
                </td>
                <td className="px-4 py-3 align-middle">
                  {lead.domain ? (
                    <a
                      href={`https://${lead.domain}`}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-[12.5px] text-secondary underline decoration-secondary/40 underline-offset-4 transition-colors hover:text-primary hover:decoration-primary"
                    >
                      {lead.domain}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span className="text-muted-foreground/60">—</span>
                  )}
                </td>
                <td className="px-4 py-3 align-middle">
                  <div className="flex flex-wrap gap-1">
                    {lead.sources.slice(0, 3).map((s) => (
                      <Badge
                        key={s}
                        variant="outline"
                        className="rounded-none border-border/70 bg-transparent px-1.5 py-0 font-mono text-[9px] uppercase tracking-wider text-muted-foreground"
                      >
                        {s}
                      </Badge>
                    ))}
                    {lead.sources.length > 3 && (
                      <Badge
                        variant="outline"
                        className="rounded-none border-border/70 bg-transparent px-1.5 py-0 font-mono text-[9px] tracking-wider text-muted-foreground"
                      >
                        +{lead.sources.length - 3}
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="pr-4 align-middle text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(lead);
                    }}
                    className="h-7 rounded-none px-2 text-[10px] uppercase tracking-wider text-muted-foreground hover:bg-primary/[0.08] hover:text-primary"
                  >
                    abrir
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
