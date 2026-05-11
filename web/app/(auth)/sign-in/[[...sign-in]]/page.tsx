/**
 * Clerk sign-in catch-all route.
 *
 * When Clerk is wired up in Phase 1, this renders <SignIn /> from
 * @clerk/nextjs and handles every sub-path (/sign-in, /sign-in/factor-one,
 * /sign-in/factor-two, etc.) under the same component.
 *
 * Until then it's a placeholder so the route exists in the routing table.
 */
export default function SignInPage() {
  return (
    <main className="container mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-4">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Clerk integration lands in Phase 1.
      </p>
    </main>
  );
}
