import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Middleware: refresca el token de sesión y protege /(app)/*.
 * Si no hay sesión, redirige a /login con el `next` original.
 */
export async function middleware(req: NextRequest) {
  const res = NextResponse.next({ request: req });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    // En desarrollo sin env vars, dejamos pasar para no romper la web local.
    return res;
  }

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return req.cookies.getAll();
      },
      setAll(cookiesToSet) {
        for (const { name, value, options } of cookiesToSet) {
          req.cookies.set(name, value);
          res.cookies.set(name, value, options);
        }
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = req.nextUrl.pathname;
  const protectedPaths = ["/discover", "/analizar", "/leads", "/outreach", "/config"];
  const needsAuth = protectedPaths.some((p) => path === p || path.startsWith(`${p}/`));

  if (needsAuth && !user) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", path);
    return NextResponse.redirect(loginUrl);
  }

  // Si ya hay sesión y va a /login, manda a /discover.
  if (user && (path === "/login" || path === "/")) {
    return NextResponse.redirect(new URL("/discover", req.url));
  }

  return res;
}

export const config = {
  // Excluimos assets estáticos y rutas internas de Next.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
