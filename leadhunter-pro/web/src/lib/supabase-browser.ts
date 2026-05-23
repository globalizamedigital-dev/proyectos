"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "@/lib/database.types";

/**
 * Cliente Supabase para componentes de cliente.
 * Solo expone la `anon key` (pública). RLS protege todo lo demás.
 *
 * Uso:
 *   const supabase = getSupabaseBrowserClient();
 *   const { data, error } = await supabase.from("leads").select("*");
 */
let singleton: ReturnType<typeof createBrowserClient<Database>> | null = null;

export function getSupabaseBrowserClient() {
  if (singleton) return singleton;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error(
      "Faltan NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
        "Revisa web/.env.local."
    );
  }

  singleton = createBrowserClient<Database>(url, key);
  return singleton;
}
