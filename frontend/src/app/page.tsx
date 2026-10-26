import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";

export default function Page() {
  return (
    <AuthGate>
      <AppShell />
    </AuthGate>
  );
}
