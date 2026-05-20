import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

const files = [
  "app/layout.tsx",
  "app/page.tsx",
  "app/agents/page.tsx",
  "app/policies/page.tsx",
  "app/runtime-gateway/page.tsx",
  "app/human-approvals/page.tsx",
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
