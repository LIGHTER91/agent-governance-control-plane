import { PlaceholderPage } from "../placeholder-content";

export default function AuditPage() {
  return (
    <PlaceholderPage
      eyebrow="Audit Trail"
      title="Audit"
      summary="A future audit review surface for append-only governance events and mutation history."
      plannedItems={[
        { label: "Agent mutation audit", status: "backend exists" },
        { label: "Human approval audit", status: "backend exists" },
        { label: "Audit search", status: "planned" }
      ]}
    />
  );
}
