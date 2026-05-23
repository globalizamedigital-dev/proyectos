"use client";

/**
 * Último recurso: error que rompe incluso el root layout. Renderizamos
 * un HTML mínimo con marca Globalizame y un botón de recarga. Sin
 * dependencias de Tailwind/shadcn porque el layout no ha cargado.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="es">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0a0a",
          color: "#fafafa",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          padding: 24,
        }}
      >
        <div style={{ maxWidth: 520 }}>
          <div
            style={{
              fontSize: 10,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "#a3a3a3",
            }}
          >
            error · root
          </div>
          <h1
            style={{
              fontWeight: 300,
              fontSize: 36,
              letterSpacing: "-0.02em",
              margin: "16px 0",
            }}
          >
            La app se cayó entera.{" "}
            <span style={{ color: "#86ca28" }}>Mala suerte.</span>
          </h1>
          <p style={{ color: "#a3a3a3", lineHeight: 1.6 }}>
            Esto solo pasa cuando el render del layout raíz revienta. Recarga.
            Si persiste, copia esto y pásaselo a Mario:
          </p>
          <pre
            style={{
              marginTop: 16,
              padding: 12,
              background: "#1f1f1f",
              fontFamily: "ui-monospace, monospace",
              fontSize: 12,
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {error.message}
            {error.digest ? `\ndigest: ${error.digest}` : ""}
          </pre>
          <button
            onClick={reset}
            style={{
              marginTop: 24,
              padding: "12px 24px",
              background: "#86ca28",
              color: "#0a0a0a",
              border: "none",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Recargar
          </button>
        </div>
      </body>
    </html>
  );
}
