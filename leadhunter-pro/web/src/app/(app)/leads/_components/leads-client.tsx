"use client";

import { useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Database,
  Download,
  ServerCrash,
} from "lucide-react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScoreChip } from "@/components/score-chip";
import { cn } from "@/lib/utils";

export interface LeadRow {
  id: string;
  razon_social: string | null;
  nif: string | null;
  score: number;
  grade: "A" | "B" | "C" | "D";
  decisor: string | null;
  decisor_role: string | null;
  email_principal: string | null;
  telefono: string | null;
  domain: string | null;
  provincia: string | null;
  sector: string | null;
  sources_hit: string[] | null;
  last_seen: string;
}

interface Props {
  initialLeads: LeadRow[];
  initialError: string | null;
}

const COLUMNS: ColumnDef<LeadRow>[] = [
  {
    accessorKey: "score",
    header: "Score",
    cell: ({ row }) => (
      <ScoreChip
        score={row.original.score}
        grade={row.original.grade}
        size="sm"
      />
    ),
    sortingFn: "basic",
  },
  {
    accessorKey: "razon_social",
    header: "Empresa",
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="font-medium">{row.original.razon_social || "—"}</span>
        <span className="text-[11px] tracking-wide text-muted-foreground">
          {[row.original.provincia, row.original.nif].filter(Boolean).join(" · ") || "—"}
        </span>
      </div>
    ),
  },
  {
    accessorKey: "decisor",
    header: "Decisor",
    cell: ({ row }) =>
      row.original.decisor ? (
        <div className="flex flex-col">
          <span className="text-sm">{row.original.decisor}</span>
          {row.original.decisor_role && (
            <span className="text-[11px] tracking-wide text-muted-foreground">
              {row.original.decisor_role}
            </span>
          )}
        </div>
      ) : (
        <Dash />
      ),
  },
  {
    accessorKey: "email_principal",
    header: "Email",
    cell: ({ row }) =>
      row.original.email_principal ? (
        <span className="font-mono text-[12.5px]">{row.original.email_principal}</span>
      ) : (
        <Dash />
      ),
  },
  {
    accessorKey: "domain",
    header: "Dominio",
    cell: ({ row }) =>
      row.original.domain ? (
        <a
          href={`https://${row.original.domain}`}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-secondary underline decoration-secondary/40 underline-offset-4 hover:text-primary hover:decoration-primary"
        >
          {row.original.domain}
        </a>
      ) : (
        <Dash />
      ),
  },
];

