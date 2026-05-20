import { PlaceholderPage } from "../placeholder-content";

export default function EvidencePage() {
  return (
    <PlaceholderPage
      eyebrow="Evidence Review"
      title="Evidence"
      summary="A future viewer for filtered Evidence Bundle JSON and linked governance records."
      plannedItems={[
        { label: "Bundle export", status: "backend exists" },
        { label: "Trace to decision links", status: "backend exists" },
        { label: "Safe evidence viewer", status: "planned" }
      ]}
    />
  );
}
