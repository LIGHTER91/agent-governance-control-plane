// @ts-nocheck
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { fetchAgentGovernanceProfile, fetchAgents } from "../lib/agents";
import { fetchCurrentActor } from "../lib/current-actor";
import { fetchHumanApprovals, transitionHumanApproval } from "../lib/human-approvals";
import { fetchPolicies, fetchPolicyVersionReviewRequests } from "../lib/policies";
import { fetchRuntimeToolCallActivity } from "../lib/runtime";
import { fetchAccessGrants, fetchSources } from "../lib/sources";
import { AGCP_REVIEW_INBOX_CSS } from "./review-inbox-styles";
import { AGCP_CONNECTED_CSS, AGCP_SHELL_CSS, AGCP_STUDIO_CSS } from "./styles";

const NAV_COMMAND = [
  { id: "command",      label: "Overview",     short: "01", icon: "grid" },
  { id: "systems",      label: "Systems",      short: "02", icon: "box" },
  { id: "policies",     label: "Policies",     short: "03", icon: "shield" },
  { id: "reviews",      label: "Reviews",      short: "04", icon: "star", badge: 37 },
  { id: "evidence",     label: "Evidence",     short: "05", icon: "archive" },
  { id: "risk",         label: "Risk",         short: "06", icon: "alert" },
  { id: "data",         label: "Data",         short: "07", icon: "db" },
  { id: "models",       label: "Models",       short: "08", icon: "cpu" },
  { id: "vendors",      label: "Vendors",      short: "09", icon: "store" },
  { id: "monitoring",   label: "Monitoring",   short: "10", icon: "monitor" },
  { id: "integrations", label: "Integrations", short: "11", icon: "plug" },
];

const KPIS = [
  { label: "SYSTEMS",       value: "128",   delta: "+3 this week",  cls: "purple" },
  { label: "DECISIONS",     value: "4,812", delta: "last 24h",      cls: "info" },
  { label: "OPEN REVIEWS",  value: "37",    delta: "â†‘ 5 pending",   cls: "warn" },
  { label: "EVIDENCE",      value: "214",   delta: "auditable",     cls: "ok" },
  { label: "ALERTS",        value: "9",     delta: "3 critical",    cls: "danger" },
];

/* [5] NÅ“uds avec statut et action */
const FLOW_NODES_TOP = [
  { dot: "#6d5ce8", label: "System",  sub: "owner + risk",      status: "ok",   statusLbl: "128",   action: "View systems",   detail: { scope: "Production", risk: "High", owner: "Platform" } },
  { dot: "#f59040", label: "Action",  sub: "runtime request",   status: "warn", statusLbl: "4.8k",  action: "Browse actions", detail: { type: "External call", rate: "4,812/day", blocked: "9%" } },
  { dot: "#36b8f6", label: "Target",  sub: "tool / data / model", status: "info", statusLbl: "47",  action: "View targets",   detail: { tools: "31 tools", data: "12 datasets", models: "4" } },
];
const FLOW_NODES_BOT = [
  { dot: "#f03f5a", label: "Decision", sub: "review required", status: "danger", statusLbl: "37",  action: "Open inbox",    detail: { pending: "37", blocked: "9", auto: "4,766" } },
  { dot: "#a892f8", label: "Policy",   sub: "rules + checks",  status: "ok",     statusLbl: "18",  action: "Edit policies", detail: { active: "18", draft: "4", coverage: "96%" } },
  { dot: "#2dd891", label: "Evidence", sub: "audit package",   status: "ok",     statusLbl: "214", action: "View vault",    detail: { collected: "214", pending: "7", gap: "0" } },
];

/* [2] INBOX avec plus de dÃ©tails */
const INBOX = [
  {
    badge: "review",  badgeLbl: "Review",
    title: "Action awaiting approval",
    sub: "Governance Â· 2h ago",
    desc: "The agent attempted to call an external API in production. Scope matches policy external_action_control â€” human review required before resume.",
    agent: "prod-agent-14",
    policy: "external-actions.agcp",
    since: "2h ago",
  },
  {
    badge: "blocked",  badgeLbl: "Blocked",
    title: "Missing required control",
    sub: "Policy enforcement Â· 14m ago",
    desc: "An action was blocked because access_grant.status is not 'active'. The agent needs a valid grant before proceeding with this operation.",
    agent: "data-pipeline-7",
    policy: "data-boundary.agcp",
    since: "14m ago",
  },
  {
    badge: "gap",  badgeLbl: "Gap",
    title: "No matching policy found",
    sub: "Coverage review Â· just now",
    desc: "A new action type 'model.fine_tune' has no matching policy. Coverage gap flagged â€” define a policy or explicitly allow in the default rule.",
    agent: "ml-ops-3",
    policy: "â€” none â€”",
    since: "now",
  },
];

/* [4] TEMPLATES */
const TEMPLATES = [
  { cls: "tc-review",   name: "Require Review",    desc: "Route action to a named team for human approval before resume.", tags: ["governance", "blocking"] },
  { cls: "tc-deny",     name: "Deny Action",        desc: "Hard-block an action matching a scope + condition.", tags: ["enforcement", "hard-block"] },
  { cls: "tc-evidence", name: "Record Evidence",    desc: "Collect decision + context into an auditable evidence bundle.", tags: ["audit", "evidence"] },
  { cls: "tc-scope",    name: "Scoped Access",      desc: "Limit agent actions to a declared system and environment.", tags: ["scope", "access"] },
  { cls: "tc-approval", name: "Approval Routing",   desc: "Dynamic routing to different reviewers based on risk level.", tags: ["routing", "risk"] },
  { cls: "tc-risk",     name: "Risk Threshold",     desc: "Trigger policy checks when action risk exceeds a threshold.", tags: ["risk", "conditional"] },
];

const WORKSPACE = [
  { dot: "#6d5ce8", name: "AI Systems",      sub: "Inventory" },
  { dot: "#a892f8", name: "Policy Studio",   sub: "Rules" },
  { dot: "#f59040", name: "Reviews",         sub: "Approvals" },
  { dot: "#2dd891", name: "Evidence Vault",  sub: "Audit" },
  { dot: "#f03f5a", name: "Risk Register",   sub: "Risk" },
  { dot: "#36b8f6", name: "Controls",        sub: "AI Act / ISO" },
  { dot: "#22d3ee", name: "Data Governance", sub: "Usage" },
  { dot: "#8b6ef5", name: "Model Governance",sub: "Models" },
];

/* [3] Blocks DSL */
const BLOCKS = [
  { step: 1, type: "when",  cls: "bc-when",  main: "system.environment == \"production\"", detail: "scope: production_systems", status: "ok",    statusLbl: "active" },
  { step: 2, type: "when",  cls: "bc-when",  main: "action.risk in [\"high\", \"critical\"]", detail: "filter: risk level", status: "ok",    statusLbl: "active" },
  { step: 3, type: "when",  cls: "bc-when",  main: "target.boundary == \"external\"", detail: "filter: boundary", status: "ok",    statusLbl: "active" },
  { step: 4, type: "check", cls: "bc-check", main: "access_grant.status == \"active\"", detail: "required fact", status: "req",   statusLbl: "required" },
  { step: 5, type: "check", cls: "bc-check", main: "target.approval == \"approved\"", detail: "required fact", status: "req",   statusLbl: "required" },
  { step: 6, type: "then",  cls: "bc-then",  main: "require_review(\"governance\")", detail: "blocking action", status: "active", statusLbl: "pending" },
  { step: 7, type: "prove", cls: "bc-prove", main: "decision, checks, reviewer, evidence_bundle", detail: "evidence package", status: "ok",    statusLbl: "collecting" },
];

const CODE_LINES = [
  { num: 1,  tokens: [["kw","policy "],["val","external_action_control"],["sym"," {"]] },
  { num: 2,  tokens: [["kw2","  scope "],["str","production_systems"]] },
  { num: 3,  tokens: [] },
  { num: 4,  tokens: [["kw","  when "],["code","system.environment"],["sym"," == "],["str",'"production"']] },
  { num: 5,  tokens: [["cmt","    and "],["code","action.risk"],["sym"," in "],["str",'["high", "critical"]']] },
  { num: 6,  tokens: [["cmt","    and "],["code","target.boundary"],["sym"," == "],["str",'"external"']] },
  { num: 7,  tokens: [] },
  { num: 8,  tokens: [["kw","  check "],["code","access_grant.status"],["sym"," == "],["str",'"active"'],["sym"," "],["req","required"]] },
  { num: 9,  tokens: [["kw","  check "],["code","target.approval"],["sym"," == "],["str",'"approved"'],["sym"," "],["req","required"]] },
  { num: 10, tokens: [] },
  { num: 11, tokens: [["kw","  then "],["fn","require_review"],["sym","("],["str",'"governance"'],["sym",")"]] },
  { num: 12, tokens: [["kw","  prove "],["code","decision, checks, reviewer, evidence_bundle"]] },
  { num: 13, tokens: [["sym","}"]] },
];

const SIM_LINES = [
  { cls: "sim-ok",    sym: "âœ“", text: "policy parsed" },
  { cls: "sim-ok",    sym: "âœ“", text: "24 matching decisions found" },
  { cls: "sim-ok",    sym: "âœ“", text: "17 would require review" },
  { cls: "sim-warn",  sym: "!", text: "2 policies overlap with this scope" },
  { cls: "sim-arrow", sym: "â†’", text: "evidence package: decision + checks + reviewer" },
];

/* â”€â”€â”€ ICONS â”€â”€â”€ */
const Icon = ({ name, size = 15, stroke = "currentColor" }) => {
  const s = { width: size, height: size, flexShrink: 0 };
  const icons = {
    grid: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><rect x="1" y="1" width="6" height="6" rx="1.5"/><rect x="9" y="1" width="6" height="6" rx="1.5"/><rect x="1" y="9" width="6" height="6" rx="1.5"/><rect x="9" y="9" width="6" height="6" rx="1.5"/></svg>,
    shield: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M8 1L14 4V8C14 11.3 11.3 14.3 8 15C4.7 14.3 2 11.3 2 8V4L8 1Z"/><path d="M5.5 8L7.5 10L10.5 6"/></svg>,
    star: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M8 1L9.8 5.6H15L10.6 8.4L12.4 13L8 10.2L3.6 13L5.4 8.4L1 5.6H6.2Z"/></svg>,
    archive: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><rect x="1" y="3" width="14" height="3" rx="1"/><path d="M2 6h12v7a1 1 0 01-1 1H3a1 1 0 01-1-1V6z"/><path d="M6 9h4"/></svg>,
    alert: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M8 1L14 13H2L8 1Z"/><path d="M8 5.5v3M8 10.5v.5"/></svg>,
    box: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M13 10.5L8 13L3 10.5V5.5L8 3L13 5.5V10.5Z"/><path d="M8 13V8M3 5.5L8 8L13 5.5"/></svg>,
    db: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><ellipse cx="8" cy="4" rx="6" ry="2"/><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4"/><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8"/></svg>,
    cpu: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><rect x="4" y="4" width="8" height="8" rx="1"/><path d="M6 1v3M10 1v3M6 12v3M10 12v3M1 6h3M1 10h3M12 6h3M12 10h3"/></svg>,
    store: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M2 5h12l-1 5H3L2 5Z"/><path d="M1 2h14M5 10v4M11 10v4M3 14h10"/></svg>,
    monitor: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><rect x="1" y="2" width="14" height="9" rx="1.5"/><path d="M5 13h6M8 11v2"/></svg>,
    plug: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M6 2v4M10 2v4M5 6h6l-1 4H6L5 6Z"/><path d="M8 10v4"/></svg>,
    bell: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M8 1a5 5 0 015 5c0 4 1 5 1 5H2s1-1 1-5a5 5 0 015-5Z"/><path d="M6.5 13a1.5 1.5 0 003 0"/></svg>,
    help: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><circle cx="8" cy="8" r="6"/><path d="M6.4 6.2A1.8 1.8 0 018 5.2c1.1 0 1.9.7 1.9 1.7 0 .8-.4 1.2-1.1 1.7-.5.4-.8.7-.8 1.4"/><path d="M8 12h.01"/></svg>,
    search: <svg style={s} viewBox="0 0 14 14" fill="none" stroke={stroke} strokeWidth="1.5"><circle cx="5.5" cy="5.5" r="4"/><path d="M9.5 9.5L13 13"/></svg>,
    chevron_down: <svg style={s} viewBox="0 0 12 12" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M3 4.5L6 7.5L9 4.5"/></svg>,
    workspace: <svg style={s} viewBox="0 0 14 14" fill="none"><rect x="3" y="2" width="8" height="10" rx="2" fill="currentColor" opacity=".9"/><path d="M5 2.5V1.8h4v.7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>,
    brand_logo: (
      <svg style={s} viewBox="0 0 32 32" fill="none">
        <path d="M16 2.8L27.3 9.2v13.6L16 29.2L4.7 22.8V9.2L16 2.8Z" stroke="#a276ff" strokeWidth="2.4" strokeLinejoin="round"/>
        <path d="M16 9.7L21.5 12.9v6.2L16 22.3l-5.5-3.2v-6.2L16 9.7Z" stroke="#8f7aff" strokeWidth="1.7" fill="rgba(162,118,255,.16)" strokeLinejoin="round"/>
      </svg>
    ),
    settings: <svg style={s} viewBox="0 0 16 16" fill="none" stroke={stroke} strokeWidth="1.5"><circle cx="8" cy="8" r="2.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.1 3.1l1.4 1.4M11.5 11.5l1.4 1.4M3.1 12.9l1.4-1.4M11.5 4.5l1.4-1.4"/></svg>,
    check: <svg style={s} viewBox="0 0 12 12" fill="none" stroke={stroke} strokeWidth="1.8"><path d="M1.5 6l3 3 6-6"/></svg>,
    arrow_right: <svg style={s} viewBox="0 0 14 14" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M3 7h8M8 4l3 3-3 3"/></svg>,
    chevron_right: <svg style={s} viewBox="0 0 12 12" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M4.5 2L8.5 6l-4 4"/></svg>,
    dot_circle: <svg style={s} viewBox="0 0 12 12" fill="none"><circle cx="6" cy="6" r="5" stroke={stroke} strokeWidth="1.3"/><circle cx="6" cy="6" r="2" fill={stroke}/></svg>,
    plus: <svg style={s} viewBox="0 0 12 12" fill="none" stroke={stroke} strokeWidth="1.8"><path d="M6 2v8M2 6h8"/></svg>,
    play: <svg style={s} viewBox="0 0 12 12" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M3 2l7 4-7 4V2Z" fill={stroke} stroke={stroke}/></svg>,
    copy: <svg style={s} viewBox="0 0 14 14" fill="none" stroke={stroke} strokeWidth="1.5"><rect x="4" y="4" width="8" height="8" rx="1.5"/><path d="M2 10V3a1 1 0 011-1h7"/></svg>,
    layers: <svg style={s} viewBox="0 0 14 14" fill="none" stroke={stroke} strokeWidth="1.5"><path d="M7 1L13 4L7 7L1 4L7 1Z"/><path d="M1 7L7 10L13 7"/><path d="M1 10L7 13L13 10"/></svg>,
    logo: (
      <svg style={s} viewBox="0 0 16 16" fill="none">
        <path d="M8 1L14 4.5V11.5L8 15L2 11.5V4.5L8 1Z" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
        <path d="M8 5L11 6.75V10.25L8 12L5 10.25V6.75L8 5Z" fill="rgba(255,255,255,.5)"/>
      </svg>
    ),
  };
  return icons[name] || null;
};

/* â”€â”€â”€ SIDEBAR â”€â”€â”€ */
const Sidebar = ({ active, onNav }) => (
  <aside className="sidebar">
    <div className="logo-area">
      <div className="logo-mark">
        <div className="logo-icon"><Icon name="logo" size={16} /></div>
        <div className="logo-text">
          <div className="brand">AGCP</div>
          <div className="tagline">CONTROL PLANE</div>
        </div>
      </div>
      <div className="status-pill">
        <span className="status-dot" />
        <span>LOCAL DEV</span>
      </div>
    </div>

    <nav className="sidebar-nav">
      {NAV_COMMAND.map(n => (
        <div
          key={n.id}
          className={`nav-item ${active === n.id ? "active" : ""}`}
          onClick={() => onNav(n.id)}
        >
          <Icon name={n.icon} size={14} className="nav-icon" />
          <span>{n.label}</span>
          {/* [2] Badge orange sur inbox */}
          {n.id === "command"
            ? <span className="nav-badge-orange">3</span>
            : n.badge
            ? <span className="nav-badge">{n.badge}</span>
            : <span className="nav-shortcut">{n.short}</span>
          }
        </div>
      ))}
    </nav>

    <div className="sidebar-footer">
      <div className="avatar">AU</div>
      <div>
        <div className="user-name">Admin User</div>
        <div className="user-role">Security Operator</div>
      </div>
    </div>
  </aside>
);

/* â”€â”€â”€ CODE TOKEN â”€â”€â”€ */
const CodeToken = ({ cls, text }) => {
  const classMap = { kw: "kw", kw2: "kw2", str: "str", val: "val", cmt: "cmt", req: "req", fn: "fn", sym: "sym", code: "code-content" };
  return <span className={classMap[cls] || "code-content"}>{text}</span>;
};

const initialStudioData = {
  loading: true,
  errors: [],
  currentActor: null,
  agents: [],
  approvals: [],
  policyReviewRequests: [],
  policies: [],
  sources: [],
  accessGrants: [],
  runtimeActivity: []
};

const formatLabel = (value) => {
  if (!value) return "not set";
  return String(value).replaceAll("_", " ");
};

const riskClass = (level) => {
  if (level === "critical" || level === "high" || level === "restricted") return "danger";
  if (level === "medium" || level === "confidential") return "warn";
  if (level === "low" || level === "public") return "ok";
  return "info";
};

const statusClass = (status) => {
  if (status === "active" || status === "approved" || status === "allow" || status === "completed") return "ok";
  if (status === "deny" || status === "rejected" || status === "cancelled" || status === "disabled" || status === "suspended" || status === "revoked" || status === "failed") return "danger";
  if (status === "pending" || status === "pending_review" || status === "require_human_review" || status === "draft" || status === "under_review" || status === "needs_review" || status === "expired") return "warn";
  return "info";
};

const compactCount = (value) => new Intl.NumberFormat("en", {
  notation: value >= 1000 ? "compact" : "standard",
  maximumFractionDigits: 1
}).format(value);

const relativeTime = (value) => {
  if (!value) return "time not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
};

