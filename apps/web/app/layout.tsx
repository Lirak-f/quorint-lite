import type { Metadata } from "next";
import { Inter, DM_Serif_Display, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { PaddleProvider } from "@/components/paddle-provider";
import { AnalyticsProvider } from "@/components/analytics-provider";
import { createClient } from "@/lib/supabase/server";
import { Toaster } from "sonner";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const dmSerifDisplay = DM_Serif_Display({
  variable: "--font-dm-serif",
  weight: ["400"],
  style: ["normal", "italic"],
  subsets: ["latin"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  weight: ["400", "500", "600"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Quorint — Export market intelligence for Balkan manufacturers",
  description:
    "Get a full export market report in under 5 minutes. Market demand, pricing, compliance, buyer contacts, and a 90-day action plan.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <html lang="en" className={`${inter.variable} ${dmSerifDisplay.variable} ${ibmPlexMono.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-white">
        <AnalyticsProvider>
          <PaddleProvider>
            <Nav userEmail={user?.email} />
            <main className="flex-1">{children}</main>
            <Toaster position="bottom-right" richColors />
          </PaddleProvider>
        </AnalyticsProvider>
      </body>
    </html>
  );
}
