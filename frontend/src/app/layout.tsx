import type { Metadata } from "next";
import { Handjet } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const handjet = Handjet({
  subsets: ["latin"],
  variable: "--font-handjet",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Polymarket AI Trading Bot",
  description: "AI-powered prediction market trading with news analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${handjet.className} antialiased bg-black text-white`}
      >
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