export function LeadsClient({ initialLeads, initialError }: Props) {
  const [data] = useState<LeadRow[]>(initialLeads);
  const [globalFilter, setGlobalFilter] = useState("");
  const [provincia, setProvincia] = useState<string>("__all");
  const [minGrade, setMinGrade] = useState<string>("__all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "score", desc: true }]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Provincias presentes en el dataset, ordenadas alfabéticamente.
  const provinces = useMemo(() => {
    const set = new Set<string>();
    data.forEach((d) => d.provincia && set.add(d.provincia));
    return Array.from(set).sort();
  }, [data]);

  const filtered = useMemo(() => {
    let out = data;
    if (provincia !== "__all") out = out.filter((d) => d.provincia === provincia);
    if (minGrade !== "__all") {
      const order = ["A", "B", "C", "D"];
      const min = order.indexOf(minGrade);
      out = out.filter((d) => order.indexOf(d.grade) <= min);
    }
    return out;
  }, [data, provincia, minGrade]);

  const table = useReactTable({
    data: filtered,
    columns: COLUMNS,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
    globalFilterFn: (row, _id, value: string) => {
      const v = value.toLowerCase();
      const r = row.original;
      return (
        (r.razon_social ?? "").toLowerCase().includes(v) ||
        (r.nif ?? "").toLowerCase().includes(v) ||
        (r.decisor ?? "").toLowerCase().includes(v) ||
        (r.email_principal ?? "").toLowerCase().includes(v) ||
        (r.domain ?? "").toLowerCase().includes(v)
      );
    },
  });

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const allVisibleSelected =
    table.getRowModel().rows.length > 0 &&
    table.getRowModel().rows.every((r) => selected.has(r.original.id));
  const toggleAllVisible = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      const rows = table.getRowModel().rows;
      const all = rows.every((r) => next.has(r.original.id));
      rows.forEach((r) => (all ? next.delete(r.original.id) : next.add(r.original.id)));
      return next;
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 px-6 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span aria-hidden className="h-px w-10 bg-primary" />
          <span className="label-eyebrow">módulo · leads</span>
        </div>
        <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
          {data.length.toString().padStart(2, "0")}
          <span className="text-muted-foreground"> leads persistidos.</span>
        </h1>
        <p className="max-w-2xl text-[14px] leading-relaxed text-muted-foreground">
          Corpus deduplicado por <code className="font-mono text-foreground/80">dedup_key</code>.
          Filtra, multi-selecciona y encola a Outreach.
        </p>
      </header>

      {initialError && (
        <div className="flex items-center gap-2 border border-destructive/40 bg-destructive/[0.06] px-4 py-2 text-[12px] text-destructive">
          <ServerCrash className="h-4 w-4" />
          <span>No se pudo cargar de Supabase: {initialError}</span>
        </div>
      )}

      {/* Filtros */}
      <div className="grid grid-cols-1 gap-px bg-border/40 md:grid-cols-[1fr_220px_220px_auto]">
        <div className="bg-card p-4">
          <FieldLabel index="01" label="Buscar" />
          <Input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="razón social, NIF, email…"
            className={cn(
              "h-10 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none",
              "focus-visible:border-primary focus-visible:ring-0",
            )}
          />
        </div>
        <div className="bg-card p-4">
          <FieldLabel index="02" label="Provincia" />
          <Select value={provincia} onValueChange={(v) => v !== null && setProvincia(v)}>
            <SelectTrigger className="h-10 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none focus:ring-0">
              <SelectValue placeholder="Todas" />
            </SelectTrigger>
            <SelectContent className="rounded-none border-border">
              <SelectItem value="__all" className="rounded-none">
                Todas las provincias
              </SelectItem>
              {provinces.map((p) => (
                <SelectItem key={p} value={p} className="rounded-none">
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="bg-card p-4">
          <FieldLabel index="03" label="Score mínimo" />
          <Select value={minGrade} onValueChange={(v) => v !== null && setMinGrade(v)}>
            <SelectTrigger className="h-10 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none focus:ring-0">
              <SelectValue placeholder="Cualquiera" />
            </SelectTrigger>
            <SelectContent className="rounded-none border-border">
              <SelectItem value="__all" className="rounded-none">
                Cualquiera
              </SelectItem>
              <SelectItem value="A" className="rounded-none">A (premium)</SelectItem>
              <SelectItem value="B" className="rounded-none">B o superior</SelectItem>
              <SelectItem value="C" className="rounded-none">C o superior</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="bg-card p-4 flex items-end justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={selected.size === 0}
            className="h-9 rounded-none border-border/80 bg-transparent text-[11px] uppercase tracking-wider"
          >
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Exportar CSV {selected.size > 0 ? `(${selected.size})` : ""}
          </Button>
        </div>
      </div>

      {/* Tabla */}
      <div className="overflow-hidden border border-border/60 bg-card">
        <div className="flex items-center justify-between border-b border-border/60 bg-background/40 px-4 py-2 text-[11px] tracking-wider text-muted-foreground">
          <span>
            mostrando {table.getRowModel().rows.length} de {filtered.length}
          </span>
          <span>{selected.size > 0 ? `${selected.size} seleccionados` : ""}</span>
        </div>

        {data.length === 0 ? (
          <EmptyDB />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border/80 bg-background/40">
                  <th className="w-10 px-3">
                    <input
                      type="checkbox"
                      aria-label="seleccionar todas"
                      checked={allVisibleSelected}
                      onChange={toggleAllVisible}
                      className="accent-primary"
                    />
                  </th>
                  {table.getHeaderGroups()[0]?.headers.map((header) => {
                    const sorted = header.column.getIsSorted();
                    const Icon = sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ArrowUpDown;
                    return (
                      <th key={header.id} className="h-10 px-4 text-left">
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className={cn(
                            "label-eyebrow flex items-center gap-1.5",
                            sorted ? "text-primary" : "hover:text-foreground",
                          )}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          <Icon className="h-3 w-3" />
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.original.id}
                    className="row-accent border-b border-border/40 transition-colors hover:bg-muted/30"
                  >
                    <td className="px-3 align-middle">
                      <input
                        type="checkbox"
                        checked={selected.has(row.original.id)}
                        onChange={() => toggleSelect(row.original.id)}
                        className="accent-primary"
                      />
                    </td>
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 align-middle">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginación */}
        {data.length > 0 && (
          <div className="flex items-center justify-between border-t border-border/60 bg-background/40 px-4 py-2 text-[11px] tracking-wider text-muted-foreground">
            <span>
              página {table.getState().pagination.pageIndex + 1} de {table.getPageCount() || 1}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="h-7 rounded-none px-2 text-[10px] uppercase tracking-wider"
              >
                anterior
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="h-7 rounded-none px-2 text-[10px] uppercase tracking-wider"
              >
                siguiente
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
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

function Dash() {
  return <span className="text-muted-foreground/60">—</span>;
}

function EmptyDB() {
  return (
    <div className="flex min-h-[280px] items-stretch overflow-hidden">
      <div className="flex w-32 shrink-0 items-center justify-center border-r border-border/60 bg-background/40">
        <Database className="h-14 w-14 stroke-[1] text-secondary" aria-hidden />
      </div>
      <div className="flex flex-col justify-center gap-3 px-8 py-10">
        <span className="label-eyebrow">corpus · vacío</span>
        <h2 className="font-heading text-2xl font-light tracking-tight">
          Aún no hay leads persistidos.
        </h2>
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
          Lanza una búsqueda en{" "}
          <span className="font-medium text-foreground">Discover</span> y los
          leads que encuentres aparecen aquí automáticamente.
        </p>
      </div>
    </div>
  );
}
