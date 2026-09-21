"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { setAuthTokenProvider } from "@/lib/authFetch";

/**
 * Headless component that syncs Clerk's JWT provider with authFetch.
 * Mounts inside RootLayout when Clerk is enabled.
 */
export function AuthTokenSync() {
  const isClerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (!isClerkConfigured) return null;
  return <AuthTokenSyncInner />;
}

function AuthTokenSyncInner() {
  const { getToken, isSignedIn, isLoaded, userId } = useAuth();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      setAuthTokenProvider(getToken);
    } else if (isLoaded && !isSignedIn) {
      setAuthTokenProvider(null);
    }
  }, [isLoaded, isSignedIn, getToken, userId]);

  return null;
}
