import { Crosshair } from "lucide-react";

/**
 * Estado vacío. Alineado a la izquierda a propósito: el centrado es
 * el reflejo automático del SaaS-slop. Aquí el operador lee de arriba a
 * abajo, por delante de la diana.
 */
export function EmptyState() {
  return (
    <div className="relative flex min-h-[280px] items-stretch overflow-hidden border border-border/60 bg-card">
      <div className="grid-pattern pointer-events-none absolute inset-0 opacity-50" />

      <div className="relative flex w-32 shrink-0 items-center justify-center border-r border-border/60 bg-background/40">
        <Crosshair
          className="h-16 w-16 stroke-[1] text-secondary"
          aria-hidden
        />
      </div>

      <div className="relative flex flex-col justify-center gap-3 px-8 py-10">
        <span className="label-eyebrow">status · idle</span>
        <h2 className="font-heading text-3xl font-light tracking-tight">
          Aún no hay leads.
        </h2>
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
          Configura el filtro y pulsa{" "}
          <span className="font-medium text-foreground">Buscar leads</span>. Te
          devolvemos empresas reales, no humo.
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] tracking-wider text-muted-foreground">
          <span className="label-eyebrow">tip</span>
          <span>
            empieza por{" "}
            <code className="bg-muted/60 px-1.5 py-0.5 text-foreground">
              asesoría fiscal en Sevilla
            </code>{" "}
            para ver el modelo en acción.
          </span>
        </div>
      </div>
    </div>
  );
}
