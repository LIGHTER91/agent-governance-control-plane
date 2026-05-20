import { AgentsList } from "./agents-list";

export default function AgentsPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Agent Registry</p>
        <h2>Agents</h2>
        <p>
          Registered agents from the backend API, shown with ownership,
          environment, lifecycle status, risk level, and framework metadata.
        </p>
      </section>

      <AgentsList />
    </>
  );
}
