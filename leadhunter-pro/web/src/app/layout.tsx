import type { Metadata } from "next";
import { Inter, Josefin_Sans } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const josefin = Josefin_Sans({
  subsets: ["latin"],
  variable: "--font-josefin",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Cazador · Globalizame",
  description:
    "El cazador de leads B2B cualificados de Globalizame. Empresas reales " +
    "desde fuentes oficiales españolas. Tu negocio liberado. Tu tiempo recuperado.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es"
      className={`${inter.variable} ${josefin.variable} h-full dark`}
    >
      <body className="min-h-full flex flex-col antialiased">{children}</body>
    </html>
  );
}
