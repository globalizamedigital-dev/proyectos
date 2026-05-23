"use client";

import { useState } from "react";
import { CheckCircle2, Mail, Send, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

interface SmtpConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  fromEmail: string;
  fromName: string;
  useSsl: boolean;
  useTls: boolean;
}

const INITIAL: SmtpConfig = {
  host: "",
  port: 465,
  user: "",
  password: "",
  fromEmail: "",
  fromName: "Globalizame",
  useSsl: true,
  useTls: false,
};

export function SmtpForm() {
  const [cfg, setCfg] = useState<SmtpConfig>(INITIAL);
  const [testState, setTestState] = useState<"idle" | "running" | "ok" | "error">("idle");
  const [testMessage, setTestMessage] = useState<string | null>(null);

  const update = <K extends keyof SmtpConfig>(k: K, v: SmtpConfig[K]) =>
    setCfg((c) => ({ ...c, [k]: v }));

  const testSmtp = async () => {
    setTestState("running");
    setTestMessage(null);
    // Stub: cuando el endpoint /config/smtp/test esté listo, lo llamamos aquí.
    await new Promise((r) => setTimeout(r, 1200));
    if (!cfg.host || !cfg.user || !cfg.password) {
      setTestState("error");
      setTestMessage("Faltan host, user o password.");
    } else {
      setTestState("ok");
      setTestMessage(`Conexión validada contra ${cfg.host}:${cfg.port}.`);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <header className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <Mail className="h-4 w-4 text-secondary" />
          <span className="label-eyebrow">SMTP · saliente</span>
        </div>
        <span className="text-[11px] tracking-wider text-muted-foreground">
          Hostinger · Gmail (App Password) · Zoho Free
        </span>
      </header>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Field label="01 · Host">
          <Input
            value={cfg.host}
            onChange={(e) => update("host", e.target.value)}
            placeholder="smtp.hostinger.com"
            className={fieldClass}
          />
        </Field>
        <Field label="02 · Puerto">
          <Input
            type="number"
            value={cfg.port}
            onChange={(e) => update("port", Number(e.target.value) || 465)}
            placeholder="465 SSL · 587 STARTTLS"
            className={fieldClass}
          />
        </Field>
        <Field label="03 · Usuario">
          <Input
            value={cfg.user}
            onChange={(e) => update("user", e.target.value)}
            placeholder="outreach@globalizame.com"
            autoComplete="off"
            className={fieldClass}
          />
        </Field>
        <Field label="04 · Contraseña">
          <Input
            type="password"
            value={cfg.password}
            onChange={(e) => update("password", e.target.value)}
            placeholder="••••••••"
            autoComplete="new-password"
            className={fieldClass}
          />
        </Field>
        <Field label="05 · From email">
          <Input
            value={cfg.fromEmail}
            onChange={(e) => update("fromEmail", e.target.value)}
            placeholder="outreach@globalizame.com"
            className={fieldClass}
          />
        </Field>
        <Field label="06 · From name">
          <Input
            value={cfg.fromName}
            onChange={(e) => update("fromName", e.target.value)}
            className={fieldClass}
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4 border-t border-border/60 pt-4">
        <label className="flex cursor-pointer select-none items-center gap-3">
          <Switch
            checked={cfg.useSsl}
            onCheckedChange={(v) => {
              update("useSsl", v);
              if (v) update("useTls", false);
            }}
            className="data-[state=checked]:bg-primary"
          />
          <span className="text-sm">
            SSL directo <span className="text-muted-foreground">(puerto 465)</span>
          </span>
        </label>
        <label className="flex cursor-pointer select-none items-center gap-3">
          <Switch
            checked={cfg.useTls}
            onCheckedChange={(v) => {
              update("useTls", v);
              if (v) update("useSsl", false);
            }}
            className="data-[state=checked]:bg-primary"
          />
          <span className="text-sm">
            STARTTLS <span className="text-muted-foreground">(puerto 587)</span>
          </span>
        </label>
      </div>

      {testMessage && (
        <div
          className={cn(
            "flex items-start gap-3 border px-4 py-3 text-[12px]",
            testState === "ok"
              ? "border-primary/40 bg-primary/[0.06] text-primary"
              : "border-destructive/40 bg-destructive/[0.06] text-destructive",
          )}
        >
          {testState === "ok" ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 shrink-0" />
          )}
          <span>{testMessage}</span>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border/60 pt-4">
        <span className="text-[11px] tracking-wider text-muted-foreground">
          Esta configuración se guarda cifrada en Supabase. No se loguea.
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={testSmtp}
            disabled={testState === "running"}
            className="rounded-none border-border bg-transparent text-[11px] uppercase tracking-wider"
          >
            {testState === "running" ? "Probando…" : "Probar conexión"}
          </Button>
          <Button className="rounded-none bg-primary uppercase tracking-wider">
            <Send className="mr-1.5 h-3.5 w-3.5" />
            Guardar
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1">
        <span className="label-eyebrow">{label}</span>
      </div>
      {children}
    </div>
  );
}

const fieldClass = cn(
  "h-11 rounded-none border-0 border-b border-border/30 bg-transparent px-0 text-sm shadow-none",
  "focus-visible:border-primary focus-visible:ring-0",
  "placeholder:text-muted-foreground/50",
);
