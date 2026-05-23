"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { Download, FileJson, ServerCrash, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchForm, type SearchFormValues } from "./search-form";
import { EmptyState } from "./empty-state";
import { ResultsTable } from "./results-table";
import { LeadDetailSheet } from "./lead-detail-sheet";
import { MOCK_LEADS, type Lead } from "@/app/(app)/discover/_data/mock-leads";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Orquestador cliente del Discover. Llama al API real `/discover`.
 * Si el API no está disponible (dev sin uvicorn arriba, o fallo de red)
 * cae a un dataset mock y muestra un banner naranja para que el
 * operador sepa que está viendo demo, no datos reales.
 */
export function DiscoverClient() {
  const [results, setResults] = useState<Lead[] | null>(null);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [, startTransition] = useTransition();
  const [isSearching, setIsSearching] = useState(false);
  const [lastQuery, setLastQuery] = useState<SearchFormValues | null>(null);
  const [error, setError] = useState<{ message: string; demoFallback: boolean } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Cancela cualquier petición en vuelo al desmontar el componente.
  useEffect(() => () => abortRef.current?.abort(), []);

  const handleSearch = async (values: SearchFormValues) => {
    setIsSearching(true);
    setLastQuery(values);
    setError(null);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const payload = await apiClient.discover(
        { geo: values.province, sector: values.sector, max: values.max, enrich: values.enrich },
        controller.signal,
      );
      startTransition(() => {
        // Coerción cómoda: el backend devuelve la forma camelCase ya conocida.
        const leads = payload.candidates as unknown as Lead[];
        setResults(leads);
        setIsSearching(false);
      });
    } catch (err) {
      if (controller.signal.aborted) return;
      const apiErr = err instanceof ApiError ? err : null;
      const message = apiErr
        ? apiErr.status === 0
          ? "El API no responde — comprobando localhost:8000…"
          : `${apiErr.status} · ${apiErr.message}`
        : err instanceof Error
          ? err.message
          : "Error desconocido";

      // Fallback a mock: solo si el API está caído (status 0), no si fue
      // 401/403/4xx que el operador debe ver.
      const demoFallback = apiErr?.status === 0;
      if (demoFallback) {
        setResults([...MOCK_LEADS].slice(0, values.max));
      }
      setError({ message, demoFallback });
      setIsSearching(false);
    }
  };

  const downloadJSON = () => {
    if (!results) return;
    const blob = new Blob([JSON.stringify(results, null, 2)], {
      type: "application/json",
    });
    triggerDownload(blob, `leadhunter-discover-${Date.now()}.json`);
  };

  const downloadCSV = () => {
    if (!results) return;
    const header = [
      "razonSocial",
      "nif",
      "score",
      "grade",
      "decisor",
      "email",
      "phone",
      "domain",
      "city",
      "sources",
    ];
    const rows = results.map((l) =>
      [
        l.razonSocial,
        l.nif ?? "",
        l.score,
        l.grade,
        l.decisor ?? "",
        l.email ?? "",
        l.phone ?? "",
        l.domain ?? "",
        l.city,
        l.sources.join("|"),
      ]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(",")
    );
    const csv = [header.join(","), ...rows].join("\n");
    const blob = new Blob(["﻿" + csv], {
      type: "text/csv;charset=utf-8",
    });
    triggerDownload(blob, `leadhunter-discover-${Date.now()}.csv`);
  };

  const withEmail = results?.filter((l) => l.email).length ?? 0;
  const withoutDomain = results?.filter((l) => !l.domain).length ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-8 px-6 py-8 lg:px-10 lg:py-10">
      {/* Header de sección */}
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="h-px w-10 bg-primary"
          />
          <span className="label-eyebrow">módulo · discover</span>
        </div>
        <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
          Descubre empresas reales,
          <br />
          <span className="text-primary">no listas compradas.</span>
        </h1>
        <p className="max-w-2xl text-[14px] leading-relaxed text-muted-foreground">
          Cruzamos BORME, OpenStreetMap, Cartociudad, PLACSP, AEPD e INE en
          tiempo real para devolverte un puñado de empresas cualificadas con
          decisor, email y teléfono — listas para entrar en outreach.
        </p>
      </header>

      <SearchForm isSearching={isSearching} onSubmit={handleSearch} />

      {/* Banner de error / fallback a demo */}
      {error && (
        <div
          className={
            error.demoFallback
              ? "flex items-start gap-3 border border-[var(--warning)]/40 bg-[var(--warning)]/[0.06] px-5 py-3"
              : "flex items-start gap-3 border border-destructive/40 bg-destructive/[0.06] px-5 py-3"
          }
        >
          {error.demoFallback ? (
            <ServerCrash className="mt-0.5 h-4 w-4 shrink-0 text-[var(--warning)]" />
          ) : (
            <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          )}
          <div className="flex-1 text-[12px] leading-relaxed">
            <div className="label-eyebrow mb-0.5">
              {error.demoFallback ? "modo demo · API offline" : "error"}
            </div>
            <div className={error.demoFallback ? "text-[var(--warning)]" : "text-destructive"}>
              {error.message}
            </div>
            {error.demoFallback && (
              <div className="mt-1 text-muted-foreground">
                Estás viendo el dataset de ejemplo. Arranca el backend con{" "}
                <code className="bg-muted/60 px-1 py-0.5 text-foreground">
                  cd api && uvicorn main:app --reload
                </code>{" "}
                para datos reales.
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="cerrar"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Resultados */}
      {results === null ? (
        <EmptyState />
      ) : (
        <section className="flex flex-col gap-3">
          <div className="flex flex-col items-start justify-between gap-3 border border-border/60 bg-card px-5 py-3 md:flex-row md:items-center">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[12px] tabular-nums text-muted-foreground">
              <span className="flex items-baseline gap-1.5">
                <span className="font-heading text-[22px] font-light text-foreground">
                  {results.length.toString().padStart(2, "0")}
                </span>
                <span className="label-eyebrow">leads encontrados</span>
              </span>
              <span className="h-3 w-px bg-border" />
              <span className="flex items-baseline gap-1.5">
                <span className="font-heading text-[18px] font-light text-primary">
                  {withEmail.toString().padStart(2, "0")}
                </span>
                <span className="label-eyebrow">con email</span>
              </span>
              <span className="h-3 w-px bg-border" />
              <span className="flex items-baseline gap-1.5">
                <span className="font-heading text-[18px] font-light text-[var(--warning)]">
                  {withoutDomain.toString().padStart(2, "0")}
                </span>
                <span className="label-eyebrow">sin dominio</span>
              </span>
              {lastQuery && (
                <>
                  <span className="h-3 w-px bg-border" />
                  <span className="text-[11px] tracking-wide text-muted-foreground/80">
                    <span className="text-foreground/80">{lastQuery.sector}</span>
                    <span className="mx-1.5 text-border">·</span>
                    {lastQuery.province}
                  </span>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={downloadCSV}
                className="h-8 rounded-none border-border/80 bg-transparent text-[11px] uppercase tracking-wider"
              >
                <Download className="mr-1.5 h-3.5 w-3.5" />
                CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={downloadJSON}
                className="h-8 rounded-none border-border/80 bg-transparent text-[11px] uppercase tracking-wider"
              >
                <FileJson className="mr-1.5 h-3.5 w-3.5" />
                JSON
              </Button>
            </div>
          </div>

          <ResultsTable leads={results} onSelect={setSelected} />
        </section>
      )}

      <LeadDetailSheet lead={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
