import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { BetSlipProvider } from "@/components/bets/BetSlip";
import "./globals.css";

export const metadata: Metadata = {
  title: "Quotenfabrik Analyser",
  description: "Privates Analyse-Frontend: Spieltage, Spiel-Details, Daten-Explorer und Auswertung",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body className="min-h-screen antialiased">
        <BetSlipProvider>
          <Nav />
          <main className="mx-auto max-w-7xl px-4 pb-16 pt-6">{children}</main>
        </BetSlipProvider>
      </body>
    </html>
  );
}
