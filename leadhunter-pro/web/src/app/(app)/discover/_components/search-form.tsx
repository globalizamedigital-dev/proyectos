"use client";

import { useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { PROVINCES } from "@/app/(app)/discover/_data/provinces";
import { cn } from "@/lib/utils";

export interface SearchFormValues {
  province: string;
  sector: string;
  max: number;
  enrich: boolean;
}

interface SearchFormProps {
  isSearching: boolean;
  onSubmit(values: SearchFormValues): void;
}

export function SearchForm({ isSearching, onSubmit }: SearchFormProps) {
  const [province, setProvince] = useState("Sevilla");
  const [sector, setSector] = useState("asesoría fiscal");
  const [max, setMax] = useState(25);
  const [enrich, setEnrich] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSearching) return;
    onSubmit({ province, sector: sector.trim(), max, enrich });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="hero-glow relative isolate overflow-hidden rounded-none border border-border/80 bg-card"
    >
      {/* fondo de cuadrícula sutil */}
      <div className="grid-pattern pointer-events-none absolute inset-0 opacity-60" />
      <div className="grain-overlay" />

      {/* Eyebrow + tagline */}
      <div className="relative flex items-center justify-between border-b border-border/60 px-6 py-3">
        <div className="flex items-center gap-2">
          <span className="label-eyebrow">expediente · 01 · discover</span>
          <span className="h-3 w-px bg-border" />
          <span className="text-[11px] tracking-wider text-muted-foreground">
            consulta a fuentes públicas
          </span>
        </div>
        <code className="hidden text-[10px] tracking-wider text-muted-foreground/70 md:block">
          /api/discover?geo=:province&sector=:cnae
        </code>
      </div>

      {/* Grid principal del formulario */}
      <div className="relative grid grid-cols-12 gap-px bg-border/40">
        {/* Provincia */}
        <div className="col-span-12 bg-card p-5 md:col-span-3">
          <FieldLabel index="01" label="Provincia" />
          <Select
            value={province}
            onValueChange={(v) => v !== null && setProvince(v)}
          >
            <SelectTrigger
              className={cn(
                "h-11 w-full rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-base font-medium",
                "focus:ring-0 focus:ring-offset-0 focus-visible:ring-0",
                "data-[placeholder]:text-muted-foreground"
              )}
            >
              <SelectValue placeholder="Selecciona" />
            </SelectTrigger>
            <SelectContent className="max-h-[320px] rounded-none border-border">
              {PROVINCES.map((p) => (
                <SelectItem
                  key={p}
                  value={p}
                  className="rounded-none font-sans tabular-nums"
                >
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Sector */}
        <div className="col-span-12 bg-card p-5 md:col-span-5">
          <FieldLabel index="02" label="Sector / CNAE" />
          <Input
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            placeholder="asesoría fiscal, inmobiliaria, software..."
            className={cn(
              "h-11 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-base font-medium shadow-none",
              "focus-visible:ring-0 focus-visible:border-primary",
              "placeholder:text-muted-foreground/60"
            )}
          />
          <p className="mt-2 text-[11px] tracking-wide text-muted-foreground/70">
            Acepta texto libre o código CNAE de 4 dígitos.
          </p>
        </div>

        {/* Máx resultados */}
        <div className="col-span-12 bg-card p-5 md:col-span-4">
          <FieldLabel index="03" label="Máx. resultados" />
          <div className="flex items-end gap-5">
            <span className="numeral-display text-primary text-[58px]">
              {max.toString().padStart(2, "0")}
            </span>
            <div className="flex-1 pb-2">
              <Slider
                value={[max]}
                min={5}
                max={100}
                step={5}
                onValueChange={(v) => {
                  const n = Array.isArray(v) ? v[0] : v;
                  if (typeof n === "number") setMax(n);
                }}
                className="[&_[data-slot=slider-track]]:rounded-none [&_[data-slot=slider-track]]:h-1 [&_[data-slot=slider-range]]:rounded-none [&_[data-slot=slider-thumb]]:rounded-none [&_[data-slot=slider-thumb]]:size-3 [&_[data-slot=slider-thumb]]:border-2 [&_[data-slot=slider-thumb]]:border-primary [&_[data-slot=slider-thumb]]:bg-background"
              />
              <div className="mt-2 flex justify-between text-[9px] tracking-wider text-muted-foreground/60">
                <span>05</span>
                <span>25</span>
                <span>50</span>
                <span>75</span>
                <span>100</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pie del formulario: enrichment + CTA */}
      <div className="relative flex flex-col items-stretch gap-4 border-t border-border/60 bg-background/40 px-6 py-4 md:flex-row md:items-center md:justify-between">
        <label className="flex cursor-pointer select-none items-center gap-3">
          <Switch
            checked={enrich}
            onCheckedChange={setEnrich}
            className="data-[state=checked]:bg-primary"
          />
          <div className="flex flex-col">
            <span className="text-sm font-medium">
              Enriquecimiento completo
            </span>
            <span className="text-[11px] text-muted-foreground">
              Resolución de dominio, scraping de equipo, permutaciones de email
            </span>
          </div>
        </label>

        <Button
          type="submit"
          disabled={isSearching || !sector.trim()}
          className={cn(
            "scanline-cta h-12 min-w-[200px] rounded-none border border-primary/0 bg-primary px-6 text-base font-medium uppercase tracking-wider text-primary-foreground hover:bg-primary/90",
            "disabled:bg-primary/40 disabled:text-primary-foreground/60"
          )}
        >
          {isSearching ? (
            <span className="flex items-center gap-3">
              <span className="relative h-1 w-24 overflow-hidden bg-primary-foreground/20">
                <span className="scan-progress absolute inset-y-0 left-0 w-1/3 bg-primary-foreground" />
              </span>
              <span className="text-xs tracking-wider">sondeando…</span>
            </span>
          ) : (
            <span className="relative z-[2] flex items-center gap-3">
              <Search className="h-4 w-4" />
              Buscar leads
              <ArrowRight className="h-4 w-4" />
            </span>
          )}
        </Button>
      </div>

      {/* Microcopy bajo el card */}
      <div className="relative border-t border-border/60 bg-card px-6 py-2.5 text-center">
        <p className="text-[11px] tracking-wider text-muted-foreground">
          Sin Apollo.<span className="mx-2 text-border">·</span>
          Sin Apify.<span className="mx-2 text-border">·</span>
          Sin Google Maps.<span className="mx-2 text-border">·</span>
          <span className="text-foreground/70">
            Solo fuentes oficiales españolas.
          </span>
        </p>
      </div>
    </form>
  );
}

function FieldLabel({ index, label }: { index: string; label: string }) {
  return (
    <div className="mb-1 flex items-center gap-2">
      <span className="label-eyebrow text-primary/80 tabular-nums">{index}</span>
      <span className="label-eyebrow">{label}</span>
    </div>
  );
}
