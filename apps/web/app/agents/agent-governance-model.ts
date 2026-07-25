import type { AgentRecord } from "../lib/agents";
import type {
  CapabilityRecord,
  ModelAssetRecord,
  SourceRecord
} from "../lib/sources";

export const OWNER_TYPES = [
  "user",
  "team",
  "service",
  "organization_unit"
] as const;
export const ENVIRONMENTS = [
  "development",
  "staging",
  "production"
] as const;
export const AGENT_STATUSES = [
  "draft",
  "under_review",
  "approved",
  "active",
  "suspended",
  "retired"
] as const;
export const RISK_LEVELS = ["low", "medium", "high", "critical"] as const;
export const SENSITIVE_AGENT_STATUSES = [
  "active",
  "suspended",
  "retired"
] as const;

export type OwnerType = (typeof OWNER_TYPES)[number];
export type Environment = (typeof ENVIRONMENTS)[number];
export type AgentStatus = (typeof AGENT_STATUSES)[number];
export type RiskLevel = (typeof RISK_LEVELS)[number];
export type InventoryTargetType = "capability" | "source" | "model_asset";
export type AgentFormField =
  | "name"
  | "description"
  | "framework"
  | "owner_type"
  | "owner_id"
  | "owner_name"
  | "owner_contact_email"
  | "environment"
  | "status"
  | "risk_level";

export type AgentFormValues = {
  name: string;
  description: string;
  framework: string;
  owner_type: OwnerType | "";
  owner_id: string;
  owner_name: string;
  owner_contact_email: string;
  environment: Environment | "";
  status: AgentStatus | "";
  risk_level: RiskLevel | "";
};

export type AgentMutationPayload = {
  name: string;
  description: string | null;
  framework: string | null;
  owner_type: OwnerType;
  owner_id: string;
  owner_name: string;
  owner_contact_email: string | null;
  environment: Environment;
  status: AgentStatus;
  risk_level: RiskLevel;
};

export type AgentFieldErrors = Partial<Record<AgentFormField, string>>;

export type InventoryTarget = {
  key: string;
  id: string;
  target_type: InventoryTargetType;
  name: string;
  description: string | null;
  status: string;
  risk_level: RiskLevel;
  type_label: string;
  context: string | null;
};

export type ProposedAccessGrant = {
  target: InventoryTarget;
  name: string;
  reason: string;
  risk_level: RiskLevel;
  expires_at: string;
};

export type ProposedGrantField = "name" | "reason" | "risk_level" | "expires_at";
export type ProposedGrantErrors = Record<string, Partial<Record<ProposedGrantField, string>>>;

export type AccessGrantCreatePayload = {
  name: string;
  description: null;
  grant_type: "capability" | "source" | "model";
  subject_type: "agent";
  subject_id: string;
  target_type: InventoryTargetType;
  target_id: string;
  external_ref: null;
  status: "pending_review";
  reason: string | null;
  expires_at: string | null;
  risk_level: RiskLevel;
  metadata: Record<string, never>;
};

export type ResourceState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

export type InventoryState = {
  capabilities: ResourceState<InventoryTarget[]>;
  sources: ResourceState<InventoryTarget[]>;
  models: ResourceState<InventoryTarget[]>;
};

