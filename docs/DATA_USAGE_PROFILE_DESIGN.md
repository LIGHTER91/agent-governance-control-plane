# Data Usage Profile Design

## Status

Design plus first backend foundation. A separate `DataUsageProfile` persistence
model, migration, Pydantic schemas, and nested Source API endpoints are
implemented. Runtime request fields, policy evaluator behavior, frontend UI,
scanners, external data catalog integrations, Evidence Bundle profile
summaries, and legal compliance claims remain out of scope.

AGCP remains a governance and evidence control plane. It can support decision
support, enforcement points, and evidence trails, but it is not a DPO, legal
counsel, DLP system, data catalog, or legal compliance certification tool.

## Critical Assessment

Source inventory alone is not enough for contextual runtime governance. A
Source record can identify a knowledge base, database, document store, API,
bucket, filesystem, or other governed data source, but it does not explain how
that data may be used by an Agent.

Data usability depends on more than source identity:

- purpose, such as support answering, semantic search indexing, training, or
  incident triage;
- model and provider, especially when data leaves an internal boundary;
- environment, such as development versus production;
- data classification, personal data, and sensitive data signals;
- review status from data owners, DPO, legal, or governance teams;
- AccessGrant state and expiry;
- policy context and HumanApproval outcomes.

This direction is useful because contextual runtime governance needs stable,
safe facts about a Source before it can decide whether a request like
confidential source vectorization with an external embedding model should be
allowed, denied, or escalated. The risk is that AGCP could overstate what it
knows. Scanner output, catalog tags, or caller-supplied metadata are governance
signals, not legal truth. AGCP should help enforce declared controls and record
evidence; it must not pretend to automatically decide whether a use is lawful.

## Problem Statement

The current Source inventory model captures name, type, external reference,
owner fields, status, risk level, metadata, and timestamps. That is enough to
answer "which source exists?" and "who owns it?", but not enough to answer:

- What kind of data does the source contain?
- Is personal or sensitive data likely to be present?
- Which purposes are allowed or prohibited?
- Which processing types are allowed or prohibited?
- Has a data owner, DPO, legal team, or governance team reviewed the source?
- Is a DPIA required or referenced?
- Has the review expired?
- What safe evidence should be exported when a runtime decision used this
  source?

A Data Usage Profile gives Source records the governance context needed for
future contextual policies without storing raw source contents.

## Source Versus Data Usage Profile

Recommendation: create a separate `DataUsageProfile` object linked to one
Source, rather than putting all fields directly on Source.

Source should remain the stable inventory record for identity, ownership,
lifecycle, and external references. Data Usage Profile should hold governance
classification, declared purpose constraints, processing constraints, review
state, and supporting references.

Reasons to separate the profile:

- Governance classification and review status change on a different cadence
  than source identity.
- Some Sources may not have a reviewed profile yet.
- Review metadata can become rich enough to need its own lifecycle, audit
  events, and eventual history.
- External data catalog, DLP, scanner, DPO, or owner signals can be tracked as
  inputs to the profile without bloating the Source API.
- Future Evidence Bundle exports can include a safe profile summary without
  implying that the entire Source record is legal approval.

The API can later choose to embed a compact profile summary in Source reads for
convenience, but the persistence concept should remain separate. This avoids
turning Source into a full data catalog while still giving runtime governance a
clear source of data-usage context.

## Proposed Fields

Suggested `DataUsageProfile` fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable profile identifier. |
| `source_id` | Linked Source inventory record. |
| `data_classification` | One of `public`, `internal`, `confidential`, `restricted`. |
| `contains_personal_data` | Boolean signal that personal data may be present. |
| `contains_sensitive_data` | Boolean signal that sensitive data may be present. |
| `data_categories` | List such as `customer_data`, `hr_data`, `financial_data`, `health_data`, `source_code`, `trade_secret`. |
| `legal_basis` | Declared metadata, not a legal determination by AGCP. |
| `allowed_purposes` | Purposes that governance owners have declared acceptable. |
| `prohibited_purposes` | Purposes that are explicitly disallowed. |
| `allowed_processing` | Processing types such as `search`, `rag`, `embedding`, `summarization`, `training`. |
| `prohibited_processing` | Processing types that are explicitly disallowed. |
| `residency` | Safe residency or region constraint reference. |
| `retention_policy` | Safe reference or short label for retention expectations. |
| `data_owner` | Safe owner reference, ideally aligned with existing owner conventions. |
| `review_status` | Review state such as `draft`, `approved`, `rejected`, `expired`, or `needs_review`. |
| `dpia_required` | Boolean signal that a DPIA may be required. |
| `dpia_reference` | Safe reference to an external DPIA record, not the DPIA contents. |
| `reviewed_at` | Timestamp of the last profile review. |
| `reviewed_by_actor_type` | Safe reviewer actor type reference. |
| `reviewed_by_actor_id` | Safe reviewer actor ID reference. |
| `review_expires_at` | Timestamp after which review should be considered stale. |
| `metadata` | Additional safe metadata after existing safety filtering. |
| `created_at` | Creation timestamp. |
| `updated_at` | Update timestamp. |

