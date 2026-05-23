"use client";

import { useState } from "react";
import { FileWarning, Mail, MessageCircle, ShieldOff, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { SmtpForm } from "./smtp-form";
import { WhatsappForm } from "./whatsapp-form";
import { SuppressionList } from "./suppression-list";
import { TeamMembers } from "./team-members";
import { PrivacyPanel } from "./privacy-panel";

type Tab = "smtp" | "whatsapp" | "suppression" | "team" | "privacy";

const TABS: { id: Tab; label: string; icon: typeof Mail }[] = [
  { id: "smtp", label: "SMTP", icon: Mail },
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { id: "suppression", label: "Suppression", icon: ShieldOff },
  { id: "team", label: "Equipo", icon: Users },
  { id: "privacy", label: "Privacidad", icon: FileWarning },
];

export function ConfigClient() {
  const [tab, setTab] = useState<Tab>("smtp");

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-6 px-6 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span aria-hidden className="h-px w-10 bg-primary" />
          <span className="label-eyebrow">módulo · config</span>
        </div>
        <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
          La caja de mandos.
        </h1>
        <p className="max-w-2xl text-[14px] leading-relaxed text-muted-foreground">
          Credenciales SMTP del tenant, WhatsApp Business, suppression list
          cross-canal y miembros del equipo Globalizame.
        </p>
      </header>

      {/* Tab nav */}
      <nav className="flex items-stretch gap-px bg-border/40 border border-border/60">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 bg-card px-4 py-3 text-sm transition-colors",
                active
                  ? "border-b-2 border-primary text-primary"
                  : "border-b-2 border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="label-eyebrow" style={{ color: "inherit" }}>{t.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Tab content */}
      <div className="border border-border/60 bg-card">
        {tab === "smtp" && <SmtpForm />}
        {tab === "whatsapp" && <WhatsappForm />}
        {tab === "suppression" && <SuppressionList />}
        {tab === "team" && <TeamMembers />}
        {tab === "privacy" && <PrivacyPanel />}
      </div>
    </div>
  );
}
