import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main className="min-h-screen w-full flex items-center justify-center bg-zinc-950 p-4 relative overflow-hidden">
      {/* Subtle grid background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#27272a15_1px,transparent_1px),linear-gradient(to_bottom,#27272a15_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* Ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center gap-6">
        <div className="text-center space-y-1.5">
          <div className="flex items-center justify-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-orange-500" />
            <h1 className="text-lg font-bold tracking-tight text-zinc-100 font-mono">
              SIGNAL
            </h1>
          </div>
          <p className="text-xs text-zinc-400">
            Supplier Intelligence Platform — Create Account
          </p>
        </div>

        <SignUp
          appearance={{
            elements: {
              card: "bg-zinc-900 border border-zinc-800 shadow-2xl rounded-lg",
              headerTitle: "text-zinc-100",
              headerSubtitle: "text-zinc-400",
              socialButtonsBlockButton: "bg-zinc-800 border-zinc-700 text-zinc-200 hover:bg-zinc-700",
              formButtonPrimary: "bg-orange-500 hover:bg-orange-600 text-white font-medium",
              formFieldLabel: "text-zinc-300",
              formFieldInput: "bg-zinc-950 border-zinc-800 text-zinc-100 focus:border-orange-500",
              footerActionLink: "text-orange-400 hover:text-orange-300",
            },
          }}
        />
      </div>
    </main>
  );
}