Field values should be conservative and explicit. Empty or unknown values should
remain unknown rather than being inferred silently.

## Suggested Controlled Values

Initial `data_classification` values:

- `public`;
- `internal`;
- `confidential`;
- `restricted`.

Initial `data_categories` values:

- `customer_data`;
- `hr_data`;
- `financial_data`;
- `health_data`;
- `source_code`;
- `trade_secret`;
- `operational_data`;
- `security_data`;
- `other`.

Initial processing values:

- `search`;
- `rag`;
- `embedding`;
- `summarization`;
- `training`;
- `classification`;
- `analytics`;
- `export`;
- `other`.

Implemented `review_status` values:

- `draft`;
- `approved`;
- `rejected`;
- `expired`;
- `needs_review`.

These are governance labels, not legal findings.

## Automatic Detection Versus Human Validation

Data Usage Profile should distinguish signal source from validation status.
Useful signals may come from:

- data catalog tags;
- DLP systems;
- PII scanners;
- source metadata supplied by a platform adapter;
- manual owner classification;
- DPO or legal review;
- external governance systems.

Automatic detection is useful for triage and default controls, but it should
not be treated as legal truth. A PII scanner can say "personal data likely
present"; it cannot decide that a purpose is lawful. A catalog tag can say
"restricted"; it cannot prove that an external embedding provider is approved.
A caller can declare purpose; it cannot validate the purpose by itself.

Human or governance validation should be explicit. Data owners can validate
classification and usage expectations. DPO or legal review can validate declared
review status and DPIA references. AGCP should record these as structured
evidence and policy context, not as certification.

Suggested responsibility split:

- Auto-detected or imported signals: candidate data categories, likely personal
  data presence, likely sensitive data presence, catalog classification tags,
  source residency hints, and scanner run references.
- Human or governance validated fields: final classification, allowed purposes,
  prohibited purposes, allowed processing, prohibited processing, legal basis
  metadata, DPIA requirement, DPIA reference, review status, review expiry, and
  exceptions.
- Runtime caller declarations: purpose, action type, selected Source IDs,
  selected ModelAsset ID, selected Capability ID, and safe request metadata.

The profile should preserve enough provenance to show whether a field was
scanner-suggested, catalog-imported, owner-validated, or DPO-reviewed when that
history becomes available.

## Runtime Use Cases

### Confidential Data And External Embedding Model

Runtime context:

- action_type: `vectorize`;
- Source Data Usage Profile: `data_classification = confidential`;
- ModelAsset: external provider;
- purpose: `semantic_search_indexing`.

Future policy result: deny or require HumanApproval unless the Agent has active
AccessGrants for the Source and ModelAsset and the profile allows embedding for
the declared purpose.

### Sensitive Personal Data And Production Summarization

Runtime context:

- action_type: `summarize`;
- environment: `production`;
- Source profile: `contains_sensitive_data = true`.

Future policy result: require HumanApproval or deny depending on policy,
review status, and AccessGrant coverage.

### Missing Purpose

Runtime context:

- Source profile has allowed and prohibited purposes;
- runtime request omits purpose.

Future policy result: deny or require review in enforcement mode because the
request cannot be matched to allowed usage.

### Prohibited Purpose

Runtime context:

- purpose: `training_data_generation`;
- Source profile: `prohibited_purposes` includes
  `training_data_generation`.

Future policy result: deny.

### Expired Review

Runtime context:

- Source profile `review_expires_at` is in the past or
  `review_status = expired`.

Future policy result: require HumanApproval or deny for production use until
the review is refreshed.

### Missing DPIA Reference

Runtime context:

- Source profile `dpia_required = true`;
- `dpia_reference` is missing;
- action_type: `embedding` or `training`.

Future policy result: require review or deny depending on environment and
classification.

## Policy Examples

These examples are structured governance rules, not a proposal for a generic
DSL.

```text
IF source.data_classification IN confidential, restricted
AND model.provider_type = external
AND action_type = vectorize
THEN deny
```

