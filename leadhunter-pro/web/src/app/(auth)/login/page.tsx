"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Crosshair, ArrowRight, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser";
import { cn } from "@/lib/utils";

/**
 * Login Cazador Globalizame · magic link.
 * Sin contraseñas. Solo emails del equipo Globalizame autorizados
 * (los das de alta a mano vía Supabase Auth → Users).
 */
export default function LoginPage() {
  // useSearchParams obliga a Suspense en App Router para que el prerender
  // estático no reviente. El boundary devuelve `null` durante el suspense
  // porque la página renderiza al instante en cliente.
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const params = useSearchParams();
  const next = params.get("next") || "/discover";

  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || state === "sending") return;
    setState("sending");
    setError(null);

    try {
      const supabase = getSupabaseBrowserClient();
      const { error: err } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        },
      });
      if (err) throw err;
      setState("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
      setState("error");
    }
  };

  return (
    <div className="relative flex min-h-screen items-center bg-background text-foreground">
      {/* Fondo de cuadrícula + halo verde sutil */}
      <div className="grid-pattern pointer-events-none absolute inset-0 opacity-40" />
      <div
        aria-hidden
        className="pointer-events-none absolute -left-32 top-1/3 h-96 w-96 rounded-full bg-primary/[0.05] blur-3xl"
      />

      <div className="relative mx-auto grid w-full max-w-5xl grid-cols-1 gap-16 px-6 md:grid-cols-2">
        {/* Columna izquierda: marca */}
        <div className="flex flex-col justify-center gap-4">
          <div className="flex items-center gap-3">
            <span aria-hidden className="h-px w-12 bg-primary" />
            <span className="label-eyebrow">acceso · equipo</span>
          </div>
          <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[56px]">
            cazador
            <br />
            <span className="text-primary">globalizame</span>
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
            Generador de leads B2B cualificados con fuentes oficiales españolas.
            Acceso solo para el equipo de Globalizame.
          </p>
          <div className="mt-6 flex items-center gap-2 text-[11px] tracking-wider text-muted-foreground">
            <Crosshair className="h-3.5 w-3.5 text-secondary" />
            <span>BORME · OSM · Cartociudad · PLACSP · AEPD · INE</span>
          </div>
        </div>

        {/* Columna derecha: formulario */}
        <div className="flex flex-col justify-center">
          <form
            onSubmit={handleSubmit}
            className="relative border border-border/80 bg-card p-8"
          >
            <div className="mb-6 flex items-center justify-between">
              <span className="label-eyebrow">expediente · login</span>
              <span className="text-[10px] tracking-wider text-muted-foreground">
                magic link
              </span>
            </div>

            <label className="mb-1.5 block">
              <span className="label-eyebrow">email del equipo</span>
            </label>
            <Input
              type="email"
              required
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu-email@globalizame.com"
              disabled={state === "sending" || state === "sent"}
              className={cn(
                "h-12 rounded-none border-0 border-b border-border/40 bg-transparent px-0 text-base shadow-none",
                "focus-visible:border-primary focus-visible:ring-0",
                "placeholder:text-muted-foreground/60"
              )}
            />

            <Button
              type="submit"
              disabled={state === "sending" || state === "sent" || !email.trim()}
              className={cn(
                "scanline-cta mt-8 h-12 w-full rounded-none bg-primary uppercase tracking-wider",
                "disabled:bg-primary/40"
              )}
            >
              {state === "sending" ? (
                <span className="relative z-[2] flex items-center gap-3">
                  <span className="relative h-1 w-24 overflow-hidden bg-primary-foreground/20">
                    <span className="scan-progress absolute inset-y-0 left-0 w-1/3 bg-primary-foreground" />
                  </span>
                  enviando
                </span>
              ) : state === "sent" ? (
                <span className="relative z-[2] flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  revisa tu email
                </span>
              ) : (
                <span className="relative z-[2] flex items-center gap-2">
                  enviar enlace
                  <ArrowRight className="h-4 w-4" />
                </span>
              )}
            </Button>

            {state === "sent" && (
              <p className="mt-4 border-l border-primary/60 bg-primary/[0.06] px-3 py-2 text-[12px] leading-relaxed text-foreground">
                Te hemos enviado un enlace a{" "}
                <span className="font-medium text-primary">{email}</span>. Ábrelo desde el mismo
                navegador.
              </p>
            )}

            {state === "error" && error && (
              <p className="mt-4 border-l border-destructive/60 bg-destructive/[0.08] px-3 py-2 text-[12px] leading-relaxed text-destructive">
                {error}
              </p>
            )}

            <p className="mt-8 text-[10px] tracking-wider text-muted-foreground/70">
              Solo emails autorizados por Globalizame. Si no tienes acceso,
              pídeselo a Mario.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
