import type { Grade } from "@/app/(app)/discover/_data/mock-leads";
import { cn } from "@/lib/utils";

interface ScoreChipProps {
  score: number;
  grade: Grade;
  size?: "sm" | "md";
}

const GRADE_STYLES: Record<Grade, string> = {
  A: "bg-primary text-primary-foreground border-primary",
  B: "bg-transparent text-primary border-primary/70",
  C: "bg-transparent text-[var(--warning)] border-[var(--warning)]/70",
  D: "bg-transparent text-muted-foreground border-border",
};

/**
 * Chip cuadrado de score. Letra Josefin grande sobre el número pequeño.
 * Sin pill / sin radius — la idea es que se lea como un sello.
 */
export function ScoreChip({ score, grade, size = "md" }: ScoreChipProps) {
  const dims =
    size === "sm"
      ? "h-7 w-12"
      : "h-9 w-14";
  const letter =
    size === "sm"
      ? "text-[15px]"
      : "text-[18px]";
  const num =
    size === "sm"
      ? "text-[9px]"
      : "text-[10px]";

  return (
    <div
      className={cn(
        "inline-flex flex-col items-center justify-center border rounded-none tabular-nums leading-none transition-colors",
        dims,
        GRADE_STYLES[grade]
      )}
      aria-label={`Score ${score} grado ${grade}`}
    >
      <span className={cn("font-heading font-medium", letter)}>{grade}</span>
      <span className={cn("opacity-70 mt-[1px]", num)}>{score}</span>
    </div>
  );
}
