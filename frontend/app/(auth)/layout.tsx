/** Logged-out screens: one phone-width column, centred on bigger screens. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto min-h-dvh max-w-md">{children}</div>;
}
