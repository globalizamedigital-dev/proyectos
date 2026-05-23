import { AlertTriangle } from "lucide-react";

export interface AssertionMismatch {
  claim: string;
  expected: unknown;
  found: unknown;
  source: string;
  note?: string;
}

interface Props {
  mismatches: AssertionMismatch[];
}

/**
 * Banner naranja con las contradicciones entre lo que afirma el
 * operador y lo que devuelven las fuentes públicas.
 */
export function AssertionBanner({ mismatches }: Props) {
  if (mismatches.length === 0) return null;

  return (
    <div className="border border-[var(--warning)]/40 bg-[var(--warning)]/[0.06] p-5">
      <div className="mb-3 flex items-center gap-2 text-[var(--warning)]">
        <AlertTriangle className="h-4 w-4" />
        <span className="label-eyebrow text-[var(--warning)]">
          {mismatches.length} contradicción{mismatches.length === 1 ? "" : "es"} con
          tus afirmaciones
        </span>
      </div>
      <ul className="divide-y divide-[var(--warning)]/20">
        {mismatches.map((m, i) => (
          <li key={`${m.claim}-${i}`} className="grid grid-cols-[140px_1fr] gap-3 py-2.5 text-[13px]">
            <div className="font-mono text-[var(--warning)]">{m.claim}</div>
            <div className="flex flex-col gap-1">
              <div>
                <span className="label-eyebrow mr-2">esperabas</span>
                <span className="text-foreground/90">{String(m.expected)}</span>
              </div>
              <div>
                <span className="label-eyebrow mr-2">{m.source} dice</span>
                <span className="text-foreground">{String(m.found)}</span>
              </div>
              {m.note && (
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                  {m.note}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
