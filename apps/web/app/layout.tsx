import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { PaddleProvider } from "@/components/paddle-provider";
import { createClient } from "@/lib/supabase/server";

const geist = Geist({
  variable: "--font-geist-sans",
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
    <html lang="en" className={`${geist.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-slate-50">
        <PaddleProvider />
        <Nav userEmail={user?.email} />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
