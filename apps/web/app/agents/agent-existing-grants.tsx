import Link from "next/link";
import type { AgentGovernanceProfileAccessGrant } from "../lib/agents";
import {
  formatGovernanceValue
} from "./agent-governance-model";
import { AgentStatusBadge } from "./agent-form-controls";

export function AgentExistingGrants({
  grants
}: {
  grants: AgentGovernanceProfileAccessGrant[];
}) {
  return (
    <section className="agent-existing-grants">
      <header>
        <div>
          <span>Persisted declarations</span>
          <h3>Existing Agent Access Grants</h3>
          <p>
            Review current declarations here. Broader suspend, revoke,
            reactivate, and expire actions remain in Access &amp; Data.
          </p>
        </div>
        <Link href="/access-data#access-grants">
          Open lifecycle workspace
        </Link>
      </header>

      {grants.length === 0 ? (
        <div className="agent-inline-state">
          <strong>No existing Access Grants</strong>
          <p>This Agent has no persisted governed access declarations yet.</p>
        </div>
      ) : (
        <ul>
          {grants.map((grant) => (
            <li key={grant.id}>
              <div className="agent-existing-grant-head">
                <div>
                  <strong>{grant.target?.name || grant.name}</strong>
                  <span>
                    {formatGovernanceValue(grant.target_type)}
                    {grant.target?.inventory_type
                      ? ` · ${formatGovernanceValue(grant.target.inventory_type)}`
                      : ""}
                  </span>
                </div>
                <div>
                  <AgentStatusBadge value={grant.status} />
                  <AgentStatusBadge value={grant.risk_level} />
                </div>
              </div>
              <p>{grant.reason || "No governance reason recorded."}</p>
              <dl>
                <div>
                  <dt>Expires</dt>
                  <dd>{formatTimestamp(grant.expires_at)}</dd>
                </div>
                <div>
                  <dt>Access Grant ID</dt>
                  <dd>{grant.id}</dd>
                </div>
                <div>
                  <dt>Target ID</dt>
                  <dd>{grant.target_id || grant.external_ref || "Not set"}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "No expiration";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}
