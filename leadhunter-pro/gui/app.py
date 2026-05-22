"""
LeadHunter Pro — Aplicación Tkinter GUI completa.

Tabs:
    1. Descubrir: Búsqueda por provincia + sector → tabla de leads puntuados
    2. Analizar: Análisis completo por NIF o razón social
    3. Leads: Tabla de todos los leads con sorting y detalle
    4. Outreach: Selección de leads, plantillas, preview y envío
    5. Config: SMTP, directorio de salida, ajustes generales

Usa threading para scraping en segundo plano (GUI no se congela).
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import tkinter.scrolledtext as scrolledtext
from pathlib import Path
from typing import Any, Optional

# Añadir scripts/ al path
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Colores y estilo

COLORS = {
    "bg": "#1a1d23",
    "panel": "#22262e",
    "border": "#2d3340",
    "text": "#e2e8f0",
    "text_dim": "#8892a4",
    "accent": "#4f8ef7",
    "accent_hover": "#6aa3ff",
    "success": "#48bb78",
    "warning": "#ed8936",
    "error": "#fc8181",
    "score_a": "#48bb78",
    "score_b": "#68d391",
    "score_c": "#ed8936",
    "score_d": "#fc8181",
    "input_bg": "#2d3340",
    "button_bg": "#4f8ef7",
    "button_fg": "#ffffff",
    "header_bg": "#141720",
}


def configure_styles():
    """Configura los estilos ttk globales."""
    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure(
        "TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=("Segoe UI", 10),
    )
    style.configure("Dim.TLabel", background=COLORS["panel"], foreground=COLORS["text_dim"], font=("Segoe UI", 9))
    style.configure(
        "Header.TLabel",
        background=COLORS["header_bg"],
        foreground=COLORS["text"],
        font=("Segoe UI", 14, "bold"),
    )
    style.configure(
        "TButton",
        background=COLORS["button_bg"],
        foreground=COLORS["button_fg"],
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
        relief="flat",
        padding=(12, 6),
    )
    style.map("TButton",
        background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent"])],
        foreground=[("active", "#ffffff")],
    )
    style.configure(
        "Secondary.TButton",
        background=COLORS["border"],
        foreground=COLORS["text"],
        font=("Segoe UI", 9),
        padding=(8, 4),
    )
    style.configure(
        "TNotebook",
        background=COLORS["header_bg"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=COLORS["panel"],
        foreground=COLORS["text_dim"],
        font=("Segoe UI", 10),
        padding=(16, 8),
    )
    style.map("TNotebook.Tab",
        background=[("selected", COLORS["bg"]), ("active", COLORS["bg"])],
        foreground=[("selected", COLORS["accent"]), ("active", COLORS["text"])],
    )
    style.configure(
        "Treeview",
        background=COLORS["panel"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["panel"],
        borderwidth=0,
        rowheight=28,
        font=("Segoe UI", 9),
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["border"],
        foreground=COLORS["text_dim"],
        font=("Segoe UI", 9, "bold"),
        relief="flat",
    )
    style.map("Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["input_bg"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
        borderwidth=1,
        relief="solid",
        font=("Segoe UI", 10),
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["input_bg"],
        background=COLORS["input_bg"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["text_dim"],
        borderwidth=1,
        relief="solid",
        font=("Segoe UI", 10),
    )
    style.configure(
        "Horizontal.TScale",
        background=COLORS["bg"],
        troughcolor=COLORS["border"],
        slidercolor=COLORS["accent"],
    )
    style.configure(
        "TScrollbar",
        background=COLORS["border"],
        troughcolor=COLORS["panel"],
        arrowcolor=COLORS["text_dim"],
    )
    style.configure("Status.TLabel",
        background=COLORS["header_bg"],
        foreground=COLORS["text_dim"],
        font=("Segoe UI", 9),
        padding=(8, 4),
    )


# ---------------------------------------------------------------------------
# Componentes reutilizables

class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kwargs):
        super().__init__(parent,
            text=text.upper(),
            bg=COLORS["panel"],
            fg=COLORS["text_dim"],
            font=("Segoe UI", 8, "bold"),
            **kwargs
        )


class Card(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent,
            bg=COLORS["panel"],
            relief="flat",
            bd=0,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            **kwargs
        )


class IconButton(tk.Button):
    def __init__(self, parent, text, command=None, style="primary", **kwargs):
        bg = COLORS["button_bg"] if style == "primary" else COLORS["border"]
        fg = COLORS["button_fg"] if style == "primary" else COLORS["text"]
        super().__init__(parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=COLORS["accent_hover"],
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=7,
            **kwargs
        )


class SpinnerLabel(tk.Label):
    """Etiqueta animada de carga."""
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg"], fg=COLORS["accent"],
                         font=("Segoe UI", 12), **kwargs)
        self._running = False
        self._frame = 0

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False
        self.config(text="")

    def _animate(self):
        if self._running:
            self.config(text=self._FRAMES[self._frame % len(self._FRAMES)])
            self._frame += 1
            self.after(80, self._animate)


# ---------------------------------------------------------------------------
# Provincias españolas para el dropdown

PROVINCIAS = [
    "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila",
    "Badajoz", "Baleares", "Barcelona", "Burgos", "Cáceres", "Cádiz",
    "Cantabria", "Castellón", "Ciudad Real", "Córdoba", "Cuenca",
    "Gerona", "Granada", "Guadalajara", "Guipúzcoa", "Huelva", "Huesca",
    "Jaén", "La Coruña", "La Rioja", "Las Palmas", "León", "Lérida",
    "Lugo", "Madrid", "Málaga", "Murcia", "Navarra", "Orense", "Palencia",
    "Pontevedra", "Salamanca", "Santa Cruz de Tenerife", "Segovia", "Sevilla",
    "Soria", "Tarragona", "Teruel", "Toledo", "Valencia", "Valladolid",
    "Vizcaya", "Zamora", "Zaragoza",
]


# ---------------------------------------------------------------------------
# Tab 1: Descubrir

class DescubrirTab(tk.Frame):
    def __init__(self, parent, status_var, result_queue):
        super().__init__(parent, bg=COLORS["bg"])
        self._status_var = status_var
        self._result_queue = result_queue
        self._leads: list[dict] = []
        self._build()

    def _build(self):
        # Header form
        form_card = Card(self)
        form_card.pack(fill="x", padx=16, pady=(16, 8))

        form_inner = tk.Frame(form_card, bg=COLORS["panel"], padx=16, pady=12)
        form_inner.pack(fill="x")

        # Provincia
        tk.Label(form_inner, text="Provincia", bg=COLORS["panel"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._province_var = tk.StringVar(value="Madrid")
        province_cb = ttk.Combobox(form_inner, textvariable=self._province_var,
                                    values=PROVINCIAS, state="readonly", width=24,
                                    font=("Segoe UI", 10))
        province_cb.grid(row=1, column=0, padx=(0, 16), pady=(0, 8))

        # Sector
        tk.Label(form_inner, text="Sector / CNAE", bg=COLORS["panel"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w")
        self._sector_var = tk.StringVar(value="asesoría fiscal")
        sector_entry = tk.Entry(form_inner, textvariable=self._sector_var,
                                bg=COLORS["input_bg"], fg=COLORS["text"],
                                insertbackground=COLORS["text"],
                                relief="flat", bd=4, width=32, font=("Segoe UI", 10))
        sector_entry.grid(row=1, column=1, padx=(0, 16), pady=(0, 8))
        sector_entry.bind("<Return>", lambda e: self._run_search())

        # Max resultados
        tk.Label(form_inner, text="Máx. resultados", bg=COLORS["panel"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w")
        self._max_var = tk.IntVar(value=25)
        max_frame = tk.Frame(form_inner, bg=COLORS["panel"])
        max_frame.grid(row=1, column=2, padx=(0, 16))
        self._max_label = tk.Label(max_frame, text="25", bg=COLORS["panel"],
                                    fg=COLORS["accent"], font=("Segoe UI", 11, "bold"), width=3)
        self._max_label.pack(side="right")
        max_scale = ttk.Scale(max_frame, from_=5, to=100, orient="horizontal",
                               variable=self._max_var, length=120,
                               command=lambda v: self._max_label.config(text=str(int(float(v)))))
        max_scale.pack(side="left")

        # Botón buscar
        self._spinner = SpinnerLabel(form_inner)
        self._spinner.grid(row=1, column=3, padx=(0, 8))
        self._btn_search = IconButton(form_inner, "  Buscar Leads", command=self._run_search)
        self._btn_search.grid(row=1, column=4, pady=(0, 8))

        # Opciones adicionales
        self._enrich_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form_inner, text="Enriquecimiento completo (emails, decisores)",
                        variable=self._enrich_var,
                        bg=COLORS["panel"], fg=COLORS["text"],
                        activebackground=COLORS["panel"],
                        selectcolor=COLORS["input_bg"],
                        font=("Segoe UI", 9)).grid(row=2, column=0, columnspan=3, sticky="w")

        # Tabla de resultados
        table_card = Card(self)
        table_card.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        table_header = tk.Frame(table_card, bg=COLORS["panel"], padx=12, pady=8)
        table_header.pack(fill="x")
        self._result_count_lbl = tk.Label(table_header, text="Sin resultados",
                                            bg=COLORS["panel"], fg=COLORS["text_dim"],
                                            font=("Segoe UI", 9))
        self._result_count_lbl.pack(side="left")

        # Botones de exportación
        btn_frame = tk.Frame(table_header, bg=COLORS["panel"])
        btn_frame.pack(side="right")
        IconButton(btn_frame, "Exportar CSV", command=self._export_csv, style="secondary",
                   font=("Segoe UI", 9), padx=10, pady=4).pack(side="left", padx=4)
        IconButton(btn_frame, "Exportar JSON", command=self._export_json, style="secondary",
                   font=("Segoe UI", 9), padx=10, pady=4).pack(side="left", padx=4)

        # Treeview
        cols = ("score", "empresa", "decisor", "email", "telefono", "dominio", "fuentes")
        self._tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="extended")

        headings = {
            "score": ("Score", 60),
            "empresa": ("Empresa", 220),
            "decisor": ("Decisor / CEO", 160),
            "email": ("Email", 200),
            "telefono": ("Teléfono", 130),
            "dominio": ("Dominio", 160),
            "fuentes": ("Fuentes", 80),
        }
        for col, (text, width) in headings.items():
            self._tree.heading(col, text=text, command=lambda c=col: self._sort_tree(c))
            self._tree.column(col, width=width, minwidth=50)

        # Scrollbars
        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(table_card, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        self._tree.bind("<Double-1>", self._on_row_double_click)
        self._tree.tag_configure("grade_a", foreground=COLORS["score_a"])
        self._tree.tag_configure("grade_b", foreground=COLORS["score_b"])
        self._tree.tag_configure("grade_c", foreground=COLORS["score_c"])
        self._tree.tag_configure("grade_d", foreground=COLORS["score_d"])

    def _run_search(self):
        province = self._province_var.get()
        sector = self._sector_var.get().strip()
        max_r = self._max_var.get()
        enrich = self._enrich_var.get()

        if not sector:
            messagebox.showwarning("LeadHunter Pro", "Por favor introduce un sector o CNAE")
            return

        self._btn_search.config(state="disabled", text="Buscando...")
        self._spinner.start()
        self._status_var.set(f"Buscando leads: {sector} en {province}...")

        def run_in_thread():
            try:
                from discover import discover
                payload = discover(province, sector, max_r, enrich=enrich)
                self._result_queue.put(("discover_result", payload))
            except Exception as e:
                self._result_queue.put(("discover_error", str(e)))

        threading.Thread(target=run_in_thread, daemon=True).start()
        self._poll_queue()

    def _poll_queue(self):
        try:
            msg_type, data = self._result_queue.get_nowait()
            if msg_type == "discover_result":
                self._on_search_complete(data)
            elif msg_type == "discover_error":
                self._on_search_error(data)
            else:
                self._result_queue.task_done()
                self.after(100, self._poll_queue)
        except queue.Empty:
            self.after(200, self._poll_queue)

    def _on_search_complete(self, payload: dict):
        self._spinner.stop()
        self._btn_search.config(state="normal", text="  Buscar Leads")
        candidates = payload.get("candidates", [])
        self._leads = candidates
        self._populate_tree(candidates)
        count = len(candidates)
        self._result_count_lbl.config(text=f"{count} leads encontrados — {payload.get('totalUnresolvedDomain', 0)} sin dominio")
        self._status_var.set(f"Búsqueda completada: {count} leads")

    def _on_search_error(self, error: str):
        self._spinner.stop()
        self._btn_search.config(state="normal", text="  Buscar Leads")
        self._status_var.set(f"Error: {error[:80]}")
        messagebox.showerror("Error en búsqueda", f"Error durante la búsqueda:\n{error}")

    def _populate_tree(self, candidates: list[dict]):
        self._tree.delete(*self._tree.get_children())
        for lead in candidates:
            score_data = lead.get("score") or {}
            if isinstance(score_data, dict):
                score_val = score_data.get("score", 0)
                grade = score_data.get("grade", "D")
            else:
                score_val = 0
                grade = "D"

            domain = lead.get("domain") or {}
            domain_str = domain.get("resolved", "") if isinstance(domain, dict) else str(domain or "")

            emails = lead.get("emails", [])
            email_str = ""
            if emails:
                first = emails[0]
                email_str = first.get("email", "") if isinstance(first, dict) else str(first)

            phones = lead.get("phones", [])
            phone_str = phones[0] if phones else ""

            dms = lead.get("decisionMakers", [])
            dm_str = ""
            if dms:
                first_dm = dms[0]
                dm_str = first_dm.get("name", "") if isinstance(first_dm, dict) else str(first_dm)

            sources = ", ".join(s for s in (lead.get("sourcesHit") or []) if s)

            tag = f"grade_{grade.lower()}"
            self._tree.insert("", "end", values=(
                f"{score_val} [{grade}]",
                lead.get("razonSocial", ""),
                dm_str[:40],
                email_str[:45],
                phone_str,
                domain_str[:35],
                sources,
            ), tags=(tag,))

    def _sort_tree(self, col):
        """Ordenar la tabla por columna."""
        items = [(self._tree.set(k, col), k) for k in self._tree.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0].split()[0]) if x[0] else 0, reverse=True)
        except (ValueError, IndexError):
            items.sort(reverse=True)
        for idx, (_, k) in enumerate(items):
            self._tree.move(k, "", idx)

    def _on_row_double_click(self, event):
        """Muestra detalle del lead al hacer doble clic."""
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx < len(self._leads):
            LeadDetailWindow(self, self._leads[idx])

    def _export_csv(self):
        if not self._leads:
            messagebox.showinfo("LeadHunter Pro", "No hay leads para exportar")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="leads_export.csv",
        )
        if path:
            try:
                from _common import export_leads_csv
                export_leads_csv(self._leads, Path(path))
                messagebox.showinfo("Exportación", f"Leads exportados a:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _export_json(self):
        if not self._leads:
            messagebox.showinfo("LeadHunter Pro", "No hay leads para exportar")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="leads_export.json",
        )
        if path:
            try:
                Path(path).write_text(json.dumps(self._leads, ensure_ascii=False, indent=2), encoding="utf-8")
                messagebox.showinfo("Exportación", f"Leads exportados a:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ---------------------------------------------------------------------------
# Tab 2: Analizar

class AnalizarTab(tk.Frame):
    def __init__(self, parent, status_var, result_queue):
        super().__init__(parent, bg=COLORS["bg"])
        self._status_var = status_var
        self._result_queue = result_queue
        self._build()

    def _build(self):
        # Form
        form_card = Card(self)
        form_card.pack(fill="x", padx=16, pady=(16, 8))
        form_inner = tk.Frame(form_card, bg=COLORS["panel"], padx=16, pady=12)
        form_inner.pack(fill="x")

        tk.Label(form_inner, text="NIF/CIF o Razón Social", bg=COLORS["panel"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).pack(anchor="w")

        input_row = tk.Frame(form_inner, bg=COLORS["panel"])
        input_row.pack(fill="x", pady=(4, 8))

        self._input_var = tk.StringVar()
        entry = tk.Entry(input_row, textvariable=self._input_var,
                         bg=COLORS["input_bg"], fg=COLORS["text"],
                         insertbackground=COLORS["text"],
                         relief="flat", bd=4, width=40, font=("Segoe UI", 11))
        entry.pack(side="left", padx=(0, 12))
        entry.bind("<Return>", lambda e: self._run_analyze())
        entry.focus()

        self._spinner = SpinnerLabel(input_row)
        self._spinner.pack(side="left", padx=(0, 8))

        self._btn_analyze = IconButton(input_row, "  Analizar", command=self._run_analyze)
        self._btn_analyze.pack(side="left")

        self._premium_var = tk.BooleanVar(value=False)
        tk.Checkbutton(form_inner, text="Premium (Registradores.org — coste ~€10-30)",
                        variable=self._premium_var,
                        bg=COLORS["panel"], fg=COLORS["text_dim"],
                        activebackground=COLORS["panel"],
                        selectcolor=COLORS["input_bg"],
                        font=("Segoe UI", 9)).pack(anchor="w")

        # Resultado
        result_card = Card(self)
        result_card.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._result_text = scrolledtext.ScrolledText(
            result_card,
            wrap=tk.WORD,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            font=("Consolas", 10),
            relief="flat",
            state="disabled",
        )
        self._result_text.pack(fill="both", expand=True, padx=8, pady=8)

        # Tags de formato
        self._result_text.tag_configure("header", foreground=COLORS["accent"], font=("Segoe UI", 11, "bold"))
        self._result_text.tag_configure("key", foreground=COLORS["text_dim"])
        self._result_text.tag_configure("value_ok", foreground=COLORS["success"])
        self._result_text.tag_configure("value_warn", foreground=COLORS["warning"])
        self._result_text.tag_configure("score_a", foreground=COLORS["score_a"], font=("Consolas", 12, "bold"))
        self._result_text.tag_configure("score_d", foreground=COLORS["score_d"])

    def _run_analyze(self):
        input_str = self._input_var.get().strip()
        if not input_str:
            messagebox.showwarning("LeadHunter Pro", "Introduce un NIF o razón social")
            return

        self._btn_analyze.config(state="disabled", text="Analizando...")
        self._spinner.start()
        self._status_var.set(f"Analizando: {input_str}...")
        self._set_text("")

        premium = self._premium_var.get()

        def run_in_thread():
            try:
                from analyze import analyze
                payload = analyze(input_str, premium)
                self._result_queue.put(("analyze_result", payload))
            except Exception as e:
                self._result_queue.put(("analyze_error", str(e)))

        threading.Thread(target=run_in_thread, daemon=True).start()
        self._poll_queue()

    def _poll_queue(self):
        try:
            msg_type, data = self._result_queue.get_nowait()
            if msg_type == "analyze_result":
                self._on_analyze_complete(data)
            elif msg_type == "analyze_error":
                self._on_analyze_error(data)
            else:
                self._result_queue.task_done()
                self.after(100, self._poll_queue)
        except queue.Empty:
            self.after(200, self._poll_queue)

    def _on_analyze_complete(self, payload: dict):
        self._spinner.stop()
        self._btn_analyze.config(state="normal", text="  Analizar")
        self._render_analysis(payload)
        self._status_var.set("Análisis completado")

    def _on_analyze_error(self, error: str):
        self._spinner.stop()
        self._btn_analyze.config(state="normal", text="  Analizar")
        self._status_var.set(f"Error: {error[:80]}")
        self._set_text(f"Error durante el análisis:\n{error}")

    def _set_text(self, text: str):
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", tk.END)
        self._result_text.insert(tk.END, text)
        self._result_text.config(state="disabled")

    def _render_analysis(self, payload: dict):
        """Renderiza el análisis de forma legible en el área de texto."""
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", tk.END)

        def add(text, tag=None):
            if tag:
                self._result_text.insert(tk.END, text, tag)
            else:
                self._result_text.insert(tk.END, text)

        inp = payload.get("input", {})
        rs = inp.get("razon_social") or inp.get("nif") or "?"

        add(f"═══ ANÁLISIS: {rs} ═══\n\n", "header")

        # Score
        score = payload.get("score") or {}
        if score:
            s = score.get("score", 0)
            grade = score.get("grade", "?")
            completeness = int((score.get("iceberg_completeness", 0)) * 100)
            tag = "score_a" if grade in ("A", "B") else "score_d"
            add(f"  SCORE: {s}/100  [{grade}]  — Completitud: {completeness}%\n\n", tag)

        # Identificación
        add("IDENTIFICACIÓN\n", "header")
        add(f"  NIF:          {inp.get('nif') or '—'}\n")
        add(f"  Razón social: {inp.get('razon_social') or '—'}\n")

        infoempresa = payload.get("infoempresa") or {}
        if infoempresa and not infoempresa.get("error"):
            add(f"  Sector:       {infoempresa.get('sector') or '—'}\n")
            add(f"  Empleados:    {infoempresa.get('employees_range') or '—'}\n")
            add(f"  Ingresos:     {infoempresa.get('revenue_range') or '—'}\n")
            add(f"  Fundación:    {infoempresa.get('founded') or '—'}\n")

        # Web
        add("\nWEB\n", "header")
        web = payload.get("web") or {}
        domain = web.get("domain")
        if domain:
            add(f"  Dominio: ", "key")
            add(f"{domain}", "value_ok")
            add(f"  (via {web.get('resolved_via', '?')}, confianza: {web.get('confidence', '?')})\n")
        else:
            add("  Dominio: ", "key")
            add("No resuelto\n", "value_warn")

        # Decisores
        dms = payload.get("decisionMakers") or []
        add(f"\nDECISORES ({len(dms)})\n", "header")
        if dms:
            for dm in dms[:5]:
                if isinstance(dm, dict):
                    add(f"  • {dm.get('name', '?')} — {dm.get('role', '?')} [{dm.get('source', '?')}]\n")
                    if dm.get("linkedin_hint"):
                        add(f"    LinkedIn: {dm['linkedin_hint']}\n", "key")
        else:
            add("  No identificados\n", "value_warn")

        # Emails
        emails = payload.get("emails") or []
        add(f"\nEMAILS ({len(emails)})\n", "header")
        if emails:
            for em in emails[:5]:
                if isinstance(em, dict):
                    conf = em.get("confidence", "?")
                    tag = "value_ok" if conf == "verified" else None
                    add(f"  • {em.get('email', '?')} [{conf}] via {em.get('via', '?')}\n", tag)
        else:
            add("  No encontrados\n", "value_warn")

        # Teléfonos
        phones = payload.get("phones") or []
        add(f"\nTELÉFONOS ({len(phones)})\n", "header")
        if phones:
            for p in phones[:3]:
                add(f"  • {p}\n")
        else:
            add("  No encontrados\n", "value_warn")

        # Compliance
        compliance = payload.get("compliance") or {}
        add("\nCOMPLIANCE\n", "header")
        dpo = compliance.get("dpoRegistered")
        add("  DPO AEPD: ", "key")
        if dpo:
            add("REGISTRADO\n", "value_ok")
        else:
            add("No detectado\n")

        # Sector público
        contracts = payload.get("publicSector", {}).get("contracts", [])
        subsidies = payload.get("publicSector", {}).get("subsidies", [])
        add("\nSECTOR PÚBLICO\n", "header")
        add(f"  Contratos PLACSP: {len(contracts)}\n")
        add(f"  Subvenciones:     {len(subsidies)}\n")

        # Timeline BORME
        timeline = payload.get("registralTimeline") or []
        add(f"\nTIMELINE BORME ({len(timeline)} eventos)\n", "header")
        for ev in timeline[:5]:
            if isinstance(ev, dict):
                add(f"  {ev.get('date', '?')} — {ev.get('type', '?')}\n")

        # Recomendación
        rec = payload.get("recommendation") or {}
        add("\nRECOMENDACIÓN\n", "header")
        add(f"  Siguiente paso: {rec.get('nextStep', '—')}\n", "value_ok")
        qualified = rec.get("qualifiedFor", [])
        if qualified:
            add(f"  Cualificado para: {', '.join(qualified)}\n")

        # Warnings
        warnings = payload.get("warnings") or []
        if warnings:
            add("\nAVISOS\n", "header")
            for w in warnings:
                add(f"  ⚠ {w}\n", "value_warn")

        add(f"\n{'─' * 60}\n")
        add(f"  Generado: {payload.get('timestamp', '?')}\n", "key")
        if payload.get("writes", {}).get("snapshot"):
            add(f"  Snapshot: {payload['writes']['snapshot']}\n", "key")

        self._result_text.config(state="disabled")


# ---------------------------------------------------------------------------
# Tab 3: Leads (tabla global)

class LeadsTab(tk.Frame):
    def __init__(self, parent, status_var):
        super().__init__(parent, bg=COLORS["bg"])
        self._status_var = status_var
        self._leads: list[dict] = []
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg=COLORS["bg"], pady=8)
        header.pack(fill="x", padx=16)

        tk.Label(header, text="Leads Guardados", bg=COLORS["bg"],
                 fg=COLORS["text"], font=("Segoe UI", 13, "bold")).pack(side="left")

        btn_frame = tk.Frame(header, bg=COLORS["bg"])
        btn_frame.pack(side="right")
        IconButton(btn_frame, "Cargar JSON", command=self._load_json, style="secondary",
                   font=("Segoe UI", 9), padx=10, pady=4).pack(side="left", padx=4)
        IconButton(btn_frame, "Exportar CSV", command=self._export_csv, style="secondary",
                   font=("Segoe UI", 9), padx=10, pady=4).pack(side="left", padx=4)

        # Tabla
        cols = ("score", "empresa", "nif", "decisor", "email", "telefono", "dominio", "ciudad", "fuentes")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended")

        headings = {
            "score": ("Score", 70),
            "empresa": ("Empresa", 210),
            "nif": ("NIF", 90),
            "decisor": ("Decisor", 150),
            "email": ("Email", 195),
            "telefono": ("Teléfono", 120),
            "dominio": ("Dominio", 150),
            "ciudad": ("Ciudad", 100),
            "fuentes": ("Fuentes", 80),
        }
        for col, (text, width) in headings.items():
            self._tree.heading(col, text=text, command=lambda c=col: self._sort_tree(c))
            self._tree.column(col, width=width, minwidth=50)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 8))
        vsb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

        self._tree.bind("<Double-1>", self._on_row_double_click)
        self._tree.tag_configure("grade_a", foreground=COLORS["score_a"])
        self._tree.tag_configure("grade_b", foreground=COLORS["score_b"])
        self._tree.tag_configure("grade_c", foreground=COLORS["score_c"])
        self._tree.tag_configure("grade_d", foreground=COLORS["score_d"])

    def load_leads(self, leads: list[dict]):
        """Carga leads en la tabla."""
        self._leads = leads
        self._tree.delete(*self._tree.get_children())
        for lead in leads:
            self._add_lead_to_tree(lead)
        self._status_var.set(f"{len(leads)} leads en total")

    def _add_lead_to_tree(self, lead: dict):
        score_data = lead.get("score") or {}
        score_val = score_data.get("score", 0) if isinstance(score_data, dict) else 0
        grade = score_data.get("grade", "D") if isinstance(score_data, dict) else "D"

        domain = lead.get("domain") or {}
        domain_str = domain.get("resolved", "") if isinstance(domain, dict) else str(domain or "")

        emails = lead.get("emails", [])
        email_str = ""
        if emails:
            first = emails[0]
            email_str = first.get("email", "") if isinstance(first, dict) else str(first)

        phones = lead.get("phones", [])
        phone_str = phones[0] if phones else ""

        dms = lead.get("decisionMakers", [])
        dm_str = ""
        if dms:
            first_dm = dms[0]
            dm_str = first_dm.get("name", "") if isinstance(first_dm, dict) else str(first_dm)

        geo = lead.get("geocoded") or {}
        city = geo.get("muni", "") if isinstance(geo, dict) else lead.get("city", "")

        sources = ", ".join(s for s in (lead.get("sourcesHit") or []) if s)

        tag = f"grade_{grade.lower()}"
        self._tree.insert("", "end", values=(
            f"{score_val} [{grade}]",
            lead.get("razonSocial", ""),
            lead.get("nif", ""),
            dm_str[:40],
            email_str[:45],
            phone_str,
            domain_str[:35],
            city[:25],
            sources,
        ), tags=(tag,))

    def _sort_tree(self, col):
        items = [(self._tree.set(k, col), k) for k in self._tree.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0].split()[0]) if x[0] else 0, reverse=True)
        except (ValueError, IndexError):
            items.sort(reverse=True)
        for idx, (_, k) in enumerate(items):
            self._tree.move(k, "", idx)

    def _on_row_double_click(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx < len(self._leads):
            LeadDetailWindow(self, self._leads[idx])

    def _load_json(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, list):
                leads = data
            elif isinstance(data, dict) and "candidates" in data:
                leads = data["candidates"]
            else:
                leads = [data]
            self.load_leads(leads)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

    def _export_csv(self):
        if not self._leads:
            messagebox.showinfo("LeadHunter Pro", "No hay leads para exportar")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="leads_export.csv",
        )
        if path:
            try:
                from _common import export_leads_csv
                export_leads_csv(self._leads, Path(path))
                messagebox.showinfo("Exportación", f"Leads exportados a:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ---------------------------------------------------------------------------
# Tab 4: Outreach

class OutreachTab(tk.Frame):
    def __init__(self, parent, status_var, leads_ref):
        super().__init__(parent, bg=COLORS["bg"])
        self._status_var = status_var
        self._leads_ref = leads_ref  # Referencia a la pestaña Leads para obtener leads
        self._selected_leads: list[dict] = []
        self._build()

    def _build(self):
        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=16, pady=16)

        # Panel izquierdo: configuración
        left = tk.Frame(main, bg=COLORS["bg"], width=320)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        # Template selection
        SectionLabel(left, "Plantilla de email").pack(anchor="w", pady=(0, 4))
        self._template_var = tk.StringVar(value="email_cold_es.txt")
        template_cb = ttk.Combobox(left, textvariable=self._template_var,
                                    values=["email_cold_es.txt", "email_followup_es.txt"],
                                    state="readonly", width=28)
        template_cb.pack(anchor="w", pady=(0, 12))

        # Opciones
        self._skip_contacted_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="Omitir ya contactados (últimos 30 días)",
                        variable=self._skip_contacted_var,
                        bg=COLORS["bg"], fg=COLORS["text"],
                        activebackground=COLORS["bg"],
                        selectcolor=COLORS["input_bg"],
                        font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 8))

        self._dry_run_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="Modo prueba (no envía)",
                        variable=self._dry_run_var,
                        bg=COLORS["bg"], fg=COLORS["warning"],
                        activebackground=COLORS["bg"],
                        selectcolor=COLORS["input_bg"],
                        font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 12))

        # Botones de acción
        IconButton(left, "  Cargar leads", command=self._load_leads_from_tab,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=4).pack(fill="x", pady=2)
        IconButton(left, "  Previsualizar email", command=self._preview_email,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=4).pack(fill="x", pady=2)
        IconButton(left, "  Enviar outreach", command=self._send_outreach).pack(fill="x", pady=(8, 2))

        tk.Label(left, text="", bg=COLORS["bg"]).pack()  # spacer
        SectionLabel(left, "Mensaje LinkedIn / WhatsApp").pack(anchor="w", pady=(12, 4))
        IconButton(left, "LinkedIn message", command=self._gen_linkedin,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=4).pack(fill="x", pady=2)
        IconButton(left, "WhatsApp message", command=self._gen_whatsapp,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=4).pack(fill="x", pady=2)

        # Historial
        tk.Label(left, text="", bg=COLORS["bg"]).pack()
        SectionLabel(left, "Historial de envíos").pack(anchor="w", pady=(8, 4))
        IconButton(left, "Ver historial", command=self._show_history,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=4).pack(fill="x", pady=2)

        # Panel derecho: leads seleccionados + preview
        right = tk.Frame(main, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True)

        SectionLabel(right, "Leads seleccionados para outreach").pack(anchor="w", pady=(0, 4))

        self._leads_listbox = tk.Listbox(right, bg=COLORS["input_bg"], fg=COLORS["text"],
                                          selectmode="extended", height=8,
                                          relief="flat", borderwidth=0,
                                          font=("Segoe UI", 9),
                                          selectbackground=COLORS["accent"])
        self._leads_listbox.pack(fill="x", pady=(0, 12))

        SectionLabel(right, "Preview del email").pack(anchor="w", pady=(0, 4))
        self._preview_text = scrolledtext.ScrolledText(right, wrap=tk.WORD,
                                                        bg=COLORS["panel"],
                                                        fg=COLORS["text"],
                                                        font=("Consolas", 10),
                                                        relief="flat",
                                                        height=20)
        self._preview_text.pack(fill="both", expand=True)

    def _load_leads_from_tab(self):
        leads = self._leads_ref._leads if hasattr(self._leads_ref, "_leads") else []
        if not leads:
            messagebox.showinfo("LeadHunter Pro", "No hay leads. Ve a 'Descubrir' primero.")
            return
        self._selected_leads = [l for l in leads if l.get("emails")]
        self._leads_listbox.delete(0, tk.END)
        for lead in self._selected_leads:
            emails = lead.get("emails", [])
            email_str = emails[0].get("email", "") if emails and isinstance(emails[0], dict) else ""
            self._leads_listbox.insert(tk.END, f"{lead.get('razonSocial', '?')} <{email_str}>")
        self._status_var.set(f"{len(self._selected_leads)} leads con email cargados")

    def _preview_email(self):
        if not self._selected_leads:
            messagebox.showinfo("LeadHunter Pro", "Carga leads primero")
            return
        lead = self._selected_leads[0]
        try:
            from outreach import prepare_email
            prepared = prepare_email(lead, self._template_var.get())
            if prepared:
                self._preview_text.delete("1.0", tk.END)
                self._preview_text.insert(tk.END, f"Para: {prepared['to']}\n")
                self._preview_text.insert(tk.END, f"Asunto: {prepared['subject']}\n")
                self._preview_text.insert(tk.END, "─" * 50 + "\n")
                self._preview_text.insert(tk.END, prepared["body"])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _send_outreach(self):
        if not self._selected_leads:
            messagebox.showinfo("LeadHunter Pro", "No hay leads seleccionados")
            return

        dry_run = self._dry_run_var.get()
        if not dry_run:
            if not messagebox.askyesno("Confirmar envío",
                                        f"¿Enviar emails reales a {len(self._selected_leads)} leads?\n"
                                        "Esta acción no se puede deshacer."):
                return

        # Cargar config SMTP (simplificado — usar Config tab)
        try:
            from outreach import send_outreach_batch
            # Cargar config desde archivo si existe
            config = self._load_smtp_config()
            results = send_outreach_batch(
                self._selected_leads,
                template_name=self._template_var.get(),
                smtp_config=config,
                dry_run=dry_run,
                skip_already_contacted=self._skip_contacted_var.get(),
            )
            msg = (
                f"Resultados del outreach:\n"
                f"  Enviados: {results['sent']}\n"
                f"  Omitidos: {results['skipped']}\n"
                f"  Suprimidos (baja): {results.get('suppressed', 0)}\n"
                f"  Rebotados: {results.get('bounced', 0)}\n"
                f"  Errores: {len(results['errors'])}\n"
                f"  Cap diario alcanzado: {'SÍ' if results.get('daily_cap_reached') else 'NO'}\n"
                f"  Modo prueba: {'SÍ' if dry_run else 'NO'}"
            )
            messagebox.showinfo("Outreach completado", msg)

            if results.get("previews"):
                self._preview_text.delete("1.0", tk.END)
                for prev in results["previews"][:3]:
                    self._preview_text.insert(tk.END, f"Para: {prev['to']}\n")
                    self._preview_text.insert(tk.END, f"Asunto: {prev['subject']}\n")
                    self._preview_text.insert(tk.END, prev['preview'] + "\n\n" + "─" * 40 + "\n\n")

        except Exception as e:
            messagebox.showerror("Error en outreach", str(e))

    def _load_smtp_config(self) -> dict:
        """Carga la configuración SMTP desde el archivo .env vía scripts/config.py."""
        try:
            import config as cfg_module
            return cfg_module.get_smtp_config()
        except Exception:
            return {}

    def _gen_linkedin(self):
        if not self._selected_leads:
            messagebox.showinfo("LeadHunter Pro", "Carga leads primero")
            return
        lead = self._selected_leads[0]
        try:
            from outreach import generate_linkedin_message
            msg = generate_linkedin_message(lead)
            self._preview_text.delete("1.0", tk.END)
            self._preview_text.insert(tk.END, "MENSAJE LINKEDIN (máx 300 chars)\n" + "─" * 40 + "\n\n")
            self._preview_text.insert(tk.END, msg + f"\n\n({len(msg)} caracteres)")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _gen_whatsapp(self):
        if not self._selected_leads:
            messagebox.showinfo("LeadHunter Pro", "Carga leads primero")
            return
        lead = self._selected_leads[0]
        try:
            from outreach import generate_whatsapp_message
            data = json.loads(generate_whatsapp_message(lead))
            self._preview_text.delete("1.0", tk.END)
            self._preview_text.insert(tk.END, "MENSAJE WHATSAPP\n" + "─" * 40 + "\n\n")
            self._preview_text.insert(tk.END, data.get("mensaje", "") + "\n\n")
            if data.get("whatsapp_url"):
                self._preview_text.insert(tk.END, f"URL: {data['whatsapp_url']}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _show_history(self):
        try:
            from outreach import get_outreach_history
            history = get_outreach_history()
            if not history:
                messagebox.showinfo("Historial", "No hay envíos registrados")
                return
            self._preview_text.delete("1.0", tk.END)
            self._preview_text.insert(tk.END, f"HISTORIAL DE OUTREACH ({len(history)} registros)\n" + "─" * 50 + "\n\n")
            for h in history[:30]:
                self._preview_text.insert(tk.END,
                    f"{h.get('ts', '?')[:19]}  {h.get('to_email', '?')[:35]}  "
                    f"[{h.get('status', '?')}]  {h.get('subject', '')[:40]}\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ---------------------------------------------------------------------------
# Tab 5: Configuración

class ConfigTab(tk.Frame):
    """
    Tab de configuración. Las credenciales SMTP se leen del archivo .env vía
    scripts/config.py — NUNCA se persisten en ningún JSON desde la GUI.
    La contraseña no se muestra ni se guarda: solo se indica si está configurada.
    """
    def __init__(self, parent, status_var):
        super().__init__(parent, bg=COLORS["bg"])
        self._status_var = status_var
        self._build()
        self._refresh_status()

    def _build(self):
        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=24, pady=16)

        # --- Cabecera de estado del .env ---
        SectionLabel(main, "Credenciales (archivo .env)").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self._env_path_lbl = tk.Label(
            main, text="", bg=COLORS["bg"], fg=COLORS["text_dim"],
            font=("Segoe UI", 9), justify="left", anchor="w")
        self._env_path_lbl.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # --- Tabla de estado de claves SMTP (sin mostrar la contraseña) ---
        self._keys_frame = tk.Frame(main, bg=COLORS["bg"])
        self._keys_frame.grid(row=2, column=0, columnspan=2, sticky="we", pady=(0, 8))

        # --- Explicación de seguridad ---
        info = (
            "Las credenciales SMTP se cargan desde un archivo .env (no se guardan\n"
            "en la aplicación). Crea un archivo .env a partir de .env.example y\n"
            "rellena SMTP_USER, SMTP_PASSWORD, etc. La contraseña NUNCA se muestra\n"
            "ni se persiste en ningún JSON.\n\n"
            "Orden de búsqueda del .env:\n"
            "  1) Ruta de la variable de entorno LEADHUNTER_ENV\n"
            "  2) ./.env (directorio de trabajo)\n"
            "  3) <raíz del proyecto>/.env\n"
            "  4) ~/.leadhunter.env\n\n"
            "Para Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, STARTTLS.\n"
            "Requiere una 'Contraseña de aplicación' (no la contraseña normal)."
        )
        tk.Label(main, text=info, bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 8), justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=4)

        # Separador
        tk.Frame(main, bg=COLORS["border"], height=1).grid(
            row=4, column=0, columnspan=2, sticky="we", pady=12)

        # --- Botones de acción ---
        btn_row = tk.Frame(main, bg=COLORS["bg"])
        btn_row.grid(row=5, column=0, columnspan=2, sticky="w")
        IconButton(btn_row, "Abrir .env", command=self._open_env).pack(side="left", padx=(0, 8))
        IconButton(btn_row, "Recargar", command=self._refresh_status,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=6).pack(side="left", padx=(0, 8))
        IconButton(btn_row, "Probar SMTP", command=self._test_smtp,
                   style="secondary", font=("Segoe UI", 9), padx=10, pady=6).pack(side="left")

        # Status config
        self._config_status = tk.Label(main, text="", bg=COLORS["bg"],
                                        fg=COLORS["text_dim"], font=("Segoe UI", 9),
                                        justify="left", anchor="w", wraplength=600)
        self._config_status.grid(row=6, column=0, columnspan=2, sticky="w", pady=8)

    def _refresh_status(self):
        """Lee el estado de configuración desde config.smtp_config_status()."""
        try:
            import config as cfg_module
            status = cfg_module.smtp_config_status()
        except Exception as e:  # noqa: BLE001
            self._env_path_lbl.config(
                text=f"Error al cargar configuración: {e}", fg=COLORS["error"])
            return

        env_found = status.get("env_found")
        env_file = status.get("env_file") or ""
        if env_found:
            self._env_path_lbl.config(
                text=f"Archivo .env encontrado: {env_file}", fg=COLORS["success"])
        else:
            self._env_path_lbl.config(
                text="No se encontró ningún archivo .env — crea uno a partir de .env.example",
                fg=COLORS["warning"])

        # Redibujar la tabla de claves
        for w in self._keys_frame.winfo_children():
            w.destroy()
        for i, (key, info) in enumerate(status.get("keys", {}).items()):
            tk.Label(self._keys_frame, text=key, bg=COLORS["bg"],
                     fg=COLORS["text_dim"], font=("Segoe UI", 9),
                     width=20, anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            configured = info.get("configured")
            display = info.get("display", "")
            color = COLORS["success"] if configured else COLORS["error"]
            tk.Label(self._keys_frame, text=display, bg=COLORS["bg"],
                     fg=color, font=("Segoe UI", 9), anchor="w").grid(
                row=i, column=1, sticky="w", pady=2)

    def _open_env(self):
        """Abre el archivo .env activo en el editor del sistema, o explica cómo crearlo."""
        try:
            import config as cfg_module
            env_path = cfg_module.get_env_path()
        except Exception:
            env_path = None

        if not env_path:
            example = _SCRIPTS_DIR.parent / ".env.example"
            messagebox.showinfo(
                "Archivo .env no encontrado",
                "No existe ningún archivo .env todavía.\n\n"
                f"1) Copia la plantilla:\n   {example}\n"
                f"2) Renómbrala a '.env' en la raíz del proyecto:\n"
                f"   {_SCRIPTS_DIR.parent / '.env'}\n"
                "3) Rellena SMTP_USER, SMTP_PASSWORD, etc.\n\n"
                "El archivo .env está en .gitignore y nunca se sube al repositorio.")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(env_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{env_path}"')
            else:
                os.system(f'xdg-open "{env_path}" >/dev/null 2>&1 &')
            self._config_status.config(
                text=f"Abriendo {env_path}", fg=COLORS["text_dim"])
        except Exception as e:  # noqa: BLE001
            messagebox.showinfo("Editar .env",
                                f"Edita manualmente el archivo:\n{env_path}\n\n({e})")

    def _test_smtp(self):
        """Prueba SMTP usando exclusivamente las credenciales del .env."""
        try:
            import config as cfg_module
            smtp_cfg = cfg_module.get_smtp_config()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error de configuración", str(e))
            return

        if not smtp_cfg.get("smtp_user") or not smtp_cfg.get("smtp_password"):
            messagebox.showwarning(
                "Configuración incompleta",
                "Faltan SMTP_USER o SMTP_PASSWORD en el archivo .env.\n"
                "Usa 'Abrir .env' para configurarlos.")
            return
        try:
            from outreach import send_email
            send_email(
                to=smtp_cfg.get("from_email") or smtp_cfg["smtp_user"],
                subject="LeadHunter Pro — Prueba de conexión SMTP",
                body="Este es un email de prueba enviado desde LeadHunter Pro "
                     "para verificar la configuración SMTP del archivo .env.",
                config=smtp_cfg,
            )
            messagebox.showinfo("SMTP OK", "Conexión SMTP correcta. Email de prueba enviado.")
            self._config_status.config(text="SMTP verificado correctamente", fg=COLORS["success"])
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error SMTP", str(e))
            self._config_status.config(text=f"Error SMTP: {str(e)[:80]}", fg=COLORS["error"])


# ---------------------------------------------------------------------------
# Ventana de detalle de lead

class LeadDetailWindow(tk.Toplevel):
    def __init__(self, parent, lead: dict):
        super().__init__(parent)
        self.title(f"Lead: {lead.get('razonSocial', '?')}")
        self.configure(bg=COLORS["bg"])
        self.geometry("680x600")
        self.resizable(True, True)

        text = scrolledtext.ScrolledText(self, wrap=tk.WORD,
                                          bg=COLORS["panel"],
                                          fg=COLORS["text"],
                                          font=("Consolas", 10),
                                          relief="flat")
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert(tk.END, json.dumps(lead, ensure_ascii=False, indent=2))
        text.config(state="disabled")

        btn_close = IconButton(self, "Cerrar", command=self.destroy, style="secondary")
        btn_close.pack(pady=(0, 12))


# ---------------------------------------------------------------------------
# Barra de estado

class StatusBar(tk.Frame):
    def __init__(self, parent, status_var):
        super().__init__(parent, bg=COLORS["header_bg"], height=28)
        self.pack_propagate(False)

        # Source status indicators
        self._source_frame = tk.Frame(self, bg=COLORS["header_bg"])
        self._source_frame.pack(side="right", padx=8)

        self._status_lbl = tk.Label(self, textvariable=status_var,
                                     bg=COLORS["header_bg"], fg=COLORS["text_dim"],
                                     font=("Segoe UI", 9), anchor="w")
        self._status_lbl.pack(side="left", padx=8)

        # Actualizar indicadores de fuentes periódicamente
        self.after(2000, self._update_sources)

    def _update_sources(self):
        try:
            from _common import SourceStatus
            snapshot = SourceStatus.snapshot()
            for widget in self._source_frame.winfo_children():
                widget.destroy()
            for src, status in list(snapshot.items())[:6]:  # Máx 6 indicadores
                color = COLORS["success"] if "ok" in status else COLORS["warning"] if "stub" in status else COLORS["error"]
                tk.Label(self._source_frame, text=f"● {src}",
                          bg=COLORS["header_bg"], fg=color,
                          font=("Segoe UI", 8)).pack(side="left", padx=4)
        except Exception:
            pass
        self.after(3000, self._update_sources)


# ---------------------------------------------------------------------------
# Ventana principal

class LeadHunterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LeadHunter Pro — B2B Lead Generation")
        self.configure(bg=COLORS["bg"])
        self.geometry("1280x820")
        self.minsize(900, 600)

        # Icono (si existe)
        # self.iconbitmap("icon.ico")

        configure_styles()

        self._status_var = tk.StringVar(value="Listo.")
        self._result_queue: queue.Queue = queue.Queue()

        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg=COLORS["header_bg"], height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="LeadHunter Pro",
                  bg=COLORS["header_bg"], fg=COLORS["text"],
                  font=("Segoe UI", 16, "bold")).pack(side="left", padx=16, pady=12)
        tk.Label(header, text="B2B Lead Generation Engine",
                  bg=COLORS["header_bg"], fg=COLORS["text_dim"],
                  font=("Segoe UI", 10)).pack(side="left")

        # Notebook (tabs)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        # Tab 1: Descubrir
        self._tab_descubrir = DescubrirTab(nb, self._status_var, self._result_queue)
        nb.add(self._tab_descubrir, text="  Descubrir  ")

        # Tab 2: Analizar
        self._tab_analizar = AnalizarTab(nb, self._status_var, self._result_queue)
        nb.add(self._tab_analizar, text="  Analizar  ")

        # Tab 3: Leads
        self._tab_leads = LeadsTab(nb, self._status_var)
        nb.add(self._tab_leads, text="  Leads  ")

        # Tab 4: Outreach
        self._tab_outreach = OutreachTab(nb, self._status_var, self._tab_leads)
        nb.add(self._tab_outreach, text="  Outreach  ")

        # Tab 5: Config
        self._tab_config = ConfigTab(nb, self._status_var)
        nb.add(self._tab_config, text="  Config  ")

        # Sincronizar leads entre Descubrir y Leads tabs
        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Status bar
        status_bar = StatusBar(self, self._status_var)
        status_bar.pack(fill="x", side="bottom")

    def _on_tab_change(self, event):
        """Sincroniza leads cuando se cambia de tab."""
        nb = event.widget
        current_tab = nb.select()
        tab_text = nb.tab(current_tab, "text").strip()
        if "Leads" in tab_text:
            # Sincronizar leads de Descubrir a Leads tab
            if hasattr(self._tab_descubrir, "_leads") and self._tab_descubrir._leads:
                self._tab_leads.load_leads(self._tab_descubrir._leads)


def run():
    """Punto de entrada para lanzar la aplicación GUI."""
    app = LeadHunterApp()
    app.mainloop()


if __name__ == "__main__":
    run()
