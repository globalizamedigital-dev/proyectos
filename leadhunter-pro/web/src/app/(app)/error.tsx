"use client";

import { useEffect } from "react";
import { AlertOctagon, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Error boundary del route group (app). Captura cualquier excepción no
 * tratada dentro de discover/analizar/leads/outreach/config y muestra
 * una pantalla limpia con dos opciones: reintentar o volver atrás.
 *
 * Importante: como es un boundary CLIENTE, se loguea aquí. En producción
 * con observabilidad activa, este logger se sustituye por uno que mande
 * a Cloud Logging o Sentry.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("(app) error boundary:", error);
  }, [error]);

  return (
    <div className="mx-auto flex w-full max-w-[900px] flex-col gap-8 px-6 py-16 lg:px-10">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span aria-hidden className="h-px w-10 bg-destructive" />
          <span className="label-eyebrow text-destructive">algo se ha roto</span>
        </div>
        <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
          La pantalla ha petado.
          <br />
          <span className="text-destructive">No es culpa tuya.</span>
        </h1>
        <p className="max-w-2xl text-[14px] leading-relaxed text-muted-foreground">
          Algo no esperado nos ha tirado el render. Lo más probable es que sea
          una respuesta rara de Supabase o del API. Reintenta. Si vuelve a
          pasar, copia el detalle de abajo y mándaselo a Mario.
        </p>
      </header>

      <div className="border border-destructive/40 bg-destructive/[0.06] p-6">
        <div className="mb-3 flex items-center gap-2 text-destructive">
          <AlertOctagon className="h-4 w-4" />
          <span className="label-eyebrow text-destructive">detalle técnico</span>
        </div>
        <div className="space-y-2 font-mono text-[12px]">
          <div>
            <span className="label-eyebrow">message</span>
            <div className="mt-1 break-all text-foreground/90">{error.message}</div>
          </div>
          {error.digest && (
            <div>
              <span className="label-eyebrow">digest</span>
              <div className="mt-1 break-all text-foreground/70">{error.digest}</div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button
          onClick={reset}
          className="rounded-none bg-primary uppercase tracking-wider"
        >
          <RefreshCcw className="mr-2 h-4 w-4" />
          Reintentar
        </Button>
        <Button
          variant="outline"
          onClick={() => window.history.back()}
          className="rounded-none border-border bg-transparent uppercase tracking-wider"
        >
          Volver atrás
        </Button>
      </div>
    </div>
  );
}
