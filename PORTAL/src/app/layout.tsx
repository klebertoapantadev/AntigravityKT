import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portal AgenteVentas | Tinkay",
  description: "Plataforma de gestión inteligente para chatbots, RAG y monitoreo multitenant.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body style={{ minHeight: '100vh' }}>
        {children}
      </body>
    </html>
  );
}
