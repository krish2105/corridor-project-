import type { Metadata } from "next";
import "./globals.css";
import Rail from "@/components/Rail";
import EnhanceTables from "@/components/EnhanceTables";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Corridor Survey Audit",
  description:
    "Independent re-derivation of the JDA classified turning movement survey for six " +
    "junctions on the Mansarover Metro–Sanganer Stadium corridor, Jaipur.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // suppressHydrationWarning: the inline theme script sets data-theme on <html>
  // before React hydrates, so server and client markup cannot match here.
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap"
        />
      </head>
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "document.documentElement.setAttribute('data-theme'," +
              "localStorage.getItem('corridor-theme')||'light');",
          }}
        />
        <ThemeToggle />
        <Rail />
        <EnhanceTables />
        {children}
      </body>
    </html>
  );
}