```text
IF source.contains_sensitive_data = true
AND environment = production
THEN require_human_review
```

```text
IF purpose NOT IN source.allowed_purposes
THEN deny
```

```text
IF action_type IN embedding, training
AND source.dpia_required = true
AND source.dpia_reference IS missing
THEN require_human_review
```

```text
IF source.review_expires_at IS before request.timestamp
THEN require_human_review
```

Future PolicyRule support should add explicit, validated fields for this kind
of matching rather than accepting arbitrary condition strings or executable
policy code.

## Evidence And Audit

Data Usage Profile should appear in Evidence Bundle export only as a safe
summary when it is relevant to an Agent, AccessGrant, or PolicyDecision.

Safe Evidence Bundle fields may include:

- source ID;
- profile ID;
- data classification;
- personal or sensitive data booleans;
- safe data category labels;
- allowed and prohibited purpose labels;
- allowed and prohibited processing labels;
- review status;
- last reviewed timestamp;
- review expiry timestamp;
- safe data owner reference;
- safe DPIA reference;
- safe external catalog reference.

Evidence Bundle export must not include:

- raw source content;
- source chunks;
- prompts;
- credentials;
- API keys;
- tokens;
- full DPIA documents;
- private customer data;
- scanner payloads that include sensitive data.

Profile mutations should eventually create append-only audit records, for
example:

- `data_usage_profile_created`;
- `data_usage_profile_updated`;
- `data_usage_profile_review_status_changed`.

Audit metadata should include safe changed-field names and safe references, not
raw sensitive data or full profile payloads if they could contain sensitive
governance details.

## Runtime Governance Connection

The contextual Runtime Gateway design expects the future decision context to
reason over Agent, Action, Source, data classification, ModelAsset, provider,
Capability, purpose, environment, AccessGrant, and Approval state.

Data Usage Profile should supply the Source side of that context:

- classification;
- personal or sensitive data flags;
- data category labels;
- allowed and prohibited purposes;
- allowed and prohibited processing;
- review status and expiry;
- DPIA requirement and safe reference.

The Runtime Gateway should resolve Source IDs to Source records and then to
their Data Usage Profiles before policy evaluation. Unknown, missing, or expired
profiles should be represented explicitly and handled by deterministic policy
rules. AGCP should not infer legal usability when a profile is absent.

Policy Pre-Checks are a related future design in
`docs/POLICY_PRE_CHECKS_DESIGN.md`. Data Usage Profile should provide
metadata-only inputs for checks such as `legal_usage_profile_checker`,
`dlp_classifier`, and `pii_detector` summaries. Those checks should record safe
CheckResults and evidence references, not raw source content or full scanner
payloads.

## Non-goals

- Do not add scanners in this design.
- Do not change Runtime Gateway behavior in this slice.
- Do not change policy evaluation in this slice.
- Do not add frontend UI in this slice.
- Do not scan or store full source contents in this design.
- Do not store raw prompts, credentials, source chunks, or private customer
  data.
- Do not claim GDPR compliance, legal compliance certification, or automatic
  lawful-use determination.
- Do not replace a DPO, legal counsel, DLP system, data catalog, or governance
  review process.

## Migration Path

Recommended staged implementation:

1. Finalize the Data Usage Profile model and controlled values. Implemented.
2. Add a DB model or equivalent persistence linked one-to-one with Source.
   Implemented.
3. Add profile create/read/update API endpoints or embed profile management
   into Source management if that proves simpler. Implemented as nested Source
   endpoints.
4. Add audit events for profile creation, update, and review status changes.
   Implemented.
5. Include safe profile summaries in Evidence Bundle export.
6. Use profile fields as optional contextual policy inputs.
7. Connect profile resolution to Runtime Gateway contextual requests.
8. Add pre-check or import helpers for external catalogs, DLP, and PII scanner
   signals only after safety boundaries are clear.

Each stage should preserve the boundary between governance metadata and legal
approval. The profile can support review workflows; it must not claim to certify
data usage.

## Open Questions

- Should `data_classification` be single-value, multi-label, or both?
- How should confidence from catalog, DLP, or scanner signals be represented
  without creating fake risk scores?
- How should runtime decisions handle multiple Sources with conflicting
  classifications?
- Should missing or expired reviews deny production use by default or require
  HumanApproval?
- How should AGCP integrate external catalogs without duplicating their full
  data model?
- Should allowed purposes be global controlled values, organization-defined
  values, or both?
- Should `legal_basis` be a controlled enum, a safe external reference, or free
  declared metadata?
- How should changes to profile review status affect existing AccessGrants?
