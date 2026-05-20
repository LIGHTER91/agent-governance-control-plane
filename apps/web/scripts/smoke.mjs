import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

const files = [
  "app/layout.tsx",
  "app/page.tsx",
  "app/agents/page.tsx",
  "app/agents/agents-list.tsx",
  "app/lib/api.ts",
  "app/lib/agents.ts",
  "app/lib/human-approvals.ts",
  "app/policies/page.tsx",
  "app/runtime-gateway/page.tsx",
  "app/human-approvals/page.tsx",
  "app/human-approvals/human-approvals-list.tsx",
  "app/evidence/page.tsx",
  "app/audit/page.tsx",
  "app/settings/page.tsx"
];

const source = (
  await Promise.all(files.map((file) => readFile(join(root, file), "utf8")))
).join("\n");

const requiredText = [
  "Agents",
  "Policies",
  "Runtime Gateway",
  "Human Approvals",
  "Evidence",
  "Audit",
  "Settings",
  "Agent Registry",
  "GET /agents",
  "NEXT_PUBLIC_AGCP_API_BASE_URL",
  "Loading agents",
  "Unable to load agents",
  "No agents registered",
  "owner_name",
  "owner_id",
  "owner_type",
  "environment",
  "status",
  "risk_level",
  "framework",
  "GET /human-approvals",
  "Loading human approvals",
  "Unable to load human approvals",
  "No human approvals",
  "policy_decision_id",
  "requested_by_actor_type",
  "requested_by_actor_id",
  "reviewed_by_actor_type",
  "reviewed_by_actor_id",
  "expires_at",
  "pending",
  "approved",
  "rejected",
  "cancelled",
  "expired",
  "Human Approval",
  "Evidence Bundle",
  "RBAC Foundations"
];

const forbiddenText = [
  "compliance score",
  "AI Act compliant",
  "ISO 42001 certified",
  "production-ready",
  "fully compliant"
];

for (const text of requiredText) {
  if (!source.includes(text)) {
    throw new Error(`Missing expected dashboard text: ${text}`);
  }
}

const normalizedSource = source.toLowerCase();

for (const text of forbiddenText) {
  if (normalizedSource.includes(text.toLowerCase())) {
    throw new Error(`Forbidden dashboard claim found: ${text}`);
  }
}

console.log("Dashboard shell smoke check passed.");
