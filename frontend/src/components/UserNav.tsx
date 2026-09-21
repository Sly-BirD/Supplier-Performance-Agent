"use client";

import { useUser, SignInButton, UserButton } from "@clerk/nextjs";
import { User, ShieldCheck } from "lucide-react";

export function UserNav() {
  const isClerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!isClerkConfigured) {
    return (
      <div
        className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900/60 border border-zinc-800 text-[11px] font-mono-data text-zinc-400 select-none"
        title="Clerk Auth is in offline dev mode. Add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY to activate."
      >
        <ShieldCheck className="w-3 h-3 text-zinc-500" />
        <span className="hidden sm:inline text-zinc-500">Dev Auth (Bypass)</span>
      </div>
    );
  }

  return <ClerkUserNavContent />;
}

function ClerkUserNavContent() {
  const { isSignedIn, isLoaded } = useUser();

  if (!isLoaded) {
    return (
      <div className="w-7 h-7 rounded-full bg-zinc-800 animate-pulse" />
    );
  }

  if (isSignedIn) {
    return (
      <div className="flex items-center gap-2">
        <UserButton />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <SignInButton mode="modal">
        <button
          type="button"
          className="flex items-center gap-1.5 h-8 px-3 rounded text-xs font-mono-data bg-orange-600 hover:bg-orange-500 text-white font-medium transition-colors"
        >
          <User className="w-3.5 h-3.5" />
          <span>Sign In</span>
        </button>
      </SignInButton>
    </div>
  );
}
