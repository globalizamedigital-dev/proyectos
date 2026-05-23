import { getSupabaseServerClient } from "@/lib/supabase-server";
import { OutreachClient } from "./_components/outreach-client";

export const metadata = {
  title: "Outreach · Cazador Globalizame",
};

/**
 * Pre-carga plantillas (Supabase) y leads en cola (`outreach_status = queued`).
 * En esta vista el envío real lo hace n8n vía webhook; aquí solo se
 * compone, se previsualiza y se confirma.
 */
export default async function OutreachPage() {
  const sb = await getSupabaseServerClient();

  const [templatesRes, leadsRes] = await Promise.all([
    sb
      .from("outreach_templates")
      .select("id, slug, name, channel, subject, body, variables")
      .order("name", { ascending: true }),
    sb
      .from("leads")
      .select("id, razon_social, decisor, email_principal, telefono, score, grade, outreach_status")
      .in("outreach_status", ["queued", "new"])
      .order("score", { ascending: false })
      .limit(100),
  ]);

  // CHECK constraints (channel, grade) garantizan los enums; estrechamos:
  return (
    <OutreachClient
      templates={
        (templatesRes.data ?? []) as unknown as Parameters<typeof OutreachClient>[0]["templates"]
      }
      leads={
        (leadsRes.data ?? []) as unknown as Parameters<typeof OutreachClient>[0]["leads"]
      }
      error={templatesRes.error?.message || leadsRes.error?.message || null}
    />
  );
}
