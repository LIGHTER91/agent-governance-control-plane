# Compliance Positioning

## Important rule

This product must not claim that it automatically makes an organization compliant with any law, regulation, or standard.

Avoid:

- "AI Act compliant";
- "ISO 42001 certified";
- "guaranteed compliance";
- "regulator-approved";
- "fully compliant by design".

Prefer:

- "supports evidence collection";
- "helps document governance controls";
- "helps enforce internal policies";
- "helps prepare audit evidence";
- "supports AI governance workflows";
- "maps controls to internal or external frameworks".

## Compliance-relevant capabilities

The platform can eventually support:

- system inventory;
- ownership;
- risk classification;
- policy enforcement;
- human oversight;
- logging;
- audit trails;
- incident review;
- lifecycle documentation;
- evidence exports.

## Product copy guidance

Good:

> Agent Governance Control Plane helps organizations govern AI agents by centralizing registry, policy decisions, human oversight, and evidence exports.

Bad:

> Agent Governance Control Plane makes your agents AI Act compliant.

## Internal design guidance

Build evidence primitives before regulatory templates.

First-class entities:

- Agent;
- Policy;
- PolicyDecision;
- AuditLog;
- Approval;
- EvidenceBundle.

Later mappings:

- internal policy controls;
- ISO 42001 control mapping;
- AI Act readiness mapping;
- customer-specific governance frameworks.
