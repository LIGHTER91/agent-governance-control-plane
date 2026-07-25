import Link from "next/link";
import { AgentsList } from "./agents-list";

export default function AgentsPage() {
  return (
    <>
      <section className="page-header agent-registry-header">
        <div>
          <p className="eyebrow">Agent Registry</p>
          <h2>Agents</h2>
          <p>
            Register and review governed Agents with ownership, environment,
            lifecycle status, risk classification, framework, and declared
            access.
          </p>
        </div>
        <Link className="agent-primary-link-button" href="/agents/new">
          Register agent
        </Link>
      </section>

      <AgentsList />
    </>
  );
}
