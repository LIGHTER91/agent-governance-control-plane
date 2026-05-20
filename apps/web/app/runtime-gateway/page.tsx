import { PlaceholderPage } from "../placeholder-content";

export default function RuntimeGatewayPage() {
  return (
    <PlaceholderPage
      eyebrow="Runtime Decisions"
      title="Runtime Gateway"
      summary="A future review surface for governed tool-call decisions, simulation results, and config-gated enforcement behavior."
      plannedItems={[
        { label: "Decision requests", status: "backend exists" },
        { label: "Resume checks", status: "backend exists" },
        { label: "Adapter status", status: "planned" }
      ]}
    />
  );
}
