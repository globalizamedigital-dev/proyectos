import { getSupabaseServerClient } from "@/lib/supabase-server";
import { LeadsClient } from "./_components/leads-client";

export const metadata = {
  title: "Leads · Cazador Globalizame",
  description: "Corpus persistido de leads B2B.",
};

/**
 * Pre-carga la primera página de leads server-side (RLS lo limita al tenant
 * del usuario autenticado). El cliente se encarga de filtros y paginación.
 */
export default async function LeadsPage() {
  const sb = await getSupabaseServerClient();
  const { data, error } = await sb
    .from("leads")
    .select(
      "id, razon_social, nif, score, grade, decisor, decisor_role, email_principal, telefono, domain, provincia, sector, sources_hit, last_seen",
    )
    .order("score", { ascending: false })
    .limit(200);

  // El check constraint de BD garantiza grade ∈ {A,B,C,D}; el tipo de
  // supabase-js lo declara como string, pero aquí podemos estrechar con seguridad.
  const leads = (data ?? []) as unknown as import("./_components/leads-client").LeadRow[];
  return <LeadsClient initialLeads={leads} initialError={error?.message ?? null} />;
}
