import type { Metadata } from "next";
import "./globals.css";
import { Inter, JetBrains_Mono } from "next/font/google";
import { cn } from "@/lib/utils";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClerkProvider } from "@clerk/nextjs";
import { AuthTokenSync } from "@/components/AuthTokenSync";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Signal — Supplier Intelligence Platform",
  description:
    "Real-time operational intelligence across your supplier network. Detect deterioration, track trajectory, and resolve exceptions.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const isClerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  const bodyContent = (
    <html
      lang="en"
      className={cn("dark font-sans", inter.variable, jetbrainsMono.variable)}
    >
      <body className="bg-background text-foreground antialiased min-h-screen overflow-hidden">
        <TooltipProvider>
          <AuthTokenSync />
          {children}
        </TooltipProvider>
      </body>
    </html>
  );

  if (!isClerkConfigured) {
    return bodyContent;
  }

  return <ClerkProvider>{bodyContent}</ClerkProvider>;
}
