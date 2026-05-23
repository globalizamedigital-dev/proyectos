import type { ReactNode } from "react";
import { Sidebar } from "@/components/app-shell/sidebar";
import { Topbar } from "@/components/app-shell/topbar";
import { StatusBar } from "@/components/app-shell/status-bar";

/**
 * Shell común para todas las pantallas del producto.
 * Estructura: sidebar (col) | { topbar / main / statusbar } (col).
 * El main es el único scrollable; topbar y statusbar quedan pegados.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="relative min-h-0 flex-1 overflow-y-auto">
          {children}
        </main>
        <StatusBar />
      </div>
    </div>
  );
}
