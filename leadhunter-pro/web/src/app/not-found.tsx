import Link from "next/link";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background px-6 text-foreground">
      <div className="grid-pattern pointer-events-none absolute inset-0 opacity-30" />
      <div className="relative grid w-full max-w-3xl grid-cols-1 gap-8 md:grid-cols-[120px_1fr]">
        <div className="flex items-start justify-center md:items-center">
          <Compass className="h-20 w-20 stroke-[1] text-secondary" aria-hidden />
        </div>
        <div className="flex flex-col gap-4">
          <span className="label-eyebrow">404 · ruta no encontrada</span>
          <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
            Aquí <span className="text-primary">no hay nada.</span>
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
            La URL que has pedido no existe o se movió. Vuelve al inicio y
            sigue desde ahí.
          </p>
          <div>
            <Link
              href="/discover"
              className="inline-flex h-11 items-center gap-2 bg-primary px-5 text-sm font-medium uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Ir a Discover
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