function useAGCPStudioData() {
  const [data, setData] = useState(initialStudioData);

  const load = useCallback(async (signal) => {
    setData((current) => ({ ...current, loading: true, errors: [] }));

    const requests = await Promise.allSettled([
      fetchAgents(signal),
      fetchHumanApprovals("all", signal),
      fetchPolicies(signal),
      fetchSources(signal),
      fetchAccessGrants(signal),
      fetchRuntimeToolCallActivity(signal),
      fetchCurrentActor(signal),
      fetchPolicyVersionReviewRequests("pending", signal)
    ]);

    if (signal?.aborted) return;

    const labels = [
      "GET /agents",
      "GET /human-approvals",
      "GET /policies",
      "GET /sources",
      "GET /access-grants",
      "GET /runtime/tool-calls/activity",
      "GET /me",
      "GET /policy-version-review-requests?status=pending"
    ];

    const values = requests.map((result) =>
      result.status === "fulfilled" ? result.value : []
    );
    const errors = requests.flatMap((result, index) =>
      result.status === "rejected"
        ? [`${labels[index]}: ${result.reason instanceof Error ? result.reason.message : "request failed"}`]
        : []
    );

    setData({
      loading: false,
      errors,
      currentActor: requests[6]?.status === "fulfilled" ? requests[6].value : null,
      agents: values[0],
      approvals: values[1],
      policyReviewRequests: values[7],
      policies: values[2],
      sources: values[3],
      accessGrants: values[4],
      runtimeActivity: values[5]
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { ...data, reload: () => load() };
}

function buildStudioKpis(data) {
  const pendingApprovals = data.approvals.filter((approval) => approval.status === "pending").length;
  const decisions = data.runtimeActivity.filter((item) => item.type === "tool_call_decision").length;
  const reviewOrDenied = data.runtimeActivity.filter((item) =>
    item.decision === "deny" || item.decision === "require_human_review"
  ).length;

  return [
    { label: "SYSTEMS", value: data.loading ? "..." : compactCount(data.agents.length), delta: "from GET /agents", cls: "purple" },
    { label: "DECISIONS", value: data.loading ? "..." : compactCount(decisions), delta: "runtime activity", cls: "info" },
    { label: "OPEN REVIEWS", value: data.loading ? "..." : compactCount(pendingApprovals), delta: "pending approvals", cls: "warn" },
    { label: "POLICIES", value: data.loading ? "..." : compactCount(data.policies.length), delta: "policy records", cls: "ok" },
    { label: "ATTENTION", value: data.loading ? "..." : compactCount(reviewOrDenied), delta: "deny or review", cls: "danger" }
  ];
}

function buildStudioInbox(data) {
  const pending = data.approvals.filter((approval) => approval.status === "pending");

  if (data.loading) {
    return [{
      badge: "gap",
      badgeLbl: "Loading",
      title: "Loading backend decision inbox",
      sub: "GET /human-approvals",
      desc: "AGCP Studio is requesting pending HumanApproval records from the backend.",
      agent: "loading",
      policy: "loading",
      since: "loading"
    }];
  }

  if (data.errors.length > 0 && pending.length === 0) {
    return [{
      badge: "blocked",
      badgeLbl: "API",
      title: "Backend data unavailable",
      sub: "Check API configuration",
      desc: data.errors.join(" | "),
      agent: "not loaded",
      policy: "not loaded",
      since: "now"
    }];
  }

  if (pending.length === 0) {
    return [{
      badge: "review",
      badgeLbl: "Clear",
      title: "No pending HumanApprovals",
      sub: "Review queue is empty",
      desc: "The backend returned no pending HumanApproval records. This is a real empty state, not demo data.",
      agent: "none pending",
      policy: "not applicable",
      since: "now"
    }];
  }

  return pending.slice(0, 3).map((approval) => ({
    badge: "review",
    badgeLbl: "Review",
    title: `Approval ${approval.id.slice(0, 8)} pending`,
    sub: `${approval.requested_by_actor_type} Â· ${relativeTime(approval.created_at)}`,
    desc: approval.reason || "A backend governance flow requested human review before the caller can resume.",
    agent: approval.agent_id,
    policy: approval.policy_decision_id || "policy decision not linked",
    since: relativeTime(approval.created_at),
    approval
  }));
}

function buildStudioFlowNodes(data) {
  const pendingApprovals = data.approvals.filter((approval) => approval.status === "pending").length;
  const decisions = data.runtimeActivity.filter((item) => item.type === "tool_call_decision").length;
  const sources = data.sources.length;
  const activePolicies = data.policies.filter((policy) => policy.status === "active").length;

  return {
    top: [
      { dot: "#6d5ce8", label: "System", sub: "registered agents", status: "ok", statusLbl: compactCount(data.agents.length), action: "View systems", detail: { source: "GET /agents", agents: String(data.agents.length), environments: [...new Set(data.agents.map((agent) => agent.environment))].join(", ") || "none" } },
      { dot: "#f59040", label: "Action", sub: "runtime requests", status: pendingApprovals > 0 ? "warn" : "ok", statusLbl: compactCount(decisions), action: "Browse activity", detail: { source: "GET /runtime/tool-calls/activity", decisions: String(decisions), pending_reviews: String(pendingApprovals) } },
      { dot: "#36b8f6", label: "Target", sub: "sources / grants", status: "info", statusLbl: compactCount(sources), action: "View data", detail: { sources: String(sources), access_grants: String(data.accessGrants.length), source: "GET /sources" } }
    ],
    bottom: [
      { dot: "#f03f5a", label: "Decision", sub: pendingApprovals > 0 ? "review required" : "no pending reviews", status: pendingApprovals > 0 ? "danger" : "ok", statusLbl: compactCount(pendingApprovals), action: "Open inbox", detail: { pending: String(pendingApprovals), total_approvals: String(data.approvals.length), source: "GET /human-approvals" } },
      { dot: "#a892f8", label: "Policy", sub: "rules + lifecycle", status: activePolicies > 0 ? "ok" : "warn", statusLbl: compactCount(activePolicies), action: "Edit policies", detail: { active: String(activePolicies), total: String(data.policies.length), source: "GET /policies" } },
      { dot: "#2dd891", label: "Evidence", sub: "manual export", status: "ok", statusLbl: "JSON", action: "View vault", detail: { canonical: "bounded JSON", trigger: "manual user action", route: "/evidence" } }
    ]
  };
}

function agentToSystem(agent, data) {
  const openReviews = data.approvals.filter(
    (approval) => approval.agent_id === agent.id && approval.status === "pending"
  ).length;
  const recentDecisions = data.runtimeActivity
    .filter((item) => item.agent_id === agent.id)
    .slice(0, 5)
    .map((item) => ({
      id: item.id,
      ts: relativeTime(item.timestamp),
      action: item.tool_name || item.type,
      result: item.decision || "recorded"
    }));

  return {
    id: agent.id,
    name: agent.name,
    owner: agent.owner_name || agent.owner_id,
    env: agent.environment,
    status: agent.status,
    risk: agent.risk_level,
    riskCls: riskClass(agent.risk_level),
    coverage: data.policies.length > 0 ? `${data.policies.length} policy records` : "no policies returned",
    openReviews,
    capabilities: [],
    dataSources: [],
    models: agent.framework ? [agent.framework] : [],
    policies: data.policies.filter((policy) => policy.status === "active").map((policy) => policy.name),
    recentDecisions,
    evidence: "manual"
  };
}

function approvalToReview(approval, agents) {
  const agent = agents.find((item) => item.id === approval.agent_id);
  return {
    id: approval.id,
    raw: approval,
    tab: approval.status === "pending" ? "mine" : "completed",
    system: agent?.name || approval.agent_id,
    risk: agent?.risk_level || "medium",
    riskCls: riskClass(agent?.risk_level || "medium"),
    due: approval.expires_at ? relativeTime(approval.expires_at) : "no expiry",
    dueCls: approval.expires_at ? "warn" : "info",
    action: approval.reason || `HumanApproval ${approval.id.slice(0, 8)}`,
    policy: approval.policy_decision_id || "policy decision not linked",
    reviewerGroup: "backend RBAC",
    why: approval.reason || "The Runtime Gateway or telemetry flow requested human oversight.",
    decision: `status=${approval.status}; approval_id=${approval.id}`,
    checks: [
      { result: approval.status, cls: statusClass(approval.status), label: "Backend HumanApproval status" },
      { result: approval.policy_decision_id ? "linked" : "not linked", cls: approval.policy_decision_id ? "ok" : "warn", label: "PolicyDecision reference" }
    ],
    separationWarning: false,
    evidence: approval.policy_decision_id || approval.id,
    note: approval.decision_note
  };
}

/* â”€â”€â”€ COMMAND VIEW â”€â”€â”€ */
const LegacyCommandView = ({ data }) => {
  const [activeInbox, setActiveInbox] = useState(0);
  const [activeMapNode, setActiveMapNode] = useState(null); // [5]
  const [bcMode, setBcMode] = useState("blocks"); // [3] blocks | code
  const [studioMode, setStudioMode] = useState("policies"); // [4] policies | templates

  const inbox = buildStudioInbox(data);
  const kpis = buildStudioKpis(data);
  const flowNodes = buildStudioFlowNodes(data);
  const selectedNode = activeMapNode !== null ? [...flowNodes.top, ...flowNodes.bottom][activeMapNode] : null;
  const activeInboxItem = inbox[Math.min(activeInbox, inbox.length - 1)] || inbox[0];

  return (
    <div className="content">

      {/* [1] Header â€” pas de KPI en premier */}
      <div className="page-header">
        <div className="page-title">Command Center</div>
        <div className="page-sub">Review agent decisions, policy coverage, and evidence across the workspace.</div>
      </div>

      {/* [2] DECISION INBOX en hero, premiÃ¨re chose visible */}
      <div className="inbox-hero">
        <div className="inbox-hero-head">
          <div className="inbox-hero-badge">
            <Icon name="bell" size={13} stroke="var(--orange)" />
          </div>
          <div>
            <div className="inbox-hero-title">Decision Inbox</div>
            <div className="inbox-hero-sub">Items requiring your attention</div>
          </div>
          <span className="inbox-count-chip">
            {data.loading
              ? "loading"
              : `${data.approvals.filter((approval) => approval.status === "pending").length} pending`}
          </span>
        </div>
        <div className="inbox-hero-body">
          {inbox.map((item, i) => (
            <div
              key={i}
              className={`inbox-item-hero ${activeInbox === i ? "selected" : ""}`}
              onClick={() => setActiveInbox(i)}
            >
              <div className={`iih-badge ${item.badge}`}>{item.badgeLbl}</div>
              <div className="iih-title">{item.title}</div>
              <div className="iih-sub">{item.sub}</div>
              {activeInbox === i && (
                <div className="iih-actions">
                  <button className="iih-btn-primary">Open</button>
                  <button className="iih-btn-sec">Simulate</button>
                  <button className="iih-btn-sec">Evidence</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* [5] CONTROL MAP + [3] BLOCKS/CODE + decision details â€” 3 col */}
      <div className="three-col">

        {/* [5] Control Map â€” actionnable */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <div className="panel-head">
            <div className="panel-title">
              <span className="panel-accent" style={{ background: "var(--purple-lt)" }} />
              Control Map
            </div>
            <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>
              {activeMapNode !== null ? "Node selected â†“" : "Click a node to inspect"}
            </span>
          </div>
          <div className="control-map-wrap" style={{ flex: 1 }}>
            <div className="flow-container">
              {/* Top row */}
              <div className="flow-row" style={{ gap: 6 }}>
                {flowNodes.top.map((n, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                    <div
                      className={`flow-node ${activeMapNode === i ? "fn-active" : ""}`}
                      onClick={() => setActiveMapNode(activeMapNode === i ? null : i)}
                    >
                      <span className={`fn-status ${n.status}`}>{n.statusLbl}</span>
                      <div className="fn-dot" style={{ background: n.dot, boxShadow: `0 0 8px ${n.dot}80` }} />
                      <div className="fn-label">{n.label}</div>
                      <div className="fn-sub">{n.sub}</div>
                      <div className="fn-action">â†’ {n.action}</div>
                    </div>
                    {i < 2 && (
                      <div className="flow-arrow" style={{ padding: "0 3px" }}>
                        <Icon name="arrow_right" size={13} />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Vertical connector with status pill */}
              <div className="flow-v-connector">
                <div className="fvc-line" />
                <span className="fvc-pill enforced">enforced</span>
                <div className="fvc-line" />
              </div>

              {/* Bottom row */}
              <div className="flow-row" style={{ gap: 6 }}>
                {flowNodes.bottom.map((n, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                    <div
                      className={`flow-node ${activeMapNode === 3 + i ? "fn-active" : ""} ${i === 0 ? "fn-active" : ""}`}
                      style={i === 1 ? { borderColor: "var(--purple-brd)", boxShadow: "var(--glow-purple)" } : {}}
                      onClick={() => setActiveMapNode(activeMapNode === 3 + i ? null : 3 + i)}
                    >
                      <span className={`fn-status ${n.status}`}>{n.statusLbl}</span>
                      <div className="fn-dot" style={{ background: n.dot, boxShadow: `0 0 8px ${n.dot}80` }} />
                      <div className="fn-label">{n.label}</div>
                      <div className="fn-sub">{n.sub}</div>
                      <div className="fn-action">â†’ {n.action}</div>
                    </div>
                    {i < 2 && (
                      <div className="flow-arrow" style={{ padding: "0 3px" }}>
                        <Icon name="arrow_right" size={13} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* [5] Tooltip contextuel si nÅ“ud sÃ©lectionnÃ© */}
            {selectedNode && (
              <div className="map-tooltip">
                <div className="mt-title">{selectedNode.label} â€” details</div>
                {Object.entries(selectedNode.detail).map(([k, v]) => (
                  <div key={k} className="mt-row">
                    <span>{k}</span>
                    <span className="mt-val">{v}</span>
                  </div>
                ))}
                <div className="mt-actions">
                  <div className="mt-btn primary">{selectedNode.action}</div>
                  <div className="mt-btn ghost">Drill down</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* [3] Blocks / Code â€” bien visible, plein panel */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <div className="blocks-code-header">
            <div className="panel-title" style={{ fontSize: "10.5px", textTransform: "uppercase", letterSpacing: ".08em", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: 7 }}>
              <span className="panel-accent" style={{ background: "var(--sky)", width: 3, height: 12, borderRadius: 2 }} />
              Policy Preview
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
              {/* [3] Toggle Blocks / Code prominent */}
              <div className="bc-toggle">
                <button className={`bc-btn ${bcMode === "blocks" ? "active" : ""}`} onClick={() => setBcMode("blocks")}>
                  Blocks
                </button>
                <button className={`bc-btn ${bcMode === "code" ? "active" : ""}`} onClick={() => setBcMode("code")}>
                  Code
                </button>
              </div>
              <div className="bc-actions">
                <button className="bc-action-btn run">
                  <Icon name="play" size={10} />
                  Run
                </button>
                <button className="bc-action-btn">
                  <Icon name="copy" size={10} />
                  Copy
                </button>
              </div>
            </div>
          </div>

          <div style={{ flex: 1, overflow: "auto" }}>
            {bcMode === "blocks" ? (
              <div className="blocks-view">
                {BLOCKS.map(b => (
                  <div key={b.step} className="block-row">
                    <div className="block-step-num">{b.step}</div>
                    <div className={`block-card ${b.cls}`}>
                      <div className="block-type">{b.type.toUpperCase()}</div>
                      <div className="block-content">
                        <div className="block-main">{b.main}</div>
                        <div className="block-detail">{b.detail}</div>
                      </div>
                      <div className={`block-status bs-${b.status}`}>{b.statusLbl}</div>
                    </div>
                  </div>
                ))}
                <div className="sim-bar" style={{ marginTop: 8 }}>
                  <Icon name="check" size={11} />
                  DSL â†’ 1 PolicyRule Â· 2 PolicyCheckSteps Â· evidence bundle
                </div>
              </div>
            ) : (
              <div className="code-preview">
                <div className="code-block">
                  {CODE_LINES.map(line => (
                    <div key={line.num} className="code-line">
                      <span className="line-num">{line.num}</span>
                      <span>
                        {line.tokens.map((t, i) => <CodeToken key={i} cls={t[0]} text={t[1]} />)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="sim-bar" style={{ marginTop: 10 }}>
                  <Icon name="check" size={11} />
                  Compiles to 1 PolicyRule and 2 PolicyCheckSteps
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: active decision detail */}
        <div className="decision-panel">
          <div className="active-decision-card">
            <div className="adc-head">
              <div className="adc-dot" />
              <div className="adc-title">{activeInboxItem.title}</div>
            </div>
            <div className="adc-body">
              <div className="adc-desc">{activeInboxItem.desc}</div>
              <div className="adc-meta-row"><span className="adc-meta-key">Agent</span><span className="adc-meta-val">{activeInboxItem.agent}</span></div>
              <div className="adc-meta-row"><span className="adc-meta-key">Policy</span><span className="adc-meta-val">{activeInboxItem.policy}</span></div>
              <div className="adc-meta-row"><span className="adc-meta-key">Since</span><span className="adc-meta-val">{activeInboxItem.since}</span></div>
              <div className="adc-buttons">
                <button className="btn-primary" style={{ flex: 1, fontSize: 11, padding: "7px 10px" }}>Open full review</button>
              </div>
              <div className="adc-buttons" style={{ marginTop: 6 }}>
                <button className="btn-secondary" style={{ flex: 1, fontSize: 11, padding: "6px 10px" }}>Simulate</button>
                <button className="btn-secondary" style={{ flex: 1, fontSize: 11, padding: "6px 10px" }}>Export evidence</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* [1] KPIs â€” compact strip aprÃ¨s l'opÃ©rationnel */}
      <div className="kpi-strip">
        {kpis.map(k => (
          <div key={k.label} className={`kpi-card ${k.cls}`}>
            <div className="kpi-label">
              {k.label}
              <span className="kpi-drill">â†’</span>
            </div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-delta">{k.delta}</div>
          </div>
        ))}
      </div>

      {/* Workspace */}
      <div className="panel">
        <div className="panel-head">
          <div className="panel-title">
            <span className="panel-accent" style={{ background: "var(--purple-lt)" }} />
            Workspace
          </div>
        </div>
        <div style={{ padding: "12px 14px" }}>
          <div className="workspace-grid">
            {WORKSPACE.map(w => (
              <div key={w.name} className="ws-card">
                <div className="ws-dot" style={{ background: w.dot, boxShadow: `0 0 7px ${w.dot}80` }} />
                <div className="ws-name">{w.name}</div>
                <div className="ws-sub">{w.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   POLICY STUDIO â€” full replacement
   Sub-components: PS_Sidebar, PS_BlocksEditor, PS_CodeEditor,
   PS_SimConsole, PS_Inspector, PS_TemplateDrawer
   All scoped with "ps2-" prefix to avoid CSS collision with Command.
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

function overviewEndpointError(data, label) {
  return data.errors.find((error) => error.startsWith(label)) || null;
}

function overviewMetricValue({ data, errorLabel, count, fallback = "Unavailable" }) {
  if (data.loading) return "Loading";
  if (overviewEndpointError(data, errorLabel)) return fallback;
  return compactCount(count);
}

function overviewEndpointCopy(data, label) {
  const error = overviewEndpointError(data, label);
  if (!error) return label;
  if (error.includes("status 403")) return `${label} returned 403`;
  return `${label} unavailable`;
}

function overviewRoles(actor) {
  if (!actor) return [];
  return Array.isArray(actor.roles) ? actor.roles : [];
}

function buildOverviewAttentionItems(data) {
  if (data.loading) {
    return [{
      tone: "info",
      title: "Loading review queues",
      meta: "GET /human-approvals and GET /policy-version-review-requests",
      body: "AGCP is requesting real pending review state from the backend."
    }];
  }

  const items = [];
  const humanApprovalError = overviewEndpointError(data, "GET /human-approvals");
  const policyReviewError = overviewEndpointError(
    data,
    "GET /policy-version-review-requests?status=pending"
  );

  if (humanApprovalError) {
    items.push({
      tone: humanApprovalError.includes("status 403") ? "warn" : "danger",
      title: humanApprovalError.includes("status 403")
        ? "Runtime reviews unavailable for this actor"
        : "Unable to load runtime reviews",
      meta: overviewEndpointCopy(data, "GET /human-approvals"),
      body: humanApprovalError.includes("status 403")
        ? "The backend denied this queue. Backend authorization still applies."
        : humanApprovalError
    });
  }

  if (policyReviewError) {
    items.push({
      tone: policyReviewError.includes("status 403") ? "warn" : "danger",
      title: policyReviewError.includes("status 403")
        ? "Policy review queue unavailable for this actor"
        : "Unable to load policy reviews",
      meta: overviewEndpointCopy(data, "GET /policy-version-review-requests?status=pending"),
      body: policyReviewError.includes("status 403")
        ? "The current actor cannot fetch this reviewer/admin queue. Backend authorization still applies."
        : policyReviewError
    });
  }

  for (const approval of data.approvals.filter((item) => item.status === "pending").slice(0, 3)) {
    items.push({
      tone: "warn",
      title: approval.reason || `Runtime HumanApproval ${approval.id.slice(0, 8)}`,
      meta: `HumanApproval - ${relativeTime(approval.created_at)}`,
      body: `Agent ${approval.agent_id}. PolicyDecision ${approval.policy_decision_id || "not linked"}.`
    });
  }

  for (const review of data.policyReviewRequests.filter((item) => item.status === "pending").slice(0, 3)) {
    items.push({
      tone: "purple",
      title: review.policy_name || `PolicyVersion review ${review.id.slice(0, 8)}`,
      meta: `Policy review - ${relativeTime(review.created_at)}`,
      body: `Draft version ${review.policy_version_number || "unknown"} is waiting for reviewer decision.`
    });
  }

  if (items.length === 0) {
    return [{
      tone: "ok",
      title: "No pending reviews found.",
      meta: "Real empty state",
      body: "The backend returned no pending runtime HumanApprovals or PolicyVersion review requests."
    }];
  }

  return items;
}

function buildOverviewActivityItems(data) {
  if (data.loading) {
    return [{
      tone: "info",
      title: "Loading runtime activity",
      meta: "GET /runtime/tool-calls/activity",
      body: "AGCP is requesting recent Runtime Gateway activity from the backend."
    }];
  }

  const runtimeError = overviewEndpointError(data, "GET /runtime/tool-calls/activity");
  if (runtimeError) {
    return [{
      tone: runtimeError.includes("status 403") ? "warn" : "danger",
      title: runtimeError.includes("status 403")
        ? "Runtime activity unavailable for this actor"
        : "Unable to load runtime activity",
      meta: overviewEndpointCopy(data, "GET /runtime/tool-calls/activity"),
      body: runtimeError.includes("status 403")
        ? "The backend denied this overview read. Backend authorization still applies."
        : runtimeError
    }];
  }

  if (data.runtimeActivity.length === 0) {
    return [{
      tone: "info",
      title: "Recent governance activity is not wired on the Overview yet.",
      meta: "No runtime activity returned",
      body: "The Overview uses the existing Runtime activity endpoint and does not invent activity."
    }];
  }

  return data.runtimeActivity.slice(0, 4).map((item) => ({
    tone: statusClass(item.decision || item.type),
    title: item.tool_name || formatLabel(item.type),
    meta: `${formatLabel(item.decision || item.type)} - ${relativeTime(item.timestamp)}`,
    body: `Agent ${item.agent_id}. Request ${item.request_id || "not set"}. Proceed ${item.proceed === null ? "not set" : String(item.proceed)}.`
  }));
}

function OverviewWorkflowCard({ tone, icon, title, href, children, metrics }) {
  return (
    <Link className="overview-workflow-card" href={href}>
      <div className="overview-card-head">
        <div className={`overview-icon ${tone}`}>
          <Icon name={icon} size={15} />
        </div>
        <div className="overview-card-title">{title}</div>
      </div>
      <div className="overview-card-body">{children}</div>
      <div style={{ display: "grid", gap: 7 }}>
        {metrics.map((metric) => (
          <div key={metric.label} className="overview-metric">
            <span className="overview-metric-label">{metric.label}</span>
            <span className="overview-metric-value">{metric.value}</span>
          </div>
        ))}
      </div>
    </Link>
  );
}

function OverviewItem({ item }) {
  return (
    <div className={`overview-item ${item.tone === "danger" ? "overview-error" : item.tone === "ok" ? "overview-empty" : ""}`}>
      <div className={`overview-chip ${item.tone}`}>{item.meta}</div>
      <strong>{item.title}</strong>
      <p>{item.body}</p>
    </div>
  );
}

function CurrentActorCard({ data }) {
  const actorError = overviewEndpointError(data, "GET /me");
  const actor = data.currentActor;
  const roles = overviewRoles(actor);

  return (
    <aside className="overview-actor-card">
      <h2>Current actor</h2>
      {data.loading ? (
        <div className="overview-item overview-empty">
          <strong>Loading actor state</strong>
          <p>GET /me is used for the local development actor context.</p>
        </div>
      ) : actor ? (
        <>
          <dl className="overview-actor-meta">
            <div>
              <dt>Display name</dt>
              <dd>{actor.display_name || actor.actor_id}</dd>
            </div>
            <div>
              <dt>Actor id</dt>
              <dd>{actor.actor_id}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{actor.environment || actor.actor_type}</dd>
            </div>
          </dl>
          <div className="overview-role-row">
            {roles.length > 0
              ? roles.map((role) => <span key={role} className="overview-chip purple">{role}</span>)
              : <span className="overview-chip warn">no roles returned</span>}
          </div>
          {actor.dev_mode_caveat ? (
            <p className="overview-copy" style={{ fontSize: 11 }}>{actor.dev_mode_caveat}</p>
          ) : null}
        </>
      ) : (
        <div className="overview-item overview-error">
          <strong>Current actor unavailable</strong>
          <p>{actorError || "GET /me did not return actor state."}</p>
        </div>
      )}
    </aside>
  );
}

const titleLabel = (value) => {
  const label = formatLabel(value);
  return label.charAt(0).toUpperCase() + label.slice(1);
};

const initialsFor = (value) => {
  const source = String(value || "AGCP").trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
};

const safeRelativeTime = (value) => {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not set";
  return relativeTime(value);
};

const safeDateTime = (value) => {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not set";
  return date.toLocaleString();
};

const riskRank = (level) => {
  const ranks = { critical: 4, high: 3, medium: 2, low: 1 };
  return ranks[level] ?? 0;
};

const latestRuntimeForAgent = (runtimeActivity, agentId) =>
  runtimeActivity
    .filter((item) => item.agent_id === agentId)
    .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime())[0] || null;

const policyNameFor = (policies, policyId) =>
  policies.find((policy) => policy.id === policyId)?.name || policyId || "Policy not linked";

const accessGrantsForAgent = (data, agentId, profile) => {
  if (profile?.access_grants) return profile.access_grants;
  return data.accessGrants.filter((grant) => grant.subject_id === agentId);
};

const activeAccessGrants = (grants) =>
  grants.filter((grant) => ["active", "approved", "allowed"].includes(grant.status));

const accessCountByTarget = (grants, targetType) =>
  activeAccessGrants(grants).filter((grant) => String(grant.target_type || "").toLowerCase().includes(targetType)).length;

const formatDecision = (decision) => {
  if (decision === "allow") return "Allowed";
  if (decision === "deny") return "Denied";
  if (decision === "require_human_review") return "Requires Review";
  if (decision === "not_applicable") return "Not applicable";
  return "No decisions";
};

const decisionClass = (decision) => {
  if (!decision) return "info";
  return statusClass(decision);
};

const overviewAgentRows = (data, query, sortBy) => {
  const normalizedQuery = query.trim().toLowerCase();
  const rows = data.agents
    .filter((agent) => {
      if (!normalizedQuery) return true;
      return [
        agent.name,
        agent.id,
        agent.owner_name,
        agent.owner_contact_email,
        agent.environment,
        agent.status,
        agent.risk_level
      ].some((value) => String(value || "").toLowerCase().includes(normalizedQuery));
    })
    .map((agent) => {
      const grants = accessGrantsForAgent(data, agent.id, null);
      const latestDecision = latestRuntimeForAgent(data.runtimeActivity, agent.id);
      const approvals = data.approvals.filter((approval) => approval.agent_id === agent.id);
      return {
        agent,
        grants,
        approvals,
        latestDecision
      };
    });

  if (sortBy === "risk") {
    return rows.sort((left, right) => riskRank(right.agent.risk_level) - riskRank(left.agent.risk_level));
  }
  if (sortBy === "updated") {
    return rows.sort((left, right) => new Date(right.agent.updated_at).getTime() - new Date(left.agent.updated_at).getTime());
  }
  return rows.sort((left, right) => left.agent.name.localeCompare(right.agent.name));
};

const overviewWorkItems = (data) => {
  const policyReviews = data.policyReviewRequests.map((review) => ({
    id: `policy-review-${review.id}`,
    tone: statusClass(review.status),
    icon: "shield",
    type: "PolicyVersion review",
    item: review.policy_name || review.policy_version_id,
    context: review.assigned_reviewer_name || review.reviewer_actor_id || review.requested_by_actor_id || "Reviewer not assigned",
    status: titleLabel(review.status),
    updatedAt: review.created_at,
    href: "/human-approvals"
  }));

  const approvals = data.approvals
    .filter((approval) => approval.status === "pending")
    .map((approval) => ({
      id: `approval-${approval.id}`,
      tone: statusClass(approval.status),
      icon: "star",
      type: "Runtime HumanApproval",
      item: approval.policy_decision_id || approval.id,
      context: approval.agent_id,
      status: titleLabel(approval.status),
      updatedAt: approval.created_at,
      href: "/human-approvals"
    }));

  const policies = data.policies
    .slice()
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
    .slice(0, 4)
    .map((policy) => ({
      id: `policy-${policy.id}`,
      tone: statusClass(policy.status),
      icon: "archive",
      type: "Policy",
      item: policy.name,
      context: "GET /policies",
      status: titleLabel(policy.status),
      updatedAt: policy.updated_at,
      href: "/policies"
    }));

  return [...policyReviews, ...approvals, ...policies]
    .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
    .slice(0, 4);
};

const CommandView = ({ data }) => {
  const [agentQuery, setAgentQuery] = useState("");
  const [agentSort, setAgentSort] = useState("risk");
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [profileState, setProfileState] = useState({
    agentId: null,
    loading: false,
    profile: null,
    error: null
  });

  const rows = overviewAgentRows(data, agentQuery, agentSort);
  const visibleRows = rows.slice(0, 5);
  const selectedAgent = data.agents.find((agent) => agent.id === selectedAgentId) || visibleRows[0]?.agent || data.agents[0] || null;
  const selectedRow = selectedAgent
    ? rows.find((row) => row.agent.id === selectedAgent.id) || {
        agent: selectedAgent,
        grants: accessGrantsForAgent(data, selectedAgent.id, null),
        approvals: data.approvals.filter((approval) => approval.agent_id === selectedAgent.id),
        latestDecision: latestRuntimeForAgent(data.runtimeActivity, selectedAgent.id)
      }
    : null;
  const selectedProfile = profileState.agentId === selectedAgent?.id ? profileState.profile : null;
  const selectedProfileError = profileState.agentId === selectedAgent?.id ? profileState.error : null;
  const selectedGrants = selectedAgent ? accessGrantsForAgent(data, selectedAgent.id, selectedProfile) : [];
  const selectedRuntime = selectedAgent
    ? data.runtimeActivity
        .filter((item) => item.agent_id === selectedAgent.id)
        .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime())
    : [];
  const selectedApprovals = selectedAgent
    ? data.approvals
        .filter((approval) => approval.agent_id === selectedAgent.id)
        .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    : [];
  const pendingApprovals = data.approvals.filter((approval) => approval.status === "pending").length;
  const agentsError = overviewEndpointError(data, "GET /agents");
  const approvalsError = overviewEndpointError(data, "GET /human-approvals");
  const policiesError = overviewEndpointError(data, "GET /policies");
  const activePolicies = data.policies.filter((policy) => policy.status === "active").length;
  const draftPolicies = data.policies.filter((policy) => policy.status === "draft").length;
  const lastPolicyUpdate = data.policies
    .map((policy) => policy.updated_at)
    .filter(Boolean)
    .sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0];
  const workItems = overviewWorkItems(data);

  useEffect(() => {
    if (!selectedAgentId && data.agents.length > 0) {
      setSelectedAgentId(data.agents[0].id);
    }
    if (selectedAgentId && !data.agents.some((agent) => agent.id === selectedAgentId)) {
      setSelectedAgentId(data.agents[0]?.id || null);
    }
  }, [data.agents, selectedAgentId]);

  useEffect(() => {
    if (!selectedAgent?.id) {
      setProfileState({ agentId: null, loading: false, profile: null, error: null });
      return undefined;
    }

    const controller = new AbortController();
    setProfileState({ agentId: selectedAgent.id, loading: true, profile: null, error: null });

    fetchAgentGovernanceProfile(selectedAgent.id, controller.signal)
      .then((profile) => {
        setProfileState({ agentId: selectedAgent.id, loading: false, profile, error: null });
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setProfileState({
            agentId: selectedAgent.id,
            loading: false,
            profile: null,
            error: error instanceof Error ? error.message : "GET /agents/{agent_id}/governance-profile failed"
          });
        }
      });

    return () => controller.abort();
  }, [selectedAgent?.id]);

  return (
    <div className="content overview-command">
      <section className="overview-command-hero">
        <div>
          <h1 className="overview-command-title">Agent Governance Control Plane</h1>
          <p className="overview-command-copy">
            Govern agents running in external runtimes. Review policy decisions, human oversight, and evidence
            without becoming the orchestrator.
          </p>
        </div>
        <div className="overview-command-actions">
          {selectedAgent ? (
            <Link className="overview-action" href={`/agents/${selectedAgent.id}`}>Open Agent 360</Link>
          ) : (
            <span className="overview-action disabled">Open Agent 360</span>
          )}
          <Link className="overview-action" href="/human-approvals">Review decision</Link>
          <Link className="overview-action primary" href="/evidence">Create evidence bundle</Link>
        </div>
      </section>

      {data.errors.length > 0 ? (
        <div className="overview-error-note">
          Some overview reads are unavailable: {data.errors.slice(0, 2).join(" | ")}
        </div>
      ) : null}

      <section className="overview-command-grid">
        <div className="overview-command-panel">
          <div className="overview-command-head">
            <h2>Agent watchlist</h2>
            <span className="overview-count">{data.loading ? "Loading" : agentsError ? "Unavailable" : `${compactCount(data.agents.length)} agents`}</span>
            <span className="overview-command-spacer" />
            <label className="overview-search">
              <Icon name="search" size={13} />
              <input
                aria-label="Search agents"
                onChange={(event) => setAgentQuery(event.target.value)}
                placeholder="Search agents..."
                value={agentQuery}
              />
            </label>
            <select
              aria-label="Sort agents"
              className="overview-command-select"
              onChange={(event) => setAgentSort(event.target.value)}
              value={agentSort}
            >
              <option value="risk">Sort by: Risk level</option>
              <option value="updated">Sort by: Last updated</option>
              <option value="name">Sort by: Name</option>
            </select>
          </div>

          {data.loading ? (
            <div className="overview-empty-state">Loading agents from GET /agents.</div>
          ) : agentsError ? (
            <div className="overview-empty-state">Unable to load agents from GET /agents. Backend data is unavailable.</div>
          ) : visibleRows.length === 0 ? (
            <div className="overview-empty-state">
              No agents returned by the current backend filters. The Overview does not create sample agents.
            </div>
          ) : (
            <div className="overview-watchlist">
              {visibleRows.map(({ agent, grants, latestDecision }) => {
                const isActive = selectedAgent?.id === agent.id;
                const statusTone = statusClass(agent.status);
                const decisionTone = decisionClass(latestDecision?.decision);

                return (
                  <button
                    className={`overview-agent-row ${isActive ? "active" : ""}`}
                    key={agent.id}
                    onClick={() => setSelectedAgentId(agent.id)}
                    type="button"
                  >
                    <div className="overview-agent-main">
                      <span className={`overview-agent-icon ${statusTone}`}>
                        <Icon name="box" size={17} />
                      </span>
                      <div>
                        <div className="overview-agent-name">{agent.name}</div>
                        <div className="overview-agent-id overview-mono">{agent.id}</div>
                        <div className="overview-cell-sub">
                          <span className={`overview-status-dot ${statusTone}`} />
                          {titleLabel(agent.status)}
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="overview-cell-label">Owner</div>
                      <div className="overview-cell-value">{agent.owner_name || agent.owner_id}</div>
                      <div className="overview-cell-sub">{agent.owner_contact_email || agent.owner_type}</div>
                    </div>
                    <div>
                      <div className="overview-cell-label">Environment</div>
                      <div className="overview-cell-value">
                        <span className={`overview-status-dot ${agent.environment === "production" ? "ok" : "info"}`} />
                        {titleLabel(agent.environment)}
                      </div>
                      <div className="overview-cell-sub">Updated {safeRelativeTime(agent.updated_at)}</div>
                    </div>
                    <div>
                      <div className="overview-cell-label">Risk Level</div>
                      <span className={`overview-status-pill ${riskClass(agent.risk_level)}`}>{titleLabel(agent.risk_level)}</span>
                    </div>
                    <div>
                      <div className="overview-cell-label">Access / Evidence</div>
                      <div className="overview-cell-value">{compactCount(activeAccessGrants(grants).length)} active grants</div>
                      <div className="overview-cell-sub">{compactCount(grants.length)} total declarations</div>
                    </div>
                    <div>
                      <div className="overview-cell-label">Latest PolicyDecision</div>
                      <span className={`overview-status-pill ${decisionTone}`}>{formatDecision(latestDecision?.decision)}</span>
                      <div className="overview-cell-sub">{latestDecision ? safeRelativeTime(latestDecision.timestamp) : "No runtime activity"}</div>
                    </div>
                    <Icon name="chevron_right" size={14} />
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="overview-detail">
          <div className="overview-command-panel overview-agent-detail-card">
            {selectedAgent ? (
              <>
                <div className="overview-detail-top">
                  <span className={`overview-agent-icon ${statusClass(selectedAgent.status)}`}>
                    <Icon name="box" size={18} />
                  </span>
                  <div>
                    <div className="overview-detail-title">{selectedAgent.name}</div>
                    <div className="overview-detail-id">{selectedAgent.id}</div>
                  </div>
                  <span className={`overview-status-pill ${statusClass(selectedAgent.status)}`}>{titleLabel(selectedAgent.status)}</span>
                  <div className="overview-detail-actions">
                    <Link className="overview-command-button" href={`/agents/${selectedAgent.id}`}>Open Agent 360</Link>
                  </div>
                </div>

                <dl className="overview-fact-grid">
                  <div className="overview-fact">
                    <dt>Owner</dt>
                    <dd>{selectedAgent.owner_name || selectedAgent.owner_id}</dd>
                  </div>
                  <div className="overview-fact">
                    <dt>Environment</dt>
                    <dd>{titleLabel(selectedAgent.environment)}</dd>
                  </div>
                  <div className="overview-fact">
                    <dt>Risk Level</dt>
                    <dd>{titleLabel(selectedAgent.risk_level)}</dd>
                  </div>
                  <div className="overview-fact">
                    <dt>Agent Status</dt>
                    <dd>{titleLabel(selectedAgent.status)}</dd>
                  </div>
                </dl>

                <div>
                  <h3 className="overview-command-section-title">Allowed access</h3>
                  <div className="overview-access-grid" style={{ marginTop: 8 }}>
                    <div className="overview-access-item">
                      <span>Tools</span>
                      <strong>{compactCount(accessCountByTarget(selectedGrants, "tool"))} allowed</strong>
                    </div>
                    <div className="overview-access-item">
                      <span>Models</span>
                      <strong>{compactCount(accessCountByTarget(selectedGrants, "model"))} allowed</strong>
                    </div>
                    <div className="overview-access-item">
                      <span>Data Sources</span>
                      <strong>{compactCount(accessCountByTarget(selectedGrants, "source"))} allowed</strong>
                    </div>
                  </div>
                  {profileState.loading ? (
                    <p className="overview-muted" style={{ marginTop: 8 }}>Loading governance profile from GET /agents/{'{agent_id}'}/governance-profile.</p>
                  ) : selectedProfileError ? (
                    <p className="overview-muted" style={{ marginTop: 8 }}>Governance profile unavailable: {selectedProfileError}</p>
                  ) : null}
                </div>
              </>
            ) : (
              <div className="overview-empty-state">No selected agent. GET /agents returned no records.</div>
            )}
          </div>

          <div className="overview-detail-lower">
            <div className="overview-list-panel">
              <div className="overview-list-panel-head">
                <h3>Recent decisions</h3>
                <Link className="overview-mini-link" href="/runtime-gateway">View all decisions</Link>
              </div>
              {selectedRuntime.length === 0 ? (
                <div className="overview-empty-state">No runtime decisions returned for this agent.</div>
              ) : selectedRuntime.slice(0, 4).map((item) => (
                <div className="overview-mini-row" key={item.id}>
                  <Icon name={item.decision === "deny" ? "alert" : "check"} size={15} stroke="currentColor" />
                  <div>
                    <div className="overview-mini-title">{formatDecision(item.decision)}</div>
                    <div className="overview-cell-sub">{policyNameFor(data.policies, item.policy_id)} Â· {item.policy_rule_id || "rule not linked"}</div>
                  </div>
                  <span className={`overview-status-pill ${decisionClass(item.decision)}`}>{safeRelativeTime(item.timestamp)}</span>
                </div>
              ))}
            </div>

            <div className="overview-list-panel">
              <div className="overview-list-panel-head">
                <h3>Human approvals</h3>
                <Link className="overview-mini-link" href="/human-approvals">View all</Link>
              </div>
              {selectedApprovals.length === 0 ? (
                <div className="overview-empty-state">No HumanApproval records returned for this agent.</div>
              ) : selectedApprovals.slice(0, 3).map((approval) => (
                <div className="overview-mini-row" key={approval.id}>
                  <Icon name="star" size={15} stroke="currentColor" />
                  <div>
                    <div className="overview-mini-title">{approval.reason || approval.policy_decision_id || approval.id}</div>
                    <div className="overview-cell-sub">Requested by {approval.requested_by_actor_id}</div>
                  </div>
                  <span className={`overview-status-pill ${statusClass(approval.status)}`}>{titleLabel(approval.status)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="overview-list-panel">
            <div className="overview-list-panel-head">
              <h3>Evidence bundle</h3>
              <Link className="overview-mini-link" href="/evidence">Evidence & Audit</Link>
            </div>
            <div className="overview-mini-row">
              <Icon name="archive" size={15} />
              <div>
                <div className="overview-mini-title">
                  {selectedProfile?.evidence_bundle?.available ? "Evidence bundle available" : "No evidence bundle available yet"}
                </div>
                <div className="overview-cell-sub">
                  {selectedProfile?.evidence_bundle
                    ? `${selectedProfile.evidence_bundle.access} Â· ${selectedProfile.evidence_bundle.export_format}`
                    : "Loaded only from the selected agent governance profile."}
                </div>
              </div>
              <span className={`overview-status-pill ${selectedProfile?.evidence_bundle?.available ? "ok" : "info"}`}>
                {selectedProfile?.evidence_bundle?.available ? "Ready" : "Not created"}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className="overview-work-grid">
        <div className="overview-command-panel">
          <div className="overview-command-head">
            <h2>Recent policy and approval work</h2>
            <span className="overview-count">{data.loading ? "Loading" : `${compactCount(workItems.length)} shown`}</span>
            <span className="overview-command-spacer" />
            <Link className="overview-mini-link" href="/human-approvals">View all</Link>
          </div>
          {workItems.length === 0 ? (
            <div className="overview-empty-state">No pending reviews, pending approvals, or policy records returned.</div>
          ) : (
            <div className="overview-work-table">
              {workItems.map((item) => (
                <Link className="overview-work-row" href={item.href} key={item.id}>
                  <span className={`overview-mini-icon ${item.tone}`}><Icon name={item.icon} size={14} /></span>
                  <div>
                    <div className="overview-mini-title">{item.type}</div>
                    <div className="overview-cell-sub">{item.item}</div>
                  </div>
                  <div className="overview-cell-value">{item.context}</div>
                  <span className={`overview-status-pill ${item.tone}`}>{item.status}</span>
                  <div className="overview-cell-sub">{safeRelativeTime(item.updatedAt)}</div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="overview-command-panel overview-policy-card">
          <div className="overview-command-head" style={{ borderBottom: 0, minHeight: 0, padding: 0 }}>
            <div>
              <h2>Policy Studio</h2>
              <p className="overview-muted" style={{ marginTop: 4 }}>Manage and refine the rules that govern your agents.</p>
            </div>
            <span className="overview-command-spacer" />
            <Link className="overview-mini-link" href="/policies">Open Policy Studio</Link>
          </div>
          <div className="overview-policy-structure">
            <div className="overview-policy-step"><strong>WHEN</strong><span>runtime request context is available</span></div>
            <div className="overview-policy-step"><strong>CHECK</strong><span>configured metadata and inventory checks</span></div>
            <div className="overview-policy-step"><strong>THEN</strong><span>policy decision returned by AGCP</span></div>
            <div className="overview-policy-step"><strong>PROVE</strong><span>evidence intent and audit references</span></div>
          </div>
          <div className="overview-policy-meta">
            <div>Active policies<strong>{data.loading ? "Loading" : policiesError ? "Unavailable" : compactCount(activePolicies)}</strong></div>
            <div>Draft policies<strong>{data.loading ? "Loading" : policiesError ? "Unavailable" : compactCount(draftPolicies)}</strong></div>
            <div>Last updated<strong>{policiesError ? "Unavailable" : lastPolicyUpdate ? safeRelativeTime(lastPolicyUpdate) : "No policy records"}</strong></div>
          </div>
        </div>
      </section>

      <nav className="overview-action-bar" aria-label="Overview actions">
        <Link className="overview-action-card purple" href="/policies">
          <span className="overview-mini-icon info"><Icon name="shield" size={15} /></span>
          <span><span className="overview-action-card-title">Open Policy Studio</span><span className="overview-action-card-sub">Create and manage policies</span></span>
          <span className="overview-command-spacer" />
          <Icon name="arrow_right" size={16} />
        </Link>
        <Link className="overview-action-card warn" href="/human-approvals">
          <span className="overview-mini-icon warn"><Icon name="star" size={15} /></span>
          <span><span className="overview-action-card-title">Review Approvals</span><span className="overview-action-card-sub">{approvalsError ? "Queue unavailable" : `${compactCount(pendingApprovals)} pending from GET /human-approvals`}</span></span>
          <span className="overview-command-spacer" />
          <Icon name="arrow_right" size={16} />
        </Link>
        <Link className="overview-action-card ok" href="/evidence">
          <span className="overview-mini-icon ok"><Icon name="archive" size={15} /></span>
          <span><span className="overview-action-card-title">Create Evidence Bundle</span><span className="overview-action-card-sub">Export governed evidence</span></span>
          <span className="overview-command-spacer" />
          <Icon name="arrow_right" size={16} />
        </Link>
        <Link className="overview-action-card info" href="/runtime-gateway">
          <span className="overview-mini-icon info"><Icon name="monitor" size={15} /></span>
          <span><span className="overview-action-card-title">Inspect Runtime Decisions</span><span className="overview-action-card-sub">Explore decisions and traces</span></span>
          <span className="overview-command-spacer" />
          <Icon name="arrow_right" size={16} />
        </Link>
      </nav>
    </div>
  );
};

/* â”€â”€ Studio Data â”€â”€ */
const PS_POLICIES = [
  { id:"eac", name:"external_action_control", env:"production", status:"draft",  dot:"var(--orange)" },
  { id:"dbc", name:"data_boundary_control",   env:"production", status:"active", dot:"var(--green)" },
  { id:"mar", name:"model_approval_required", env:"all",        status:"active", dot:"var(--green)" },
  { id:"apr", name:"approval_routing",        env:"production", status:"review", dot:"var(--sky)" },
  { id:"rea", name:"risk_escalation_audit",   env:"staging",    status:"draft",  dot:"var(--orange)" },
];
const PS_LIBS = [
  { id:"rl", name:"risk-levels"     },
  { id:"rt", name:"review-teams"    },
  { id:"es", name:"evidence-schema" },
];
const PS_BLOCKS = [
  { id:"w1", group:"when",  kind:"when",  expr:'system.environment == "production"',     detail:"scope: production_systems",     st:"active",    stCls:"ps2-st-ok" },
  { id:"w2", group:"when",  kind:"when",  expr:'action.risk in ["high", "critical"]',    detail:"filter: risk level â‰¥ high",     st:"active",    stCls:"ps2-st-ok" },
  { id:"w3", group:"when",  kind:"when",  expr:'target.boundary == "external"',          detail:"filter: external boundary only",st:"active",    stCls:"ps2-st-ok" },
  { id:"c1", group:"check", kind:"check", expr:'access_grant.status == "active"',        detail:"required fact â€” blocking",      st:"required",  stCls:"ps2-st-req" },
  { id:"c2", group:"check", kind:"check", expr:'target.approval == "approved"',          detail:"required fact â€” blocking",      st:"required",  stCls:"ps2-st-req" },
  { id:"t1", group:"then",  kind:"then",  expr:'require_review("governance")',            detail:"human review gate â€” blocks execution", st:"pending", stCls:"ps2-st-pnd" },
  { id:"p1", group:"prove", kind:"prove", expr:"decision, checks, reviewer, evidence_bundle", detail:"audit package â€” collected on review", st:"collecting", stCls:"ps2-st-col" },
];
const PS_CODE = [
  { n:1,  toks:[["ps2-ck","policy "],["ps2-cv","external_action_control"],["ps2-cx"," {"]] },
  { n:2,  toks:[["ps2-ck2","  scope "],["ps2-cs","production_systems"]] },
  { n:3,  toks:[] },
  { n:4,  toks:[["ps2-ck","  when "],["ps2-cn","system.environment"],["ps2-cx"," == "],["ps2-cs",'"production"']] },
  { n:5,  toks:[["ps2-cc","    and "],["ps2-cn","action.risk"],["ps2-cx"," in "],["ps2-cs",'["high", "critical"]']] },
  { n:6,  toks:[["ps2-cc","    and "],["ps2-cn","target.boundary"],["ps2-cx"," == "],["ps2-cs",'"external"']] },
  { n:7,  toks:[] },
  { n:8,  toks:[["ps2-ck","  check "],["ps2-cn","access_grant.status"],["ps2-cx"," == "],["ps2-cs",'"active"'],["ps2-cx"," "],["ps2-cr","required"]] },
  { n:9,  toks:[["ps2-ck","  check "],["ps2-cn","target.approval"],["ps2-cx"," == "],["ps2-cs",'"approved"'],["ps2-cx"," "],["ps2-cr","required"]] },
  { n:10, toks:[] },
  { n:11, toks:[["ps2-ck","  then "],["ps2-cf","require_review"],["ps2-cx","("],["ps2-cs",'"governance"'],["ps2-cx",")"]] },
  { n:12, toks:[["ps2-ck","  prove "],["ps2-cn","decision, checks, reviewer, evidence_bundle"]] },
  { n:13, toks:[["ps2-cx","}"]] },
];
const PS_SIM = [
  { cls:"ps2-sim-ok",   sym:"âœ“", text:"policy external_action_control parsed" },
  { cls:"ps2-sim-ok",   sym:"âœ“", text:"scope resolved â†’ 18 AI systems matched" },
  { cls:"ps2-sim-ok",   sym:"âœ“", text:"24 recent decisions matched conditions" },
  { cls:"ps2-sim-ok",   sym:"âœ“", text:"17 decisions would trigger require_review" },
  { cls:"ps2-sim-warn", sym:"!", text:"2 overlapping policies: approval_routing, data_boundary_control" },
  { cls:"ps2-sim-info", sym:"i", text:"0 decisions would be auto-denied" },
  { cls:"ps2-sim-arrow",sym:"â†’", text:"evidence package: decision Â· checks Â· reviewer Â· bundle" },
  { cls:"ps2-sim-ok",   sym:"âœ“", text:"no blocking compilation errors" },
];
const PS_COMPILED = [
  { type:"PolicyRule",      name:"external_action_control",         color:"var(--purple-lt)" },
  { type:"PolicyCheckStep", name:"access_grant.status required",    color:"#38b4f5" },
  { type:"PolicyCheckStep", name:"target.approval required",        color:"#38b4f5" },
  { type:"HumanApproval",   name:"governance team â†’ blocking",      color:"#f0873a" },
  { type:"EvidenceBundle",  name:"retention: decision + checks + reviewer", color:"#22d37a" },
];
const PS_IMPACT = [
  { label:"AI systems affected",     val:"18",  color:"var(--text)" },
  { label:"Matched decisions",       val:"24",  color:"var(--text)" },
  { label:"Would allow",             val:"0",   color:"var(--text-muted)" },
  { label:"Would deny",              val:"7",   color:"var(--red)" },
  { label:"Would require review",    val:"17",  color:"var(--orange)" },
  { label:"Overlapping policies",    val:"2",   color:"#e8c44a" },
  { label:"Validation issues",       val:"0",   color:"var(--green)" },
];
const PS_TEMPLATES = [
  { cls:"ps2-tc-access",   name:"Require Active Grant",   desc:"Block any action unless a valid access_grant is present and active.", tags:["access","blocking"] },
  { cls:"ps2-tc-deny",     name:"Hard Deny Action",        desc:"Unconditionally deny a scoped action type without human review.", tags:["enforcement","deny"] },
  { cls:"ps2-tc-evidence", name:"Evidence Collection",     desc:"Collect full audit evidence on every matching decision, non-blocking.", tags:["audit","evidence"] },
  { cls:"ps2-tc-review",   name:"Governance Review Gate",  desc:"Route high-risk actions to a named review group before execution resumes.", tags:["review","routing"] },
  { cls:"ps2-tc-risk",     name:"Risk Threshold Trigger",  desc:"Trigger policy checks when the action risk classification exceeds a defined threshold.", tags:["risk","conditional"] },
  { cls:"ps2-tc-scope",    name:"Scoped Boundary Control", desc:"Restrict agent actions to an explicit system scope and environment boundary.", tags:["scope","access"] },
];

/* â”€â”€ PS Icon helper (reuses Icon from parent but with Ic shorthand) â”€â”€ */
const Ic = ({ n, s = 14, c = "currentColor" }) => <Icon name={n} size={s} stroke={c} />;

/* â”€â”€ Template Drawer â”€â”€ */
const PS_TemplateDrawer = ({ onClose }) => {
  const [cat, setCat] = useState("All");
  return (
    <div className="ps2-drawer" onClick={onClose}>
      <div className="ps2-drawer-panel" onClick={e => e.stopPropagation()}>
        <div className="ps2-drawer-head">
          <div>
            <div className="ps2-drawer-title">Policy Templates</div>
            <div className="ps2-drawer-sub">Start from a validated governance pattern</div>
          </div>
          <button className="ps2-drawer-close" onClick={onClose}>âœ•</button>
        </div>
        <div className="ps2-drawer-cats">
          {["All","Access","Review","Evidence","Risk"].map(c => (
            <button key={c} className={`ps2-drawer-cat ${cat===c?"active":""}`} onClick={() => setCat(c)}>{c}</button>
          ))}
        </div>
        <div className="ps2-tmpl-grid">
          {PS_TEMPLATES.map((t,i) => (
            <div key={i} className={`ps2-tmpl-card ${t.cls}`}>
              <div className="ps2-tmpl-name">{t.name}</div>
              <div className="ps2-tmpl-desc">{t.desc}</div>
              <div className="ps2-tmpl-footer">
                {t.tags.map(tg => <span key={tg} className="ps2-tmpl-tag">{tg}</span>)}
                <span className="ps2-tmpl-use">Use template â†’</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* â”€â”€ Inspector â”€â”€ */
const PS_Inspector = () => (
  <div className="ps2-inspector">
    <div className="ps2-insp-top">
      <div className="ps2-insp-title">Inspector</div>
      <span className="chip chip-draft">draft v0.3</span>
    </div>
    <div className="ps2-insp-scroll">

      {/* Summary */}
      <div className="ps2-insp-sec">
        <div className="ps2-insp-sec-title ist2-summary">Summary</div>
        <div className="ps2-summary-box">
          External high-risk actions in production require active access, approved target status, and a governance review before execution can resume.
        </div>
      </div>

      {/* Decision Flow */}
      <div className="ps2-insp-sec">
        <div className="ps2-insp-sec-title ist2-flow">Decision Flow</div>
        <div className="ps2-dflow">
          <div className="ps2-dflow-row">
            {[{dot:"#8b78f6",label:"When",sub:"3 conditions"},{dot:"#38b4f5",label:"Check",sub:"2 required facts"}].map((n,i)=>(
              <span key={i} style={{display:"contents"}}>
                {i>0&&<div className="ps2-darrow">â†’</div>}
                <div className="ps2-dnode">
                  <div className="ps2-ddot" style={{background:n.dot,boxShadow:`0 0 7px ${n.dot}`}} />
                  <div className="ps2-dlabel">{n.label}</div>
                  <div className="ps2-dsub">{n.sub}</div>
                </div>
              </span>
            ))}
          </div>
          <div className="ps2-dconn">
            <div className="ps2-dconn-line" />
            <span className="ps2-dconn-pill">if all checks pass</span>
            <div className="ps2-dconn-line" />
          </div>
          <div className="ps2-dflow-row">
            {[{dot:"#f0873a",label:"Then",sub:"require_review"},{dot:"#22d37a",label:"Prove",sub:"evidence bundle"}].map((n,i)=>(
              <span key={i} style={{display:"contents"}}>
                {i>0&&<div className="ps2-darrow">â†’</div>}
                <div className="ps2-dnode">
                  <div className="ps2-ddot" style={{background:n.dot,boxShadow:`0 0 7px ${n.dot}`}} />
                  <div className="ps2-dlabel">{n.label}</div>
                  <div className="ps2-dsub">{n.sub}</div>
                </div>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Impact */}
      <div className="ps2-insp-sec">
        <div className="ps2-insp-sec-title ist2-impact">Impact Simulation</div>
        {PS_IMPACT.map(r => (
          <div key={r.label} className="ps2-impact-row">
            <span className="ps2-ir-label">{r.label}</span>
            <span className="ps2-ir-val" style={{color:r.color}}>{r.val}</span>
          </div>
        ))}
        <div className="ps2-overlap-card">
          <div style={{width:6,height:6,borderRadius:"50%",background:"#e8c44a",boxShadow:"0 0 6px #e8c44a",flexShrink:0,marginTop:3}} />
          <div>
            <div className="ps2-oc-title">Overlap detected</div>
            <div className="ps2-oc-sub">approval_routing and data_boundary_control share scope. Review ordering before activation.</div>
          </div>
        </div>
      </div>

      {/* Compiled Output */}
      <div className="ps2-insp-sec">
        <div className="ps2-insp-sec-title ist2-compiled">Compiled Output</div>
        <div className="ps2-compiled-list">
          {PS_COMPILED.map((c,i) => (
            <div key={i} className="ps2-compiled-item">
              <div className="ps2-ci-dot" style={{background:c.color,boxShadow:`0 0 5px ${c.color}`}} />
              <div className="ps2-ci-type">{c.type}</div>
              <div className="ps2-ci-name">{c.name}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Review */}
      <div className="ps2-insp-sec">
        <div className="ps2-insp-sec-title ist2-review">Review Status</div>
        <div className="ps2-review-card">
          {[
            {key:"Status",         val:"Draft â€” not submitted"},
            {key:"Reviewer group", val:"governance"},
            {key:"Policy version", val:"0.3 (unsaved)"},
            {key:"Last activated", val:"v0.2 Â· 3 days ago"},
          ].map(r=>(
            <div key={r.key} className="ps2-rc-row">
              <span className="ps2-rc-key">{r.key}</span>
              <span className="ps2-rc-val">{r.val}</span>
            </div>
          ))}
        </div>
        <textarea className="ps2-review-note" rows={2} placeholder="Add a version note before submittingâ€¦" />
      </div>

    </div>
    <div className="ps2-insp-actions">
      <div className="ps2-act-row">
        <button className="ps2-act-btn ps2-btn-save">Save draft</button>
        <button className="ps2-act-btn ps2-btn-sim">â–¶ Simulate</button>
      </div>
      <button className="ps2-act-btn ps2-btn-submit">Submit for review</button>
    </div>
  </div>
);

/* â”€â”€â”€ POLICY STUDIO VIEW (replaces old PolicyStudioView) â”€â”€â”€ */
const PolicyStudioView = () => {
  const [activeStep, setActiveStep] = useState("when");
  const [activeTab, setActiveTab] = useState("blocks");
  const [activePol, setActivePol]   = useState("eac");
  const [selBlock, setSelBlock]     = useState(null);
  const [showTmpl, setShowTmpl]     = useState(false);
  const [studioMode, setStudioMode] = useState("policies");

  const steps = [
    { id:"when",  label:"WHEN",  cls:"s-when",  count:3 },
    { id:"check", label:"CHECK", cls:"s-check", count:2 },
    { id:"then",  label:"THEN",  cls:"s-then",  count:1 },
    { id:"prove", label:"PROVE", cls:"s-prove", count:1 },
  ];

  const statusChip = { draft:["chip chip-draft","draft"], active:["chip chip-active","active"], review:["chip chip-review","review"] };
  const statusDot  = { draft:"var(--orange)", active:"var(--green)", review:"var(--sky)" };

  const BLOCK_GROUPS = [
    { key:"when",  label:"WHEN",  color:"#8b78f6", desc:"conditions" },
    { key:"check", label:"CHECK", color:"#38b4f5", desc:"required facts" },
    { key:"then",  label:"THEN",  color:"#f0873a", desc:"action" },
    { key:"prove", label:"PROVE", color:"#22d37a", desc:"evidence" },
  ];

  return (
    <div style={{ display:"flex", flex:1, overflow:"hidden", position:"relative" }}>

      {/* â”€â”€ LEFT: Policy List â”€â”€ */}
      <div className="ps2-list-pane">
        <div className="ps2-pane-head">
          <div className="ps2-pane-title">Policy Studio</div>
          <div className="ps2-mode-row">
            <button className={`ps2-mode-btn ${studioMode==="policies"?"p-on":""}`} onClick={() => setStudioMode("policies")}>Policies</button>
            <button className={`ps2-mode-btn ${studioMode==="templates"?"t-on":""}`} onClick={() => setStudioMode("templates")}>Templates</button>
          </div>
          <div className="ps2-search">
            <Icon name="search" size={11} />
            <input placeholder={studioMode === "templates" ? "Search templatesâ€¦" : "Search policiesâ€¦"} />
          </div>
        </div>

        <div className="ps2-list-scroll">
          {studioMode === "policies" ? (<>
            <div className="ps2-section-lbl">// Production</div>
            {PS_POLICIES.map(p => (
              <div key={p.id} className={`ps2-entry ${activePol===p.id?"active":""}`} onClick={() => setActivePol(p.id)}>
                <div className="ps2-entry-dot" style={{ background: statusDot[p.status] }} />
                <div style={{ flex:1, minWidth:0 }}>
                  <div className="ps2-entry-name">{p.name}</div>
                  <div className="ps2-entry-meta">{p.env}</div>
                </div>
                <span className={`ps2-entry-chip chip ${statusChip[p.status][0].split(" ")[1]}`}>{statusChip[p.status][1]}</span>
              </div>
            ))}
            <div className="ps2-section-lbl" style={{ marginTop:6 }}>// Libraries</div>
            {PS_LIBS.map(l => (
              <div key={l.id} className="ps2-entry">
                <div className="ps2-entry-dot" style={{ background:"var(--sky)", opacity:.6 }} />
                <div>
                  <div className="ps2-entry-name">{l.name}</div>
                  <div className="ps2-entry-meta">lib Â· shared</div>
                </div>
                <span className="ps2-entry-chip chip chip-review">lib</span>
              </div>
            ))}
          </>) : (<>
            <div className="ps2-section-lbl">// Templates</div>
            {PS_TEMPLATES.map((t,i) => (
              <div key={i} className="ps2-entry" style={{ flexDirection:"column", alignItems:"flex-start", padding:"8px 8px" }}>
                <div style={{ display:"flex", alignItems:"center", gap:7, width:"100%", marginBottom:3 }}>
                  <div style={{ width:6, height:6, borderRadius:"50%", background:"var(--orange)", flexShrink:0, opacity:.8 }} />
                  <span className="ps2-entry-name">{t.name}</span>
                  <span className="ps2-entry-chip chip chip-draft" style={{ marginLeft:"auto" }}>tmpl</span>
                </div>
                <div style={{ fontSize:10, color:"var(--text-muted)", lineHeight:1.4, paddingLeft:13 }}>{t.desc}</div>
              </div>
            ))}
          </>)}
        </div>

        <div className="ps2-new-btn">
          <Icon name="plus" size={12} />
          {studioMode === "templates" ? "Use template" : "New policy"}
        </div>
      </div>

      {/* â”€â”€ CENTER: Editor â”€â”€ */}
      <div className="ps2-editor-pane">

        {/* Structure bar + Blocks/Code toggle */}
        <div className="ps2-struct-bar">
          <span className="ps2-struct-lbl">policy structure</span>
          {steps.map((s, i) => (
            <span key={s.id} style={{ display:"contents" }}>
              {i > 0 && <span className="ps2-step-sep">â†’</span>}
              <div
                className={`ps2-step ${s.cls} ${activeStep===s.id?"active":""}`}
                onClick={() => setActiveStep(s.id)}
              >
                <div className="ps2-step-count">{s.count}</div>
                {s.label}
              </div>
            </span>
          ))}
          <div className="ps2-editor-toggle">
            <button className={`ps2-etbtn ${activeTab==="blocks"?"on-blocks":""}`} onClick={() => setActiveTab("blocks")}>
              <Icon name="layers" size={10} />Blocks
            </button>
            <button className={`ps2-etbtn ${activeTab==="code"?"on-code":""}`} onClick={() => setActiveTab("code")}>
              <Icon name="copy" size={10} />Code DSL
            </button>
          </div>
        </div>

        {/* Editor scroll */}
        <div className="ps2-editor-scroll">
          {activeTab === "blocks" ? (
            <div className="ps2-block-list">
              {BLOCK_GROUPS.map((g, gi) => {
                const blocks = PS_BLOCKS.filter(b => b.group === g.key);
                return (
                  <div key={g.key} className="ps2-block-group">
                    {gi > 0 && (
                      <div className="ps2-spacer" style={{ color: g.color }}>enforced â†’</div>
                    )}
                    <div className="ps2-block-group-label" style={{ color: g.color }}>
                      {g.label}
                      <span className="ps2-group-line" />
                      <span className="ps2-group-sub">{g.desc}</span>
                    </div>
                    {blocks.map(b => (
                      <div
                        key={b.id}
                        className={`ps2-block bk-${b.kind} ${selBlock===b.id?"sel":""}`}
                        onClick={() => setSelBlock(b.id)}
                      >
                        <div className="ps2-block-accent" />
                        <div className="ps2-block-inner">
                          <div className="ps2-block-type">{b.kind.toUpperCase()}</div>
                          <div className="ps2-block-body">
                            <div className="ps2-block-expr">{b.expr}</div>
                            <div className="ps2-block-detail">{b.detail}</div>
                          </div>
                          <div className={`ps2-block-st ${b.stCls}`}>{b.st}</div>
                        </div>
                      </div>
                    ))}
                    <button className="ps2-add-block">
                      <Icon name="plus" size={10} />Add {g.label} condition
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="ps2-code-view">
              {PS_CODE.map(line => (
                <div key={line.n} className="ps2-code-line">
                  <span className="ps2-ln">{line.n}</span>
                  <span className="ps2-cb">
                    {line.toks.map((t,i) => <span key={i} className={t[0]}>{t[1]}</span>)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Compile bar */}
        <div className="ps2-compile-bar">
          <Icon name="check" size={11} stroke="var(--green)" />
          Compiles to
          <div className="ps2-compile-pills">
            {[
              {txt:"1 PolicyRule",               cls:"chip-vio"},
              {txt:"2 PolicyCheckSteps",         cls:"chip-review"},
              {txt:"HumanApproval: governance",  cls:"chip-draft"},
              {txt:"EvidenceBundle",             cls:"chip-active"},
            ].map(c => (
              <span key={c.txt} className={`ps2-co-pill chip ${c.cls}`}>{c.txt}</span>
            ))}
          </div>
        </div>

        {/* Simulation console */}
        <div className="ps2-sim">
          <div className="ps2-sim-head">
            <span className="ps2-sim-title">// SIMULATION OUTPUT</span>
            <button className="ps2-sim-run">
              <Icon name="play" size={10} stroke="var(--green)" />
              Run simulation
            </button>
          </div>
          <div className="ps2-sim-body">
            {PS_SIM.map((l,i) => (
              <div key={i} className={`ps2-sim-line ${l.cls}`}>
                <span className="ps2-sym">{l.sym}</span>
                <span>{l.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* â”€â”€ RIGHT: Inspector â”€â”€ */}
      <PS_Inspector />

      {/* Template Drawer */}
      {showTmpl && <PS_TemplateDrawer onClose={() => setShowTmpl(false)} />}
    </div>
  );
};

/* â”€â”€â”€ TOPBAR â”€â”€â”€ */
const Topbar = () => null;

const AI_SYSTEMS = [
  { id: "s1", name: "prod-agent-14", owner: "Platform Eng", env: "production", risk: "high", riskCls: "danger", coverage: "96%", openReviews: 3, decisions: 142, status: "active",
    capabilities: ["external_api_call", "data_read", "report_write"],
    dataSources: ["customer-db", "analytics-warehouse"],
    models: ["gpt-4o", "claude-3-5-sonnet"],
    policies: ["external_action_control", "data-boundary", "pii-access"],
    recentDecisions: [
      { id: "d1", action: "POST /api/external/crm", result: "review_required", ts: "2h ago" },
      { id: "d2", action: "GET /data/customers?limit=500", result: "allowed", ts: "3h ago" },
      { id: "d3", action: "model.completion gpt-4o", result: "allowed", ts: "4h ago" },
    ],
    evidence: 14,
  },
  { id: "s2", name: "ml-ops-3", owner: "ML Platform", env: "staging", risk: "medium", riskCls: "warn", coverage: "72%", openReviews: 1, decisions: 58, status: "active",
    capabilities: ["model_fine_tune", "data_read", "model_deploy"],
    dataSources: ["training-dataset-v3", "eval-set"],
    models: ["claude-3-5-sonnet", "llama-3-70b"],
    policies: ["model-governance", "training-data-policy"],
    recentDecisions: [
      { id: "d4", action: "model.fine_tune llama-3-70b", result: "gap_flagged", ts: "now" },
      { id: "d5", action: "data_read training-dataset-v3", result: "allowed", ts: "1h ago" },
    ],
    evidence: 6,
  },
  { id: "s3", name: "data-pipeline-7", owner: "Data Infra", env: "production", risk: "critical", riskCls: "danger", coverage: "88%", openReviews: 0, decisions: 311, status: "active",
    capabilities: ["data_read", "data_write", "schema_modify"],
    dataSources: ["production-postgres", "datalake-raw"],
    models: [],
    policies: ["data-boundary", "pii-access", "schema-change-policy"],
    recentDecisions: [
      { id: "d6", action: "data_write production-postgres", result: "blocked", ts: "14m ago" },
      { id: "d7", action: "schema_modify users_table", result: "review_required", ts: "2h ago" },
    ],
    evidence: 28,
  },
  { id: "s4", name: "customer-support-bot", owner: "CX Team", env: "production", risk: "low", riskCls: "ok", coverage: "100%", openReviews: 0, decisions: 892, status: "active",
    capabilities: ["crm_read", "ticket_write", "kb_search"],
    dataSources: ["support-kb", "crm-readonly"],
    models: ["claude-3-haiku"],
    policies: ["support-scope-policy", "pii-access"],
    recentDecisions: [
      { id: "d8", action: "crm_read customer_id:4421", result: "allowed", ts: "5m ago" },
    ],
    evidence: 44,
  },
  { id: "s5", name: "finance-reconciler", owner: "Finance Ops", env: "production", risk: "high", riskCls: "danger", coverage: "91%", openReviews: 2, decisions: 77, status: "paused",
    capabilities: ["ledger_read", "ledger_write", "report_generate"],
    dataSources: ["finance-db", "erp-system"],
    models: ["gpt-4o"],
    policies: ["financial-data-policy", "dual-approval-required"],
    recentDecisions: [
      { id: "d9", action: "ledger_write batch_close_q4", result: "review_required", ts: "1d ago" },
    ],
    evidence: 9,
  },
];

const REVIEWS = [
  { id: "r1", system: "prod-agent-14", action: "POST /api/external/crm", policy: "external_action_control", risk: "high", riskCls: "danger", requestedBy: "prod-agent-14", reviewerGroup: "Governance Team", due: "overdue", dueCls: "danger", tab: "mine", status: "Assigned to me",
    why: "This action calls an external CRM endpoint in production. Policy external_action_control requires human approval for all cross-boundary API calls with risk level high or critical.",
    decision: "REVIEW_REQUIRED â€” policy condition met: target.boundary == external AND action.risk == high",
    checks: [
      { label: "access_grant.status == active", result: "pass", cls: "ok" },
      { label: "target.approval == approved", result: "fail", cls: "danger" },
      { label: "system.environment == production", result: "pass", cls: "ok" },
    ],
    evidence: "EVD-2024-1182",
    separationWarning: false,
    note: "",
  },
  { id: "r2", system: "finance-reconciler", action: "ledger_write batch_close_q4", policy: "dual-approval-required", risk: "critical", riskCls: "danger", requestedBy: "finance-reconciler", reviewerGroup: "Finance Controls", due: "due today", dueCls: "warn", tab: "mine", status: "Assigned to me",
    why: "Ledger writes above threshold $500k require dual approval from Finance Controls group. This batch close affects 3 entities across 2 fiscal periods.",
    decision: "REVIEW_REQUIRED â€” ledger_write.amount > threshold AND fiscal_period.closing == true",
    checks: [
      { label: "write.amount < $500k threshold", result: "fail", cls: "danger" },
      { label: "fiscal_period.approved", result: "pending", cls: "warn" },
    ],
    evidence: "EVD-2024-1183",
    separationWarning: true,
    note: "",
  },
  { id: "r3", system: "data-pipeline-7", action: "schema_modify users_table", policy: "schema-change-policy", risk: "high", riskCls: "danger", requestedBy: "data-pipeline-7", reviewerGroup: "Data Stewards", due: "2h remaining", dueCls: "warn", tab: "waiting", status: "Waiting for reviewer",
    why: "Schema modifications to production tables require sign-off from a Data Steward. This change drops a column that may be referenced by downstream consumers.",
    decision: "REVIEW_REQUIRED â€” schema_change.type == DROP_COLUMN AND table.environment == production",
    checks: [
      { label: "downstream_consumers.notified", result: "pending", cls: "warn" },
      { label: "backup.verified", result: "pass", cls: "ok" },
    ],
    evidence: "EVD-2024-1179",
    separationWarning: false,
    note: "",
  },
  { id: "r4", system: "ml-ops-3", action: "model.fine_tune llama-3-70b", policy: "model-governance", risk: "medium", riskCls: "warn", requestedBy: "ml-ops-3", reviewerGroup: "ML Governance", due: "no deadline set", dueCls: "info", tab: "escalated", status: "Escalated",
    why: "Fine-tuning on a third-party base model with internal data requires review. Dataset classification must be confirmed before training begins.",
    decision: "REVIEW_REQUIRED â€” training.data_classification == unverified AND model.provider == external",
    checks: [
      { label: "training_data.classification == internal-safe", result: "pending", cls: "warn" },
      { label: "model.provider_agreement.signed", result: "pass", cls: "ok" },
    ],
    evidence: "EVD-2024-1177",
    separationWarning: false,
    note: "",
  },
  { id: "r5", system: "customer-support-bot", action: "crm_read customer_id:4421", policy: "pii-access", risk: "low", riskCls: "ok", requestedBy: "customer-support-bot", reviewerGroup: "Privacy Team", due: "completed", dueCls: "ok", tab: "completed", status: "Completed",
    why: "PII access review completed â€” access was within defined purpose and data minimization constraints.",
    decision: "ALLOWED â€” all checks passed, no sensitive data threshold exceeded",
    checks: [
      { label: "purpose.declared == support_resolution", result: "pass", cls: "ok" },
      { label: "access.minimized", result: "pass", cls: "ok" },
    ],
    evidence: "EVD-2024-1168",
    separationWarning: false,
    note: "Approved by J. Moreau on 2024-12-14",
  },
];

const EVIDENCE = [
  { id: "e1", pkg: "EVD-2024-1182", system: "prod-agent-14", action: "POST /api/external/crm", decision: "REVIEW_REQUIRED", policy: "external_action_control", reviewer: "Pending", date: "2024-12-16", status: "pending", statusCls: "warn",
    timeline: [
      { step: "Runtime Request", ts: "14:02:11", detail: "POST /api/external/crm â€” prod-agent-14" },
      { step: "Policy Decision", ts: "14:02:11", detail: "REVIEW_REQUIRED â€” external_action_control matched" },
      { step: "Check Results", ts: "14:02:12", detail: "access_grant: PASS Â· target.approval: FAIL" },
      { step: "Human Approval", ts: "â€”", detail: "Awaiting Governance Team" },
      { step: "Audit Log", ts: "â€”", detail: "Not yet complete" },
      { step: "Evidence Package", ts: "â€”", detail: "Pending reviewer decision" },
    ]
  },
  { id: "e2", pkg: "EVD-2024-1168", system: "customer-support-bot", action: "crm_read customer_id:4421", decision: "ALLOWED", policy: "pii-access", reviewer: "J. Moreau", date: "2024-12-14", status: "complete", statusCls: "ok",
    timeline: [
      { step: "Runtime Request", ts: "09:14:03", detail: "crm_read â€” customer-support-bot" },
      { step: "Policy Decision", ts: "09:14:03", detail: "ALLOWED â€” all checks passed" },
      { step: "Check Results", ts: "09:14:04", detail: "purpose: PASS Â· minimization: PASS" },
      { step: "Human Approval", ts: "09:21:55", detail: "Approved â€” J. Moreau (Privacy Team)" },
      { step: "Audit Log", ts: "09:22:01", detail: "Sealed â€” 7 audit events" },
      { step: "Evidence Package", ts: "09:22:02", detail: "Exported â€” EVD-2024-1168.json" },
    ]
  },
  { id: "e3", pkg: "EVD-2024-1179", system: "data-pipeline-7", action: "schema_modify users_table", decision: "REVIEW_REQUIRED", policy: "schema-change-policy", reviewer: "Pending", date: "2024-12-15", status: "pending", statusCls: "warn",
    timeline: [
      { step: "Runtime Request", ts: "11:44:30", detail: "schema_modify users_table â€” data-pipeline-7" },
      { step: "Policy Decision", ts: "11:44:30", detail: "REVIEW_REQUIRED â€” DROP_COLUMN in production" },
      { step: "Check Results", ts: "11:44:31", detail: "consumers.notified: PENDING Â· backup: PASS" },
      { step: "Human Approval", ts: "â€”", detail: "Awaiting Data Stewards" },
      { step: "Audit Log", ts: "â€”", detail: "Not yet complete" },
      { step: "Evidence Package", ts: "â€”", detail: "Pending" },
    ]
  },
  { id: "e4", pkg: "EVD-2024-1155", system: "finance-reconciler", action: "report_generate Q3_summary", decision: "ALLOWED", policy: "financial-data-policy", reviewer: "C. Lebrun", date: "2024-12-10", status: "complete", statusCls: "ok",
    timeline: [
      { step: "Runtime Request", ts: "08:00:12", detail: "report_generate Q3_summary â€” finance-reconciler" },
      { step: "Policy Decision", ts: "08:00:12", detail: "ALLOWED â€” read-only, within scope" },
      { step: "Check Results", ts: "08:00:13", detail: "ledger.read_only: PASS Â· scope: PASS" },
      { step: "Human Approval", ts: "08:05:44", detail: "Approved â€” C. Lebrun (Finance Controls)" },
      { step: "Audit Log", ts: "08:05:50", detail: "Sealed â€” 4 audit events" },
      { step: "Evidence Package", ts: "08:05:51", detail: "Exported â€” EVD-2024-1155.json" },
    ]
  },
];

const RISKS = [
  { id: "rk1", title: "Unreviewed external API calls in production", severity: "critical", sevCls: "danger", systems: ["prod-agent-14"], coverage: "Partial", owner: "Platform Eng", status: "Open", statusCls: "danger",
    description: "The prod-agent-14 system can initiate external API calls that are subject to review but may bypass enforcement if the gateway is misconfigured. Active review queue confirms exposure.",
    policies: ["external_action_control"], evidence: ["EVD-2024-1182"], openReviews: 3, mitigationStatus: "In progress" },
  { id: "rk2", title: "Fine-tuning with unclassified training data", severity: "high", sevCls: "danger", systems: ["ml-ops-3"], coverage: "Low", owner: "ML Platform", status: "Open", statusCls: "danger",
    description: "ML agents can initiate training jobs on datasets that have not completed classification review. Training on unclassified internal data may violate data usage agreements.",
    policies: ["model-governance", "training-data-policy"], evidence: ["EVD-2024-1177"], openReviews: 1, mitigationStatus: "Review pending" },
  { id: "rk3", title: "Schema changes without downstream notification", severity: "high", sevCls: "danger", systems: ["data-pipeline-7"], coverage: "Medium", owner: "Data Infra", status: "Open", statusCls: "warn",
    description: "DDL operations on production tables do not consistently trigger consumer notification checks. A failed check was recorded during a recent DROP_COLUMN request.",
    policies: ["schema-change-policy"], evidence: ["EVD-2024-1179"], openReviews: 0, mitigationStatus: "Policy gap identified" },
  { id: "rk4", title: "Single-approver ledger writes above threshold", severity: "medium", sevCls: "warn", systems: ["finance-reconciler"], coverage: "Medium", owner: "Finance Ops", status: "Open", statusCls: "warn",
    description: "The dual-approval policy is active but reviewer group availability is low. Escalation paths are not defined if the primary group cannot respond within SLA.",
    policies: ["dual-approval-required"], evidence: [], openReviews: 2, mitigationStatus: "Escalation path not defined" },
  { id: "rk5", title: "Vendor model API key rotation overdue", severity: "low", sevCls: "ok", systems: ["prod-agent-14", "finance-reconciler"], coverage: "Full", owner: "Platform Eng", status: "Monitored", statusCls: "info",
    description: "API credentials for two vendor model providers are due for rotation. No active exposure but the rotation schedule is 30 days overdue.",
    policies: ["model-governance"], evidence: [], openReviews: 0, mitigationStatus: "Rotation scheduled" },
];

const DATA_SOURCES = [
  { id: "ds1", name: "production-postgres", classification: "Confidential", personal: true, sensitive: true, purpose: ["support_resolution", "reporting"], prohibited: ["training", "external_transfer"], processing: ["read", "write"], reviewStatus: "approved", dpia: "DPIA-2024-03", systems: ["prod-agent-14", "data-pipeline-7"], policies: ["data-boundary", "pii-access"] },
  { id: "ds2", name: "customer-db", classification: "Restricted", personal: true, sensitive: false, purpose: ["support_resolution", "analytics"], prohibited: ["training"], processing: ["read"], reviewStatus: "approved", dpia: "DPIA-2024-01", systems: ["prod-agent-14", "customer-support-bot"], policies: ["pii-access"] },
  { id: "ds3", name: "analytics-warehouse", classification: "Internal", personal: false, sensitive: false, purpose: ["analytics", "reporting", "training"], prohibited: [], processing: ["read"], reviewStatus: "approved", dpia: null, systems: ["prod-agent-14", "ml-ops-3"], policies: ["data-boundary"] },
  { id: "ds4", name: "training-dataset-v3", classification: "Unclassified", personal: false, sensitive: true, purpose: ["training"], prohibited: ["external_transfer", "production_use"], processing: ["read"], reviewStatus: "pending", dpia: null, systems: ["ml-ops-3"], policies: ["training-data-policy"] },
  { id: "ds5", name: "finance-db", classification: "Restricted", personal: false, sensitive: true, purpose: ["reporting", "reconciliation"], prohibited: ["external_transfer", "training"], processing: ["read", "write"], reviewStatus: "approved", dpia: "DPIA-2024-05", systems: ["finance-reconciler"], policies: ["financial-data-policy"] },
];

const MODELS = [
  { id: "m1", name: "gpt-4o", provider: "OpenAI", providerType: "External SaaS", modelType: "LLM", approval: "approved", approvalCls: "ok", risk: "medium", riskCls: "warn", usage: ["inference", "function_calling"], systems: ["prod-agent-14", "finance-reconciler"], policies: ["model-governance"], decisions: 3412 },
  { id: "m2", name: "claude-3-5-sonnet", provider: "Anthropic", providerType: "External SaaS", modelType: "LLM", approval: "approved", approvalCls: "ok", risk: "medium", riskCls: "warn", usage: ["inference", "function_calling", "vision"], systems: ["prod-agent-14", "ml-ops-3"], policies: ["model-governance"], decisions: 2188 },
  { id: "m3", name: "claude-3-haiku", provider: "Anthropic", providerType: "External SaaS", modelType: "LLM", approval: "approved", approvalCls: "ok", risk: "low", riskCls: "ok", usage: ["inference"], systems: ["customer-support-bot"], policies: ["model-governance"], decisions: 892 },
  { id: "m4", name: "llama-3-70b", provider: "Meta / self-hosted", providerType: "Self-hosted", modelType: "LLM", approval: "conditional", approvalCls: "warn", risk: "medium", riskCls: "warn", usage: ["inference", "fine_tuning"], systems: ["ml-ops-3"], policies: ["model-governance", "training-data-policy"], decisions: 58 },
  { id: "m5", name: "text-embedding-3-large", provider: "OpenAI", providerType: "External SaaS", modelType: "Embedding", approval: "approved", approvalCls: "ok", risk: "low", riskCls: "ok", usage: ["embedding"], systems: ["customer-support-bot"], policies: ["model-governance"], decisions: 4421 },
];

const VENDORS = [
  { id: "v1", name: "OpenAI", type: "LLM Provider", approval: "approved", approvalCls: "ok", models: ["gpt-4o", "text-embedding-3-large"], systems: ["prod-agent-14", "finance-reconciler", "customer-support-bot"], risk: "medium", riskCls: "warn", policyCoverage: "Full", evidence: 12 },
  { id: "v2", name: "Anthropic", type: "LLM Provider", approval: "approved", approvalCls: "ok", models: ["claude-3-5-sonnet", "claude-3-haiku"], systems: ["prod-agent-14", "ml-ops-3", "customer-support-bot"], risk: "medium", riskCls: "warn", policyCoverage: "Full", evidence: 8 },
  { id: "v3", name: "AWS Bedrock", type: "Model Gateway", approval: "approved", approvalCls: "ok", models: ["claude-3-5-sonnet", "llama-3-70b"], systems: ["ml-ops-3"], risk: "low", riskCls: "ok", policyCoverage: "Partial", evidence: 4 },
  { id: "v4", name: "Salesforce CRM", type: "SaaS API", approval: "approved", approvalCls: "ok", models: [], systems: ["prod-agent-14", "customer-support-bot"], risk: "high", riskCls: "danger", policyCoverage: "Full", evidence: 7 },
  { id: "v5", name: "Dataiku DSS", type: "Orchestration", approval: "pending", approvalCls: "warn", models: [], systems: ["ml-ops-3"], risk: "medium", riskCls: "warn", policyCoverage: "Partial", evidence: 1 },
];

const MONITORING_SIGNALS = [
  { label: "Decisions today", value: "4,812", delta: "+14%", cls: "info", trend: [38,42,45,41,51,58,54,62,71,68] },
  { label: "Review required", value: "37", delta: "+5 since yesterday", cls: "warn", trend: [28,30,29,32,31,33,35,34,36,37] },
  { label: "Denied actions", value: "9", delta: "3 critical", cls: "danger", trend: [4,5,6,4,7,8,7,9,8,9] },
  { label: "Policy gaps flagged", value: "2", delta: "New: model.fine_tune", cls: "warn", trend: [0,1,0,0,1,2,1,2,2,2] },
  { label: "Evidence collected", value: "214", delta: "+7 today", cls: "ok", trend: [190,195,198,201,202,205,207,209,212,214] },
];

const MONITORING_EVENTS = [
  { ts: "14:02", type: "REVIEW_REQUIRED", system: "prod-agent-14", action: "POST /api/external/crm", policy: "external_action_control", cls: "warn" },
  { ts: "13:44", type: "BLOCKED", system: "data-pipeline-7", action: "data_write production-postgres", policy: "data-boundary", cls: "danger" },
  { ts: "13:21", type: "GAP_FLAGGED", system: "ml-ops-3", action: "model.fine_tune llama-3-70b", policy: "â€”", cls: "info" },
  { ts: "12:58", type: "ALLOWED", system: "customer-support-bot", action: "crm_read customer_id:4421", policy: "pii-access", cls: "ok" },
  { ts: "12:31", type: "REVIEW_REQUIRED", system: "finance-reconciler", action: "ledger_write batch_close_q4", policy: "dual-approval-required", cls: "warn" },
  { ts: "11:14", type: "ALLOWED", system: "prod-agent-14", action: "GET /data/customers", policy: "data-boundary", cls: "ok" },
  { ts: "10:44", type: "BLOCKED", system: "finance-reconciler", action: "ledger_write test_entry", policy: "financial-data-policy", cls: "danger" },
];

const INTEGRATIONS = [
  { id: "i1", name: "Runtime Gateway API", type: "core", desc: "HTTP/HTTPS endpoint that runtimes call before executing any action. AGCP evaluates the request and returns a decision.", status: "active", statusCls: "ok", endpoint: "https://gateway.agcp.internal/v1/decide", methods: ["POST /decide", "POST /record", "GET /decision/:id"], keyScope: "gateway:write,evidence:write" },
  { id: "i2", name: "LangGraph", type: "runtime", desc: "Native pre-execution hook. The LangGraph node calls AGCP before any tool use. Decision is injected into the graph state.", status: "active", statusCls: "ok", endpoint: "agcp-langgraph-sdk v2.1", methods: ["before_tool_call", "after_tool_call"], keyScope: "gateway:write" },
  { id: "i3", name: "n8n", type: "runtime", desc: "AGCP governance node for n8n workflows. Inserted before sensitive HTTP request or database operation nodes.", status: "active", statusCls: "ok", endpoint: "n8n-agcp-node v1.4", methods: ["AGCPDecideNode", "AGCPRecordNode"], keyScope: "gateway:write,evidence:read" },
  { id: "i4", name: "Dataiku DSS", type: "runtime", desc: "Recipe-level governance hook for Dataiku pipelines. Evaluated before dataset writes and model deployments.", status: "pending", statusCls: "warn", endpoint: "agcp-dataiku-plugin v0.9", methods: ["pre_recipe_hook"], keyScope: "gateway:write" },
  { id: "i5", name: "MCP Server", type: "protocol", desc: "AGCP exposes a Model Context Protocol server. LLM tool calls are evaluated before being routed to underlying implementations.", status: "active", statusCls: "ok", endpoint: "mcp://agcp.internal/tools", methods: ["tools/list", "tools/call (intercepted)"], keyScope: "gateway:write,tools:read" },
  { id: "i6", name: "Generic Webhook", type: "generic", desc: "Configurable webhook for any runtime or orchestrator. Send a JSON payload describing the action; receive a decision.", status: "active", statusCls: "ok", endpoint: "POST https://gateway.agcp.internal/v1/webhook", methods: ["POST (any runtime)"], keyScope: "gateway:write" },
];

const ADMIN_USERS = [
  { name: "Admin User", email: "admin@company.com", role: "Governance Admin", groups: ["Governance Team"], status: "active" },
  { name: "J. Moreau", email: "j.moreau@company.com", role: "Privacy Reviewer", groups: ["Privacy Team"], status: "active" },
  { name: "C. Lebrun", email: "c.lebrun@company.com", role: "Finance Reviewer", groups: ["Finance Controls"], status: "active" },
  { name: "M. Singh", email: "m.singh@company.com", role: "Data Steward", groups: ["Data Stewards"], status: "active" },
  { name: "T. Park", email: "t.park@company.com", role: "ML Governance Lead", groups: ["ML Governance"], status: "active" },
];

const REVIEWER_GROUPS = [
  { name: "Governance Team", members: 3, policies: ["external_action_control", "data-boundary"], pending: 3 },
  { name: "Finance Controls", members: 2, policies: ["dual-approval-required", "financial-data-policy"], pending: 2 },
  { name: "Data Stewards", members: 2, policies: ["schema-change-policy", "data-boundary"], pending: 1 },
  { name: "Privacy Team", members: 2, policies: ["pii-access"], pending: 0 },
  { name: "ML Governance", members: 1, policies: ["model-governance", "training-data-policy"], pending: 1 },
];

/* â”€â”€â”€ SHARED COMPONENTS â”€â”€â”€ */
const RiskBadge = ({ level, cls }) => {
  const colors = { ok: { color: "var(--green)", bg: "var(--green-dim)", border: "var(--green-brd)" }, warn: { color: "var(--orange)", bg: "var(--orange-dim)", border: "var(--orange-brd)" }, danger: { color: "var(--red)", bg: "var(--red-dim)", border: "var(--red-brd)" }, info: { color: "var(--sky)", bg: "var(--sky-dim)", border: "var(--sky-brd)" } };
  const c = colors[cls] || colors.info;
  return (
    <span style={{ fontFamily: "var(--mono)", fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 4, letterSpacing: ".06em", color: c.color, background: c.bg, border: `1px solid ${c.border}`, whiteSpace: "nowrap" }}>
      {level.toUpperCase()}
    </span>
  );
};

const StatusBadge = ({ label, cls }) => <RiskBadge level={label} cls={cls} />;

const SectionHeader = ({ title, sub, actions }) => (
  <div style={{ marginBottom: 16 }}>
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
      <div>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-.015em", color: "#eeeef8", marginBottom: 3 }}>{title}</div>
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{sub}</div>
      </div>
      {actions && <div style={{ display: "flex", gap: 6, alignItems: "center" }}>{actions}</div>}
    </div>
  </div>
);

const MetaRow = ({ label, value }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "1px solid var(--border2)", fontSize: 11 }}>
    <span style={{ color: "var(--text-muted)", fontFamily: "var(--mono)", fontSize: 10.5 }}>{label}</span>
    <span style={{ color: "var(--text)", fontFamily: "var(--mono)", fontSize: 10.5, fontWeight: 500 }}>{value}</span>
  </div>
);

const PanelBox = ({ title, children, accent = "var(--purple-lt)", action }) => (
  <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden", marginBottom: 10 }}>
    <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border2)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--text-dim)" }}>
        <span style={{ width: 3, height: 12, borderRadius: 2, background: accent, flexShrink: 0, display: "block" }} />
        {title}
      </div>
      {action}
    </div>
    <div style={{ padding: "12px 14px" }}>{children}</div>
  </div>
);

const Pill = ({ label, color = "#9898bb", bg = "rgba(255,255,255,.05)", border = "rgba(255,255,255,.08)" }) => (
  <span style={{ fontFamily: "var(--mono)", fontSize: 9, fontWeight: 600, padding: "2px 7px", borderRadius: 4, letterSpacing: ".05em", color, background: bg, border: `1px solid ${border}`, whiteSpace: "nowrap" }}>
    {label}
  </span>
);

/* â”€â”€â”€ AI SYSTEMS VIEW â”€â”€â”€ */
const AISystemsView = ({ data }) => {
  const systems = data.agents.map((agent) => agentToSystem(agent, data));
  const [selectedId, setSelectedId] = useState(systems[0]?.id || null);
  const [envFilter, setEnvFilter] = useState("all");
  const filtered = envFilter === "all" ? systems : systems.filter(s => s.env === envFilter);
  const selected = systems.find((system) => system.id === selectedId) || filtered[0] || systems[0] || null;

  useEffect(() => {
    if (!selectedId && systems[0]) {
      setSelectedId(systems[0].id);
    }
  }, [selectedId, systems]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      {/* List pane */}
      <div style={{ width: 340, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0, overflow: "hidden", background: "var(--bg-panel)" }}>
        <div style={{ padding: "16px 14px 10px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#eeeef8", marginBottom: 10 }}>AI Systems</div>
          <div style={{ display: "flex", gap: 4 }}>
            {["all", "production", "staging"].map(f => (
              <button key={f} onClick={() => setEnvFilter(f)} style={{ fontFamily: "var(--mono)", fontSize: 10, padding: "4px 10px", borderRadius: 5, cursor: "pointer", border: "1px solid var(--border)", background: envFilter === f ? "var(--purple-dim)" : "transparent", color: envFilter === f ? "var(--purple-lt)" : "var(--text-muted)", transition: "all .12s" }}>
                {f}
              </button>
            ))}
          </div>
        </div>
        <div style={{ flex: 1, overflow: "auto", padding: "6px 8px" }}>
          {filtered.length === 0 && (
            <div style={{ padding: "20px 10px", fontSize: 11, color: "var(--text-muted)", textAlign: "center" }}>
              {data.loading ? "Loading Agents from GET /agents" : "No Agents returned by the backend"}
            </div>
          )}
          {filtered.map(sys => (
            <div key={sys.id} onClick={() => setSelectedId(sys.id)} style={{ padding: "10px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 3, border: `1px solid ${selected?.id === sys.id ? "var(--purple-brd)" : "transparent"}`, background: selected?.id === sys.id ? "var(--purple-dim)" : "transparent", transition: "all .12s" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: sys.status === "active" ? "var(--green)" : "var(--orange)", flexShrink: 0, boxShadow: sys.status === "active" ? "0 0 6px rgba(45,216,145,.5)" : "none" }} />
                <span style={{ fontWeight: 600, fontSize: 12.5, color: "var(--text)", flex: 1, fontFamily: "var(--mono)" }}>{sys.name}</span>
                <RiskBadge level={sys.risk} cls={sys.riskCls} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>
                <span>{sys.owner}</span>
                <span style={{ color: "var(--text-faint)" }}>Â·</span>
                <span>{sys.env}</span>
                <span style={{ color: "var(--text-faint)" }}>Â·</span>
                <span style={{ color: sys.openReviews > 0 ? "var(--orange)" : "var(--text-muted)" }}>{sys.openReviews} reviews</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail pane */}
      {selected && (
        <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <span style={{ fontSize: 20, fontWeight: 700, color: "#eeeef8", fontFamily: "var(--mono)" }}>{selected.name}</span>
                <RiskBadge level={selected.risk} cls={selected.riskCls} />
                <StatusBadge label={selected.status} cls={selected.status === "active" ? "ok" : "warn"} />
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{selected.owner} Â· {selected.env} environment Â· Policy coverage: {selected.coverage}</div>
            </div>
            <a href={`/agents/${encodeURIComponent(selected.id)}`} style={{ background: "linear-gradient(135deg, #5c4ed4, #7c6df0)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", padding: "8px 16px", fontSize: 12, fontWeight: 600, cursor: "pointer", boxShadow: "0 2px 10px rgba(92,78,212,.35)", textDecoration: "none" }}>
              Open governance profile
            </a>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <PanelBox title="Allowed Capabilities" accent="var(--purple-lt)">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {selected.capabilities.map(c => <Pill key={c} label={c} color="var(--purple-lt)" bg="var(--purple-dim)" border="var(--purple-brd)" />)}
              </div>
            </PanelBox>
            <PanelBox title="Data Sources" accent="var(--sky)">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {selected.dataSources.map(d => <Pill key={d} label={d} color="var(--sky)" bg="var(--sky-dim)" border="var(--sky-brd)" />)}
                {selected.dataSources.length === 0 && <span style={{ fontSize: 11, color: "var(--text-muted)" }}>No data sources declared</span>}
              </div>
            </PanelBox>
            <PanelBox title="Models in Use" accent="var(--orange)">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {selected.models.map(m => <Pill key={m} label={m} color="var(--orange)" bg="var(--orange-dim)" border="var(--orange-brd)" />)}
                {selected.models.length === 0 && <span style={{ fontSize: 11, color: "var(--text-muted)" }}>No models registered</span>}
              </div>
            </PanelBox>
            <PanelBox title="Active Policies" accent="var(--green)">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {selected.policies.map(p => <Pill key={p} label={p} color="var(--green)" bg="var(--green-dim)" border="var(--green-brd)" />)}
              </div>
            </PanelBox>
          </div>

          <PanelBox title="Recent Decisions" accent="var(--text-dim)">
            {selected.recentDecisions.map(d => {
              const cls = d.result === "allowed" ? "ok" : d.result === "blocked" ? "danger" : "warn";
              return (
                <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: "1px solid var(--border2)", fontSize: 11 }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)", flexShrink: 0 }}>{d.ts}</span>
                  <span style={{ flex: 1, fontFamily: "var(--mono)", color: "var(--text)", fontSize: 11 }}>{d.action}</span>
                  <RiskBadge level={d.result.replace("_", " ")} cls={cls} />
                </div>
              );
            })}
          </PanelBox>

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4 }}>
            <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "10px 14px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--mono)", color: "var(--green)" }}>{selected.evidence}</span>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Evidence packages available</span>
            </div>
            <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "10px 14px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--mono)", color: selected.openReviews > 0 ? "var(--orange)" : "var(--text-dim)" }}>{selected.openReviews}</span>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Open reviews</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ REVIEWS VIEW â”€â”€â”€ */
const ReviewsView = ({ data }) => {
  const [tab, setTab] = useState("mine");
  const reviews = data.approvals.map((approval) => approvalToReview(approval, data.agents));
  const [selectedId, setSelectedId] = useState(reviews[0]?.id || null);
  const [decisionNote, setDecisionNote] = useState("");
  const [actionState, setActionState] = useState(null);
  const tabs = ["mine", "waiting", "escalated", "completed"];
  const filtered = reviews.filter(r => {
    if (tab === "mine") return r.raw.status === "pending";
    if (tab === "completed") return r.raw.status !== "pending";
    return false;
  });
  const selected = reviews.find((review) => review.id === selectedId) || filtered[0] || reviews[0] || null;

  useEffect(() => {
    if (!selectedId && reviews[0]) {
      setSelectedId(reviews[0].id);
    }
  }, [selectedId, reviews]);

  async function handleReviewAction(action) {
    if (!selected) return;
    setActionState({ status: "loading", message: `${action} in progress` });

    try {
      await transitionHumanApproval(
        selected.id,
        action,
        action === "cancel" ? undefined : decisionNote
      );
      setDecisionNote("");
      setActionState({ status: "success", message: `HumanApproval ${action} completed. Refreshing from backend.` });
      await data.reload();
    } catch (error) {
      setActionState({
        status: "error",
        message: error instanceof Error ? error.message : "Unable to update HumanApproval."
      });
    }
  }

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      {/* List pane */}
      <div style={{ width: 360, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0, overflow: "hidden", background: "var(--bg-panel)" }}>
        <div style={{ padding: "16px 14px 10px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#eeeef8", marginBottom: 10 }}>Review Inbox</div>
          <div style={{ display: "flex", gap: 3 }}>
            {tabs.map(t => (
              <button key={t} onClick={() => { setTab(t); const first = reviews.find(r => (t === "mine" ? r.raw.status === "pending" : t === "completed" ? r.raw.status !== "pending" : false)); if (first) setSelectedId(first.id); }} style={{ fontFamily: "var(--mono)", fontSize: 9, padding: "4px 8px", borderRadius: 4, cursor: "pointer", border: "1px solid var(--border)", background: tab === t ? "var(--purple-dim)" : "transparent", color: tab === t ? "var(--purple-lt)" : "var(--text-muted)", textTransform: "capitalize" }}>
                {t.replace("-", " ")}
                {t === "mine" && <span style={{ marginLeft: 4, background: "var(--orange)", color: "#fff", borderRadius: 10, fontSize: 8, padding: "0 4px", fontWeight: 700 }}>{reviews.filter(r => r.raw.status === "pending").length}</span>}
              </button>
            ))}
          </div>
        </div>
        <div style={{ flex: 1, overflow: "auto", padding: "6px 8px" }}>
          {filtered.length === 0 && <div style={{ padding: "20px 10px", fontSize: 11, color: "var(--text-muted)", textAlign: "center" }}>No items in this queue</div>}
          {filtered.map(r => (
            <div key={r.id} onClick={() => setSelectedId(r.id)} style={{ padding: "10px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 3, border: `1px solid ${selected?.id === r.id ? "var(--purple-brd)" : "transparent"}`, background: selected?.id === r.id ? "var(--purple-dim)" : "transparent", transition: "all .12s" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{r.system}</span>
                <RiskBadge level={r.risk} cls={r.riskCls} />
                <span style={{ marginLeft: "auto", fontFamily: "var(--mono)", fontSize: 9, color: r.dueCls === "danger" ? "var(--red)" : r.dueCls === "warn" ? "var(--orange)" : "var(--text-muted)" }}>{r.due}</span>
              </div>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text)", marginBottom: 3 }}>{r.action}</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>Policy: {r.policy}</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>Reviewer group: <span style={{ color: "var(--text-dim)" }}>{r.reviewerGroup}</span></div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail pane */}
      {selected && (
        <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#eeeef8", marginBottom: 4 }}>{selected.action}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{selected.system} Â· Requested by system Â· Reviewer group: <span style={{ color: "var(--text-dim)", fontWeight: 500 }}>{selected.reviewerGroup}</span></div>
            </div>
            <RiskBadge level={selected.risk} cls={selected.riskCls} />
          </div>

          <PanelBox title="Why Review Is Required" accent="var(--orange)">
            <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>{selected.why}</p>
          </PanelBox>

          <PanelBox title="Policy Decision" accent="var(--purple-lt)">
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text)", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "9px 12px", lineHeight: 1.6 }}>{selected.decision}</div>
          </PanelBox>

          <PanelBox title="Policy Checks" accent="var(--sky)">
            {selected.checks.map((c, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: i < selected.checks.length - 1 ? "1px solid var(--border2)" : "none" }}>
                <RiskBadge level={c.result} cls={c.cls} />
                <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-dim)" }}>{c.label}</span>
              </div>
            ))}
          </PanelBox>

          {selected.separationWarning && (
            <div style={{ background: "rgba(245,144,64,.06)", border: "1px solid var(--orange-brd)", borderRadius: "var(--radius)", padding: "12px 14px", marginBottom: 10 }}>
              <div style={{ fontSize: 11.5, fontWeight: 700, color: "var(--orange)", marginBottom: 3 }}>Separation of duties required</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>The reviewer must not be the owner of the requesting system. Ensure a qualified member of {selected.reviewerGroup} handles this review.</div>
            </div>
          )}

          <PanelBox title="Evidence Preview" accent="var(--green)">
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-muted)" }}>Reference: <span style={{ color: "var(--green)" }}>{selected.evidence}</span></div>
            {selected.note && <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-dim)", fontStyle: "italic" }}>{selected.note}</div>}
          </PanelBox>

          {actionState && (
            <div style={{ background: actionState.status === "error" ? "var(--red-dim)" : "var(--green-dim)", border: `1px solid ${actionState.status === "error" ? "var(--red-brd)" : "var(--green-brd)"}`, borderRadius: "var(--radius)", padding: "9px 12px", marginBottom: 8, fontSize: 11, color: actionState.status === "error" ? "var(--red)" : "var(--green)" }}>
              {actionState.message}
            </div>
          )}

          {selected.raw.status === "pending" && (
            <div style={{ display: "grid", gap: 8, marginTop: 4 }}>
              <textarea value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} placeholder="Optional decision note for approve or reject" rows={2} style={{ background: "var(--bg-card)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "9px 10px", fontFamily: "var(--mono)", fontSize: 11, resize: "vertical" }} />
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => void handleReviewAction("approve")} style={{ background: "linear-gradient(135deg, #5c4ed4, #7c6df0)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", padding: "9px 18px", fontSize: 12.5, fontWeight: 700, cursor: "pointer", boxShadow: "0 2px 10px rgba(92,78,212,.35)", flex: 1.5 }}>Approve</button>
                <button onClick={() => void handleReviewAction("reject")} style={{ background: "var(--red-dim)", color: "var(--red)", border: "1px solid var(--red-brd)", borderRadius: "var(--radius-sm)", padding: "9px 18px", fontSize: 12, fontWeight: 600, cursor: "pointer", flex: 1 }}>Reject</button>
                <button onClick={() => void handleReviewAction("cancel")} style={{ background: "transparent", color: "var(--text-dim)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "9px 14px", fontSize: 12, fontWeight: 500, cursor: "pointer", flex: 1 }}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ EVIDENCE VIEW â”€â”€â”€ */
const EvidenceView = ({ data }) => {
  const evidenceItems = data.agents.map((agent) => ({
    id: agent.id,
    pkg: `agent-${agent.id.slice(0, 8)}`,
    status: "manual",
    statusCls: "info",
    action: "Evidence Bundle JSON available by Agent ID",
    system: agent.name,
    date: relativeTime(agent.updated_at),
    policy: "loaded from bundle on demand",
    reviewer: "backend RBAC",
    decision: "ON DEMAND",
    timeline: [
      { step: "Agent", ts: relativeTime(agent.created_at), detail: `Registered Agent ${agent.name}` },
      { step: "Export", ts: "manual", detail: "Open /evidence to load GET /agents/{agent_id}/evidence-bundle." }
    ]
  }));
  const [selectedId, setSelectedId] = useState(evidenceItems[0]?.id || null);
  const selected = evidenceItems.find((item) => item.id === selectedId) || evidenceItems[0] || null;
  const timelineColors = ["var(--purple-lt)", "var(--sky)", "var(--orange)", "var(--green)", "var(--text-dim)", "var(--green)"];

  useEffect(() => {
    if (!selectedId && evidenceItems[0]) {
      setSelectedId(evidenceItems[0].id);
    }
  }, [selectedId, evidenceItems]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      {/* List pane */}
      <div style={{ width: 340, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0, overflow: "hidden", background: "var(--bg-panel)" }}>
        <div style={{ padding: "16px 14px 10px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#eeeef8", marginBottom: 4 }}>Evidence Vault</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Auditable decision packages</div>
        </div>
        <div style={{ flex: 1, overflow: "auto", padding: "6px 8px" }}>
          {evidenceItems.length === 0 && (
            <div style={{ padding: "20px 10px", fontSize: 11, color: "var(--text-muted)", textAlign: "center" }}>
              {data.loading ? "Loading Agents for Evidence Bundle lookup" : "No Agents returned by the backend"}
            </div>
          )}
          {evidenceItems.map(ev => (
            <div key={ev.id} onClick={() => setSelectedId(ev.id)} style={{ padding: "10px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 3, border: `1px solid ${selected?.id === ev.id ? "var(--purple-brd)" : "transparent"}`, background: selected?.id === ev.id ? "var(--purple-dim)" : "transparent", transition: "all .12s" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--purple-lt)", fontWeight: 700 }}>{ev.pkg}</span>
                <StatusBadge label={ev.status} cls={ev.statusCls} />
              </div>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text)", marginBottom: 3 }}>{ev.action}</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>{ev.system} Â· {ev.date}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail pane */}
      {selected && (
        <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#eeeef8", marginBottom: 4 }}>{selected.pkg}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{selected.system} Â· Policy: {selected.policy} Â· Reviewer: {selected.reviewer}</div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <a href={`/evidence?agent_id=${encodeURIComponent(selected.id)}`} style={{ fontFamily: "var(--mono)", fontSize: 10.5, padding: "7px 13px", borderRadius: "var(--radius-sm)", cursor: "pointer", border: "1px solid var(--purple-brd)", background: "var(--purple-dim)", color: "var(--purple-lt)", textDecoration: "none" }}>Open evidence page</a>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 14 }}>
            <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "10px 12px" }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--text-muted)", marginBottom: 4, letterSpacing: ".07em" }}>AI SYSTEM</div>
              <div style={{ fontSize: 13, fontWeight: 600, fontFamily: "var(--mono)", color: "var(--text)" }}>{selected.system}</div>
            </div>
            <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "10px 12px" }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--text-muted)", marginBottom: 4, letterSpacing: ".07em" }}>DECISION</div>
              <StatusBadge label={selected.decision} cls={selected.decision === "ALLOWED" ? "ok" : "warn"} />
            </div>
            <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "10px 12px" }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--text-muted)", marginBottom: 4, letterSpacing: ".07em" }}>PACKAGE STATUS</div>
              <StatusBadge label={selected.status} cls={selected.statusCls} />
            </div>
          </div>

          <PanelBox title="Audit Timeline" accent="var(--purple-lt)">
            <div style={{ position: "relative" }}>
              {selected.timeline.map((step, i) => (
                <div key={i} style={{ display: "flex", gap: 14, marginBottom: 14, position: "relative" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: timelineColors[i], border: `2px solid ${timelineColors[i]}`, boxShadow: `0 0 8px ${timelineColors[i]}60`, marginTop: 2 }} />
                    {i < selected.timeline.length - 1 && <div style={{ width: 1, flex: 1, background: "rgba(255,255,255,.06)", minHeight: 20, marginTop: 4 }} />}
                  </div>
                  <div style={{ flex: 1, paddingBottom: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 10.5, fontWeight: 700, color: timelineColors[i] }}>{step.step}</span>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--text-faint)" }}>{step.ts}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{step.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </PanelBox>
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ RISK VIEW â”€â”€â”€ */
const RiskView = () => {
  const [selected, setSelected] = useState(RISKS[0]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
        <SectionHeader title="Risk Register" sub="AI governance risk inventory â€” linked to systems, policies, and evidence" />
        <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden", marginBottom: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 100px 160px 100px 120px 100px", gap: 0, padding: "8px 14px", borderBottom: "1px solid var(--border)", fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".07em", textTransform: "uppercase" }}>
            <span>Risk</span><span>Severity</span><span>Affected Systems</span><span>Coverage</span><span>Owner</span><span>Status</span>
          </div>
          {RISKS.map(r => (
            <div key={r.id} onClick={() => setSelected(r)} style={{ display: "grid", gridTemplateColumns: "2fr 100px 160px 100px 120px 100px", gap: 0, padding: "11px 14px", borderBottom: "1px solid var(--border2)", cursor: "pointer", background: selected?.id === r.id ? "rgba(124,109,240,.04)" : "transparent", transition: "background .12s", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>{r.title}</span>
              <span><RiskBadge level={r.severity} cls={r.sevCls} /></span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{r.systems.join(", ")}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{r.coverage}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{r.owner}</span>
              <span><StatusBadge label={r.status} cls={r.statusCls} /></span>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div style={{ width: 320, borderLeft: "1px solid var(--border)", background: "var(--bg-panel)", overflow: "auto", padding: "16px 14px", flexShrink: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#eeeef8", marginBottom: 8 }}>{selected.title}</div>
          <RiskBadge level={selected.severity} cls={selected.sevCls} />
          <p style={{ marginTop: 10, fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.6, marginBottom: 12 }}>{selected.description}</p>
          <MetaRow label="Owner" value={selected.owner} />
          <MetaRow label="Coverage" value={selected.coverage} />
          <MetaRow label="Open reviews" value={selected.openReviews.toString()} />
          <MetaRow label="Mitigation" value={selected.mitigationStatus} />
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Linked Policies</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.policies.map(p => <Pill key={p} label={p} color="var(--purple-lt)" bg="var(--purple-dim)" border="var(--purple-brd)" />)}
            </div>
          </div>
          {selected.evidence.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Linked Evidence</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {selected.evidence.map(e => <Pill key={e} label={e} color="var(--green)" bg="var(--green-dim)" border="var(--green-brd)" />)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ DATA VIEW â”€â”€â”€ */
const DataView = ({ data }) => {
  const sources = data.sources.map((source) => ({
    id: source.id,
    name: source.name,
    classification: formatLabel(source.metadata?.data_classification || source.risk_level),
    personal: Boolean(source.metadata?.contains_personal_data),
    sensitive: Boolean(source.metadata?.contains_sensitive_data),
    reviewStatus: formatLabel(source.metadata?.review_status || source.status),
    dpia: source.metadata?.dpia_reference || null,
    owner: source.owner_name || source.owner_id,
    status: source.status,
    purpose: [],
    prohibited: [],
    retention: "available on Source/Data Usage page",
    systems: data.accessGrants
      .filter((grant) => grant.target_type === "source" && grant.target_id === source.id)
      .map((grant) => {
        const agent = data.agents.find((item) => item.id === grant.subject_id);
        return agent?.name || grant.subject_id;
      }),
    policies: data.policies.map((policy) => policy.name)
  }));
  const [selectedId, setSelectedId] = useState(sources[0]?.id || null);
  const selected = sources.find((source) => source.id === selectedId) || sources[0] || null;

  useEffect(() => {
    if (!selectedId && sources[0]) {
      setSelectedId(sources[0].id);
    }
  }, [selectedId, sources]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
        <SectionHeader title="Data Governance" sub="Data sources, usage profiles, and classification status" />
        <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "160px 120px 60px 60px 120px 90px", gap: 0, padding: "8px 14px", borderBottom: "1px solid var(--border)", fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".07em", textTransform: "uppercase" }}>
            <span>Source</span><span>Classification</span><span>Personal</span><span>Sensitive</span><span>Review status</span><span>DPIA</span>
          </div>
          {sources.length === 0 && (
            <div style={{ padding: "18px 14px", fontSize: 11, color: "var(--text-muted)" }}>
              {data.loading ? "Loading Sources from GET /sources" : "No Sources returned by the backend"}
            </div>
          )}
          {sources.map(ds => (
            <div key={ds.id} onClick={() => setSelectedId(ds.id)} style={{ display: "grid", gridTemplateColumns: "160px 120px 60px 60px 120px 90px", gap: 0, padding: "11px 14px", borderBottom: "1px solid var(--border2)", cursor: "pointer", background: selected?.id === ds.id ? "rgba(124,109,240,.04)" : "transparent", transition: "background .12s", alignItems: "center" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 600, color: "var(--text)" }}>{ds.name}</span>
              <span><RiskBadge level={ds.classification} cls={ds.classification === "Restricted" ? "danger" : ds.classification === "Confidential" ? "warn" : ds.classification === "Unclassified" ? "info" : "ok"} /></span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: ds.personal ? "var(--red)" : "var(--text-muted)" }}>{ds.personal ? "Yes" : "No"}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: ds.sensitive ? "var(--orange)" : "var(--text-muted)" }}>{ds.sensitive ? "Yes" : "No"}</span>
              <span><StatusBadge label={ds.reviewStatus} cls={ds.reviewStatus === "approved" ? "ok" : "warn"} /></span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: ds.dpia ? "var(--sky)" : "var(--text-faint)" }}>{ds.dpia || "â€”"}</span>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div style={{ width: 320, borderLeft: "1px solid var(--border)", background: "var(--bg-panel)", overflow: "auto", padding: "16px 14px", flexShrink: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#eeeef8", marginBottom: 8, fontFamily: "var(--mono)" }}>{selected.name}</div>
          <MetaRow label="Classification" value={selected.classification} />
          <MetaRow label="Personal data" value={selected.personal ? "Yes" : "No"} />
          <MetaRow label="Sensitive data" value={selected.sensitive ? "Yes" : "No"} />
          <MetaRow label="Review status" value={selected.reviewStatus} />
          {selected.dpia && <MetaRow label="DPIA reference" value={selected.dpia} />}
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Allowed Purposes</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.purpose.map(p => <Pill key={p} label={p} color="var(--green)" bg="var(--green-dim)" border="var(--green-brd)" />)}
            </div>
          </div>
          {selected.prohibited.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Prohibited Purposes</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {selected.prohibited.map(p => <Pill key={p} label={p} color="var(--red)" bg="var(--red-dim)" border="var(--red-brd)" />)}
              </div>
            </div>
          )}
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Linked AI Systems</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.systems.map(s => <Pill key={s} label={s} color="var(--purple-lt)" bg="var(--purple-dim)" border="var(--purple-brd)" />)}
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Linked Policies</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.policies.map(p => <Pill key={p} label={p} color="var(--sky)" bg="var(--sky-dim)" border="var(--sky-brd)" />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ MODELS VIEW â”€â”€â”€ */
const ModelsView = () => {
  const [selected, setSelected] = useState(MODELS[0]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
        <SectionHeader title="Model Inventory" sub="Models used by AI systems â€” approval status, risk, and governance coverage" />
        <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "140px 130px 130px 100px 80px 80px", gap: 0, padding: "8px 14px", borderBottom: "1px solid var(--border)", fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".07em", textTransform: "uppercase" }}>
            <span>Model</span><span>Provider</span><span>Provider type</span><span>Type</span><span>Approval</span><span>Risk</span>
          </div>
          {MODELS.map(m => (
            <div key={m.id} onClick={() => setSelected(m)} style={{ display: "grid", gridTemplateColumns: "140px 130px 130px 100px 80px 80px", gap: 0, padding: "11px 14px", borderBottom: "1px solid var(--border2)", cursor: "pointer", background: selected?.id === m.id ? "rgba(124,109,240,.04)" : "transparent", transition: "background .12s", alignItems: "center" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 600, color: "var(--text)" }}>{m.name}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{m.provider}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{m.providerType}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{m.modelType}</span>
              <span><StatusBadge label={m.approval} cls={m.approvalCls} /></span>
              <span><RiskBadge level={m.risk} cls={m.riskCls} /></span>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div style={{ width: 300, borderLeft: "1px solid var(--border)", background: "var(--bg-panel)", overflow: "auto", padding: "16px 14px", flexShrink: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#eeeef8", marginBottom: 8, fontFamily: "var(--mono)" }}>{selected.name}</div>
          <MetaRow label="Provider" value={selected.provider} />
          <MetaRow label="Provider type" value={selected.providerType} />
          <MetaRow label="Model type" value={selected.modelType} />
          <MetaRow label="Approval" value={selected.approval} />
          <MetaRow label="Decisions" value={selected.decisions.toLocaleString()} />
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Allowed Usage</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.usage.map(u => <Pill key={u} label={u} color="var(--sky)" bg="var(--sky-dim)" border="var(--sky-brd)" />)}
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Linked AI Systems</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.systems.map(s => <Pill key={s} label={s} color="var(--purple-lt)" bg="var(--purple-dim)" border="var(--purple-brd)" />)}
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Policies</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.policies.map(p => <Pill key={p} label={p} color="var(--green)" bg="var(--green-dim)" border="var(--green-brd)" />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ VENDORS VIEW â”€â”€â”€ */
const VendorsView = () => {
  const [selected, setSelected] = useState(VENDORS[0]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
        <SectionHeader title="Vendors & Providers" sub="External providers used by governed AI systems" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          {VENDORS.map(v => (
            <div key={v.id} onClick={() => setSelected(v)} style={{ background: "var(--bg-panel)", border: `1px solid ${selected?.id === v.id ? "var(--purple-brd)" : "var(--border)"}`, borderRadius: "var(--radius)", padding: "14px 14px", cursor: "pointer", transition: "all .12s" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <div style={{ flex: 1, fontSize: 13, fontWeight: 700, color: "#eeeef8" }}>{v.name}</div>
                <StatusBadge label={v.approval} cls={v.approvalCls} />
              </div>
              <div style={{ fontSize: 10.5, color: "var(--text-muted)", fontFamily: "var(--mono)", marginBottom: 10 }}>{v.type}</div>
              <div style={{ display: "flex", gap: 6 }}>
                <RiskBadge level={`${v.risk} risk`} cls={v.riskCls} />
                <Pill label={`${v.systems.length} systems`} />
                {v.models.length > 0 && <Pill label={`${v.models.length} models`} />}
              </div>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div style={{ width: 300, borderLeft: "1px solid var(--border)", background: "var(--bg-panel)", overflow: "auto", padding: "16px 14px", flexShrink: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#eeeef8", marginBottom: 8 }}>{selected.name}</div>
          <MetaRow label="Type" value={selected.type} />
          <MetaRow label="Approval" value={selected.approval} />
          <MetaRow label="Risk" value={selected.risk} />
          <MetaRow label="Policy coverage" value={selected.policyCoverage} />
          <MetaRow label="Evidence packages" value={selected.evidence.toString()} />
          {selected.models.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Models Provided</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {selected.models.map(m => <Pill key={m} label={m} color="var(--orange)" bg="var(--orange-dim)" border="var(--orange-brd)" />)}
              </div>
            </div>
          )}
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 6 }}>Systems Using Provider</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {selected.systems.map(s => <Pill key={s} label={s} color="var(--purple-lt)" bg="var(--purple-dim)" border="var(--purple-brd)" />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* â”€â”€â”€ MONITORING VIEW â”€â”€â”€ */
const MiniBar = ({ values, color }) => {
  const max = Math.max(...values);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 28 }}>
      {values.map((v, i) => (
        <div key={i} style={{ flex: 1, background: color, borderRadius: 2, opacity: i === values.length - 1 ? 1 : 0.3 + (i / values.length) * 0.7, height: `${Math.max(15, (v / max) * 100)}%`, minHeight: 3 }} />
      ))}
    </div>
  );
};

const MonitoringView = ({ data }) => {
  const decisionCount = data.runtimeActivity.filter((item) => item.type === "tool_call_decision").length;
  const deniedCount = data.runtimeActivity.filter((item) => item.decision === "deny").length;
  const reviewCount = data.runtimeActivity.filter((item) => item.decision === "require_human_review").length;
  const allowedCount = data.runtimeActivity.filter((item) => item.decision === "allow").length;
  const signals = [
    { label: "Runtime records", value: compactCount(data.runtimeActivity.length), cls: "info", trend: [0, 0, data.runtimeActivity.length || 1], delta: "GET /runtime/tool-calls/activity" },
    { label: "Decisions", value: compactCount(decisionCount), cls: "purple", trend: [0, decisionCount || 1, decisionCount || 1], delta: "tool call decisions" },
    { label: "Allowed", value: compactCount(allowedCount), cls: "ok", trend: [0, allowedCount || 1, allowedCount || 1], delta: "decision=allow" },
    { label: "Review", value: compactCount(reviewCount), cls: "warn", trend: [0, reviewCount || 1, reviewCount || 1], delta: "requires review" },
    { label: "Denied", value: compactCount(deniedCount), cls: "danger", trend: [0, deniedCount || 1, deniedCount || 1], delta: "decision=deny" }
  ];
  const events = data.runtimeActivity.slice(0, 12).map((item) => ({
    ts: relativeTime(item.timestamp),
    type: item.decision || item.type,
    cls: statusClass(item.decision || item.type),
    action: item.tool_name || item.request_id || item.type,
    system: data.agents.find((agent) => agent.id === item.agent_id)?.name || item.agent_id,
    policy: item.policy_decision_id || "policy decision not linked"
  }));

  return (
  <div className="content">
    <SectionHeader title="Monitoring" sub="Governance signals from active AI systems â€” decisions, denials, gaps, and policy events" />

    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 14 }}>
      {signals.map(s => (
        <div key={s.label} style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "12px 14px", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${s.cls === "ok" ? "var(--green)" : s.cls === "danger" ? "var(--red)" : s.cls === "info" ? "var(--sky)" : "var(--orange)"}, transparent)` }} />
          <div style={{ fontSize: 9.5, color: "var(--text-muted)", fontFamily: "var(--mono)", letterSpacing: ".07em", textTransform: "uppercase", marginBottom: 6 }}>{s.label}</div>
          <div style={{ fontSize: 22, fontFamily: "var(--mono)", fontWeight: 700, color: s.cls === "ok" ? "var(--green)" : s.cls === "danger" ? "var(--red)" : s.cls === "info" ? "var(--sky)" : "var(--orange)", marginBottom: 4 }}>{s.value}</div>
          <MiniBar values={s.trend} color={s.cls === "ok" ? "var(--green)" : s.cls === "danger" ? "var(--red)" : s.cls === "info" ? "var(--sky)" : "var(--orange)"} />
          <div style={{ fontSize: 9.5, color: "var(--text-faint)", fontFamily: "var(--mono)", marginTop: 4 }}>{s.delta}</div>
        </div>
      ))}
    </div>

    <PanelBox title="Recent Governance Events" accent="var(--text-dim)">
      {events.length === 0 && (
        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {data.loading ? "Loading Runtime activity" : "No Runtime activity records returned by the backend."}
        </div>
      )}
      {events.map((ev, i) => (
        <div key={i} style={{ display: "grid", gridTemplateColumns: "50px 130px 1fr 160px 200px", gap: 10, padding: "8px 0", borderBottom: i < events.length - 1 ? "1px solid var(--border2)" : "none", alignItems: "center" }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-faint)" }}>{ev.ts}</span>
          <RiskBadge level={ev.type.replace("_", " ")} cls={ev.cls} />
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text)" }}>{ev.action}</span>
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{ev.system}</span>
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{ev.policy}</span>
        </div>
      ))}
    </PanelBox>
  </div>
  );
};

/* â”€â”€â”€ INTEGRATIONS VIEW â”€â”€â”€ */
const IntegrationsView = () => (
  <div className="content">
    <SectionHeader title="Integrations" sub="Connect AGCP to your AI runtimes and orchestration platforms" />
    <div style={{ background: "rgba(54,184,246,.05)", border: "1px solid var(--sky-brd)", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--sky)", flexShrink: 0 }} />
      <div style={{ fontSize: 12, color: "var(--sky)", fontFamily: "var(--mono)" }}>
        <strong>AGCP decides and records. External runtimes execute.</strong> Integrations are pre-execution hooks â€” your runtime calls AGCP before performing an action, and receives a decision.
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      {INTEGRATIONS.map(int => (
        <div key={int.id} style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border2)", display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#eeeef8" }}>{int.name}</span>
                <StatusBadge label={int.status} cls={int.statusCls} />
                <Pill label={int.type} />
              </div>
            </div>
          </div>
          <div style={{ padding: "12px 16px" }}>
            <p style={{ fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.55, marginBottom: 10 }}>{int.desc}</p>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-faint)", marginBottom: 6 }}>Endpoint / SDK</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--sky)", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "6px 10px", marginBottom: 10 }}>{int.endpoint}</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-faint)", marginBottom: 6 }}>API key scope</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--purple-lt)" }}>{int.keyScope}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/* â”€â”€â”€ ADMIN VIEW â”€â”€â”€ */
const AdminView = () => {
  const [tab, setTab] = useState("users");
  const tabs = ["users", "groups", "api-keys", "settings"];

  return (
    <div className="content">
      <SectionHeader title="Admin" sub="Users, reviewer groups, API keys, and workspace configuration" />
      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid var(--border)", paddingBottom: 0 }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ fontFamily: "var(--mono)", fontSize: 11, padding: "8px 14px", borderRadius: 0, cursor: "pointer", border: "none", background: "transparent", color: tab === t ? "var(--purple-lt)" : "var(--text-muted)", borderBottom: `2px solid ${tab === t ? "var(--purple-lt)" : "transparent"}`, transition: "all .13s", textTransform: "capitalize" }}>
            {t.replace("-", " ")}
          </button>
        ))}
      </div>

      {tab === "users" && (
        <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "180px 200px 160px 160px 80px", gap: 0, padding: "8px 14px", borderBottom: "1px solid var(--border)", fontSize: 9.5, fontFamily: "var(--mono)", color: "var(--text-muted)", letterSpacing: ".07em", textTransform: "uppercase" }}>
            <span>Name</span><span>Email</span><span>Role</span><span>Reviewer Groups</span><span>Status</span>
          </div>
          {ADMIN_USERS.map(u => (
            <div key={u.email} style={{ display: "grid", gridTemplateColumns: "180px 200px 160px 160px 80px", gap: 0, padding: "11px 14px", borderBottom: "1px solid var(--border2)", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{u.name}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{u.email}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--text-dim)" }}>{u.role}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>{u.groups.join(", ")}</span>
              <StatusBadge label={u.status} cls="ok" />
            </div>
          ))}
        </div>
      )}

      {tab === "groups" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {REVIEWER_GROUPS.map(g => (
            <div key={g.name} style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 16px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#eeeef8" }}>{g.name}</span>
                {g.pending > 0 && <span style={{ fontFamily: "var(--mono)", fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 10, background: "var(--orange-dim)", color: "var(--orange)", border: "1px solid var(--orange-brd)" }}>{g.pending} pending</span>}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 10 }}>{g.members} member{g.members !== 1 ? "s" : ""}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {g.policies.map(p => <Pill key={p} label={p} color="var(--purple-lt)" bg="var(--purple-dim)" border="var(--purple-brd)" />)}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "api-keys" && (
        <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
          {[
            { name: "prod-gateway-key", scope: "gateway:write,evidence:write", created: "2024-11-01", lastUsed: "2m ago", status: "active" },
            { name: "ml-ops-key", scope: "gateway:write", created: "2024-10-15", lastUsed: "1h ago", status: "active" },
            { name: "audit-export-key", scope: "evidence:read", created: "2024-09-20", lastUsed: "3d ago", status: "active" },
            { name: "staging-key", scope: "gateway:write,evidence:read", created: "2024-12-01", lastUsed: "never", status: "inactive" },
          ].map((k, i, arr) => (
            <div key={k.name} style={{ display: "grid", gridTemplateColumns: "180px 240px 110px 120px 70px", gap: 0, padding: "11px 14px", borderBottom: i < arr.length - 1 ? "1px solid var(--border2)" : "none", alignItems: "center" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 600, color: "var(--text)" }}>{k.name}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--sky)" }}>{k.scope}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>Created {k.created}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)" }}>Used {k.lastUsed}</span>
              <StatusBadge label={k.status} cls={k.status === "active" ? "ok" : "warn"} />
            </div>
          ))}
        </div>
      )}

      {tab === "settings" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[
            { title: "Policy version control", items: [["Default branch", "main"], ["Approval required for activation", "Yes"], ["Rollback window", "30 days"]] },
            { title: "Environments", items: [["Active environments", "production, staging"], ["Enforcement mode", "Enforced"], ["Simulation allowed", "Yes"]] },
            { title: "Audit retention", items: [["Evidence retention", "7 years"], ["Audit log retention", "5 years"], ["Review history", "Indefinite"]] },
            { title: "Notification settings", items: [["Review SLA alert", "2h before due"], ["Gap detection", "Real-time"], ["Critical risk alerts", "Immediate"]] },
          ].map(s => (
            <PanelBox key={s.title} title={s.title} accent="var(--purple-lt)">
              {s.items.map(([k, v]) => <MetaRow key={k} label={k} value={v} />)}
            </PanelBox>
          ))}
        </div>
      )}
    </div>
  );
};

const AGCP_ROUTE_VIEW_BY_PATH = [
  { path: "/", view: "command", label: "Overview" },
  { path: "/agents", view: "systems", label: "Agents" },
  { path: "/human-approvals", view: "reviews", label: "Human Approvals" },
  { path: "/evidence", view: "evidence", label: "Evidence & Audit" },
  { path: "/audit", view: "evidence", label: "Audit Logs" },
  { path: "/policies", view: "policies", label: "Policy Studio" },
  { path: "/access-data", view: "data", label: "Access & Data" },
  { path: "/integrations", view: "integrations", label: "Integrations" },
  { path: "/runtime-gateway", view: "runtime", label: "Runtime Trace" },
  { path: "/settings", view: "admin", label: "Settings" }
];

const getRouteView = (pathname) => {
  const match = AGCP_ROUTE_VIEW_BY_PATH
    .filter((route) => pathname === route.path || (route.path !== "/" && pathname.startsWith(`${route.path}/`)))
    .sort((left, right) => right.path.length - left.path.length)[0];

  return match || AGCP_ROUTE_VIEW_BY_PATH[0];
};

/* â”€â”€â”€ EXTENDED SIDEBAR â”€â”€â”€ */
const ExtendedSidebar = ({ active, onNav, data, actor }) => {
  const pendingApprovals = data.pendingApprovals ?? data.approvals?.filter((approval) => approval.status === "pending").length ?? 0;
  const sections = [
    {
      label: "Workspace",
      items: [
        { id: "command", label: "Overview", icon: "grid", badge: null, href: "/" },
        { id: "systems", label: "Agents", icon: "box", badge: null, href: "/agents" },
        {
          id: "policies",
          label: "Policy Studio",
          icon: "shield",
          badge: null,
          href: "/policies",
          children: [{ label: "Repository", href: "/policies" }, { label: "Blocks / Code DSL", href: "/policies" }]
        },
        {
          id: "reviews",
          label: "Human Approvals",
          icon: "star",
          badge: pendingApprovals,
          href: "/human-approvals"
        },
        {
          id: "evidence",
          label: "Evidence & Audit",
          icon: "archive",
          badge: null,
          href: "/evidence",
          children: [
            { label: "Evidence Workbench", href: "/evidence" },
            { label: "Audit Logs", href: "/audit" },
            { label: "Evidence Bundles", href: "/evidence" },
            { label: "Exports", href: "/evidence" }
          ]
        },
      ]
    },
    {
      label: "Governance",
      items: [
        {
          id: "data",
          label: "Access & Data",
          icon: "db",
          badge: null,
          href: "/access-data",
          children: [
            { label: "Access Grants", href: "/access-data#access-grants" },
            { label: "Data Sources", href: "/access-data" },
            { label: "Usage Profiles", href: "/access-data#data-usage-profiles" }
          ]
        },
        { id: "runtime", label: "Runtime Trace", icon: "monitor", badge: null, href: "/runtime-gateway" },
        { id: "risk", label: "Risk & Incidents", icon: "alert", badge: null, disabled: true },
        { id: "models", label: "Models", icon: "cpu", badge: null, disabled: true },
      ]
    },
    {
      label: "Platform",
      items: [
        { id: "integrations", label: "Integrations", icon: "plug",     badge: null, href: "/integrations" },
        { id: "admin",        label: "Admin",         icon: "settings", badge: null, href: "/settings" },
      ]
    }
  ];
  const navItems = sections.flatMap((section) => section.items);
  const activeItem = navItems.find((item) => item.id === active) ?? navItems[0];
  const isOverviewContext = activeItem.id === "command";
  const isDataContext = activeItem.id === "data";
  const isPolicyContext = activeItem.id === "policies";
  const isEvidenceContext = activeItem.id === "evidence";
  const isReviewContext = activeItem.id === "reviews";
  const isIntegrationContext = activeItem.id === "integrations";
  const usesRailOnlySidebar = isPolicyContext || isReviewContext;
  const quickFilters = isEvidenceContext
    ? ["Runs with approvals", "Denied decisions", "Runs with escalations", "Exports created"]
    : isReviewContext
    ? ["Pending review", "Needs owner", "Exception request", "Recently approved"]
    : isIntegrationContext
    ? ["Connected", "Design-only", "Service actors", "Audit linked"]
    : ["Active", "Pending Review", "Suspended", "Expired"];
  const actorName = actor?.display_name || actor?.actor_id || "Admin User";
  const actorRole = overviewRoles(actor)[0] || actor?.actor_type || "Security Operator";

  return (
    <aside className={`sidebar ${isOverviewContext ? "overview-no-rail" : ""} ${usesRailOnlySidebar ? "rail-only" : ""}`}>
      {!isOverviewContext ? (
        <div className="sidebar-rail" aria-label="Primary navigation">
          <Link className="sidebar-rail-mark" href="/" aria-label="AGCP Studio overview">
            <Icon name="brand_logo" size={36} />
          </Link>
          <nav className="sidebar-rail-nav">
            {navItems.map((item) => {
              const isActive = active === item.id;
              const icon = <Icon name={item.icon} size={15} />;

              if (item.disabled || !item.href) {
                return (
                  <span
                    aria-disabled={item.disabled ? "true" : undefined}
                    className={`sidebar-rail-link disabled ${isActive ? "active" : ""}`}
                    data-label={`${item.label} is planned`}
                    key={`rail-${item.id}`}
                    title={item.disabled ? `${item.label} is planned` : item.label}
                  >
                    {icon}
                  </span>
                );
              }

              return (
                <Link
                  aria-current={isActive ? "page" : undefined}
                  aria-label={item.label}
                  className={`sidebar-rail-link ${isActive ? "active" : ""}`}
                  data-label={item.label}
                  href={item.href}
                  key={`rail-${item.id}`}
                  title={item.label}
                >
                  {icon}
                  {item.badge ? <span className="sidebar-rail-badge">{item.badge}</span> : null}
                </Link>
              );
            })}
          </nav>
          <span className="sidebar-rail-spacer" />
          <Link className="sidebar-rail-footer" href="/settings" aria-label="Settings" title="Settings">
            <Icon name="settings" size={15} />
          </Link>
        </div>
      ) : null}

      {!usesRailOnlySidebar ? (
      <div className="sidebar-context">
        <div className="logo-area">
          <div className="logo-mark">
            <Icon name="brand_logo" size={isOverviewContext ? 36 : 32} />
            <div className="logo-text">
              <div className="brand">AGCP Studio</div>
              <div className="tagline">Agent Governance Control Plane</div>
            </div>
          </div>
        </div>

        {isOverviewContext ? (
          <nav className="sidebar-nav" aria-label="AGCP Studio navigation">
            {sections.map((section) => (
              <div className="nav-section" key={section.label}>
                <div className="nav-section-label">{section.label}</div>
                {section.items.map((item) => {
                  const isActive = active === item.id;
                  const navIcon = (
                    <span className="nav-item-icon">
                      <Icon name={item.icon} size={15} />
                    </span>
                  );

                  if (item.disabled || !item.href) {
                    return (
                      <span
                        aria-disabled="true"
                        className={`nav-item disabled ${isActive ? "active" : ""}`}
                        key={item.id}
                        title={`${item.label} is planned`}
                      >
                        {navIcon}
                        <span className="nav-item-label">{item.label}</span>
                      </span>
                    );
                  }

                  return (
                    <div className="nav-branch" key={item.id}>
                      <Link
                        aria-current={isActive ? "page" : undefined}
                        className={`nav-item ${isActive ? "active" : ""}`}
                        href={item.href}
                      >
                        {navIcon}
                        <span className="nav-item-label">{item.label}</span>
                        {item.badge ? <span className={item.id === "reviews" ? "nav-badge-orange" : "nav-badge"}>{item.badge}</span> : null}
                      </Link>
                      {isActive && item.children?.length ? (
                        <div className="nav-subtree" aria-label={`${item.label} sections`}>
                          {item.children.map((child) => (
                            <Link className="nav-subitem" href={child.href} key={child.label}>
                              {child.label}
                            </Link>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ))}
          </nav>
        ) : (
          <>
            <div className="sidebar-sidepanel">
              <div className="sidebar-module">
                <span className="sidebar-module-icon"><Icon name={activeItem.icon} size={24} /></span>
                <div>
                  <div className="sidebar-module-title">{activeItem.label}</div>
                  <div className="sidebar-module-sub">Agent Governance Control Plane</div>
                </div>
              </div>

              <div className="sidebar-divider" />

              <div className="sidebar-filters">
                <div className="sidebar-filter-head">
                  <span>Filters</span>
                  <button type="button">Clear</button>
                </div>

                {isPolicyContext ? (
                  <>
                    <label className="sidebar-field">
                      <span>Repository</span>
                      <select defaultValue="local"><option value="local">Local backend</option></select>
                    </label>
                    <label className="sidebar-field">
                      <span>Policy status</span>
                      <select defaultValue="all"><option value="all">All policies</option></select>
                    </label>
                    <div className="sidebar-note">Policy Studio keeps repository, block library, editor, compile bar, and inspector in the workspace.</div>
                  </>
                ) : isDataContext ? (
                  <>
                    <label className="sidebar-field">
                      <span>Agent</span>
                      <select defaultValue="all"><option value="all">All agents</option></select>
                    </label>
                    <label className="sidebar-field">
                      <span>Access Grant status</span>
                      <select defaultValue="all"><option value="all">All</option></select>
                    </label>
                  </>
                ) : (
                  <>
                    <label className="sidebar-field">
                      <span>Environment</span>
                      <select defaultValue="production">
                        <option value="production">Production</option>
                        <option value="development">Development</option>
                      </select>
                    </label>
                    <label className="sidebar-field">
                      <span>{isEvidenceContext ? "Policy Decision" : "Status"}</span>
                      <select defaultValue="all"><option value="all">All</option></select>
                    </label>
                  </>
                )}

                <div className="sidebar-quick">
                  {quickFilters.map((filter, index) => (
                    <button type="button" key={filter}>
                      <span className={`dot dot-${index % 4}`} />
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              <button type="button" className="sidebar-save">
                <Icon name="archive" size={16} />
                Save view
              </button>
            </div>

            <div className="sidebar-footer">
              <span className="avatar">{initialsFor(actorName)}</span>
              <div>
                <div className="user-name">{actorName}</div>
                <div className="user-role">{actorRole}</div>
              </div>
            </div>
          </>
        )}

      </div>
      ) : null}
    </aside>
  );
};

/* â”€â”€â”€ EXTENDED TOPBAR â”€â”€â”€ */
const ExtendedTopbar = ({ title, pendingApprovals, actor }) => {
  const actorName = actor?.display_name || actor?.actor_id || "Current actor";
  const actorRole = overviewRoles(actor)[0] || actor?.actor_type || "Backend actor";

  return (
    <header className="topbar" aria-label="AGCP Studio page header">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <span>AGCP</span>
        <span className="bc-sep">{">"}</span>
        <span className="active">{title || "Overview"}</span>
      </nav>

      <span className="topbar-spacer" />

      <label className="topbar-search">
        <Icon name="search" size={15} />
        <input aria-label="Search AGCP" placeholder="Search AGCP..." />
        <span className="topbar-kbd">Ctrl K</span>
      </label>

      <div className="topbar-actions">
        <Link className="icon-btn" href="/human-approvals" aria-label="Notifications">
          <Icon name="bell" size={18} />
          {pendingApprovals > 0 ? <span className="notif-dot">{pendingApprovals}</span> : null}
        </Link>
        <Link className="icon-btn" href="/settings" aria-label="Help">
          <Icon name="help" size={18} />
        </Link>
        <Link className="topbar-profile" href="/settings" aria-label="User settings">
          <span className="topbar-avatar">{initialsFor(actorName)}</span>
          <span className="topbar-profile-copy">
            <span className="topbar-profile-name">{actorName}</span>
            <span className="topbar-profile-role">{actorRole}</span>
          </span>
          <span className="topbar-profile-chevron" aria-hidden="true">
            <Icon name="chevron_down" size={12} />
          </span>
        </Link>
      </div>
    </header>
  );
};

export function AGCPStudioShell({ children }) {
  const [mode, setMode] = useState("live");
  const [theme, setTheme] = useState("dark");
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [shellActor, setShellActor] = useState(null);
  const pathname = usePathname() || "/";
  const routeView = getRouteView(pathname);
  const navDensity = "full";

  useEffect(() => {
    const controller = new AbortController();

    fetchHumanApprovals("all", controller.signal)
      .then((approvals) => {
        setPendingApprovals(approvals.filter((approval) => approval.status === "pending").length);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setPendingApprovals(0);
        }
      });

    fetchCurrentActor(controller.signal)
      .then((actor) => {
        setShellActor(actor);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setShellActor(null);
        }
      });

    return () => controller.abort();
  }, [pathname]);

  const shellData = { pendingApprovals, approvals: [] };
  const content =
    pathname === "/"
      ? children
      : <main className="content agcp-connected-content">{children}</main>;

  return (
    <>
      <style>{AGCP_SHELL_CSS}</style>
      <style>{AGCP_STUDIO_CSS}</style>
      <style>{AGCP_CONNECTED_CSS}</style>
      <style>{AGCP_REVIEW_INBOX_CSS}</style>
      <div
        className="shell"
        data-theme={theme}
        data-nav-density={navDensity}
      >
        <ExtendedSidebar active={routeView.view} onNav={() => undefined} data={shellData} actor={shellActor} />
        <div className="main">
          <ExtendedTopbar title={routeView.label} pendingApprovals={pendingApprovals} actor={shellActor} />
          {content}
        </div>
      </div>
    </>
  );
}

export function AGCPStudioDashboard() {
  const studioData = useAGCPStudioData();

  return <CommandView data={studioData} />;
}