export const EMPTY_AGENT_FORM: AgentFormValues = {
  name: "",
  description: "",
  framework: "",
  owner_type: "",
  owner_id: "",
  owner_name: "",
  owner_contact_email: "",
  environment: "",
  status: "",
  risk_level: ""
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function agentFormFromRecord(agent: AgentRecord): AgentFormValues {
  return {
    name: agent.name,
    description: agent.description || "",
    framework: agent.framework || "",
    owner_type: agent.owner_type as OwnerType,
    owner_id: agent.owner_id,
    owner_name: agent.owner_name,
    owner_contact_email: agent.owner_contact_email || "",
    environment: agent.environment as Environment,
    status: agent.status as AgentStatus,
    risk_level: agent.risk_level as RiskLevel
  };
}

export function validateAgentForm(values: AgentFormValues): AgentFieldErrors {
  const errors: AgentFieldErrors = {};

  if (!values.name.trim()) {
    errors.name = "Enter a stable name for this Agent.";
  }
  if (!values.owner_type) {
    errors.owner_type = "Select a backend-supported owner type.";
  }
  if (!values.owner_id.trim()) {
    errors.owner_id = "Enter the real stable owner identifier.";
  }
  if (!values.owner_name.trim()) {
    errors.owner_name = "Enter the persisted owner display name.";
  }
  if (
    values.owner_contact_email.trim() &&
    !EMAIL_PATTERN.test(values.owner_contact_email.trim())
  ) {
    errors.owner_contact_email = "Enter a valid contact email or leave it blank.";
  }
  if (!values.environment) {
    errors.environment = "Select the Agent environment.";
  }
  if (!values.status) {
    errors.status = "Select the Agent lifecycle status.";
  }
  if (!values.risk_level) {
    errors.risk_level = "Select the Agent risk classification.";
  }

  return errors;
}

export function validateProposedGrants(
  proposals: ProposedAccessGrant[]
): ProposedGrantErrors {
  return proposals.reduce<ProposedGrantErrors>((errors, proposal) => {
    const grantErrors: Partial<Record<ProposedGrantField, string>> = {};

    if (!proposal.name.trim()) {
      grantErrors.name = "Enter a name for this Access Grant declaration.";
    }
    if (!RISK_LEVELS.includes(proposal.risk_level)) {
      grantErrors.risk_level = "Select a supported grant risk classification.";
    }
    if (proposal.expires_at && Number.isNaN(Date.parse(proposal.expires_at))) {
      grantErrors.expires_at = "Enter a valid expiration date and time.";
    }

    if (Object.keys(grantErrors).length > 0) {
      errors[proposal.target.key] = grantErrors;
    }
    return errors;
  }, {});
}

export function buildAgentPayload(
  values: AgentFormValues
): AgentMutationPayload {
  if (
    !values.owner_type ||
    !values.environment ||
    !values.status ||
    !values.risk_level
  ) {
    throw new Error("Agent form enums must be selected before building a payload.");
  }

  return {
    name: values.name.trim(),
    description: trimmedOrNull(values.description),
    framework: trimmedOrNull(values.framework),
    owner_type: values.owner_type,
    owner_id: values.owner_id.trim(),
    owner_name: values.owner_name.trim(),
    owner_contact_email: trimmedOrNull(values.owner_contact_email),
    environment: values.environment,
    status: values.status,
    risk_level: values.risk_level
  };
}

export function buildAgentPatch(
  values: AgentFormValues,
  initialValues: AgentFormValues
): Partial<AgentMutationPayload> {
  const current = buildAgentPayload(values);
  const initial = buildAgentPayload(initialValues);

  return (Object.keys(current) as Array<keyof AgentMutationPayload>).reduce<
    Partial<AgentMutationPayload>
  >((patch, field) => {
    if (current[field] !== initial[field]) {
      Object.assign(patch, { [field]: current[field] });
    }
    return patch;
  }, {});
}

export function needsStatusConfirmation(
  values: AgentFormValues,
  initialValues?: AgentFormValues
) {
  if (
    !values.status ||
    !SENSITIVE_AGENT_STATUSES.includes(
      values.status as (typeof SENSITIVE_AGENT_STATUSES)[number]
    )
  ) {
    return false;
  }
  return values.status !== initialValues?.status;
}

export function normalizeCapability(capability: CapabilityRecord): InventoryTarget {
  return {
    key: `capability:${capability.id}`,
    id: capability.id,
    target_type: "capability",
    name: capability.name,
    description: capability.description,
    status: capability.status,
    risk_level: capability.risk_level as RiskLevel,
    type_label: capability.capability_type,
    context: capability.external_ref
  };
}

export function normalizeSource(source: SourceRecord): InventoryTarget {
  return {
    key: `source:${source.id}`,
    id: source.id,
    target_type: "source",
    name: source.name,
    description: source.description,
    status: source.status,
    risk_level: source.risk_level as RiskLevel,
    type_label: source.source_type,
    context: source.owner_name
  };
}

export function normalizeModel(model: ModelAssetRecord): InventoryTarget {
  return {
    key: `model_asset:${model.id}`,
    id: model.id,
    target_type: "model_asset",
    name: model.name,
    description: model.description,
    status: model.status,
    risk_level: model.risk_level as RiskLevel,
    type_label: model.model_type,
    context: [model.provider, model.version].filter(Boolean).join(" · ") || null
  };
}

export function createProposal(target: InventoryTarget): ProposedAccessGrant {
  return {
    target,
    name: "",
    reason: "",
    risk_level: target.risk_level,
    expires_at: ""
  };
}

export function buildAccessGrantPayload(
  agentId: string,
  proposal: ProposedAccessGrant
): AccessGrantCreatePayload {
  return {
    name: proposal.name.trim(),
    description: null,
    grant_type:
      proposal.target.target_type === "model_asset"
        ? "model"
        : proposal.target.target_type,
    subject_type: "agent",
    subject_id: agentId,
    target_type: proposal.target.target_type,
    target_id: proposal.target.id,
    external_ref: null,
    status: "pending_review",
    reason: trimmedOrNull(proposal.reason),
    expires_at: proposal.expires_at
      ? new Date(proposal.expires_at).toISOString()
      : null,
    risk_level: proposal.risk_level,
    metadata: {}
  };
}

export function formatGovernanceValue(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function trimmedOrNull(value: string) {
  const trimmed = value.trim();
  return trimmed || null;
}
