import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import type { Database } from "@/lib/database.types";

/**
 * Cliente Supabase para server components, route handlers y server actions.
 * Lee/escribe las cookies de sesión vía `next/headers` para que la sesión
 * fluya entre cliente y servidor sin tener que pasarla a mano.
 *
 * Usa la `anon key`; las operaciones quedan limitadas por RLS al usuario
 * autenticado. Para escrituras "service" que tienen que saltar RLS (jobs,
 * webhooks), crear un cliente separado con `SUPABASE_SERVICE_ROLE_KEY` en
 * api/, NUNCA en el frontend.
 */
export async function getSupabaseServerClient() {
  const cookieStore = await cookies();

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error(
      "Faltan NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_ANON_KEY."
    );
  }

  return createServerClient<Database>(url, key, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // `cookieStore.set` falla en server components que NO son route
          // handlers. Ignorar: las cookies se mantendrán hasta la próxima
          // request que sí pueda escribirlas (middleware o route handler).
        }
      },
    },
  });
}
