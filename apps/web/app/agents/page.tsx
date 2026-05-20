import { PlaceholderPage } from "../placeholder-content";

export default function AgentsPage() {
  return (
    <PlaceholderPage
      eyebrow="Agent Registry"
      title="Agents"
      summary="A future registry workspace for agent ownership, environment, status, and risk review."
      plannedItems={[
        { label: "Agent list", status: "next" },
        { label: "Agent detail", status: "planned" },
        { label: "Ownership and risk fields", status: "backend exists" }
      ]}
    />
  );
}
