"use client";

import { useState } from "react";
import { Copy, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function WhatsappForm() {
  const [phoneId, setPhoneId] = useState("");
  const [businessId, setBusinessId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [verifyToken, setVerifyToken] = useState("");
  const [copied, setCopied] = useState(false);

  const webhookUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/api/webhooks/whatsapp`
      : "/api/webhooks/whatsapp";

  const copy = async () => {
    await navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="space-y-6 p-6">
      <header className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <MessageCircle className="h-4 w-4 text-secondary" />
          <span className="label-eyebrow">WhatsApp · Meta Cloud API directa</span>
        </div>
        <span className="text-[11px] tracking-wider text-muted-foreground">
          Free tier · 1.000 conversaciones/mes
        </span>
      </header>

      <p className="text-[13px] leading-relaxed text-muted-foreground">
        Saca estos valores en{" "}
        <a
          href="https://developers.facebook.com"
          target="_blank"
          rel="noreferrer"
          className="text-primary underline decoration-primary/40 underline-offset-4 hover:decoration-primary"
        >
          developers.facebook.com
        </a>{" "}
        → tu app WhatsApp → API Setup. El access token debe ser de un{" "}
        <span className="font-medium text-foreground">System User permanente</span>,
        no el temporal de 24 h.
      </p>

      <div className="grid grid-cols-1 gap-6">
        <Field label="01 · Phone number ID">
          <Input
            value={phoneId}
            onChange={(e) => setPhoneId(e.target.value)}
            placeholder="15 dígitos"
            className={fieldClass}
          />
        </Field>
        <Field label="02 · WhatsApp Business Account ID">
          <Input
            value={businessId}
            onChange={(e) => setBusinessId(e.target.value)}
            placeholder="15 dígitos"
            className={fieldClass}
          />
        </Field>
        <Field label="03 · Access token (System User · permanente)">
          <Input
            type="password"
            value={accessToken}
            onChange={(e) => setAccessToken(e.target.value)}
            placeholder="EAAxxxxxxxxxxxxxxxx"
            autoComplete="off"
            className={fieldClass}
          />
        </Field>
        <Field label="04 · Verify token (lo inventas tú)">
          <Input
            value={verifyToken}
            onChange={(e) => setVerifyToken(e.target.value)}
            placeholder="cualquier string aleatorio"
            className={fieldClass}
          />
        </Field>
      </div>

      <div className="space-y-2 border-t border-border/60 pt-4">
        <span className="label-eyebrow">05 · Webhook URL (configura esto en Meta)</span>
        <div className="flex items-center gap-2">
          <code className="flex-1 truncate border border-border/60 bg-muted/40 px-3 py-2 font-mono text-[12px]">
            {webhookUrl}
          </code>
          <Button
            variant="outline"
            size="sm"
            onClick={copy}
            className="h-10 shrink-0 rounded-none border-border bg-transparent text-[11px] uppercase tracking-wider"
          >
            <Copy className="mr-1.5 h-3.5 w-3.5" />
            {copied ? "copiado" : "copiar"}
          </Button>
        </div>
        <p className="text-[11px] tracking-wide text-muted-foreground">
          En Meta → tu app → WhatsApp → Configuration → pega esta URL y el
          verify token de arriba. Suscribe los campos: <code>messages</code>,{" "}
          <code>message_status</code>.
        </p>
      </div>

      <div className="flex justify-end border-t border-border/60 pt-4">
        <Button className="rounded-none bg-primary uppercase tracking-wider">
          Guardar config WhatsApp
        </Button>
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
