import { PlaceholderPage } from "../placeholder-content";

export default function SettingsPage() {
  return (
    <PlaceholderPage
      eyebrow="Configuration"
      title="Settings"
      summary="A future administration area for runtime, actor, and evidence settings after auth decisions mature."
      plannedItems={[
        { label: "Runtime flags", status: "backend config exists" },
        { label: "Service actor scopes", status: "backend config exists" },
        { label: "User auth settings", status: "not implemented" }
      ]}
    />
  );
}
