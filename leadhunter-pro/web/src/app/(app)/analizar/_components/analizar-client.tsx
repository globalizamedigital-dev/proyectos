"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Microscope, ServerCrash, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { apiClient, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { AssertionBanner, type AssertionMismatch } from "./assertion-banner";
import { Ficha, type AnalyzeResult } from "./ficha";

const NIF_RE = /^[A-HJNPQRSUVW]\d{7}[0-9A-J]$|^\d{8}[A-Z]$|^[XYZ]\d{7}[A-Z]$/i;

/** Detecta si la entrada parece un NIF/CIF/NIE. */
function looksLikeNif(input: string): boolean {
  return NIF_RE.test(input.replace(/\s|-/g, "").trim());
}

export function AnalizarClient() {
  const [input, setInput] = useState("");
  const [isCustomerClaim, setIsCustomerClaim] = useState(false);
  const [hasDpoClaim, setHasDpoClaim] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [mismatches, setMismatches] = useState<AssertionMismatch[]>([]);
  const [error, setError] = useState<{ message: string; demoFallback: boolean } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setMismatches([]);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const claims: Record<string, boolean> = {};
    if (isCustomerClaim) claims.is_customer = true;
    if (hasDpoClaim) claims.has_dpo = true;

    try {
      const payload = (await apiClient.analyze(
        {
          input: input.trim(),
          premium: false,
          user_claims: Object.keys(claims).length ? claims : undefined,
        },
        controller.signal,
      )) as AnalyzeResult & { assertion_mismatches?: AssertionMismatch[] };
      setResult(payload);
      setMismatches(payload.assertion_mismatches ?? []);
    } catch (err) {
      if (controller.signal.aborted) return;
      const apiErr = err instanceof ApiError ? err : null;
      const message = apiErr
        ? apiErr.status === 0
          ? "El API no responde — arranca uvicorn localhost:8000"
          : `${apiErr.status} · ${apiErr.message}`
        : err instanceof Error
          ? err.message
          : "Error desconocido";
      setError({ message, demoFallback: apiErr?.status === 0 });
    } finally {
      setBusy(false);
    }
  };

  const isNif = input.length >= 9 && looksLikeNif(input);

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-8 px-6 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span aria-hidden className="h-px w-10 bg-primary" />
          <span className="label-eyebrow">módulo · analizar</span>
        </div>
        <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
          Pega un NIF o razón social.
          <br />
          <span className="text-primary">Te lo desnudamos.</span>
        </h1>
        <p className="max-w-2xl text-[14px] leading-relaxed text-muted-foreground">
          Cruzamos BORME, PLACSP, Infosubvenciones y AEPD. Devolvemos timeline
          registral, decisores, contratos públicos y compliance. Si afirmas
          algo y no se sostiene en los datos, te lo marcamos como
          assertion_mismatch.
        </p>
      </header>

      <form
        onSubmit={submit}
        className="hero-glow relative isolate overflow-hidden rounded-none border border-border/80 bg-card"
      >
        <div className="grid-pattern pointer-events-none absolute inset-0 opacity-60" />

        <div className="relative flex items-center justify-between border-b border-border/60 px-6 py-3">
          <div className="flex items-center gap-2">
            <span className="label-eyebrow">expediente · 02 · analizar</span>
            <span className="h-3 w-px bg-border" />
            <span className="text-[11px] tracking-wider text-muted-foreground">
              entrada NIF o razón social
            </span>
          </div>
          <code className="hidden text-[10px] tracking-wider text-muted-foreground/70 md:block">
            POST /analyze {`{input,premium,user_claims}`}
          </code>
        </div>

        <div className="relative p-6">
          <div className="mb-1.5 flex items-center gap-2">
            <span className="label-eyebrow text-primary/80 tabular-nums">01</span>
            <span className="label-eyebrow">Empresa</span>
            {input.length >= 9 && (
              <span
                className={cn(
                  "label-eyebrow ml-auto",
                  isNif ? "text-primary" : "text-secondary",
                )}
              >
                {isNif ? "NIF detectado" : "razón social"}
              </span>
            )}
          </div>
          <Input
            autoFocus
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="B41234567   o   Asesoría García S.L."
            className={cn(
              "h-12 rounded-none border-0 border-b border-border/40 bg-transparent px-0 text-base font-medium shadow-none",
              "focus-visible:border-primary focus-visible:ring-0",
              "placeholder:text-muted-foreground/60",
            )}
          />

          {/* Claims del operador */}
          <div className="mt-6 flex flex-col gap-3 border-t border-border/60 pt-5">
            <span className="label-eyebrow">tus afirmaciones (opcional)</span>
            <p className="text-[11px] tracking-wide text-muted-foreground/70">
              Marca lo que afirmes sobre la empresa. Si no se sostiene en las
              fuentes públicas, te lo marcamos.
            </p>
            <label className="flex cursor-pointer select-none items-center gap-3">
              <Switch
                checked={isCustomerClaim}
                onCheckedChange={setIsCustomerClaim}
                className="data-[state=checked]:bg-secondary"
              />
              <span className="text-sm">Es cliente nuestro (debería tener trazas públicas)</span>
            </label>
            <label className="flex cursor-pointer select-none items-center gap-3">
              <Switch
                checked={hasDpoClaim}
                onCheckedChange={setHasDpoClaim}
                className="data-[state=checked]:bg-secondary"
              />
              <span className="text-sm">Tiene DPO registrado en AEPD</span>
            </label>
          </div>
        </div>

        <div className="relative flex items-center justify-between border-t border-border/60 bg-background/40 px-6 py-4">
          <span className="text-[11px] tracking-wider text-muted-foreground">
            Tarda unos segundos. Cruzamos hasta 5 fuentes en paralelo.
          </span>
          <Button
            type="submit"
            disabled={busy || !input.trim()}
            className={cn(
              "scanline-cta h-12 min-w-[180px] rounded-none bg-primary px-6 uppercase tracking-wider",
              "disabled:bg-primary/40",
            )}
          >
            {busy ? (
              <span className="flex items-center gap-3">
                <span className="relative h-1 w-24 overflow-hidden bg-primary-foreground/20">
                  <span className="scan-progress absolute inset-y-0 left-0 w-1/3 bg-primary-foreground" />
                </span>
                <span className="text-xs">cruzando…</span>
              </span>
            ) : (
              <span className="relative z-[2] flex items-center gap-2">
                <Microscope className="h-4 w-4" />
                Analizar
                <ArrowRight className="h-4 w-4" />
              </span>
            )}
          </Button>
        </div>
      </form>

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
            <div className="label-eyebrow mb-0.5">error</div>
            <div className={error.demoFallback ? "text-[var(--warning)]" : "text-destructive"}>
              {error.message}
            </div>
          </div>
          <button onClick={() => setError(null)} aria-label="cerrar">
            <XCircle className="h-4 w-4 text-muted-foreground hover:text-foreground" />
          </button>
        </div>
      )}

      <AssertionBanner mismatches={mismatches} />

      {result && <Ficha result={result} />}
    </div>
  );
}
