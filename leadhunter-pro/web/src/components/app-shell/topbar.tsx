import Link from "next/link";

/**
 * Cabecera estrecha. Wordmark en Josefin con el verde de marca actuando
 * como el "punto" tipográfico — referencia visual al BORME y a documentos
 * oficiales españoles donde el cuño es lo único en color.
 */
export function Topbar() {
  return (
    <header className="relative z-20 flex h-12 items-center justify-between border-b border-border/60 bg-background/80 px-6 backdrop-blur">
      <Link href="/discover" className="group flex items-baseline gap-2">
        <span className="font-heading text-[17px] font-light tracking-tight text-foreground">
          cazador
        </span>
        <span
          aria-hidden
          className="h-1.5 w-1.5 translate-y-[-3px] rounded-full bg-primary dot-bloom"
        />
        <span className="font-heading text-[17px] font-medium tracking-tight text-primary">
          globalizame
        </span>
      </Link>

      <div className="hidden items-center gap-6 text-[11px] tracking-wider text-muted-foreground sm:flex">
        <span className="label-eyebrow">v0.1 · prerelease</span>
        <span className="h-3 w-px bg-border" />
        <span>
          by{" "}
          <a
            href="https://globalizame.com"
            target="_blank"
            rel="noreferrer"
            className="text-foreground/80 underline decoration-secondary/60 decoration-2 underline-offset-4 transition-colors hover:text-primary"
          >
            globalizame
          </a>
        </span>
      </div>
    </header>
  );
}
