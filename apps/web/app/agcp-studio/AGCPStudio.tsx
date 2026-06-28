// @ts-nocheck
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { fetchAgents } from "../lib/agents";
import { fetchHumanApprovals, transitionHumanApproval } from "../lib/human-approvals";
import { fetchPolicies, fetchPolicyVersionReviewRequests } from "../lib/policies";
import { fetchAccessGrants, fetchSources } from "../lib/sources";
import { fetchRuntimeToolCallActivity } from "../lib/runtime";
import { fetchCurrentActor } from "../lib/current-actor";

/* ─── DESIGN TOKENS ─── */
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    /* [6] Adoucissement: fonds légèrement plus clairs, moins vide absolu */
    --bg:        #0a0a14;
    --bg-panel:  #0f0f1a;
    --bg-panel2: #13131f;
    --bg-card:   #161624;
    --border:    rgba(255,255,255,.08);
    --border2:   rgba(255,255,255,.05);
    --text:      #eaeaf2;
    --text-dim:  #9898bb;
    --text-muted:#545470;
    --text-faint:#30304a;
    --purple:    #7c6df0;
    --purple-lt: #a892f8;
    --purple-dim:rgba(124,109,240,.11);
    --purple-brd:rgba(124,109,240,.26);
    --green:     #2dd891;
    --green-dim: rgba(45,216,145,.08);
    --green-brd: rgba(45,216,145,.2);
    --red:       #f03f5a;
    --red-dim:   rgba(240,63,90,.08);
    --red-brd:   rgba(240,63,90,.2);
    --orange:    #f59040;
    --orange-dim:rgba(245,144,64,.08);
    --orange-brd:rgba(245,144,64,.2);
    --sky:       #36b8f6;
    --sky-dim:   rgba(54,184,246,.07);
    --sky-brd:   rgba(54,184,246,.18);
    --mono:      'JetBrains Mono', monospace;
    --sans:      'Inter', system-ui, sans-serif;
    --radius-sm: 6px;
    --radius:    10px;
    --radius-lg: 14px;
    --glow-purple: 0 0 20px rgba(124,109,240,.14);
    --glow-green:  0 0 10px rgba(45,216,145,.45);
    --glow-orange: 0 0 14px rgba(245,144,64,.35);
  }

  /* ── LIGHT THEME ── */
  .shell[data-theme="light"] {
    --bg:        #f4f5f7;
    --bg-panel:  #ffffff;
    --bg-panel2: #f8f8fb;
    --bg-card:   #eeeef6;
    --border:    rgba(0,0,0,.09);
    --border2:   rgba(0,0,0,.05);
    --text:      #18182e;
    --text-dim:  #4a4a6a;
    --text-muted:#7878a0;
    --text-faint:#b0b0c8;
    --purple:    #5c4ed4;
    --purple-lt: #5c4ed4;
    --purple-dim:rgba(92,78,212,.08);
    --purple-brd:rgba(92,78,212,.22);
    --green:     #1a9e6a;
    --green-dim: rgba(26,158,106,.08);
    --green-brd: rgba(26,158,106,.2);
    --red:       #d42e4a;
    --red-dim:   rgba(212,46,74,.07);
    --red-brd:   rgba(212,46,74,.18);
    --orange:    #c97020;
    --orange-dim:rgba(201,112,32,.07);
    --orange-brd:rgba(201,112,32,.18);
    --sky:       #1a8fc5;
    --sky-dim:   rgba(26,143,197,.07);
    --sky-brd:   rgba(26,143,197,.17);
    --glow-purple: 0 0 16px rgba(92,78,212,.1);
    --glow-green:  0 0 8px rgba(26,158,106,.25);
    --glow-orange: 0 0 10px rgba(201,112,32,.2);
  }

  .shell[data-theme="light"]::before {
    background:
      radial-gradient(ellipse 50% 35% at 18% -8%, rgba(92,78,212,.04) 0%, transparent 60%),
      radial-gradient(ellipse 35% 25% at 82% 105%, rgba(26,158,106,.03) 0%, transparent 60%);
  }

  .shell[data-theme="light"] .topbar {
    background: rgba(255,255,255,.92);
  }

  .shell[data-theme="light"] .editor-scroll { background: #f0f0f8; }
  .shell[data-theme="light"] .code-preview  { background: #f0f0f8; border-top-color: rgba(0,0,0,.06); }
  .shell[data-theme="light"] .code-content  { color: #5a5a82; }
  .shell[data-theme="light"] .kw    { color: #4a3ac0; }
  .shell[data-theme="light"] .kw2   { color: #6750d8; }
  .shell[data-theme="light"] .str   { color: #1a7a4a; }
  .shell[data-theme="light"] .val   { color: #b05c10; }
  .shell[data-theme="light"] .cmt   { color: #a0a0c0; }
  .shell[data-theme="light"] .req   { color: #c0203a; }
  .shell[data-theme="light"] .fn    { color: #1a8a58; }
  .shell[data-theme="light"] .sym   { color: #9898ba; }
  .shell[data-theme="light"] .line-num { color: #c0c0da; }
  .shell[data-theme="light"] .code-line:hover { background: rgba(0,0,0,.03); }

  .shell[data-theme="light"] ::-webkit-scrollbar-thumb { background: rgba(0,0,0,.12); }

  .shell[data-theme="light"] .nav-item:hover { background: rgba(0,0,0,.04); color: #3a3a5a; }
  .shell[data-theme="light"] .logo-text .brand { color: #18182e; }

  .shell[data-theme="light"] .search-box { background: rgba(0,0,0,.04); }
  .shell[data-theme="light"] .search-box input { color: #18182e; }

  .shell[data-theme="light"] .iih-btn-sec:hover { background: rgba(0,0,0,.04); }
  .shell[data-theme="light"] .btn-secondary:hover { background: rgba(0,0,0,.04); }
  .shell[data-theme="light"] .btn-small:hover { background: rgba(0,0,0,.04); }
  .shell[data-theme="light"] .icon-btn:hover { background: rgba(0,0,0,.05); }
  .shell[data-theme="light"] .flow-node:hover { background: var(--purple-dim); }
  .shell[data-theme="light"] .inbox-item-hero:hover { background: rgba(0,0,0,.02); }
  .shell[data-theme="light"] .bc-action-btn:hover { background: rgba(0,0,0,.04); }
  .shell[data-theme="light"] .mode-switcher { background: rgba(0,0,0,.04); }

  .shell[data-theme="light"] .page-title { color: #18182e; }
  .shell[data-theme="light"] .logo-text .tagline { color: #9898b8; }
  .shell[data-theme="light"] .user-name { color: #3a3a5a; }

  /* Fix hardcoded #eeeef8 headings in new views */
  .shell[data-theme="light"] .pane-title,
  .shell[data-theme="light"] .insp-title,
  .shell[data-theme="light"] .panel-title { color: #18182e; }

  .shell[data-theme="light"] .iih-title { color: #18182e; }
  .shell[data-theme="light"] .ws-name   { color: #18182e; }
  .shell[data-theme="light"] .adc-title { color: #18182e; }
  .shell[data-theme="light"] .fn-label  { color: #18182e; }
  .shell[data-theme="light"] .dfm-label { color: #18182e; }
  .shell[data-theme="light"] .tmpl-name { color: #18182e; }
  .shell[data-theme="light"] .block-main { color: #18182e; }
  .shell[data-theme="light"] .iih-sub   { color: #7878a0; }

  .shell[data-theme="light"] .status-pill { background: rgba(26,158,106,.07); border-color: rgba(26,158,106,.18); }

  /* theme toggle button */
  .theme-toggle {
    display: flex; align-items: center; gap: 5px;
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    padding: 5px 11px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: transparent;
    color: var(--text-muted); cursor: pointer; transition: all .15s;
    letter-spacing: .04em; flex-shrink: 0;
  }
  .theme-toggle:hover { border-color: var(--purple-brd); color: var(--purple-lt); background: var(--purple-dim); }

  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08); border-radius: 4px; }

  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.35;transform:scale(1.5)} }
  @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  @keyframes slideIn { from{opacity:0;transform:translateX(-6px)} to{opacity:1;transform:translateX(0)} }
  @keyframes inboxPulse { 0%,100%{box-shadow:0 0 0 0 rgba(245,144,64,.4)} 50%{box-shadow:0 0 0 6px rgba(245,144,64,0)} }
  @keyframes rowIn { from{opacity:0;transform:translateX(-4px)} to{opacity:1;transform:translateX(0)} }

  /* ── SHELL ── */
  .shell {
    display: flex;
    height: 100vh;
    min-height: 700px;
    background: var(--bg);
    font-family: var(--sans);
    color: var(--text);
    overflow: hidden;
    position: relative;
  }
  .shell::before {
    content: '';
    position: fixed; inset: 0;
    background:
      radial-gradient(ellipse 50% 35% at 18% -8%, rgba(124,109,240,.06) 0%, transparent 60%),
      radial-gradient(ellipse 35% 25% at 82% 105%, rgba(45,216,145,.04) 0%, transparent 60%);
    pointer-events: none; z-index: 0;
  }
  .app-body {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    position: relative;
    z-index: 1;
  }

  /* ── SIDEBAR ── */
  .sidebar {
    width: 318px; flex-shrink: 0;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    display: flex;
    position: relative; z-index: 10;
  }
  .sidebar.rail-only {
    width: 54px;
    background: #090913;
    border-right: 0;
  }
  .sidebar-rail {
    width: 54px; flex-shrink: 0;
    background: #090913;
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column; align-items: center;
    padding: 12px 7px;
  }
  .sidebar-rail-mark {
    width: 39px; height: 39px;
    display: flex; align-items: center; justify-content: center;
    color: var(--purple-lt);
    margin-bottom: 8px;
  }
  .sidebar-rail-nav {
    display: grid; gap: 9px;
    width: 100%;
  }
  .sidebar-rail-link {
    width: 39px; height: 39px;
    display: flex; align-items: center; justify-content: center;
    border: 1px solid transparent;
    border-radius: 10px;
    color: #8b8ba6;
    text-decoration: none;
    transition: all .13s;
    position: relative;
  }
  .sidebar-rail-link::after {
    content: attr(data-label);
    position: absolute;
    left: 46px;
    top: 50%;
    transform: translateY(-50%) translateX(-4px);
    min-width: max-content;
    max-width: 180px;
    pointer-events: none;
    opacity: 0;
    z-index: 80;
    border: 1px solid rgba(168,146,248,.26);
    border-radius: 7px;
    background: rgba(13,18,27,.96);
    box-shadow: 0 10px 28px rgba(0,0,0,.35);
    color: #eef1f8;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1;
    padding: 9px 10px;
    transition: opacity .13s ease, transform .13s ease;
    white-space: nowrap;
  }
  .sidebar-rail-link:hover::after,
  .sidebar-rail-link:focus-visible::after {
    opacity: 1;
    transform: translateY(-50%) translateX(0);
  }
  .sidebar-rail-link:hover {
    background: rgba(255,255,255,.035);
    color: var(--text-dim);
  }
  .sidebar-rail-link.active {
    background: var(--purple-dim);
    border-color: var(--purple-brd);
    color: var(--purple-lt);
    box-shadow: inset 0 0 0 1px rgba(168,146,248,.08);
  }
  .sidebar-rail-link.active::before {
    content: "";
    position: absolute;
    left: -8px; top: 9px; bottom: 9px;
    width: 3px;
    border-radius: 0 2px 2px 0;
    background: var(--purple-lt);
  }
  .sidebar-rail-spacer { flex: 1; }
  .sidebar-rail-footer {
    width: 39px; height: 39px;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-muted);
  }
  .sidebar-context {
    min-width: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .sidebar.rail-only .sidebar-context {
    display: none;
  }
  .logo-area {
    height: 62px;
    padding: 0 22px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
  }
  .logo-mark { display: flex; align-items: center; gap: 10px; margin-bottom: 0; }
  .logo-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #5c4ed4, #9278f0);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 18px rgba(92,78,212,.3), inset 0 1px 0 rgba(255,255,255,.12);
    flex-shrink: 0;
  }
  .logo-text .brand { font-size: 20px; font-weight: 700; letter-spacing: -.01em; color: #f4f5fb; }
  .logo-text .tagline { font-size: 9px; color: var(--text-muted); letter-spacing: .12em; margin-top: 1px; font-family: var(--mono); }
  .status-pill {
    display: flex; align-items: center; gap: 7px;
    background: var(--green-dim);
    border: 1px solid var(--green-brd);
    border-radius: var(--radius-sm);
    padding: 5px 10px;
  }
  .status-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--green); box-shadow: var(--glow-green);
    animation: pulse 2s ease-in-out infinite; flex-shrink: 0;
  }
  .status-pill span { font-family: var(--mono); font-size: 9px; color: var(--green); letter-spacing: .08em; }

  .sidebar-nav { flex: 1; padding: 18px 10px 10px; overflow: auto; }
  .nav-section-label {
    font-family: var(--mono); font-size: 9px; letter-spacing: .12em;
    color: var(--text-faint); text-transform: uppercase; padding: 11px 14px 7px;
  }
  .nav-item {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; border-radius: 7px; cursor: pointer;
    transition: all .13s; color: var(--text-muted);
    font-size: 14px; font-weight: 500; margin-bottom: 2px;
    border: 1px solid transparent; position: relative; user-select: none;
    text-decoration: none;
  }
  .nav-item:hover { background: rgba(255,255,255,.04); color: #bcbcd4; }
  .nav-item.active {
    background: var(--purple-dim); color: var(--purple-lt);
    border-color: var(--purple-brd);
  }
  .nav-item.active::before {
    content: '';
    position: absolute; left: -11px; top: 50%;
    transform: translateY(-50%);
    width: 3px; height: 60%;
    background: var(--purple-lt);
    border-radius: 0 2px 2px 0;
  }
  .nav-badge {
    margin-left: auto;
    background: var(--red); color: #fff;
    border-radius: 10px; font-size: 9px; font-weight: 700;
    padding: 1px 6px; font-family: var(--mono);
    min-width: 18px; text-align: center;
    box-shadow: 0 0 8px rgba(240,63,90,.5);
  }
  /* [2] Badge urgence inbox dans sidebar */
  .nav-badge-orange {
    margin-left: auto;
    background: var(--orange); color: #fff;
    border-radius: 10px; font-size: 9px; font-weight: 700;
    padding: 1px 6px; font-family: var(--mono);
    min-width: 18px; text-align: center;
    box-shadow: var(--glow-orange);
    animation: inboxPulse 2.5s ease-in-out infinite;
  }
  .nav-shortcut {
    margin-left: auto; font-family: var(--mono); font-size: 9.5px;
    color: rgba(90,90,122,.4);
  }
  .nav-item.active .nav-shortcut { color: rgba(168,146,248,.35); }
  .nav-item-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 18px; height: 18px; flex-shrink: 0;
  }
  .nav-item-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .nav-branch { margin-bottom: 2px; }
  .nav-subtree {
    display: grid; gap: 3px; margin: 4px 0 9px 42px;
    border-left: 0; padding-left: 0;
  }
  .nav-subitem {
    color: var(--text-muted); display: flex; align-items: center; gap: 7px;
    border-radius: 6px; font-size: 13px; padding: 8px 10px;
    text-decoration: none; transition: all .12s;
  }
  .nav-subitem::before {
    content: ""; width: 5px; height: 5px; border-radius: 999px;
    background: var(--text-faint); flex-shrink: 0;
  }
  .nav-subitem:hover { background: rgba(255,255,255,.035); color: var(--text-dim); }
  .nav-subitem.active {
    background: var(--purple-dim); color: var(--purple-lt);
  }
  .nav-subitem.active::before { background: var(--purple-lt); box-shadow: 0 0 8px rgba(168,146,248,.45); }

  .sidebar-context .nav-subitem[aria-current="false"] {
    background: transparent;
    color: var(--text-muted);
  }
  .sidebar-context .nav-subitem[aria-current="false"]::before {
    background: var(--text-faint);
    box-shadow: none;
  }

  .context-panel {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: auto;
  }
  .context-module {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 24px 22px 20px;
  }
  .context-module-icon {
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--purple-lt);
  }
  .context-module-title {
    color: #f4f5fb;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -.01em;
  }
  .context-module-sub {
    color: #8d94a8;
    font-size: 12px;
    margin-top: 2px;
  }
  .context-tabs {
    display: grid;
    gap: 8px;
    padding: 0 8px 22px;
  }
  .context-tab {
    min-height: 52px;
    border-radius: 7px;
    border: 1px solid transparent;
    color: #9aa1b5;
    display: flex;
    align-items: center;
    gap: 13px;
    padding: 0 18px;
    text-decoration: none;
    font-size: 14px;
    transition: all .13s;
    position: relative;
  }
  .context-tab:hover {
    background: rgba(255,255,255,.035);
    color: #cdd2df;
  }
  .context-tab.active {
    background: var(--purple-dim);
    border-color: var(--purple-brd);
    color: var(--purple-lt);
    box-shadow: inset 0 0 0 1px rgba(168,146,248,.08);
  }
  .context-tab.active::before {
    content: "";
    position: absolute;
    left: -9px;
    top: 10px;
    bottom: 10px;
    width: 3px;
    border-radius: 0 2px 2px 0;
    background: var(--purple-lt);
  }
  .sidebar-rail-link.disabled {
    opacity: .38;
    cursor: not-allowed;
  }
  .sidebar-rail-badge {
    position: absolute;
    right: -3px;
    top: -3px;
    min-width: 17px;
    height: 17px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--purple-lt);
    color: white;
    font-family: var(--mono);
    font-size: 9px;
    font-weight: 700;
    box-shadow: 0 0 10px rgba(168,146,248,.5);
  }
  .context-tab-icon {
    width: 20px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .context-divider {
    height: 1px;
    background: var(--border);
    margin: 0;
  }
  .context-filters {
    padding: 22px 20px;
    display: grid;
    gap: 16px;
  }
  .context-filter-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #f0f2f7;
    font-size: 14px;
    font-weight: 700;
  }
  .context-filter-head button {
    border: 0;
    background: transparent;
    color: var(--purple-lt);
    font-size: 12px;
    cursor: pointer;
  }
  .context-field {
    display: grid;
    gap: 8px;
  }
  .context-field > span {
    color: #c7cad6;
    font-size: 12px;
  }
  .context-field select,
  .context-field input {
    width: 100%;
    height: 38px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: rgba(255,255,255,.035);
    color: var(--text);
    padding: 0 12px;
    font: inherit;
    outline: none;
  }
  .context-field select:focus,
  .context-field input:focus {
    border-color: rgba(168,146,248,.34);
    background: rgba(255,255,255,.05);
  }
  .context-field.search div {
    position: relative;
  }
  .context-field.search input {
    padding-right: 36px;
  }
  .context-field.search svg {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
  }
  .context-quick {
    border-top: 1px solid var(--border);
    padding-top: 14px;
    display: grid;
    gap: 10px;
  }
  .context-quick button {
    border: 0;
    background: transparent;
    color: #8f96aa;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    font-size: 12px;
    padding: 0;
    text-align: left;
  }
  .context-quick .dot {
    width: 9px;
    height: 9px;
    border-radius: 999px;
    border: 1px solid currentColor;
    margin-right: 2px;
  }
  .context-quick button {
    justify-content: flex-start;
  }
  .dot-0 { color: var(--green); }
  .dot-1 { color: var(--orange); }
  .dot-2 { color: var(--red); }
  .dot-3 { color: #9aa3b5; }
  .context-note {
    border: 1px solid var(--purple-brd);
    border-radius: 7px;
    background: rgba(124,109,240,.08);
    color: #8d94a8;
    font-size: 12px;
    line-height: 1.45;
    padding: 12px;
  }
  .policy-context-stack {
    display: grid;
    gap: 14px;
    padding: 22px 20px;
  }
  .policy-context-label {
    color: var(--text-faint);
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: .13em;
    text-transform: uppercase;
  }
  .policy-repo-card {
    border: 1px solid var(--border);
    border-radius: 7px;
    background: rgba(255,255,255,.035);
    padding: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .policy-repo-card svg { color: #a892f8; flex-shrink: 0; }
  .policy-repo-name {
    color: #f2f4fb;
    font-size: 13px;
    font-weight: 700;
  }
  .policy-repo-sub {
    color: #7d8498;
    font-size: 11px;
    margin-top: 2px;
  }
  .policy-command-row {
    display: grid;
    grid-template-columns: 1fr 36px 36px 36px;
    gap: 7px;
  }
  .policy-command-row .policy-search {
    height: 36px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: rgba(255,255,255,.035);
    color: var(--text);
    padding: 0 11px;
    min-width: 0;
    outline: none;
  }
  .policy-command-row button {
    height: 36px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: rgba(255,255,255,.035);
    color: #cfd3df;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .policy-command-row button:hover {
    border-color: rgba(168,146,248,.3);
    color: var(--purple-lt);
  }
  .policy-workbench-list,
  .policy-version-list {
    display: grid;
    gap: 7px;
  }
  .policy-workbench-item {
    border: 1px solid var(--border);
    border-radius: 7px;
    background: rgba(255,255,255,.025);
    padding: 10px 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #dce1ed;
    font-size: 12px;
  }
  .policy-workbench-item.active {
    border-color: var(--purple-brd);
    background: rgba(124,109,240,.14);
    box-shadow: inset 3px 0 0 rgba(168,146,248,.95);
  }
  .policy-workbench-item svg { color: var(--purple-lt); flex-shrink: 0; }
  .policy-empty-note {
    border: 1px solid var(--border);
    border-radius: 7px;
    background: rgba(255,255,255,.025);
    color: #737c92;
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.45;
    padding: 11px;
  }
  .policy-new-btn {
    min-height: 38px;
    border: 1px dashed var(--purple-brd);
    border-radius: 7px;
    background: rgba(124,109,240,.08);
    color: var(--purple-lt);
    font-weight: 700;
  }
  .context-page-summary {
    border-top: 1px solid var(--border);
    padding: 18px 20px;
    display: grid;
    gap: 10px;
  }
  .context-summary-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #8f96aa;
    font-size: 12px;
  }
  .context-summary-row strong {
    color: #f1f3fb;
    font-weight: 700;
  }
  .context-save {
    margin: auto 20px 24px;
    min-height: 42px;
    border: 1px solid var(--purple-brd);
    border-radius: 7px;
    background: rgba(124,109,240,.08);
    color: var(--purple-lt);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-weight: 600;
    cursor: pointer;
  }
  .context-save:hover {
    background: rgba(124,109,240,.14);
  }

  .shell[data-nav-density="compact"] .sidebar {
    width: 280px;
  }
  .shell[data-nav-density="compact"] .logo-area {
    padding: 12px 7px 10px;
  }
  .shell[data-nav-density="compact"] .logo-mark {
    justify-content: center; margin-bottom: 0;
  }
  .shell[data-nav-density="compact"] .logo-text,
  .shell[data-nav-density="compact"] .status-pill,
  .shell[data-nav-density="compact"] .nav-section-label,
  .shell[data-nav-density="compact"] .nav-item-label,
  .shell[data-nav-density="compact"] .nav-shortcut,
  .shell[data-nav-density="compact"] .nav-badge,
  .shell[data-nav-density="compact"] .nav-badge-orange,
  .shell[data-nav-density="compact"] .nav-subtree,
  .shell[data-nav-density="compact"] .sidebar-footer > div:not(.avatar) {
    display: none;
  }
  .shell[data-nav-density="compact"] .sidebar-nav {
    padding: 8px 6px;
  }
  .shell[data-nav-density="compact"] .nav-item {
    align-items: center; justify-content: center;
    height: 36px; margin-bottom: 5px; padding: 0;
  }
  .shell[data-nav-density="compact"] .nav-item.active::before {
    left: -6px; height: 60%;
  }
  .shell[data-nav-density="compact"] .sidebar-footer {
    justify-content: center; padding: 10px 6px;
  }
  .shell[data-nav-density="compact"] .avatar {
    width: 28px; height: 28px;
  }

  @media (min-width: 1680px) {
    .shell[data-nav-density="compact"] .sidebar {
      width: 214px;
    }
    .shell[data-nav-density="compact"] .logo-area {
      padding: 20px 16px 14px;
    }
    .shell[data-nav-density="compact"] .logo-mark {
      justify-content: flex-start; margin-bottom: 12px;
    }
    .shell[data-nav-density="compact"] .logo-text,
    .shell[data-nav-density="compact"] .status-pill,
    .shell[data-nav-density="compact"] .nav-section-label,
    .shell[data-nav-density="compact"] .nav-item-label,
    .shell[data-nav-density="compact"] .nav-subtree,
    .shell[data-nav-density="compact"] .sidebar-footer > div:not(.avatar) {
      display: unset;
    }
    .shell[data-nav-density="compact"] .logo-text { display: block; }
    .shell[data-nav-density="compact"] .status-pill { display: flex; }
    .shell[data-nav-density="compact"] .nav-section-label { display: block; }
    .shell[data-nav-density="compact"] .nav-item-label { display: inline; }
    .shell[data-nav-density="compact"] .nav-subtree { display: grid; }
    .shell[data-nav-density="compact"] .sidebar-nav {
      padding: 8px 7px;
    }
    .shell[data-nav-density="compact"] .nav-item {
      justify-content: flex-start; height: auto; margin-bottom: 1px; padding: 7.5px 10px;
    }
    .shell[data-nav-density="compact"] .sidebar-footer {
      justify-content: flex-start; padding: 11px 13px;
    }
  }

  .sidebar-footer {
    padding: 11px 13px; border-top: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
  }
  .avatar {
    width: 28px; height: 28px; border-radius: 50%;
    background: linear-gradient(135deg, #5c4ed4, #9278f0);
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; color: #fff; flex-shrink: 0;
    box-shadow: 0 0 10px rgba(92,78,212,.3);
  }
  .user-name { font-size: 12px; font-weight: 500; color: #bcbcd4; }
  .user-role { font-size: 10px; color: var(--text-muted); margin-top: 1px; }

  /* ── MAIN ── */
  .main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; z-index: 1; }

  /* ── TOPBAR ── */
  .topbar {
    height: 62px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center;
    padding: 0 26px; gap: 16px; flex-shrink: 0;
    background: rgba(10,17,25,.88);
    backdrop-filter: blur(14px);
    position: relative;
    z-index: 20;
  }
  .topbar-brand {
    align-items: center;
    display: flex;
    gap: 12px;
    min-width: 245px;
    text-decoration: none;
  }
  .topbar-logo {
    align-items: center;
    color: var(--purple-lt);
    display: flex;
    height: 36px;
    justify-content: center;
    width: 36px;
  }
  .topbar-brand-title {
    display: block;
    color: #f1f3fb;
    font-size: 19px;
    font-weight: 700;
    letter-spacing: -.015em;
    line-height: 1.05;
  }
  .topbar-brand-sub {
    display: block;
    color: #a4a9b8;
    font-size: 12px;
    line-height: 1.15;
    margin-top: 2px;
  }
  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #8991a3;
    font-size: 14px;
    min-width: 240px;
  }
  .breadcrumb .active { color: #dfe3ec; font-weight: 500; }
  .bc-sep { color: #5f6878; }
  .topbar-spacer { flex: 1; }
  .workspace-switcher {
    align-items: center;
    background: rgba(255,255,255,.035);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    display: flex;
    gap: 10px;
    min-height: 42px;
    min-width: 208px;
    padding: 7px 12px;
    text-decoration: none;
  }
  .workspace-switcher:hover,
  .topbar-search:focus-within {
    border-color: rgba(168,146,248,.28);
    background: rgba(255,255,255,.05);
  }
  .workspace-icon {
    align-items: center;
    background: rgba(45,216,145,.12);
    border: 1px solid rgba(45,216,145,.18);
    border-radius: 6px;
    color: #52d8b0;
    display: flex;
    height: 24px;
    justify-content: center;
    width: 24px;
  }
  .workspace-copy {
    display: grid;
    gap: 1px;
    min-width: 0;
  }
  .workspace-name {
    color: #f0f2f7;
    font-size: 13px;
    font-weight: 600;
    line-height: 1.05;
  }
  .workspace-env {
    color: #8d94a8;
    font-size: 12px;
  }
  .workspace-chevron { margin-left: auto; color: #b8bdc8; }
  .topbar-search {
    align-items: center;
    background: rgba(255,255,255,.035);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    display: flex;
    gap: 9px;
    height: 38px;
    min-width: 292px;
    padding: 0 10px 0 13px;
  }
  .topbar-search input {
    background: transparent;
    border: 0;
    color: var(--text);
    flex: 1;
    font-size: 13px;
    min-width: 0;
    outline: none;
  }
  .topbar-search input::placeholder { color: #777d8f; }
  .topbar-kbd {
    background: rgba(255,255,255,.055);
    border-radius: 5px;
    color: #9da3b3;
    font-family: var(--mono);
    font-size: 10px;
    padding: 3px 6px;
  }
  .topbar-actions { display: flex; align-items: center; gap: 14px; margin-left: 10px; }
  .icon-btn {
    width: 30px; height: 30px; border: 0;
    border-radius: 999px; background: transparent; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    color: #d7dbe6; position: relative; transition: all .12s;
  }
  .icon-btn:hover { color: #fff; background: rgba(255,255,255,.055); }
  .notif-dot {
    position: absolute; top: -4px; right: -3px;
    min-width: 18px; height: 18px; border-radius: 999px;
    align-items: center; display: flex; justify-content: center;
    background: var(--purple-lt);
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    box-shadow: 0 0 10px rgba(168,146,248,.5);
  }
  .topbar-profile {
    align-items: center;
    color: inherit;
    display: flex;
    gap: 10px;
    text-decoration: none;
  }
  .topbar-avatar {
    align-items: center;
    background: linear-gradient(135deg, #6867d9, #8d79f0);
    border-radius: 999px;
    color: #fff;
    display: flex;
    font-size: 13px;
    font-weight: 700;
    height: 36px;
    justify-content: center;
    width: 36px;
  }
  .topbar-profile-copy { display: grid; gap: 1px; }
  .topbar-profile-name { color: #f0f2f7; font-size: 13px; font-weight: 600; }
  .topbar-profile-role { color: #8d94a8; font-size: 12px; }
  .topbar-profile-chevron { color: #b8bdc8; margin-left: 4px; }

  /* ── CONTENT ── */
  .content { flex: 1; overflow: auto; padding: 20px 22px; animation: fadeUp .2s ease; }

  /* ── [1] PAGE HEADER — pas de KPI en premier ── */
  .page-header { margin-bottom: 16px; }
  .page-title { font-size: 22px; font-weight: 700; letter-spacing: -.015em; color: #eeeef8; margin-bottom: 3px; }
  .page-sub { font-size: 12.5px; color: var(--text-muted); }
  .overview-page {
    display: grid;
    gap: 14px;
  }
  .overview-hero {
    background:
      linear-gradient(135deg, rgba(124,109,240,.16), rgba(54,184,246,.06)),
      var(--bg-panel);
    border: 1px solid var(--purple-brd);
    border-radius: var(--radius-lg);
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.4fr) minmax(280px, .6fr);
    overflow: hidden;
    padding: 18px 20px;
  }
  .overview-kicker {
    color: var(--purple-lt);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    margin-bottom: 8px;
    text-transform: uppercase;
  }
  .overview-title {
    color: #eeeef8;
    font-size: 28px;
    font-weight: 700;
    line-height: 1.08;
    margin-bottom: 10px;
  }
  .overview-copy {
    color: var(--text-dim);
    font-size: 13px;
    line-height: 1.55;
    max-width: 760px;
  }
  .overview-promises {
    display: grid;
    gap: 7px;
    margin-top: 14px;
  }
  .overview-promise {
    align-items: center;
    color: var(--text);
    display: flex;
    font-size: 12.5px;
    gap: 8px;
  }
  .overview-promise span:first-child {
    border-radius: 999px;
    height: 7px;
    width: 7px;
  }
  .overview-actor-card {
    align-self: stretch;
    background: rgba(10,10,20,.38);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    display: grid;
    gap: 9px;
    padding: 13px;
  }
  .overview-actor-card h2,
  .overview-panel-title {
    color: #eeeef8;
    font-size: 13px;
    font-weight: 700;
    margin: 0;
  }
  .overview-actor-meta {
    display: grid;
    gap: 6px;
  }
  .overview-actor-meta div {
    display: grid;
    gap: 2px;
  }
  .overview-actor-meta dt,
  .overview-metric-label,
  .overview-item-meta,
  .overview-demo-command {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10px;
  }
  .overview-actor-meta dd {
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 11px;
    margin: 0;
    word-break: break-word;
  }
  .overview-role-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .overview-chip {
    border: 1px solid var(--border);
    border-radius: 999px;
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 9.5px;
    padding: 3px 7px;
  }
  .overview-chip.ok { background: var(--green-dim); border-color: var(--green-brd); color: var(--green); }
  .overview-chip.warn { background: var(--orange-dim); border-color: var(--orange-brd); color: var(--orange); }
  .overview-chip.info { background: var(--sky-dim); border-color: var(--sky-brd); color: var(--sky); }
  .overview-chip.purple { background: var(--purple-dim); border-color: var(--purple-brd); color: var(--purple-lt); }
  .overview-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .overview-workflow-card,
  .overview-panel,
  .overview-demo-card,
  .overview-shortcuts {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .overview-workflow-card {
    color: inherit;
    display: grid;
    gap: 12px;
    min-height: 180px;
    padding: 14px;
    text-decoration: none;
    transition: border-color .14s, transform .14s;
  }
  .overview-workflow-card:hover {
    border-color: var(--purple-brd);
    transform: translateY(-1px);
  }
  .overview-card-head {
    align-items: center;
    display: flex;
    gap: 9px;
  }
  .overview-icon {
    align-items: center;
    border-radius: 9px;
    display: flex;
    height: 32px;
    justify-content: center;
    width: 32px;
  }
  .overview-icon.purple { background: var(--purple-dim); border: 1px solid var(--purple-brd); color: var(--purple-lt); }
  .overview-icon.orange { background: var(--orange-dim); border: 1px solid var(--orange-brd); color: var(--orange); }
  .overview-icon.green { background: var(--green-dim); border: 1px solid var(--green-brd); color: var(--green); }
  .overview-card-title {
    color: #eeeef8;
    font-size: 14px;
    font-weight: 700;
  }
  .overview-card-body {
    color: var(--text-muted);
    font-size: 12px;
    line-height: 1.5;
  }
  .overview-metric {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 10px;
  }
  .overview-metric-value {
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    text-align: right;
  }
  .overview-row {
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
  .overview-panel-head {
    align-items: center;
    border-bottom: 1px solid var(--border2);
    display: flex;
    gap: 8px;
    justify-content: space-between;
    padding: 12px 14px;
  }
  .overview-panel-body {
    display: grid;
    gap: 8px;
    padding: 12px 14px 14px;
  }
  .overview-item {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    display: grid;
    gap: 5px;
    padding: 10px;
  }
  .overview-item strong {
    color: var(--text);
    font-size: 12px;
  }
  .overview-item p {
    color: var(--text-muted);
    font-size: 11.5px;
    line-height: 1.45;
    margin: 0;
  }
  .overview-error {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }
  .overview-empty {
    background: rgba(255,255,255,.02);
    border-style: dashed;
  }
  .overview-demo-card {
    align-items: center;
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 14px;
  }
  .overview-demo-command {
    background: #080811;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--green);
    padding: 9px 10px;
  }
  .overview-shortcuts {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    padding: 10px;
  }
  .overview-shortcut {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    font-size: 11px;
    padding: 9px;
    text-align: center;
    text-decoration: none;
    transition: border-color .14s, color .14s;
  }
  .overview-shortcut:hover {
    border-color: var(--purple-brd);
    color: var(--purple-lt);
  }

  /* ── [2] DECISION INBOX en hero ── */
  .inbox-hero {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    margin-bottom: 14px;
    overflow: hidden;
  }
  .inbox-hero-head {
    padding: 14px 18px;
    border-bottom: 1px solid var(--border2);
    display: flex; align-items: center; gap: 10px;
  }
  .inbox-hero-badge {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px;
    background: var(--orange-dim);
    border: 1px solid var(--orange-brd);
    flex-shrink: 0;
  }
  .inbox-hero-title { font-size: 13px; font-weight: 700; color: var(--text); }
  .inbox-hero-sub { font-size: 10.5px; color: var(--text-muted); margin-top: 1px; }
  .inbox-count-chip {
    margin-left: auto;
    background: var(--orange-dim); color: var(--orange);
    border: 1px solid var(--orange-brd);
    border-radius: 20px; font-family: var(--mono);
    font-size: 10px; font-weight: 700;
    padding: 2px 10px; letter-spacing: .04em;
  }
  .inbox-hero-body {
    display: grid; grid-template-columns: 1fr 1fr 1fr;
  }
  .inbox-item-hero {
    padding: 14px 16px;
    border-right: 1px solid var(--border2);
    cursor: pointer; transition: background .12s;
    position: relative;
  }
  .inbox-item-hero:last-child { border-right: none; }
  .inbox-item-hero:hover { background: rgba(255,255,255,.025); }
  .inbox-item-hero.selected { background: rgba(245,144,64,.04); }
  .inbox-item-hero.selected::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--orange), transparent);
  }
  .iih-badge {
    display: inline-flex; align-items: center;
    font-family: var(--mono); font-size: 9px; font-weight: 600;
    padding: 2px 7px; border-radius: 4px; margin-bottom: 7px;
    border: 1px solid transparent; letter-spacing: .06em;
  }
  .iih-badge.review  { color: var(--orange); background: var(--orange-dim); border-color: var(--orange-brd); }
  .iih-badge.blocked { color: var(--red);    background: var(--red-dim);    border-color: var(--red-brd); }
  .iih-badge.gap     { color: var(--sky);    background: var(--sky-dim);    border-color: var(--sky-brd); }
  .iih-title { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 3px; line-height: 1.35; }
  .iih-sub { font-size: 10px; color: var(--text-muted); font-family: var(--mono); }
  .iih-actions { display: flex; gap: 6px; margin-top: 10px; }
  .iih-btn-primary {
    background: linear-gradient(135deg, #5c4ed4, #7c6df0);
    color: #fff; border: none; border-radius: 5px;
    padding: 5px 12px; font-size: 11px; font-weight: 600;
    cursor: pointer; transition: all .13s;
    box-shadow: 0 2px 8px rgba(92,78,212,.3);
  }
  .iih-btn-primary:hover { box-shadow: 0 3px 12px rgba(92,78,212,.45); transform: translateY(-1px); }
  .iih-btn-sec {
    background: transparent; color: var(--text-dim);
    border: 1px solid var(--border);
    border-radius: 5px; padding: 5px 10px;
    font-size: 11px; font-weight: 500; cursor: pointer; transition: all .13s;
  }
  .iih-btn-sec:hover { border-color: rgba(255,255,255,.14); background: rgba(255,255,255,.04); }

  /* ── THREE-COL below inbox ── */
  .three-col {
    display: grid;
    grid-template-columns: 1fr 1fr 280px;
    gap: 12px; margin-bottom: 14px;
  }

  /* ── [1] KPI STRIP — compact, secondary ── */
  .kpi-strip {
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 8px; margin-bottom: 14px;
  }
  .kpi-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 11px 14px;
    position: relative; overflow: hidden;
    cursor: pointer; transition: border-color .14s;
  }
  .kpi-card:hover { border-color: rgba(255,255,255,.12); }
  .kpi-card::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 2px; border-radius: 10px 10px 0 0;
  }
  .kpi-card.ok::after     { background: linear-gradient(90deg, var(--green), transparent); }
  .kpi-card.danger::after { background: linear-gradient(90deg, var(--red), transparent); }
  .kpi-card.info::after   { background: linear-gradient(90deg, var(--sky), transparent); }
  .kpi-card.purple::after { background: linear-gradient(90deg, var(--purple), transparent); }
  .kpi-card.warn::after   { background: linear-gradient(90deg, var(--orange), transparent); }
  .kpi-label {
    font-size: 9.5px; color: var(--text-muted);
    letter-spacing: .07em; margin-bottom: 5px;
    text-transform: uppercase; font-family: var(--mono);
    display: flex; align-items: center; justify-content: space-between;
  }
  /* [1] Flèche de drill-down discrete */
  .kpi-drill { color: var(--text-faint); opacity: 0; transition: opacity .14s; font-size: 9px; }
  .kpi-card:hover .kpi-drill { opacity: 1; }
  .kpi-value { font-size: 22px; font-family: var(--mono); font-weight: 600; line-height: 1; margin-bottom: 3px; }
  .kpi-delta { font-size: 9.5px; color: var(--text-faint); font-family: var(--mono); }
  .kpi-card.ok .kpi-value     { color: var(--green); }
  .kpi-card.danger .kpi-value { color: var(--red); }
  .kpi-card.info .kpi-value   { color: var(--sky); }
  .kpi-card.purple .kpi-value { color: var(--purple-lt); }
  .kpi-card.warn .kpi-value   { color: var(--orange); }

  /* ── PANEL ── */
  .panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .panel-head {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border2);
    display: flex; align-items: center; justify-content: space-between;
  }
  .panel-title {
    font-size: 10.5px; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; color: var(--text-dim);
    display: flex; align-items: center; gap: 7px;
  }
  .panel-accent { width: 3px; height: 12px; border-radius: 2px; }
  .panel-btn {
    font-family: var(--mono); font-size: 10px; color: var(--purple);
    cursor: pointer; letter-spacing: .04em;
    border: 1px solid var(--purple-brd);
    border-radius: 5px; padding: 3px 8px;
    background: transparent; transition: all .12s;
  }
  .panel-btn:hover { background: var(--purple-dim); border-color: var(--purple); }

  /* ── [5] CONTROL MAP — actionnable ── */
  .control-map-wrap { padding: 14px 14px 10px; }
  .flow-container { display: flex; flex-direction: column; gap: 10px; width: 100%; }
  .flow-row { display: flex; align-items: stretch; gap: 0; justify-content: center; }
  .flow-node {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    min-width: 100px; text-align: center;
    position: relative; transition: border-color .15s, box-shadow .15s, transform .15s;
    cursor: pointer; flex: 1;
  }
  .flow-node:hover {
    border-color: var(--purple-brd);
    box-shadow: var(--glow-purple);
    transform: translateY(-1px);
  }
  /* [5] Nœud actif (sélectionné) */
  .flow-node.fn-active {
    border-color: var(--purple-brd);
    box-shadow: var(--glow-purple);
    background: var(--purple-dim);
  }
  /* [5] Badge de statut sur le nœud */
  .fn-status {
    position: absolute; top: -5px; right: -5px;
    font-family: var(--mono); font-size: 8px; font-weight: 700;
    padding: 1px 5px; border-radius: 4px; letter-spacing: .05em;
    border: 1px solid transparent;
  }
  .fn-status.ok     { color: var(--green);  background: var(--green-dim);  border-color: var(--green-brd); }
  .fn-status.warn   { color: var(--orange); background: var(--orange-dim); border-color: var(--orange-brd); }
  .fn-status.danger { color: var(--red);    background: var(--red-dim);    border-color: var(--red-brd); }
  .fn-status.info   { color: var(--sky);    background: var(--sky-dim);    border-color: var(--sky-brd); }
  .flow-node .fn-dot { width: 7px; height: 7px; border-radius: 50%; margin: 0 auto 6px; }
  .flow-node .fn-label { font-size: 11px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
  .flow-node .fn-sub { font-size: 9px; color: var(--text-muted); font-family: var(--mono); }
  /* [5] Bouton action au survol */
  .fn-action {
    margin-top: 6px;
    font-family: var(--mono); font-size: 9px; color: var(--purple-lt);
    opacity: 0; transition: opacity .14s;
    letter-spacing: .04em;
  }
  .flow-node:hover .fn-action { opacity: 1; }
  .flow-arrow {
    display: flex; align-items: center;
    padding: 0 4px; color: var(--text-faint); flex-shrink: 0;
  }
  /* [5] Connecteur vertical avec statut */
  .flow-v-connector {
    display: flex; align-items: center; justify-content: center;
    gap: 8px; padding: 2px 0;
  }
  .fvc-line {
    height: 20px; width: 1px;
    background: linear-gradient(to bottom, var(--border), transparent);
  }
  .fvc-pill {
    font-family: var(--mono); font-size: 9px; font-weight: 600;
    padding: 2px 8px; border-radius: 20px; letter-spacing: .05em;
  }
  .fvc-pill.enforced {
    color: var(--green); background: var(--green-dim); border: 1px solid var(--green-brd);
  }
  .fvc-pill.pending {
    color: var(--orange); background: var(--orange-dim); border: 1px solid var(--orange-brd);
  }

  /* [5] Tooltip contextuel au clic */
  .map-tooltip {
    margin-top: 10px;
    background: var(--bg-card);
    border: 1px solid var(--purple-brd);
    border-radius: var(--radius);
    padding: 10px 12px;
    animation: fadeUp .15s ease;
  }
  .mt-title { font-size: 11px; font-weight: 600; color: var(--purple-lt); margin-bottom: 6px; }
  .mt-row {
    display: flex; justify-content: space-between;
    font-size: 10.5px; color: var(--text-muted);
    padding: 3px 0; border-bottom: 1px solid var(--border2);
    font-family: var(--mono);
  }
  .mt-row:last-child { border-bottom: none; }
  .mt-val { color: var(--text); }
  .mt-actions { display: flex; gap: 6px; margin-top: 8px; }
  .mt-btn {
    flex: 1; font-family: var(--mono); font-size: 10px;
    padding: 5px 0; border-radius: 5px; cursor: pointer;
    text-align: center; transition: all .12s;
    font-weight: 600; letter-spacing: .04em;
  }
  .mt-btn.primary {
    background: var(--purple-dim); color: var(--purple-lt);
    border: 1px solid var(--purple-brd);
  }
  .mt-btn.primary:hover { background: rgba(124,109,240,.18); }
  .mt-btn.ghost { background: transparent; color: var(--text-muted); border: 1px solid var(--border); }
  .mt-btn.ghost:hover { border-color: rgba(255,255,255,.14); color: var(--text-dim); }

  /* ── [3] BLOCKS / CODE — section visible ── */
  .blocks-code-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px 8px;
  }
  .bc-toggle {
    display: flex; gap: 2px;
    background: rgba(255,255,255,.04);
    border: 1px solid var(--border);
    border-radius: 6px; padding: 2px;
  }
  .bc-btn {
    font-family: var(--mono); font-size: 10px; letter-spacing: .04em;
    padding: 4px 11px; border-radius: 4px; cursor: pointer;
    border: none; background: transparent; color: var(--text-muted);
    transition: all .13s; font-weight: 500;
  }
  .bc-btn.active {
    background: var(--purple-dim); color: var(--purple-lt);
    border: 1px solid var(--purple-brd);
  }
  .bc-actions { display: flex; gap: 5px; }
  .bc-action-btn {
    display: flex; align-items: center; gap: 5px;
    font-family: var(--mono); font-size: 10px;
    padding: 4px 10px; border-radius: 5px; cursor: pointer;
    border: 1px solid var(--border); background: transparent;
    color: var(--text-muted); transition: all .12s;
  }
  .bc-action-btn:hover { border-color: rgba(255,255,255,.14); color: var(--text-dim); background: rgba(255,255,255,.04); }
  .bc-action-btn.run {
    background: var(--green-dim); color: var(--green);
    border-color: var(--green-brd);
  }
  .bc-action-btn.run:hover { background: rgba(45,216,145,.14); }

  /* Blocks view */
  .blocks-view { padding: 10px 14px 12px; }
  .block-row {
    display: flex; align-items: stretch; gap: 8px;
    margin-bottom: 6px;
    animation: rowIn .15s ease;
  }
  .block-step-num {
    width: 22px; flex-shrink: 0;
    display: flex; align-items: flex-start; justify-content: center;
    padding-top: 9px;
    font-family: var(--mono); font-size: 9px; color: var(--text-faint);
    font-weight: 600;
  }
  .block-card {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 11px;
    display: flex; align-items: center; gap: 10px;
    cursor: pointer; transition: border-color .12s;
  }
  .block-card:hover { border-color: var(--purple-brd); }
  .block-card.bc-when  { border-left: 2px solid var(--purple); }
  .block-card.bc-check { border-left: 2px solid var(--sky); }
  .block-card.bc-then  { border-left: 2px solid var(--orange); }
  .block-card.bc-prove { border-left: 2px solid var(--green); }
  .block-type {
    font-family: var(--mono); font-size: 9px; font-weight: 600;
    letter-spacing: .08em; min-width: 40px;
  }
  .bc-when .block-type  { color: var(--purple-lt); }
  .bc-check .block-type { color: var(--sky); }
  .bc-then .block-type  { color: var(--orange); }
  .bc-prove .block-type { color: var(--green); }
  .block-content { flex: 1; }
  .block-main { font-size: 11px; font-weight: 500; color: var(--text); margin-bottom: 2px; }
  .block-detail { font-size: 9.5px; color: var(--text-muted); font-family: var(--mono); }
  .block-status {
    font-family: var(--mono); font-size: 9px; font-weight: 600;
    padding: 2px 7px; border-radius: 4px;
  }
  .bs-ok     { color: var(--green);  background: var(--green-dim);  border: 1px solid var(--green-brd); }
  .bs-req    { color: var(--red);    background: var(--red-dim);    border: 1px solid var(--red-brd); }
  .bs-active { color: var(--orange); background: var(--orange-dim); border: 1px solid var(--orange-brd); }

  /* Compile/sim bar */
  .sim-bar {
    margin: 0 14px 12px;
    background: var(--green-dim);
    border: 1px solid var(--green-brd);
    border-radius: var(--radius-sm);
    padding: 7px 12px;
    font-family: var(--mono); font-size: 10px; color: var(--green);
    display: flex; align-items: center; gap: 8px;
  }

  /* [3] Code preview inline */
  .code-preview {
    padding: 10px 14px 12px;
    background: var(--bg);
    border-top: 1px solid var(--border2);
  }
  .code-block { padding: 0; font-family: var(--mono); font-size: 12px; line-height: 1.75; }
  .code-line {
    display: flex; align-items: baseline;
    padding: 0 4px; transition: background .1s;
    white-space: pre;
  }
  .code-line:hover { background: rgba(255,255,255,.025); }
  .line-num {
    width: 28px; flex-shrink: 0;
    color: var(--text-faint); font-size: 10.5px;
    text-align: right; padding-right: 14px;
    user-select: none; line-height: 1.75;
  }
  .code-content { color: #8888b0; }
  .kw   { color: #7060e8; }
  .kw2  { color: #9278f0; }
  .str  { color: #7ddba0; }
  .val  { color: #f08030; }
  .cmt  { color: #38385a; }
  .req  { color: #e03050; font-weight: 600; }
  .fn   { color: #2dce88; }
  .sym  { color: #50507a; }

  /* ── [4] TEMPLATES ── */
  .templates-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 8px; padding: 12px 14px;
  }
  .tmpl-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 14px;
    cursor: pointer; transition: all .14s;
    position: relative; overflow: hidden;
  }
  .tmpl-card:hover { border-color: var(--purple-brd); background: var(--purple-dim); }
  .tmpl-card::before {
    content: '';
    position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    border-radius: 10px 0 0 10px;
  }
  .tmpl-card.tc-review::before  { background: var(--orange); }
  .tmpl-card.tc-deny::before    { background: var(--red); }
  .tmpl-card.tc-evidence::before{ background: var(--green); }
  .tmpl-card.tc-scope::before   { background: var(--sky); }
  .tmpl-card.tc-approval::before{ background: var(--purple); }
  .tmpl-card.tc-risk::before    { background: #e879f9; }
  .tmpl-name { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 3px; }
  .tmpl-desc { font-size: 10px; color: var(--text-muted); line-height: 1.4; margin-bottom: 8px; }
  .tmpl-meta { display: flex; align-items: center; gap: 6px; }
  .tmpl-tag {
    font-family: var(--mono); font-size: 9px;
    padding: 1px 6px; border-radius: 4px;
    color: var(--text-muted); background: rgba(255,255,255,.05);
    border: 1px solid var(--border2);
  }
  .tmpl-use-btn {
    margin-left: auto;
    font-family: var(--mono); font-size: 9px; font-weight: 600;
    padding: 3px 8px; border-radius: 4px; cursor: pointer;
    background: var(--purple-dim); color: var(--purple-lt);
    border: 1px solid var(--purple-brd); letter-spacing: .04em;
    opacity: 0; transition: opacity .13s;
  }
  .tmpl-card:hover .tmpl-use-btn { opacity: 1; }

  /* ── RIGHT PANEL — decision active ── */
  .decision-panel { display: flex; flex-direction: column; gap: 10px; }

  .active-decision-card {
    background: var(--bg-panel);
    border: 1px solid var(--orange-brd);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .adc-head {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border2);
    background: var(--orange-dim);
    display: flex; align-items: center; gap: 8px;
  }
  .adc-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--orange); box-shadow: var(--glow-orange);
    animation: pulse 2s ease-in-out infinite; flex-shrink: 0;
  }
  .adc-title { font-size: 11.5px; font-weight: 700; color: var(--text); flex: 1; }
  .adc-body { padding: 12px 14px; }
  .adc-desc { font-size: 11px; color: var(--text-muted); line-height: 1.55; margin-bottom: 12px; }
  .adc-meta-row {
    display: flex; justify-content: space-between;
    font-size: 10.5px; padding: 4px 0;
    border-bottom: 1px solid var(--border2);
    font-family: var(--mono);
  }
  .adc-meta-row:last-of-type { border-bottom: none; margin-bottom: 10px; }
  .adc-meta-key { color: var(--text-muted); }
  .adc-meta-val { color: var(--text); }
  .adc-buttons { display: flex; gap: 6px; margin-top: 4px; }
  .btn-primary {
    background: linear-gradient(135deg, #5c4ed4, #7c6df0);
    color: #fff; border: none; border-radius: var(--radius-sm);
    padding: 7px 14px; font-size: 12px; font-weight: 600;
    cursor: pointer; transition: all .14s;
    box-shadow: 0 2px 10px rgba(92,78,212,.32);
  }
  .btn-primary:hover { box-shadow: 0 3px 14px rgba(92,78,212,.48); transform: translateY(-1px); }
  .btn-secondary {
    background: transparent; color: var(--text-dim);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 7px 12px; font-size: 12px; font-weight: 500;
    cursor: pointer; transition: all .14s;
  }
  .btn-secondary:hover { border-color: rgba(255,255,255,.14); background: rgba(255,255,255,.04); }

  /* ── WORKSPACE ── */
  .workspace-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; }
  .ws-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 8px; cursor: pointer; transition: all .14s; text-align: center;
  }
  .ws-card:hover { border-color: var(--purple-brd); background: var(--purple-dim); }
  .ws-dot { width: 7px; height: 7px; border-radius: 50%; margin: 0 auto 6px; }
  .ws-name { font-size: 10.5px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
  .ws-sub { font-size: 9px; color: var(--text-muted); font-family: var(--mono); letter-spacing: .04em; }

  /* ── TAG ── */
  .tag {
    display: inline-flex; align-items: center;
    font-family: var(--mono); font-size: 9px; font-weight: 600;
    letter-spacing: .06em; padding: 2px 7px;
    border-radius: 4px; white-space: nowrap; border: 1px solid transparent;
  }
  .tag-ok     { color: var(--green);    background: var(--green-dim);  border-color: var(--green-brd); }
  .tag-danger { color: var(--red);      background: var(--red-dim);    border-color: var(--red-brd); }
  .tag-warn   { color: var(--orange);   background: var(--orange-dim); border-color: var(--orange-brd); }
  .tag-info   { color: var(--sky);      background: var(--sky-dim);    border-color: var(--sky-brd); }
  .tag-purple { color: var(--purple-lt);background: var(--purple-dim); border-color: var(--purple-brd); }

  /* ── POLICY STUDIO ── */
  .studio-layout { display: grid; grid-template-columns: 260px 1fr 280px; gap: 0; height: 100%; }

  .policy-list-pane {
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column;
    background: var(--bg-panel);
    height: calc(100vh - 48px); overflow: hidden;
  }
  .pane-head { padding: 14px 14px 10px; border-bottom: 1px solid var(--border2); flex-shrink: 0; }
  .pane-title { font-size: 14px; font-weight: 700; color: #eeeef8; margin-bottom: 10px; }
  .search-box {
    display: flex; align-items: center; gap: 7px;
    background: rgba(255,255,255,.04); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0 10px; height: 30px;
    transition: border-color .14s;
  }
  .search-box:focus-within { border-color: var(--purple-brd); }
  .search-box input {
    background: none; border: none; outline: none;
    color: var(--text); font-size: 11.5px;
    font-family: var(--mono); width: 100%; letter-spacing: .02em;
  }
  .search-box input::placeholder { color: var(--text-faint); }

  .policy-list-scroll { flex: 1; overflow: auto; padding: 8px 8px; }
  .policy-section-label {
    font-size: 9px; color: var(--text-faint); letter-spacing: .12em;
    text-transform: uppercase; font-family: var(--mono);
    padding: 7px 6px 3px; font-weight: 600;
  }
  .policy-entry {
    display: flex; align-items: center; gap: 7px;
    padding: 7px 8px; border-radius: 6px;
    cursor: pointer; transition: all .12s;
    margin-bottom: 1px; border: 1px solid transparent;
  }
  .policy-entry:hover { background: rgba(255,255,255,.04); }
  .policy-entry.active { background: var(--purple-dim); border-color: var(--purple-brd); }
  .pe-name { font-size: 11px; font-weight: 500; flex: 1; color: var(--text); }
  .pe-badge { font-family: var(--mono); font-size: 9px; color: var(--text-muted); letter-spacing: .05em; }
  .pe-badge.lib  { color: var(--sky); }
  .pe-badge.tmpl { color: var(--orange); }

  .new-policy-sidebar {
    margin: 8px;
    display: flex; align-items: center; justify-content: center; gap: 6px;
    background: var(--purple-dim); border: 1px dashed var(--purple-brd);
    color: var(--purple-lt); border-radius: var(--radius-sm);
    padding: 8px; font-size: 12px; font-weight: 600;
    cursor: pointer; transition: all .14s; flex-shrink: 0;
  }
  .new-policy-sidebar:hover { background: rgba(124,109,240,.16); }

  /* Editor pane */
  .editor-pane { display: flex; flex-direction: column; height: calc(100vh - 48px); overflow: hidden; }
  .editor-tabs {
    display: flex; align-items: center;
    background: var(--bg-panel); border-bottom: 1px solid var(--border);
    padding: 0; flex-shrink: 0; height: 38px;
  }
  .editor-tab {
    display: flex; align-items: center; gap: 6px;
    padding: 0 14px; height: 100%;
    font-family: var(--mono); font-size: 11px;
    color: var(--text-muted); cursor: pointer;
    border-right: 1px solid var(--border2);
    transition: all .12s; white-space: nowrap;
  }
  .editor-tab.active { color: var(--text); background: rgba(255,255,255,.03); border-bottom: 1px solid var(--purple); }
  .tab-toggle {
    display: flex; align-items: center; gap: 2px;
    margin-left: auto; margin-right: 10px;
    background: rgba(255,255,255,.04); border: 1px solid var(--border);
    border-radius: 5px; padding: 2px;
  }
  .ttg-btn {
    font-family: var(--mono); font-size: 9.5px; letter-spacing: .05em;
    padding: 3px 10px; border-radius: 3px; cursor: pointer;
    border: none; background: transparent; color: var(--text-muted); transition: all .12s;
  }
  .ttg-btn.active { background: var(--purple-dim); color: var(--purple-lt); border: 1px solid var(--purple-brd); }

  .editor-scroll { flex: 1; overflow: auto; background: var(--bg); }
  .policy-structure-bar {
    background: var(--bg-panel2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 9px 12px;
    margin: 12px 16px 0;
    display: flex; align-items: center; gap: 0; flex-shrink: 0;
  }
  .ps-step {
    font-family: var(--mono); font-size: 10.5px; font-weight: 600;
    letter-spacing: .08em; color: var(--text-dim);
    padding: 4px 12px; border-radius: 5px;
    cursor: pointer; transition: all .15s; flex: 1; text-align: center;
  }
  .ps-step.active { background: var(--purple-dim); color: var(--purple-lt); }
  .ps-arrow { color: var(--text-faint); font-size: 13px; flex-shrink: 0; }

  .compile-banner {
    margin: 0 16px 0;
    background: var(--green-dim); border: 1px solid var(--green-brd);
    border-radius: var(--radius-sm); padding: 7px 12px;
    font-family: var(--mono); font-size: 10px; color: var(--green);
    display: flex; align-items: center; gap: 8px;
  }
  .simulation-pane {
    background: var(--bg-panel2); border-top: 1px solid var(--border);
    padding: 12px 16px; flex-shrink: 0;
  }
  .sim-title { font-size: 10.5px; font-weight: 600; color: var(--text-dim); margin-bottom: 8px; letter-spacing: .04em; }
  .sim-line {
    display: flex; align-items: center; gap: 7px;
    font-family: var(--mono); font-size: 10.5px; color: var(--text-muted);
    margin-bottom: 4px; line-height: 1.4;
  }
  .sim-ok   { color: var(--green); }
  .sim-warn { color: var(--orange); }
  .sim-arrow { color: var(--purple-lt); }

  /* Inspector pane */
  .inspector-pane {
    border-left: 1px solid var(--border);
    display: flex; flex-direction: column;
    height: calc(100vh - 48px); overflow: auto;
    background: var(--bg-panel);
  }
  .insp-section { padding: 14px 14px; border-bottom: 1px solid var(--border2); }
  .insp-title { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 10px; }
  .insp-subtitle { font-size: 10.5px; font-weight: 600; color: var(--text-dim); margin-bottom: 8px; letter-spacing: .04em; }

  .dfm-node {
    background: var(--bg-panel2); border: 1px solid var(--border);
    border-radius: 8px; padding: 7px 9px; text-align: center;
  }
  .dfm-dot { width: 7px; height: 7px; border-radius: 50%; margin: 0 auto 4px; }
  .dfm-label { font-size: 11px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
  .dfm-sub { font-size: 9px; color: var(--text-muted); font-family: var(--mono); }

  .summary-text { font-size: 11px; color: var(--text-muted); line-height: 1.6; }

  .impact-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; border-bottom: 1px solid var(--border2); font-size: 11px;
  }
  .impact-row:last-child { border-bottom: none; }
  .impact-label { color: var(--text-muted); }
  .impact-val { font-family: var(--mono); font-size: 11.5px; font-weight: 600; color: var(--text); }

  .review-required-card {
    display: flex; align-items: flex-start; gap: 9px;
    background: rgba(245,144,64,.06); border: 1px solid var(--orange-brd);
    border-radius: var(--radius-sm); padding: 9px 11px; margin-top: 8px;
  }
  .rrc-title { font-size: 11.5px; font-weight: 600; color: var(--orange); margin-bottom: 2px; }
  .rrc-sub { font-size: 10px; color: var(--text-muted); }

  .insp-actions {
    padding: 10px 14px; border-top: 1px solid var(--border);
    display: flex; gap: 6px; flex-shrink: 0;
    background: var(--bg-panel); margin-top: auto;
    position: sticky; bottom: 0;
  }
  .btn-small {
    border: 1px solid var(--border); background: transparent;
    color: var(--text-dim); border-radius: var(--radius-sm);
    padding: 6px 10px; font-size: 11px; font-weight: 500;
    cursor: pointer; transition: all .12s; flex: 1; text-align: center;
  }
  .btn-small:hover { border-color: rgba(255,255,255,.13); background: rgba(255,255,255,.04); }
  .btn-submit {
    background: linear-gradient(135deg, #5c4ed4, #7c6df0);
    color: #fff; border: none; border-radius: var(--radius-sm);
    padding: 6px 12px; font-size: 11px; font-weight: 700;
    cursor: pointer; transition: all .14s; flex: 1.5; text-align: center;
    box-shadow: 0 2px 8px rgba(92,78,212,.3);
  }
  .btn-submit:hover { box-shadow: 0 3px 14px rgba(92,78,212,.5); transform: translateY(-1px); }

  .chip { font-family: var(--mono); font-size: 10px; font-weight: 600; padding: 4px 10px; border-radius: 5px; letter-spacing: .05em; border: 1px solid transparent; }
  .chip-draft   { color: var(--orange); background: var(--orange-dim); border-color: var(--orange-brd); }
  .chip-unsaved { color: var(--red);    background: var(--red-dim);    border-color: var(--red-brd); }
  .chip-active  { color: var(--green);     background: var(--green-dim);  border-color: var(--green-brd); }
  .chip-review  { color: var(--sky);       background: var(--sky-dim);    border-color: var(--sky-brd); }
  .chip-vio     { color: var(--purple-lt); background: var(--purple-dim); border-color: var(--purple-brd); }

  .flex { display: flex; }
  .items-center { align-items: center; }
  .gap-2 { gap: 8px; }
  .ml-auto { margin-left: auto; }
`;

/* ─── DATA ─── */
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
  { label: "OPEN REVIEWS",  value: "37",    delta: "↑ 5 pending",   cls: "warn" },
  { label: "EVIDENCE",      value: "214",   delta: "auditable",     cls: "ok" },
  { label: "ALERTS",        value: "9",     delta: "3 critical",    cls: "danger" },
];

/* [5] Nœuds avec statut et action */
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

/* [2] INBOX avec plus de détails */
const INBOX = [
  {
    badge: "review",  badgeLbl: "Review",
    title: "Action awaiting approval",
    sub: "Governance · 2h ago",
    desc: "The agent attempted to call an external API in production. Scope matches policy external_action_control — human review required before resume.",
    agent: "prod-agent-14",
    policy: "external-actions.agcp",
    since: "2h ago",
  },
  {
    badge: "blocked",  badgeLbl: "Blocked",
    title: "Missing required control",
    sub: "Policy enforcement · 14m ago",
    desc: "An action was blocked because access_grant.status is not 'active'. The agent needs a valid grant before proceeding with this operation.",
    agent: "data-pipeline-7",
    policy: "data-boundary.agcp",
    since: "14m ago",
  },
  {
    badge: "gap",  badgeLbl: "Gap",
    title: "No matching policy found",
    sub: "Coverage review · just now",
    desc: "A new action type 'model.fine_tune' has no matching policy. Coverage gap flagged — define a policy or explicitly allow in the default rule.",
    agent: "ml-ops-3",
    policy: "— none —",
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
  { cls: "sim-ok",    sym: "✓", text: "policy parsed" },
  { cls: "sim-ok",    sym: "✓", text: "24 matching decisions found" },
  { cls: "sim-ok",    sym: "✓", text: "17 would require review" },
  { cls: "sim-warn",  sym: "!", text: "2 policies overlap with this scope" },
  { cls: "sim-arrow", sym: "→", text: "evidence package: decision + checks + reviewer" },
];

/* ─── ICONS ─── */
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

/* ─── SIDEBAR ─── */
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

/* ─── CODE TOKEN ─── */
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
  if (status === "active" || status === "approved" || status === "allow") return "ok";
  if (status === "deny" || status === "rejected" || status === "cancelled") return "danger";
  if (status === "pending" || status === "require_human_review" || status === "draft") return "warn";
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
    sub: `${approval.requested_by_actor_type} · ${relativeTime(approval.created_at)}`,
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

/* ─── COMMAND VIEW ─── */
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

      {/* [1] Header — pas de KPI en premier */}
      <div className="page-header">
        <div className="page-title">Command Center</div>
        <div className="page-sub">Review agent decisions, policy coverage, and evidence across the workspace.</div>
      </div>

      {/* [2] DECISION INBOX en hero, première chose visible */}
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

      {/* [5] CONTROL MAP + [3] BLOCKS/CODE + decision details — 3 col */}
      <div className="three-col">

        {/* [5] Control Map — actionnable */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <div className="panel-head">
            <div className="panel-title">
              <span className="panel-accent" style={{ background: "var(--purple-lt)" }} />
              Control Map
            </div>
            <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>
              {activeMapNode !== null ? "Node selected ↓" : "Click a node to inspect"}
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
                      <div className="fn-action">→ {n.action}</div>
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
                      <div className="fn-action">→ {n.action}</div>
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

            {/* [5] Tooltip contextuel si nœud sélectionné */}
            {selectedNode && (
              <div className="map-tooltip">
                <div className="mt-title">{selectedNode.label} — details</div>
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

        {/* [3] Blocks / Code — bien visible, plein panel */}
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
                  DSL → 1 PolicyRule · 2 PolicyCheckSteps · evidence bundle
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

      {/* [1] KPIs — compact strip après l'opérationnel */}
      <div className="kpi-strip">
        {kpis.map(k => (
          <div key={k.label} className={`kpi-card ${k.cls}`}>
            <div className="kpi-label">
              {k.label}
              <span className="kpi-drill">→</span>
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

/* ════════════════════════════════════════════════════════════
   POLICY STUDIO — full replacement
   Sub-components: PS_Sidebar, PS_BlocksEditor, PS_CodeEditor,
   PS_SimConsole, PS_Inspector, PS_TemplateDrawer
   All scoped with "ps2-" prefix to avoid CSS collision with Command.
════════════════════════════════════════════════════════════ */

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

const CommandView = ({ data }) => {
  const pendingRuntimeApprovals = data.approvals.filter((approval) => approval.status === "pending").length;
  const pendingPolicyReviews = data.policyReviewRequests.filter((review) => review.status === "pending").length;
  const runtimeDecisionCount = data.runtimeActivity.filter((item) => item.type === "tool_call_decision").length;
  const activePolicies = data.policies.filter((policy) => policy.status === "active").length;
  const attentionItems = buildOverviewAttentionItems(data);
  const activityItems = buildOverviewActivityItems(data);

  return (
    <div className="content overview-page">
      <section className="overview-hero">
        <div>
          <div className="overview-kicker">Governance and evidence control plane</div>
          <h1 className="overview-title">Agent Governance Control Plane</h1>
          <p className="overview-copy">
            AGCP helps teams govern agents that run in external runtimes. It is a governance/evidence control plane,
            not an orchestrator, and not a legal compliance certification tool.
          </p>
          <div className="overview-promises">
            <div className="overview-promise">
              <span style={{ background: "var(--purple-lt)" }} />
              <strong>Know which agents exist.</strong>
            </div>
            <div className="overview-promise">
              <span style={{ background: "var(--orange)" }} />
              <strong>Control risky actions before they happen.</strong>
            </div>
            <div className="overview-promise">
              <span style={{ background: "var(--green)" }} />
              <strong>Prove decisions with policy, review, and evidence trails.</strong>
            </div>
          </div>
        </div>
        <CurrentActorCard data={data} />
      </section>

      <section className="overview-grid" aria-label="Primary governance workflows">
        <OverviewWorkflowCard
          tone="purple"
          icon="box"
          title="Know your agents"
          href="/agents"
          metrics={[
            {
              label: overviewEndpointCopy(data, "GET /agents"),
              value: overviewMetricValue({ data, errorLabel: "GET /agents", count: data.agents.length })
            },
            {
              label: "Environments returned",
              value: data.loading || overviewEndpointError(data, "GET /agents")
                ? "Unavailable"
                : compactCount(new Set(data.agents.map((agent) => agent.environment)).size)
            }
          ]}
        >
          Start from the Agent registry to see owners, environments, risk levels, activity, approvals, and evidence access.
        </OverviewWorkflowCard>

        <OverviewWorkflowCard
          tone="orange"
          icon="shield"
          title="Control risky actions"
          href="/policies"
          metrics={[
            {
              label: overviewEndpointCopy(data, "GET /policies"),
              value: data.loading || overviewEndpointError(data, "GET /policies")
                ? "Unavailable"
                : `${compactCount(activePolicies)} active`
            },
            {
              label: "Reviews waiting",
              value: data.loading
                ? "Loading"
                : compactCount(pendingRuntimeApprovals + pendingPolicyReviews)
            }
          ]}
        >
          Use Policy Studio, metadata pre-checks, Runtime Decisions, and Review Inbox to prepare reviewed governance decisions.
        </OverviewWorkflowCard>

        <OverviewWorkflowCard
          tone="green"
          icon="archive"
          title="Prove what happened"
          href="/evidence"
          metrics={[
            {
              label: "Runtime decisions",
              value: overviewMetricValue({
                data,
                errorLabel: "GET /runtime/tool-calls/activity",
                count: runtimeDecisionCount
              })
            },
            {
              label: "Evidence export",
              value: "Manual JSON"
            }
          ]}
        >
          Review bounded Evidence Bundles, PolicyDecision context, CheckResults, HumanApprovals, TraceEvents, and AuditLogs.
        </OverviewWorkflowCard>
      </section>

      <section className="overview-row">
        <div className="overview-panel">
          <div className="overview-panel-head">
            <h2 className="overview-panel-title">Needs attention</h2>
            <span className="overview-chip warn">
              {data.loading ? "loading" : `${pendingRuntimeApprovals + pendingPolicyReviews} pending`}
            </span>
          </div>
          <div className="overview-panel-body">
            {attentionItems.map((item, index) => <OverviewItem key={`${item.title}-${index}`} item={item} />)}
          </div>
        </div>

        <div className="overview-panel">
          <div className="overview-panel-head">
            <h2 className="overview-panel-title">Recent governance activity</h2>
            <Link className="overview-chip info" href="/runtime-gateway">Runtime Decisions</Link>
          </div>
          <div className="overview-panel-body">
            {activityItems.map((item, index) => <OverviewItem key={`${item.title}-${index}`} item={item} />)}
          </div>
        </div>
      </section>

      <section className="overview-demo-card">
        <div>
          <h2 className="overview-panel-title">Run the metadata pre-check demo</h2>
          <p className="overview-card-body" style={{ marginTop: 6 }}>
            Local/demo-only path for real metadata-only CheckResults, a require_human_review decision, and Evidence Bundle inspection.
            This is no fake production simulation.
          </p>
        </div>
        <code className="overview-demo-command">.\scripts\dev-demo.ps1</code>
      </section>

      <nav className="overview-shortcuts" aria-label="Overview shortcuts">
        <Link className="overview-shortcut" href="/policies">Policy Studio</Link>
        <Link className="overview-shortcut" href="/human-approvals">Review Inbox</Link>
        <Link className="overview-shortcut" href="/evidence">Evidence & Audit</Link>
        <Link className="overview-shortcut" href="/agents">Agents</Link>
        <Link className="overview-shortcut" href="/access-data">Access & Data</Link>
        <Link className="overview-shortcut" href="/runtime-gateway">Runtime Decisions</Link>
      </nav>
    </div>
  );
};

const CSS_STUDIO = `
  /* ── Studio-specific tokens (prefixed to avoid collision) ── */
  .ps2-shell { display:flex; height:100%; overflow:hidden; position:relative; }

  /* Block grammar accent colors */
  --when-c:  #8b78f6;
  --check-c: #38b4f5;
  --then-c:  #f0873a;
  --prove-c: #22d37a;

  /* Studio surfaces slightly darker than Command */
  .ps2-editor-bg { background: #080811; }

  /* ── Policy List Pane ── */
  .ps2-list-pane {
    width: 224px; flex-shrink:0;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    display:flex; flex-direction:column; overflow:hidden;
    height: calc(100vh - 48px);
  }
  .ps2-pane-head { padding:14px 14px 10px; border-bottom:1px solid var(--border); flex-shrink:0; }
  .ps2-pane-title { font-size:14px; font-weight:700; color:#eeeef8; margin-bottom:10px; }
  .ps2-mode-row { display:flex; gap:4px; margin-bottom:10px; }
  .ps2-mode-btn {
    flex:1; font-family:var(--mono); font-size:10px; padding:5px 0;
    border-radius:5px; cursor:pointer; border:1px solid var(--border);
    background:transparent; color:var(--text-muted); transition:all .13s;
    letter-spacing:.04em;
  }
  .ps2-mode-btn.p-on { background:var(--purple-dim); color:var(--purple-lt); border-color:var(--purple-brd); }
  .ps2-mode-btn.t-on { background:var(--orange-dim); color:var(--orange);    border-color:var(--orange-brd); }

  .ps2-search {
    display:flex; align-items:center; gap:7px;
    background:rgba(255,255,255,.04); border:1px solid var(--border);
    border-radius:var(--radius-sm); padding:0 10px; height:30px;
    transition:border-color .14s;
  }
  .ps2-search:focus-within { border-color:var(--purple-brd); }
  .ps2-search input { background:none; border:none; outline:none; color:var(--text);
    font-size:11.5px; font-family:var(--mono); width:100%; }
  .ps2-search input::placeholder { color:var(--text-faint); }

  .ps2-list-scroll { flex:1; overflow:auto; padding:6px; }
  .ps2-section-lbl { font-size:9px; color:var(--text-faint); letter-spacing:.13em;
    text-transform:uppercase; font-family:var(--mono); font-weight:600;
    padding:7px 6px 3px; }
  .ps2-entry {
    display:flex; align-items:flex-start; gap:7px;
    padding:7px 8px; border-radius:6px; cursor:pointer;
    transition:all .12s; margin-bottom:1px; border:1px solid transparent;
  }
  .ps2-entry:hover { background:rgba(255,255,255,.035); }
  .ps2-entry.active { background:var(--purple-dim); border-color:var(--purple-brd); }
  .ps2-entry-dot { width:6px; height:6px; border-radius:50%; margin-top:4px; flex-shrink:0; }
  .ps2-entry-name { font-size:11px; font-weight:500; color:var(--text); margin-bottom:2px;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ps2-entry-meta { font-size:9px; color:var(--text-muted); font-family:var(--mono); }
  .ps2-entry-chip { margin-left:auto; font-family:var(--mono); font-size:8.5px; font-weight:600;
    padding:1px 5px; border-radius:4px; flex-shrink:0; }

  .ps2-new-btn {
    margin:8px; display:flex; align-items:center; justify-content:center; gap:6px;
    background:var(--purple-dim); border:1px dashed var(--purple-brd);
    color:var(--purple-lt); border-radius:var(--radius-sm);
    padding:8px; font-size:12px; font-weight:600;
    cursor:pointer; transition:all .14s; flex-shrink:0;
  }
  .ps2-new-btn:hover { background:rgba(124,109,240,.16); }

  /* ── Editor Pane ── */
  .ps2-editor-pane {
    flex:1; display:flex; flex-direction:column;
    height:calc(100vh - 48px); overflow:hidden;
    background:#08080f;
  }

  /* Struct bar */
  .ps2-struct-bar {
    display:flex; align-items:center; gap:0;
    border-bottom:1px solid var(--border); flex-shrink:0;
    padding:0 14px; height:38px;
    background:rgba(10,10,17,.75);
  }
  .ps2-struct-lbl { font-family:var(--mono); font-size:10px; color:var(--text-faint);
    letter-spacing:.1em; margin-right:12px; flex-shrink:0; }
  .ps2-step {
    display:flex; align-items:center; gap:6px; padding:0 13px; height:100%;
    font-family:var(--mono); font-size:10.5px; font-weight:600; letter-spacing:.06em;
    color:var(--text-muted); cursor:pointer; transition:all .13s;
    border-bottom:2px solid transparent; white-space:nowrap;
  }
  .ps2-step:hover { color:var(--text-dim); }
  .ps2-step.s-when.active  { color:#8b78f6; border-bottom-color:#8b78f6; }
  .ps2-step.s-check.active { color:#38b4f5; border-bottom-color:#38b4f5; }
  .ps2-step.s-then.active  { color:#f0873a; border-bottom-color:#f0873a; }
  .ps2-step.s-prove.active { color:#22d37a; border-bottom-color:#22d37a; }
  .ps2-step-count {
    width:16px; height:16px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:8.5px; font-weight:700;
  }
  .ps2-step.s-when.active  .ps2-step-count { background:rgba(139,120,246,.18); color:#8b78f6; }
  .ps2-step.s-check.active .ps2-step-count { background:rgba(56,180,245,.12);  color:#38b4f5; }
  .ps2-step.s-then.active  .ps2-step-count { background:rgba(240,135,58,.12);  color:#f0873a; }
  .ps2-step.s-prove.active .ps2-step-count { background:rgba(34,211,122,.10);  color:#22d37a; }
  .ps2-step-sep { color:var(--text-faint); font-family:var(--mono); font-size:12px; padding:0 2px; }

  /* Blocks/Code toggle in struct bar */
  .ps2-editor-toggle {
    display:flex; gap:2px; margin-left:auto;
    background:rgba(255,255,255,.04); border:1px solid var(--border);
    border-radius:var(--radius-sm); padding:2px;
  }
  .ps2-etbtn {
    font-family:var(--mono); font-size:10px; letter-spacing:.04em;
    padding:3px 11px; border-radius:4px; cursor:pointer;
    border:none; background:transparent; transition:all .13s; color:var(--text-muted);
    display:flex; align-items:center; gap:5px;
  }
  .ps2-etbtn.on-blocks { background:var(--purple-dim); color:var(--purple-lt); border:1px solid var(--purple-brd); }
  .ps2-etbtn.on-code   { background:var(--sky-dim);    color:var(--sky);       border:1px solid var(--sky-brd); }

  /* Editor scroll */
  .ps2-editor-scroll { flex:1; overflow:auto; padding:14px 16px; }

  /* Blocks */
  .ps2-block-list { display:flex; flex-direction:column; gap:5px; }
  .ps2-block-group { display:flex; flex-direction:column; gap:3px; }
  .ps2-block-group-label {
    display:flex; align-items:center; gap:8px;
    font-family:var(--mono); font-size:9.5px; font-weight:700;
    letter-spacing:.1em; text-transform:uppercase; padding:0 0 2px 4px;
  }
  .ps2-group-line { flex:1; height:1px; background:rgba(255,255,255,.04); }
  .ps2-group-sub { font-size:9px; color:var(--text-faint); font-family:var(--mono); font-weight:400; }
  .ps2-spacer {
    height:6px; position:relative; display:flex; align-items:center; padding:0 0 0 20px;
    font-family:var(--mono); font-size:9px; color:var(--text-faint); letter-spacing:.06em;
  }
  .ps2-spacer::before { content:'→'; margin-right:5px; color:var(--text-faint); }

  .ps2-block {
    display:flex; align-items:stretch; border-radius:var(--radius);
    border:1px solid var(--border2); background:var(--bg-card);
    transition:border-color .13s; cursor:pointer; overflow:hidden;
    animation:rowIn .15s ease;
  }
  .ps2-block:hover { border-color:rgba(255,255,255,.1); }
  .ps2-block.sel { border-color:var(--purple-brd); box-shadow:var(--glow-purple); }
  .ps2-block-accent { width:4px; flex-shrink:0; }
  .ps2-block-inner { flex:1; display:flex; align-items:center; gap:12px; padding:9px 12px; }
  .ps2-block-type {
    font-family:var(--mono); font-size:9.5px; font-weight:700; letter-spacing:.08em;
    padding:3px 8px; border-radius:4px; flex-shrink:0; min-width:50px;
    text-align:center; border:1px solid transparent;
  }
  .ps2-block-body { flex:1; }
  .ps2-block-expr { font-family:var(--mono); font-size:12px; color:var(--text); line-height:1.4; margin-bottom:2px; }
  .ps2-block-detail { font-size:10px; color:var(--text-muted); font-family:var(--mono); }
  .ps2-block-st {
    font-family:var(--mono); font-size:9px; font-weight:600;
    padding:2px 7px; border-radius:4px; flex-shrink:0; border:1px solid transparent;
  }

  /* Block kind variants */
  .ps2-block.bk-when  .ps2-block-accent { background:#8b78f6; }
  .ps2-block.bk-when  .ps2-block-type   { color:#8b78f6; background:rgba(139,120,246,.1); border-color:rgba(139,120,246,.22); }
  .ps2-block.bk-check .ps2-block-accent { background:#38b4f5; }
  .ps2-block.bk-check .ps2-block-type   { color:#38b4f5; background:rgba(56,180,245,.09); border-color:rgba(56,180,245,.20); }
  .ps2-block.bk-then  .ps2-block-accent { background:#f0873a; }
  .ps2-block.bk-then  .ps2-block-type   { color:#f0873a; background:rgba(240,135,58,.09); border-color:rgba(240,135,58,.20); }
  .ps2-block.bk-prove .ps2-block-accent { background:#22d37a; }
  .ps2-block.bk-prove .ps2-block-type   { color:#22d37a; background:rgba(34,211,122,.08); border-color:rgba(34,211,122,.18); }

  .ps2-st-ok  { color:var(--green);  background:var(--green-dim);  border-color:var(--green-brd); }
  .ps2-st-req { color:var(--red);    background:var(--red-dim);    border-color:var(--red-brd); }
  .ps2-st-pnd { color:var(--orange); background:var(--orange-dim); border-color:var(--orange-brd); }
  .ps2-st-col { color:var(--sky);    background:var(--sky-dim);    border-color:var(--sky-brd); }

  .ps2-add-block {
    display:flex; align-items:center; gap:5px;
    font-family:var(--mono); font-size:10px; color:var(--text-muted);
    border:1px dashed rgba(255,255,255,.07); border-radius:var(--radius-sm);
    padding:5px 12px; background:transparent; cursor:pointer; transition:all .12s;
    letter-spacing:.04em; margin-top:2px;
  }
  .ps2-add-block:hover { border-color:var(--purple-brd); color:var(--purple-lt); background:var(--purple-dim); }

  /* Code editor */
  .ps2-code-view { padding:2px 0; }
  .ps2-code-line { display:flex; align-items:baseline; padding:0 4px; transition:background .1s; }
  .ps2-code-line:hover { background:rgba(255,255,255,.02); }
  .ps2-ln { width:32px; flex-shrink:0; color:var(--text-faint); font-family:var(--mono);
    font-size:10.5px; text-align:right; padding-right:16px; user-select:none; line-height:1.85; }
  .ps2-cb { font-family:var(--mono); font-size:12.5px; line-height:1.85; }
  .ps2-ck  { color:#7870e0; } .ps2-ck2 { color:#a090f8; }
  .ps2-cs  { color:#68c98e; } .ps2-cv  { color:#e89040; }
  .ps2-cc  { color:#2a2a40; } .ps2-cr  { color:#e04060; font-weight:600; }
  .ps2-cf  { color:#28c880; } .ps2-cx  { color:#48487a; }
  .ps2-cn  { color:#7898c0; }

  /* Compile bar */
  .ps2-compile-bar {
    display:flex; align-items:center; gap:8px; padding:7px 16px;
    border-top:1px solid var(--border); background:rgba(34,211,122,.05);
    font-family:var(--mono); font-size:10.5px; color:var(--green); flex-shrink:0;
  }
  .ps2-compile-pills { display:flex; gap:5px; flex-wrap:wrap; }
  .ps2-co-pill {
    font-family:var(--mono); font-size:9.5px; font-weight:600;
    padding:2px 8px; border-radius:4px; border:1px solid transparent;
  }

  /* Simulation console */
  .ps2-sim {
    border-top:1px solid var(--border); flex-shrink:0;
    background:rgba(8,8,15,.97);
  }
  .ps2-sim-head {
    display:flex; align-items:center; justify-content:space-between;
    padding:7px 16px; border-bottom:1px solid var(--border2);
  }
  .ps2-sim-title-group { display:grid; gap:2px; min-width:0; }
  .ps2-sim-title { font-family:var(--mono); font-size:10.5px; color:var(--text-muted); letter-spacing:.07em; }
  .ps2-sim-help { font-family:var(--mono); font-size:10px; color:var(--text-faint); letter-spacing:.02em; }
  .ps2-sim-run {
    display:flex; align-items:center; gap:5px;
    font-family:var(--mono); font-size:10px; font-weight:600; letter-spacing:.04em;
    padding:4px 11px; border-radius:var(--radius-sm); cursor:pointer;
    background:var(--green-dim); color:var(--green); border:1px solid var(--green-brd);
    transition:all .13s;
  }
  .ps2-sim-run:hover { background:rgba(45,216,145,.14); }
  .ps2-sim-body { padding:7px 16px 10px; }
  .ps2-sim-line { display:flex; align-items:flex-start; gap:8px;
    font-family:var(--mono); font-size:11px; line-height:1.6; padding:1px 0; }
  .ps2-sym { width:14px; flex-shrink:0; font-size:10px; margin-top:2px; }
  .ps2-sim-ok   { color:var(--green); }
  .ps2-sim-warn { color:var(--orange); }
  .ps2-sim-info { color:var(--sky); }
  .ps2-sim-arrow{ color:var(--purple-lt); }

  /* Inspector */
  .ps2-inspector {
    width:268px; flex-shrink:0; border-left:1px solid var(--border);
    background:var(--bg-panel); display:flex; flex-direction:column;
    height:calc(100vh - 48px); overflow:hidden;
  }
  .ps2-insp-top { padding:12px 14px 10px; border-bottom:1px solid var(--border); flex-shrink:0;
    display:flex; align-items:center; justify-content:space-between; }
  .ps2-insp-title { font-size:13px; font-weight:700; color:#eeeef8; }
  .ps2-insp-scroll { flex:1; overflow:auto; }
  .ps2-insp-sec { padding:13px 14px; border-bottom:1px solid var(--border2); }
  .ps2-insp-sec-title {
    font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
    color:var(--text-muted); font-family:var(--mono); margin-bottom:9px;
    display:flex; align-items:center; gap:6px;
  }
  .ps2-insp-sec-title::before { content:''; width:10px; height:2px; border-radius:2px; }
  .ist2-summary::before  { background:var(--purple-lt); }
  .ist2-flow::before     { background:var(--sky); }
  .ist2-impact::before   { background:var(--orange); }
  .ist2-compiled::before { background:var(--green); }
  .ist2-review::before   { background:#e8c44a; }

  .ps2-summary-box {
    font-size:12px; color:var(--text-dim); line-height:1.65;
    background:var(--bg-card); border:1px solid var(--border);
    border-radius:var(--radius-sm); padding:10px 12px;
    border-left:3px solid var(--purple);
  }
  /* Decision flow mini */
  .ps2-dflow { display:flex; flex-direction:column; gap:3px; }
  .ps2-dflow-row { display:flex; align-items:stretch; gap:4px; }
  .ps2-dnode {
    flex:1; background:var(--bg-card); border:1px solid var(--border2);
    border-radius:var(--radius-sm); padding:6px 8px; text-align:center;
  }
  .ps2-ddot { width:6px; height:6px; border-radius:50%; margin:0 auto 4px; }
  .ps2-dlabel { font-size:10.5px; font-weight:600; color:var(--text); margin-bottom:1px; }
  .ps2-dsub { font-size:9px; color:var(--text-muted); font-family:var(--mono); }
  .ps2-darrow { display:flex; align-items:center; justify-content:center; color:var(--text-faint); font-size:12px; }
  .ps2-dconn { display:flex; align-items:center; justify-content:center; gap:6px; padding:1px 0; }
  .ps2-dconn-line { height:14px; width:1px; background:var(--border2); }
  .ps2-dconn-pill {
    font-family:var(--mono); font-size:9px; font-weight:600;
    padding:1px 7px; border-radius:10px; letter-spacing:.05em;
    color:var(--orange); background:var(--orange-dim); border:1px solid var(--orange-brd);
  }

  /* Impact */
  .ps2-impact-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:5px 0; border-bottom:1px solid var(--border2); font-size:11.5px;
  }
  .ps2-impact-row:last-child { border-bottom:none; }
  .ps2-ir-label { color:var(--text-muted); }
  .ps2-ir-val { font-family:var(--mono); font-size:11.5px; font-weight:600; }
  .ps2-overlap-card {
    display:flex; align-items:flex-start; gap:8px;
    background:rgba(232,196,74,.06); border:1px solid rgba(232,196,74,.2);
    border-radius:var(--radius-sm); padding:8px 10px; margin-top:8px;
  }
  .ps2-oc-title { font-size:11px; font-weight:600; color:#e8c44a; margin-bottom:2px; }
  .ps2-oc-sub { font-size:10px; color:var(--text-muted); line-height:1.4; }

  /* Compiled */
  .ps2-compiled-list { display:flex; flex-direction:column; gap:4px; }
  .ps2-compiled-item {
    display:flex; align-items:center; gap:8px;
    background:var(--bg-card); border:1px solid var(--border2);
    border-radius:var(--radius-sm); padding:7px 10px;
  }
  .ps2-ci-type { font-family:var(--mono); font-size:9px; font-weight:700; letter-spacing:.07em; color:var(--text-muted); min-width:64px; }
  .ps2-ci-name { font-family:var(--mono); font-size:11px; color:var(--text); flex:1; }
  .ps2-ci-dot  { width:5px; height:5px; border-radius:50%; flex-shrink:0; }

  /* Review */
  .ps2-review-card {
    background:var(--bg-card); border:1px solid var(--border2);
    border-radius:var(--radius-sm); padding:10px 12px; margin-bottom:8px;
  }
  .ps2-rc-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:4px 0; border-bottom:1px solid var(--border2); font-size:11px;
  }
  .ps2-rc-row:last-child { border-bottom:none; }
  .ps2-rc-key { color:var(--text-muted); }
  .ps2-rc-val { font-family:var(--mono); font-size:10.5px; color:var(--text-dim); }
  .ps2-review-note {
    width:100%; background:var(--bg-card); border:1px solid var(--border2);
    border-radius:var(--radius-sm); padding:7px 10px;
    font-family:var(--mono); font-size:11px; color:var(--text-dim);
    resize:none; outline:none; transition:border-color .13s; margin-top:4px;
  }
  .ps2-review-note:focus { border-color:var(--purple-brd); }
  .ps2-review-note::placeholder { color:var(--text-faint); }
  .ps2-review-diff {
    background:var(--bg-card); border:1px solid var(--border2);
    border-radius:var(--radius-sm); padding:8px 10px; margin-top:8px;
    display:grid; gap:5px;
  }
  .ps2-review-diff strong {
    color:var(--text); font-family:var(--mono); font-size:10.5px;
    letter-spacing:.06em; text-transform:uppercase;
  }
  .ps2-review-diff span {
    color:var(--purple-lt); font-family:var(--mono); font-size:10.5px;
  }
  .ps2-review-diff p {
    color:var(--text-muted); font-size:11px; line-height:1.45; margin:0;
  }
  .ps2-review-diff small {
    color:var(--text-dim); font-family:var(--mono); font-size:10px;
    overflow-wrap:anywhere;
  }
  .ps2-lifecycle-card {
    background:var(--bg-card); border:1px solid var(--border2);
    border-radius:var(--radius-sm); padding:9px 10px; display:grid; gap:8px;
  }
  .ps2-lifecycle-copy {
    display:grid; gap:4px; color:var(--text-muted); font-size:10.5px;
    line-height:1.45;
  }
  .ps2-lifecycle-copy span {
    padding-left:8px; border-left:2px solid rgba(255,255,255,.08);
  }
  .ps2-lifecycle-actions { display:flex; gap:5px; }

  .ps2-inline-review-action {
    background: var(--sky-dim);
    border: 1px solid var(--sky-brd);
    border-radius: var(--radius-sm);
    color: var(--sky);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 650;
    margin-top: 8px;
    padding: 8px 10px;
    width: 100%;
  }

  .ps2-inline-review-action:disabled {
    cursor: not-allowed;
    opacity: .55;
  }

  .ps2-btn-archive {
    background:var(--orange-dim); color:var(--orange);
    border:1px solid var(--orange-brd);
  }
  .ps2-btn-archive:hover { background:rgba(240,135,58,.14); }
  .ps2-btn-delete {
    background:var(--red-dim); color:var(--red);
    border:1px solid var(--red-brd);
  }
  .ps2-btn-delete:hover { background:rgba(255,91,116,.13); }
  .ps2-lifecycle-reason {
    color:var(--text-muted); font-family:var(--mono); font-size:9.5px;
    line-height:1.45; overflow-wrap:anywhere;
  }

  /* Inspector footer */
  .ps2-insp-actions {
    padding:10px 12px; border-top:1px solid var(--border); flex-shrink:0;
    display:flex; flex-direction:column; gap:5px; background:var(--bg-panel);
  }
  .ps2-act-row { display:flex; gap:5px; }
  .ps2-act-btn {
    flex:1; font-family:var(--mono); font-size:10.5px; font-weight:600;
    letter-spacing:.04em; padding:7px 0; border-radius:var(--radius-sm);
    cursor:pointer; text-align:center; transition:all .14s;
  }
  .ps2-btn-save  { background:transparent; color:var(--text-dim); border:1px solid var(--border); }
  .ps2-btn-save:hover { border-color:rgba(255,255,255,.13); background:rgba(255,255,255,.03); }
  .ps2-btn-sim   { background:var(--green-dim); color:var(--green); border:1px solid var(--green-brd); }
  .ps2-btn-sim:hover { background:rgba(45,216,145,.14); }
  .ps2-btn-submit {
    background:linear-gradient(135deg,#5c4ed4,#7c6df0); color:#fff; border:none;
    box-shadow:0 2px 10px rgba(92,78,212,.3); font-size:11px; padding:8px 0;
  }
  .ps2-btn-submit:hover { box-shadow:0 3px 16px rgba(92,78,212,.48); transform:translateY(-1px); }

  /* Template Drawer */
  .ps2-drawer {
    position:absolute; inset:0; background:rgba(8,8,17,.85);
    backdrop-filter:blur(8px); z-index:100;
    display:flex; align-items:flex-start; justify-content:center;
    padding-top:44px; animation:fadeUp .15s ease;
  }
  .ps2-drawer-panel {
    width:600px; max-height:76vh;
    background:var(--bg-panel); border:1px solid rgba(255,255,255,.1);
    border-radius:var(--radius-lg); overflow:hidden;
    display:flex; flex-direction:column;
    box-shadow:0 24px 60px rgba(0,0,0,.6);
    animation:fadeUp .2s ease;
  }
  .ps2-drawer-head {
    padding:16px 18px 12px; border-bottom:1px solid var(--border);
    display:flex; align-items:center; justify-content:space-between; flex-shrink:0;
  }
  .ps2-drawer-title { font-size:14px; font-weight:700; color:#eeeef8; }
  .ps2-drawer-sub { font-size:11px; color:var(--text-muted); margin-top:2px; }
  .ps2-drawer-close {
    width:28px; height:28px; border:1px solid var(--border); border-radius:var(--radius-sm);
    background:transparent; cursor:pointer; color:var(--text-muted);
    display:flex; align-items:center; justify-content:center; transition:all .12s;
  }
  .ps2-drawer-close:hover { background:rgba(255,255,255,.05); color:var(--text); }
  .ps2-drawer-cats {
    display:flex; gap:4px; padding:10px 18px 0; border-bottom:1px solid var(--border); flex-shrink:0;
  }
  .ps2-drawer-cat {
    font-family:var(--mono); font-size:10px; letter-spacing:.05em;
    padding:5px 12px; border-radius:var(--radius-sm) var(--radius-sm) 0 0; cursor:pointer;
    border:1px solid transparent; border-bottom:none; transition:all .13s;
    color:var(--text-muted); background:transparent;
  }
  .ps2-drawer-cat.active { color:var(--text); background:var(--bg-card);
    border-color:var(--border2); border-bottom:1px solid var(--bg-card); margin-bottom:-1px; }
  .ps2-tmpl-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; padding:14px 18px; overflow:auto; }
  .ps2-tmpl-card {
    background:var(--bg-card); border:1px solid var(--border2); border-radius:var(--radius);
    padding:12px 14px; cursor:pointer; transition:all .14s;
    position:relative; overflow:hidden;
  }
  .ps2-tmpl-card:hover { border-color:var(--purple-brd); background:var(--purple-dim); }
  .ps2-tmpl-card::before {
    content:''; position:absolute; top:0; left:0;
    width:3px; height:100%; border-radius:var(--radius) 0 0 var(--radius);
  }
  .ps2-tc-access::before   { background:var(--purple); }
  .ps2-tc-deny::before     { background:var(--red); }
  .ps2-tc-evidence::before { background:var(--green); }
  .ps2-tc-review::before   { background:var(--orange); }
  .ps2-tc-risk::before     { background:#e879f9; }
  .ps2-tc-scope::before    { background:var(--sky); }
  .ps2-tmpl-name { font-size:12px; font-weight:600; color:var(--text); margin-bottom:3px; }
  .ps2-tmpl-desc { font-size:10px; color:var(--text-muted); line-height:1.45; margin-bottom:8px; }
  .ps2-tmpl-footer { display:flex; align-items:center; gap:5px; }
  .ps2-tmpl-tag { font-family:var(--mono); font-size:9px; color:var(--text-muted);
    background:rgba(255,255,255,.05); border:1px solid var(--border2);
    border-radius:4px; padding:1px 6px; }
  .ps2-tmpl-use {
    margin-left:auto; font-family:var(--mono); font-size:9px; font-weight:700;
    padding:3px 9px; border-radius:var(--radius-sm); letter-spacing:.05em;
    background:var(--purple-dim); color:var(--purple-lt); border:1px solid var(--purple-brd);
    opacity:0; transition:opacity .13s; cursor:pointer;
  }
  .ps2-tmpl-card:hover .ps2-tmpl-use { opacity:1; }
`;

/* ── Studio Data ── */
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
  { id:"w2", group:"when",  kind:"when",  expr:'action.risk in ["high", "critical"]',    detail:"filter: risk level ≥ high",     st:"active",    stCls:"ps2-st-ok" },
  { id:"w3", group:"when",  kind:"when",  expr:'target.boundary == "external"',          detail:"filter: external boundary only",st:"active",    stCls:"ps2-st-ok" },
  { id:"c1", group:"check", kind:"check", expr:'access_grant.status == "active"',        detail:"required fact — blocking",      st:"required",  stCls:"ps2-st-req" },
  { id:"c2", group:"check", kind:"check", expr:'target.approval == "approved"',          detail:"required fact — blocking",      st:"required",  stCls:"ps2-st-req" },
  { id:"t1", group:"then",  kind:"then",  expr:'require_review("governance")',            detail:"human review gate — blocks execution", st:"pending", stCls:"ps2-st-pnd" },
  { id:"p1", group:"prove", kind:"prove", expr:"decision, checks, reviewer, evidence_bundle", detail:"audit package — collected on review", st:"collecting", stCls:"ps2-st-col" },
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
  { cls:"ps2-sim-ok",   sym:"✓", text:"policy external_action_control parsed" },
  { cls:"ps2-sim-ok",   sym:"✓", text:"scope resolved → 18 AI systems matched" },
  { cls:"ps2-sim-ok",   sym:"✓", text:"24 recent decisions matched conditions" },
  { cls:"ps2-sim-ok",   sym:"✓", text:"17 decisions would trigger require_review" },
  { cls:"ps2-sim-warn", sym:"!", text:"2 overlapping policies: approval_routing, data_boundary_control" },
  { cls:"ps2-sim-info", sym:"i", text:"0 decisions would be auto-denied" },
  { cls:"ps2-sim-arrow",sym:"→", text:"evidence package: decision · checks · reviewer · bundle" },
  { cls:"ps2-sim-ok",   sym:"✓", text:"no blocking compilation errors" },
];
const PS_COMPILED = [
  { type:"PolicyRule",      name:"external_action_control",         color:"var(--purple-lt)" },
  { type:"PolicyCheckStep", name:"access_grant.status required",    color:"#38b4f5" },
  { type:"PolicyCheckStep", name:"target.approval required",        color:"#38b4f5" },
  { type:"HumanApproval",   name:"governance team → blocking",      color:"#f0873a" },
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

/* ── PS Icon helper (reuses Icon from parent but with Ic shorthand) ── */
const Ic = ({ n, s = 14, c = "currentColor" }) => <Icon name={n} size={s} stroke={c} />;

/* ── Template Drawer ── */
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
          <button className="ps2-drawer-close" onClick={onClose}>✕</button>
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
                <span className="ps2-tmpl-use">Use template →</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ── Inspector ── */
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
                {i>0&&<div className="ps2-darrow">→</div>}
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
                {i>0&&<div className="ps2-darrow">→</div>}
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
            {key:"Status",         val:"Draft — not submitted"},
            {key:"Reviewer group", val:"governance"},
            {key:"Policy version", val:"0.3 (unsaved)"},
            {key:"Last activated", val:"v0.2 · 3 days ago"},
          ].map(r=>(
            <div key={r.key} className="ps2-rc-row">
              <span className="ps2-rc-key">{r.key}</span>
              <span className="ps2-rc-val">{r.val}</span>
            </div>
          ))}
        </div>
        <textarea className="ps2-review-note" rows={2} placeholder="Add a version note before submitting…" />
      </div>

    </div>
    <div className="ps2-insp-actions">
      <div className="ps2-act-row">
        <button className="ps2-act-btn ps2-btn-save">Save draft</button>
        <button className="ps2-act-btn ps2-btn-sim">▶ Simulate</button>
      </div>
      <button className="ps2-act-btn ps2-btn-submit">Submit for review</button>
    </div>
  </div>
);

/* ─── POLICY STUDIO VIEW (replaces old PolicyStudioView) ─── */
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

      {/* ── LEFT: Policy List ── */}
      <div className="ps2-list-pane">
        <div className="ps2-pane-head">
          <div className="ps2-pane-title">Policy Studio</div>
          <div className="ps2-mode-row">
            <button className={`ps2-mode-btn ${studioMode==="policies"?"p-on":""}`} onClick={() => setStudioMode("policies")}>Policies</button>
            <button className={`ps2-mode-btn ${studioMode==="templates"?"t-on":""}`} onClick={() => setStudioMode("templates")}>Templates</button>
          </div>
          <div className="ps2-search">
            <Icon name="search" size={11} />
            <input placeholder={studioMode === "templates" ? "Search templates…" : "Search policies…"} />
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
                  <div className="ps2-entry-meta">lib · shared</div>
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

      {/* ── CENTER: Editor ── */}
      <div className="ps2-editor-pane">

        {/* Structure bar + Blocks/Code toggle */}
        <div className="ps2-struct-bar">
          <span className="ps2-struct-lbl">policy structure</span>
          {steps.map((s, i) => (
            <span key={s.id} style={{ display:"contents" }}>
              {i > 0 && <span className="ps2-step-sep">→</span>}
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
                      <div className="ps2-spacer" style={{ color: g.color }}>enforced →</div>
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

      {/* ── RIGHT: Inspector ── */}
      <PS_Inspector />

      {/* Template Drawer */}
      {showTmpl && <PS_TemplateDrawer onClose={() => setShowTmpl(false)} />}
    </div>
  );
};

/* ─── TOPBAR ─── */
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
    decision: "REVIEW_REQUIRED — policy condition met: target.boundary == external AND action.risk == high",
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
    decision: "REVIEW_REQUIRED — ledger_write.amount > threshold AND fiscal_period.closing == true",
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
    decision: "REVIEW_REQUIRED — schema_change.type == DROP_COLUMN AND table.environment == production",
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
    decision: "REVIEW_REQUIRED — training.data_classification == unverified AND model.provider == external",
    checks: [
      { label: "training_data.classification == internal-safe", result: "pending", cls: "warn" },
      { label: "model.provider_agreement.signed", result: "pass", cls: "ok" },
    ],
    evidence: "EVD-2024-1177",
    separationWarning: false,
    note: "",
  },
  { id: "r5", system: "customer-support-bot", action: "crm_read customer_id:4421", policy: "pii-access", risk: "low", riskCls: "ok", requestedBy: "customer-support-bot", reviewerGroup: "Privacy Team", due: "completed", dueCls: "ok", tab: "completed", status: "Completed",
    why: "PII access review completed — access was within defined purpose and data minimization constraints.",
    decision: "ALLOWED — all checks passed, no sensitive data threshold exceeded",
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
      { step: "Runtime Request", ts: "14:02:11", detail: "POST /api/external/crm — prod-agent-14" },
      { step: "Policy Decision", ts: "14:02:11", detail: "REVIEW_REQUIRED — external_action_control matched" },
      { step: "Check Results", ts: "14:02:12", detail: "access_grant: PASS · target.approval: FAIL" },
      { step: "Human Approval", ts: "—", detail: "Awaiting Governance Team" },
      { step: "Audit Log", ts: "—", detail: "Not yet complete" },
      { step: "Evidence Package", ts: "—", detail: "Pending reviewer decision" },
    ]
  },
  { id: "e2", pkg: "EVD-2024-1168", system: "customer-support-bot", action: "crm_read customer_id:4421", decision: "ALLOWED", policy: "pii-access", reviewer: "J. Moreau", date: "2024-12-14", status: "complete", statusCls: "ok",
    timeline: [
      { step: "Runtime Request", ts: "09:14:03", detail: "crm_read — customer-support-bot" },
      { step: "Policy Decision", ts: "09:14:03", detail: "ALLOWED — all checks passed" },
      { step: "Check Results", ts: "09:14:04", detail: "purpose: PASS · minimization: PASS" },
      { step: "Human Approval", ts: "09:21:55", detail: "Approved — J. Moreau (Privacy Team)" },
      { step: "Audit Log", ts: "09:22:01", detail: "Sealed — 7 audit events" },
      { step: "Evidence Package", ts: "09:22:02", detail: "Exported — EVD-2024-1168.json" },
    ]
  },
  { id: "e3", pkg: "EVD-2024-1179", system: "data-pipeline-7", action: "schema_modify users_table", decision: "REVIEW_REQUIRED", policy: "schema-change-policy", reviewer: "Pending", date: "2024-12-15", status: "pending", statusCls: "warn",
    timeline: [
      { step: "Runtime Request", ts: "11:44:30", detail: "schema_modify users_table — data-pipeline-7" },
      { step: "Policy Decision", ts: "11:44:30", detail: "REVIEW_REQUIRED — DROP_COLUMN in production" },
      { step: "Check Results", ts: "11:44:31", detail: "consumers.notified: PENDING · backup: PASS" },
      { step: "Human Approval", ts: "—", detail: "Awaiting Data Stewards" },
      { step: "Audit Log", ts: "—", detail: "Not yet complete" },
      { step: "Evidence Package", ts: "—", detail: "Pending" },
    ]
  },
  { id: "e4", pkg: "EVD-2024-1155", system: "finance-reconciler", action: "report_generate Q3_summary", decision: "ALLOWED", policy: "financial-data-policy", reviewer: "C. Lebrun", date: "2024-12-10", status: "complete", statusCls: "ok",
    timeline: [
      { step: "Runtime Request", ts: "08:00:12", detail: "report_generate Q3_summary — finance-reconciler" },
      { step: "Policy Decision", ts: "08:00:12", detail: "ALLOWED — read-only, within scope" },
      { step: "Check Results", ts: "08:00:13", detail: "ledger.read_only: PASS · scope: PASS" },
      { step: "Human Approval", ts: "08:05:44", detail: "Approved — C. Lebrun (Finance Controls)" },
      { step: "Audit Log", ts: "08:05:50", detail: "Sealed — 4 audit events" },
      { step: "Evidence Package", ts: "08:05:51", detail: "Exported — EVD-2024-1155.json" },
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
  { ts: "13:21", type: "GAP_FLAGGED", system: "ml-ops-3", action: "model.fine_tune llama-3-70b", policy: "—", cls: "info" },
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

/* ─── SHARED COMPONENTS ─── */
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

/* ─── AI SYSTEMS VIEW ─── */
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
                <span style={{ color: "var(--text-faint)" }}>·</span>
                <span>{sys.env}</span>
                <span style={{ color: "var(--text-faint)" }}>·</span>
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
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{selected.owner} · {selected.env} environment · Policy coverage: {selected.coverage}</div>
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

/* ─── REVIEWS VIEW ─── */
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
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{selected.system} · Requested by system · Reviewer group: <span style={{ color: "var(--text-dim)", fontWeight: 500 }}>{selected.reviewerGroup}</span></div>
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

/* ─── EVIDENCE VIEW ─── */
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
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>{ev.system} · {ev.date}</div>
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
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{selected.system} · Policy: {selected.policy} · Reviewer: {selected.reviewer}</div>
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

/* ─── RISK VIEW ─── */
const RiskView = () => {
  const [selected, setSelected] = useState(RISKS[0]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
        <SectionHeader title="Risk Register" sub="AI governance risk inventory — linked to systems, policies, and evidence" />
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

/* ─── DATA VIEW ─── */
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
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: ds.dpia ? "var(--sky)" : "var(--text-faint)" }}>{ds.dpia || "—"}</span>
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

/* ─── MODELS VIEW ─── */
const ModelsView = () => {
  const [selected, setSelected] = useState(MODELS[0]);

  return (
    <div className="content" style={{ padding: 0, display: "flex", height: "calc(100vh - 48px)", overflow: "hidden" }}>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 22px" }}>
        <SectionHeader title="Model Inventory" sub="Models used by AI systems — approval status, risk, and governance coverage" />
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

/* ─── VENDORS VIEW ─── */
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

/* ─── MONITORING VIEW ─── */
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
    <SectionHeader title="Monitoring" sub="Governance signals from active AI systems — decisions, denials, gaps, and policy events" />

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

/* ─── INTEGRATIONS VIEW ─── */
const IntegrationsView = () => (
  <div className="content">
    <SectionHeader title="Integrations" sub="Connect AGCP to your AI runtimes and orchestration platforms" />
    <div style={{ background: "rgba(54,184,246,.05)", border: "1px solid var(--sky-brd)", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--sky)", flexShrink: 0 }} />
      <div style={{ fontSize: 12, color: "var(--sky)", fontFamily: "var(--mono)" }}>
        <strong>AGCP decides and records. External runtimes execute.</strong> Integrations are pre-execution hooks — your runtime calls AGCP before performing an action, and receives a decision.
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

/* ─── ADMIN VIEW ─── */
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
  { path: "/human-approvals", view: "reviews", label: "Human Reviews" },
  { path: "/evidence", view: "evidence", label: "Evidence & Audit" },
  { path: "/audit", view: "evidence", label: "Audit Logs" },
  { path: "/policies", view: "policies", label: "Policy Studio" },
  { path: "/access-data", view: "data", label: "Access & Inventory" },
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

const AGCP_CONNECTED_CSS = `
  .agcp-connected-content {
    min-height: 0;
  }

  .agcp-connected-content .page-header {
    margin-bottom: 16px;
    max-width: 980px;
  }

  .agcp-connected-content .eyebrow {
    color: var(--purple-lt);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .12em;
    margin: 0 0 8px;
    text-transform: uppercase;
  }

  .agcp-connected-content .page-header h2 {
    color: #eeeef8;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -.015em;
    line-height: 1.15;
    margin: 0;
  }

  .agcp-connected-content .page-header p:not(.eyebrow) {
    color: var(--text-muted);
    font-size: 12.5px;
    line-height: 1.65;
    margin: 8px 0 0;
    max-width: 860px;
  }

  .agcp-connected-content .data-panel,
  .agcp-connected-content .placeholder-panel,
  .agcp-connected-content .detail-card,
  .agcp-connected-content .evidence-section,
  .agcp-connected-content .lookup-panel,
  .agcp-connected-content .policy-boundary,
  .agcp-connected-content .policy-form-panel,
  .agcp-connected-content .integration-boundary,
  .agcp-connected-content .profile-section {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: none;
    color: var(--text);
    overflow: hidden;
  }

  .agcp-connected-content .policy-boundary,
  .agcp-connected-content .placeholder-panel,
  .agcp-connected-content .evidence-section,
  .agcp-connected-content .lookup-panel,
  .agcp-connected-content .detail-card {
    padding: 16px;
  }

  .agcp-connected-content .policy-boundary p,
  .agcp-connected-content .placeholder-panel p,
  .agcp-connected-content .state-message p,
  .agcp-connected-content .work-item p,
  .agcp-connected-content .detail-card p,
  .agcp-connected-content .evidence-section p {
    color: var(--text-muted);
  }

  .agcp-connected-content .section-title,
  .agcp-connected-content .detail-card-header strong,
  .agcp-connected-content .evidence-section-header h3,
  .agcp-connected-content .evidence-section h3,
  .agcp-connected-content .policy-boundary strong,
  .agcp-connected-content .placeholder-panel h3 {
    color: #eeeef8;
    font-size: 13px;
    letter-spacing: .02em;
  }

  .agcp-connected-content .state-message {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    padding: 16px;
  }

  .agcp-connected-content .state-message strong {
    color: #eeeef8;
  }

  .agcp-connected-content .state-message.error,
  .agcp-connected-content .review-action-message.error,
  .agcp-connected-content .approval-action-status.error {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .agcp-connected-content .review-action-message.success,
  .agcp-connected-content .approval-action-status.success,
  .agcp-connected-content .success-state {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .agcp-connected-content .filter-bar,
  .agcp-connected-content .lookup-form,
  .agcp-connected-content .policy-form-header {
    background: var(--bg-panel2);
    border-bottom: 1px solid var(--border);
  }

  .agcp-connected-content input,
  .agcp-connected-content select,
  .agcp-connected-content textarea {
    background: rgba(255,255,255,.035);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
  }

  .agcp-connected-content .data-table {
    color: var(--text-dim);
    min-width: 920px;
  }

  .agcp-connected-content .data-table th,
  .agcp-connected-content .data-table td {
    border-bottom: 1px solid var(--border2);
  }

  .agcp-connected-content .data-table th {
    background: var(--bg-panel2);
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .08em;
  }

  .agcp-connected-content .data-table tr:hover td {
    background: rgba(124,109,240,.045);
  }

  .agcp-connected-content .row-link,
  .agcp-connected-content .secondary-action {
    color: var(--purple-lt);
  }

  .agcp-connected-content .secondary-action,
  .agcp-connected-content .table-action-button,
  .agcp-connected-content button {
    border-radius: var(--radius-sm);
  }

  .agcp-connected-content .secondary-action,
  .agcp-connected-content .table-action-button {
    border: 1px solid var(--purple-brd);
    background: var(--purple-dim);
    color: var(--purple-lt);
  }

  .agcp-connected-content .table-action-button.reject,
  .agcp-connected-content .table-action-button.cancel,
  .agcp-connected-content .grant-action-revoke,
  .agcp-connected-content .grant-action-expire {
    border-color: var(--red-brd);
    background: var(--red-dim);
    color: var(--red);
  }

  .agcp-connected-content .table-action-button.approve,
  .agcp-connected-content .grant-action-reactivate {
    border-color: var(--green-brd);
    background: var(--green-dim);
    color: var(--green);
  }

  .agcp-connected-content .table-pill,
  .agcp-connected-content .status-label,
  .agcp-connected-content .activity-severity {
    border: 1px solid var(--border);
    border-radius: 999px;
    background: rgba(255,255,255,.045);
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .04em;
  }

  .agcp-connected-content .risk-high,
  .agcp-connected-content .risk-critical,
  .agcp-connected-content .approval-rejected,
  .agcp-connected-content .decision-deny {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .agcp-connected-content .risk-medium,
  .agcp-connected-content .approval-pending,
  .agcp-connected-content .decision-require_human_review {
    background: var(--orange-dim);
    border-color: var(--orange-brd);
    color: var(--orange);
  }

  .agcp-connected-content .risk-low,
  .agcp-connected-content .approval-approved,
  .agcp-connected-content .decision-allow {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .agcp-connected-content .id-cell,
  .agcp-connected-content .metadata-block,
  .agcp-connected-content .evidence-json-block {
    color: var(--text-muted);
    font-family: var(--mono);
  }

  .agcp-connected-content .metadata-block,
  .agcp-connected-content .evidence-json-block {
    background: #090912;
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
  }

  .agcp-connected-content .detail-summary-grid,
  .agcp-connected-content .detail-count-grid,
  .agcp-connected-content .status-grid,
  .agcp-connected-content .evidence-count-grid,
  .agcp-connected-content .integration-status-grid {
    gap: 12px;
  }

  .agcp-connected-content .work-item,
  .agcp-connected-content .status-card,
  .agcp-connected-content .evidence-reference-group {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: none;
  }

  .agcp-connected-content .placeholder-list li {
    background: rgba(255,255,255,.025);
    border-color: var(--border2);
    color: var(--text-dim);
  }

  .agcp-connected-content:has(.access-inventory-route) {
    overflow: hidden;
    padding: 0;
  }

  .access-inventory-route {
    background:
      linear-gradient(180deg, rgba(24,32,42,.92), rgba(10,13,22,.96)),
      var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    height: calc(100vh - 48px);
    min-width: 1180px;
    overflow: hidden;
  }

  .access-inventory-header {
    align-items: flex-start;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 18px;
    justify-content: space-between;
    padding: 20px 22px 16px;
  }

  .access-inventory-header h1 {
    color: #eeeef8;
    font-size: 27px;
    font-weight: 750;
    letter-spacing: -.02em;
    line-height: 1.05;
    margin: 0 0 8px;
  }

  .access-inventory-header p {
    color: var(--text-muted);
    font-size: 12.5px;
    line-height: 1.45;
    margin: 0;
  }

  .access-inventory-header p::first-letter {
    color: inherit;
  }

  .access-inventory-toolbar {
    align-items: center;
    display: flex;
    gap: 10px;
    margin-top: 6px;
  }

  .access-inventory-toolbar span {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10px;
  }

  .access-inventory-toolbar strong {
    color: var(--text-dim);
    font-weight: 500;
  }

  .access-inventory-toolbar button,
  .access-rail-title button {
    background: rgba(255,255,255,.035);
    border: 1px solid var(--border);
    color: var(--text-dim);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10.5px;
    padding: 8px 10px;
  }

  .access-inventory-toolbar button:hover,
  .access-rail-title button:hover {
    background: var(--purple-dim);
    border-color: var(--purple-brd);
    color: var(--purple-lt);
  }

  .access-inventory-shell {
    display: grid;
    flex: 1;
    grid-template-columns: 220px minmax(650px, 1fr) 306px;
    min-height: 0;
  }

  .access-filter-rail,
  .access-inspector {
    background: rgba(15,18,28,.86);
    border-color: var(--border);
    min-height: 0;
    overflow: auto;
  }

  .access-filter-rail {
    border-right: 1px solid var(--border);
    display: grid;
    gap: 14px;
    grid-auto-rows: max-content;
    padding: 16px 14px;
  }

  .access-rail-title {
    align-items: center;
    display: flex;
    justify-content: space-between;
  }

  .access-rail-title strong,
  .access-inspector-section strong {
    color: #eeeef8;
    font-size: 13px;
    letter-spacing: .01em;
  }

  .access-filter-rail label {
    display: grid;
    gap: 7px;
  }

  .access-filter-rail label span {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .08em;
    text-transform: uppercase;
  }

  .access-filter-rail input,
  .access-filter-rail select {
    font-size: 12px;
    min-height: 34px;
    padding: 8px 10px;
    width: 100%;
  }

  .access-status-list {
    border-top: 1px solid var(--border2);
    display: grid;
    gap: 5px;
    padding-top: 12px;
  }

  .access-status-list button {
    align-items: center;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    cursor: pointer;
    display: grid;
    font-size: 11.5px;
    gap: 7px;
    grid-template-columns: auto minmax(0, 1fr) auto;
    padding: 7px 8px;
    text-align: left;
  }

  .access-status-list button:hover,
  .access-status-list button.active {
    background: rgba(255,255,255,.035);
    border-color: var(--border);
    color: var(--text-dim);
  }

  .access-status-list strong {
    color: var(--text-faint);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
  }

  .access-boundary-note {
    background: rgba(124,109,240,.08);
    border: 1px solid var(--purple-brd);
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    display: grid;
    gap: 6px;
    font-size: 11.5px;
    line-height: 1.5;
    padding: 11px;
  }

  .access-boundary-note strong {
    color: var(--purple-lt);
    font-size: 11.5px;
  }

  .access-boundary-note p {
    margin: 0;
  }

  .access-matrix-workspace {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    padding: 0;
  }

  .access-matrix-meta {
    align-items: center;
    border-bottom: 1px solid var(--border);
    color: var(--text-muted);
    display: flex;
    font-family: var(--mono);
    font-size: 10px;
    gap: 10px;
    min-height: 36px;
    padding: 0 12px;
  }

  .access-matrix-meta span {
    background: rgba(255,255,255,.035);
    border: 1px solid var(--border2);
    border-radius: 999px;
    padding: 4px 8px;
  }

  .access-matrix-scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  .access-matrix-table {
    border-collapse: collapse;
    color: var(--text-dim);
    font-size: 11px;
    min-width: 960px;
    width: 100%;
  }

  .access-matrix-table th,
  .access-matrix-table td {
    border-bottom: 1px solid var(--border2);
    border-right: 1px solid var(--border2);
    height: 49px;
    padding: 0;
  }

  .access-matrix-table thead th {
    background: rgba(18,24,32,.94);
    color: #c5c5dc;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
    min-width: 62px;
    padding: 8px 7px;
    position: sticky;
    text-align: center;
    top: 0;
    vertical-align: bottom;
    z-index: 2;
  }

  .access-matrix-table thead th span {
    color: var(--text-faint);
    display: block;
    font-size: 8.5px;
    letter-spacing: .06em;
    margin-bottom: 5px;
    text-transform: uppercase;
  }

  .access-matrix-table .agent-col {
    left: 0;
    min-width: 168px;
    position: sticky;
    text-align: left;
    z-index: 3;
  }

  .access-matrix-table tbody .agent-col {
    align-items: center;
    background: rgba(13,18,25,.98);
    display: flex;
    gap: 9px;
    padding: 9px 10px;
  }

  .access-matrix-table tbody tr:hover .agent-col,
  .access-matrix-table tbody tr:hover td {
    background: rgba(124,109,240,.035);
  }

  .agent-avatar,
  .inspector-avatar {
    align-items: center;
    background: var(--purple-dim);
    border: 1px solid var(--purple-brd);
    border-radius: 9px;
    color: var(--purple-lt);
    display: inline-flex;
    flex-shrink: 0;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 800;
    height: 29px;
    justify-content: center;
    width: 29px;
  }

  .access-matrix-table .agent-col strong {
    color: #dedeee;
    display: block;
    font-size: 11px;
    max-width: 108px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .access-matrix-table .agent-col em {
    color: var(--text-muted);
    display: block;
    font-size: 10px;
    font-style: normal;
    margin-top: 2px;
  }

  .access-matrix-table td {
    background: rgba(12,17,24,.55);
    text-align: center;
  }

  .matrix-cell {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--text-faint);
    cursor: pointer;
    display: inline-flex;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 800;
    height: 100%;
    justify-content: center;
    min-height: 38px;
    padding: 0;
    width: 100%;
  }

  .matrix-cell:disabled {
    cursor: default;
    opacity: .6;
  }

  .matrix-cell.allowed { color: var(--green); }
  .matrix-cell.review { color: var(--orange); }
  .matrix-cell.suspended { color: var(--red); }
  .matrix-cell.expired { color: #9aa0b8; }
  .matrix-cell.not-declared { color: #6c7086; }

  .matrix-cell:not(:disabled):hover {
    background: rgba(124,109,240,.1);
    box-shadow: inset 0 0 0 1px var(--purple-brd);
  }

  .matrix-legend {
    align-items: center;
    border-top: 1px solid var(--border);
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    font-size: 11px;
    gap: 14px;
    min-height: 42px;
    padding: 9px 12px;
  }

  .matrix-legend span {
    align-items: center;
    display: inline-flex;
    gap: 6px;
  }

  .matrix-dot {
    border: 1px solid currentColor;
    border-radius: 999px;
    display: inline-flex;
    height: 11px;
    width: 11px;
  }

  .matrix-dot.allowed { color: var(--green); }
  .matrix-dot.review { color: var(--orange); }
  .matrix-dot.suspended { color: var(--red); }
  .matrix-dot.expired { color: #a0a7be; }
  .matrix-dot.not-declared { color: #73788d; }

  .access-inspector {
    border-left: 1px solid var(--border);
    display: grid;
    gap: 15px;
    grid-auto-rows: max-content;
    padding: 18px 14px;
    position: relative;
  }

  .access-inspector-accent {
    background: linear-gradient(90deg, var(--purple-lt), transparent);
    height: 3px;
    left: 0;
    position: absolute;
    right: 0;
    top: 0;
  }

  .access-inspector header {
    align-items: center;
    display: flex;
    gap: 10px;
  }

  .access-inspector header strong {
    color: #eeeef8;
    display: block;
    font-size: 13.5px;
  }

  .access-inspector header p {
    color: var(--text-muted);
    font-size: 11.5px;
    margin: 3px 0 0;
  }

  .access-detail-list {
    border-top: 1px solid var(--border2);
    display: grid;
    gap: 0;
    margin: 0;
    padding-top: 8px;
  }

  .access-detail-list div {
    display: grid;
    gap: 8px;
    grid-template-columns: 92px minmax(0, 1fr);
    padding: 8px 0;
  }

  .access-detail-list dt {
    color: var(--text-muted);
    font-size: 11px;
  }

  .access-detail-list dd {
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 10.5px;
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .access-inspector-section {
    border-top: 1px solid var(--border2);
    display: grid;
    gap: 8px;
    padding-top: 13px;
  }

  .access-inspector-section a {
    align-items: center;
    background: rgba(255,255,255,.03);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    color: var(--purple-lt);
    display: flex;
    font-size: 11.5px;
    justify-content: space-between;
    padding: 8px 9px;
  }

  .access-inspector-section a:hover {
    background: var(--purple-dim);
    border-color: var(--purple-brd);
  }

  .access-action-grid {
    display: grid;
    gap: 7px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .access-action {
    background: rgba(255,255,255,.035);
    border: 1px solid var(--border);
    color: var(--text-dim);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    min-height: 38px;
    padding: 7px 8px;
  }

  .access-action.suspend,
  .access-action.expire {
    background: var(--orange-dim);
    border-color: var(--orange-brd);
    color: var(--orange);
  }

  .access-action.revoke {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .access-action.reactivate {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .access-action:disabled {
    cursor: not-allowed;
    opacity: .55;
  }

  .access-action-message {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 11.5px;
    margin: 0;
    padding: 9px;
  }

  .access-action-message.success {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .access-action-message.error,
  .access-state-panel.error {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .access-state-panel {
    align-self: center;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    display: grid;
    gap: 7px;
    justify-self: center;
    margin: 32px;
    max-width: 520px;
    padding: 18px;
  }

  .access-state-panel strong {
    color: #eeeef8;
    font-size: 13px;
  }

  .access-state-panel p {
    margin: 0;
  }

  .agcp-panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    position: relative;
  }

  .agcp-panel::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(124,109,240,.045), transparent 34%);
    pointer-events: none;
  }

  .agcp-section-header {
    align-items: flex-start;
    border-bottom: 1px solid var(--border2);
    display: flex;
    gap: 14px;
    justify-content: space-between;
    padding: 14px 16px;
    position: relative;
  }

  .agcp-section-header h3 {
    color: #eeeef8;
    font-size: 13px;
    letter-spacing: .02em;
    margin: 2px 0 0;
  }

  .agcp-section-header p {
    color: var(--text-muted);
    font-size: 12px;
    line-height: 1.55;
    margin: 5px 0 0;
    max-width: 760px;
  }

  .agcp-eyebrow {
    color: var(--purple-lt);
    display: inline-flex;
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
  }

  .agcp-section-actions {
    align-items: center;
    display: flex;
    flex-shrink: 0;
    gap: 8px;
  }

  .agcp-badge {
    align-items: center;
    background: rgba(255,255,255,.04);
    border: 1px solid var(--border);
    border-radius: 999px;
    color: var(--text-dim);
    display: inline-flex;
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 700;
    gap: 5px;
    letter-spacing: .05em;
    line-height: 1;
    min-height: 22px;
    padding: 5px 8px;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .agcp-badge.ok {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .agcp-badge.warn {
    background: var(--orange-dim);
    border-color: var(--orange-brd);
    color: var(--orange);
  }

  .agcp-badge.danger {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .agcp-badge.info {
    background: var(--sky-dim);
    border-color: var(--sky-brd);
    color: var(--sky);
  }

  .agcp-badge.purple {
    background: var(--purple-dim);
    border-color: var(--purple-brd);
    color: var(--purple-lt);
  }

  .agcp-badge.muted {
    color: var(--text-muted);
  }

  .agcp-state {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    margin: 14px;
    padding: 14px;
  }

  .agcp-state strong {
    color: #eeeef8;
    display: block;
    font-size: 13px;
    margin-bottom: 5px;
  }

  .agcp-state p {
    color: var(--text-muted);
    font-size: 12.5px;
    line-height: 1.6;
    margin: 0;
  }

  .agcp-state.error {
    background: var(--red-dim);
    border-color: var(--red-brd);
  }

  .agcp-state.error strong,
  .agcp-state.error p {
    color: var(--red);
  }

  .agcp-table-wrap {
    overflow-x: auto;
    position: relative;
  }

  .agcp-data-table {
    border-collapse: collapse;
    color: var(--text-dim);
    min-width: 880px;
    width: 100%;
  }

  .agcp-data-table th,
  .agcp-data-table td {
    border-bottom: 1px solid var(--border2);
    font-size: 12px;
    padding: 12px 14px;
    text-align: left;
    vertical-align: top;
  }

  .agcp-data-table th {
    background: rgba(255,255,255,.025);
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .1em;
    text-transform: uppercase;
  }

  .agcp-data-table tr:hover td {
    background: rgba(124,109,240,.045);
  }

  .agcp-data-table tr:last-child td {
    border-bottom: 0;
  }

  .agcp-primary-link {
    color: #eeeef8;
    display: inline-flex;
    font-weight: 700;
    margin-bottom: 3px;
    text-decoration: none;
  }

  .agcp-primary-link:hover {
    color: var(--purple-lt);
  }

  .agcp-muted {
    color: var(--text-muted);
  }

  .agcp-id {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10.5px;
    word-break: break-all;
  }

  .agcp-meta-grid {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    margin: 14px;
  }

  .agcp-meta-grid > div {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    padding: 12px;
  }

  .agcp-meta-grid dt {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .09em;
    margin-bottom: 6px;
    text-transform: uppercase;
  }

  .agcp-meta-grid dd {
    color: #eeeef8;
    font-size: 13px;
    font-weight: 700;
    margin: 0;
  }

  .agcp-meta-grid .tone-ok { color: var(--green); }
  .agcp-meta-grid .tone-warn { color: var(--orange); }
  .agcp-meta-grid .tone-danger { color: var(--red); }
  .agcp-meta-grid .tone-info { color: var(--sky); }
  .agcp-meta-grid .tone-purple { color: var(--purple-lt); }

  .agcp-registry-summary {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    padding: 14px;
  }

  .agcp-registry-summary > div {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    padding: 12px;
  }

  .agcp-registry-summary span {
    color: var(--text-muted);
    display: block;
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .1em;
    text-transform: uppercase;
  }

  .agcp-registry-summary strong {
    color: #eeeef8;
    display: block;
    font-size: 22px;
    margin-top: 5px;
  }

  .agcp-review-list,
  .agcp-card-grid {
    display: grid;
    gap: 10px;
    padding: 14px;
  }

  .agcp-review-card {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    display: grid;
    gap: 10px;
    padding: 13px;
  }

  .agcp-review-head {
    align-items: flex-start;
    display: flex;
    gap: 10px;
    justify-content: space-between;
  }

  .agcp-review-title {
    color: #eeeef8;
    font-size: 13px;
    font-weight: 700;
  }

  .agcp-review-meta {
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    font-family: var(--mono);
    font-size: 10.5px;
    gap: 8px;
  }

  .agcp-review-filter {
    padding: 12px 14px;
  }

  .agcp-review-filter label {
    max-width: 240px;
  }

  .agcp-approval-details {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    margin: 0;
  }

  .agcp-approval-details > div {
    background: rgba(10,10,20,.38);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    padding: 9px;
  }

  .agcp-approval-details dt {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: .08em;
    margin-bottom: 5px;
    text-transform: uppercase;
  }

  .agcp-approval-details dd {
    color: var(--text-dim);
    font-size: 11.5px;
    margin: 0;
    word-break: break-word;
  }

  .agcp-agent-hero {
    background: linear-gradient(135deg, rgba(124,109,240,.14), rgba(54,184,246,.045) 45%, rgba(255,255,255,.015));
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.4fr) minmax(260px, .6fr);
    margin-bottom: 16px;
    padding: 18px;
  }

  .agcp-agent-hero h2 {
    color: #eeeef8;
    font-size: 26px;
    letter-spacing: -.02em;
    line-height: 1.1;
    margin: 6px 0;
  }

  .agcp-agent-hero p {
    color: var(--text-muted);
    font-size: 12.5px;
    line-height: 1.6;
    margin: 0;
  }

  .agcp-agent-hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
  }

  .agcp-owner-card {
    background: rgba(10,10,20,.5);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 14px;
  }

  .agcp-owner-card span {
    color: var(--text-muted);
    display: block;
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .09em;
    margin-bottom: 5px;
    text-transform: uppercase;
  }

  .agcp-owner-card strong {
    color: #eeeef8;
    display: block;
    font-size: 15px;
  }

  .agcp-owner-card p {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10.5px;
    margin-top: 8px;
    word-break: break-all;
  }

  .agcp-timeline {
    list-style: none;
    margin: 0;
    padding: 14px;
  }

  .agcp-timeline-item {
    display: grid;
    grid-template-columns: 16px minmax(0, 1fr);
    gap: 10px;
    margin-bottom: 10px;
  }

  .agcp-timeline-item:last-child {
    margin-bottom: 0;
  }

  .agcp-timeline-marker {
    background: var(--purple-lt);
    border-radius: 999px;
    box-shadow: var(--glow-purple);
    height: 7px;
    margin: 16px auto 0;
    width: 7px;
  }

  .agcp-timeline-card {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 12px;
  }

  .agcp-timeline-head {
    align-items: center;
    display: flex;
    gap: 8px;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .agcp-timeline-head time {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10px;
  }

  .agcp-timeline-card strong {
    color: #eeeef8;
    font-size: 13px;
  }

  .agcp-timeline-body p {
    color: var(--text-muted);
    font-size: 12px;
    line-height: 1.55;
    margin: 5px 0 0;
  }

  .agcp-evidence-workspace {
    display: grid;
    gap: 14px;
  }

  .agcp-evidence-lookup {
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 14px;
  }

  .agcp-evidence-lookup label {
    display: grid;
    gap: 6px;
  }

  .agcp-evidence-lookup label span {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .09em;
    text-transform: uppercase;
  }

  .agcp-evidence-lookup button {
    align-self: end;
    background: linear-gradient(135deg, #5c4ed4, #7c6df0);
    border: 0;
    border-radius: var(--radius-sm);
    color: #fff;
    cursor: pointer;
    font-weight: 700;
    min-height: 40px;
    padding: 0 14px;
  }

  .policy-workbench {
    display: grid;
    gap: 14px;
  }

  .policy-workbench-hero {
    background:
      linear-gradient(135deg, rgba(124,109,240,.14), rgba(54,184,246,.045) 42%, rgba(45,216,145,.025)),
      var(--bg-panel);
    border-radius: var(--radius-lg);
  }

  .policy-workbench-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    justify-content: flex-end;
  }

  .policy-workbench-notes,
  .policy-rule-warning {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 16px;
  }

  .policy-workbench-notes span,
  .policy-rule-warning span {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 10px;
    line-height: 1.45;
    padding: 7px 9px;
  }

  .policy-rule-warning span:first-child,
  .policy-workbench-notes span:first-child {
    background: var(--orange-dim);
    border-color: var(--orange-brd);
    color: var(--orange);
  }

  .policy-workbench-grid {
    align-items: start;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.15fr) minmax(330px, .85fr);
  }

  .policy-inspector-column,
  .policy-rule-workspace {
    display: grid;
    gap: 14px;
  }

  .policy-library-panel,
  .policy-inspector-panel,
  .policy-rule-builder-head,
  .policy-builder-panel,
  .policy-rule-editor-panel {
    box-shadow: var(--glow-purple);
  }

  .policy-library-table .agcp-data-table,
  .policy-rule-table .agcp-data-table {
    min-width: 820px;
  }

  .policy-library-table .selected-row td,
  .policy-rule-table .selected-row td {
    background: var(--purple-dim);
    box-shadow: inset 3px 0 0 var(--purple-lt);
  }

  .policy-inspector-form,
  .policy-rule-form {
    display: grid;
    gap: 12px;
    padding: 14px;
  }

  .policy-form label,
  .policy-rule-form label {
    display: grid;
    gap: 6px;
  }

  .policy-form label span,
  .policy-rule-form label span {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .09em;
    text-transform: uppercase;
  }

  .policy-form input,
  .policy-form select,
  .policy-form textarea,
  .policy-rule-form input,
  .policy-rule-form select,
  .policy-rule-form textarea {
    font-family: var(--sans);
    font-size: 12px;
    min-height: 36px;
    padding: 9px 10px;
    width: 100%;
  }

  .policy-form textarea,
  .policy-rule-form textarea {
    min-height: 82px;
    resize: vertical;
  }

  .policy-form input:focus,
  .policy-form select:focus,
  .policy-form textarea:focus,
  .policy-rule-form input:focus,
  .policy-rule-form select:focus,
  .policy-rule-form textarea:focus {
    border-color: var(--purple-brd);
    box-shadow: 0 0 0 3px rgba(124,109,240,.08);
    outline: none;
  }

  .policy-form .agcp-meta-grid {
    margin: 0;
  }

  .policy-form-warning {
    background: var(--orange-dim);
    border: 1px solid var(--orange-brd);
    border-radius: var(--radius-sm);
    color: var(--orange);
    font-size: 11.5px;
    line-height: 1.55;
    padding: 10px 12px;
  }

  .form-message {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 12px;
    margin: 0;
    padding: 10px 12px;
  }

  .policy-workbench > .form-message {
    margin: 0;
  }

  .form-message.success {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .form-message.error {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .policy-rule-grid {
    align-items: start;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(280px, .85fr) minmax(0, 1.35fr);
  }

  .policy-rule-group {
    background: rgba(255,255,255,.02);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    display: grid;
    gap: 11px;
    margin: 0;
    padding: 13px;
  }

  .policy-rule-group legend {
    color: var(--purple-lt);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .1em;
    padding: 0 5px;
    text-transform: uppercase;
  }

  .rule-form-grid {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }

  .condition-preview {
    background: #090912;
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }

  .condition-preview summary {
    color: var(--sky);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10.5px;
    padding: 10px 12px;
  }

  .condition-preview pre {
    border-top: 1px solid var(--border2);
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.6;
    margin: 0;
    max-height: 340px;
    overflow: auto;
    padding: 12px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .secondary-action,
  .table-action-button {
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: .05em;
    min-height: 32px;
    padding: 7px 11px;
    text-transform: uppercase;
    transition: all .14s;
  }

  .secondary-action:hover:not(:disabled),
  .table-action-button:hover:not(:disabled) {
    border-color: var(--purple-lt);
    box-shadow: var(--glow-purple);
    transform: translateY(-1px);
  }

  .secondary-action:disabled,
  .table-action-button:disabled {
    cursor: not-allowed;
    opacity: .5;
  }

  .agcp-connected-content:has(.review-inbox-route) {
    padding: 0;
  }

  .review-inbox-route {
    background:
      radial-gradient(ellipse 55% 38% at 18% -12%, rgba(124,109,240,.08), transparent 62%),
      radial-gradient(ellipse 42% 26% at 100% 105%, rgba(45,216,145,.055), transparent 60%);
    display: flex;
    height: calc(100vh - 48px);
    min-height: 0;
    overflow: hidden;
  }

  .review-inbox-pane {
    background: rgba(15,15,26,.94);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    min-width: 320px;
    overflow: hidden;
    width: 360px;
  }

  .review-inbox-header {
    align-items: flex-start;
    border-bottom: 1px solid var(--border2);
    display: flex;
    gap: 12px;
    justify-content: space-between;
    padding: 18px 18px 14px;
  }

  .review-kicker {
    color: var(--orange);
    display: block;
    font-family: var(--mono);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .12em;
    margin-bottom: 6px;
    text-transform: uppercase;
  }

  .review-inbox-header h2 {
    color: #eeeef8;
    font-size: 19px;
    letter-spacing: -.015em;
    margin: 0 0 4px;
  }

  .review-inbox-header p,
  .review-current-actor small,
  .review-section-body p,
  .review-disabled-reason {
    color: var(--text-muted);
    font-size: 11.5px;
    line-height: 1.55;
    margin: 0;
  }

  .review-current-actor {
    background: rgba(255,255,255,.025);
    border-bottom: 1px solid var(--border2);
    display: grid;
    gap: 6px;
    padding: 12px 18px;
  }

  .review-current-actor.warning {
    background: var(--orange-dim);
  }

  .review-current-actor strong {
    color: #eeeef8;
    font-size: 11px;
  }

  .review-current-actor span {
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 10.5px;
  }

  .review-inbox-tabs {
    border-bottom: 1px solid var(--border2);
    display: grid;
    gap: 4px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    padding: 10px;
  }

  .review-inbox-tab {
    align-items: center;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    font-family: var(--mono);
    font-size: 9.5px;
    gap: 4px;
    min-height: 46px;
    padding: 6px 4px;
    text-transform: uppercase;
    transition: all .14s;
  }

  .review-inbox-tab span {
    color: var(--text-faint);
    font-size: 10px;
  }

  .review-inbox-tab.active,
  .review-inbox-tab:hover {
    background: var(--purple-dim);
    border-color: var(--purple-brd);
    color: var(--purple-lt);
  }

  .review-inbox-list {
    display: grid;
    gap: 8px;
    overflow: auto;
    padding: 12px;
  }

  .review-inbox-item {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    color: inherit;
    cursor: pointer;
    display: grid;
    gap: 7px;
    padding: 12px;
    text-align: left;
    transition: all .14s;
    width: 100%;
  }

  .review-inbox-item:hover,
  .review-inbox-item.selected {
    background: rgba(124,109,240,.08);
    border-color: var(--purple-brd);
    box-shadow: var(--glow-purple);
  }

  .review-inbox-item-top {
    align-items: center;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }

  .review-inbox-item-top > span {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: .08em;
    text-transform: uppercase;
  }

  .review-inbox-item strong {
    color: #eeeef8;
    display: block;
    font-size: 12.5px;
    line-height: 1.35;
  }

  .review-inbox-item p {
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1.45;
    margin: 0;
  }

  .review-inbox-item-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .review-inbox-item-meta span {
    background: rgba(10,10,20,.5);
    border: 1px solid var(--border2);
    border-radius: 4px;
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9.5px;
    padding: 3px 6px;
  }

  .review-inbox-warning {
    background: var(--orange-dim);
    border-bottom: 1px solid var(--orange-brd);
    color: var(--orange);
    font-size: 11px;
    line-height: 1.5;
    padding: 10px 14px;
  }

  .review-inbox-warning p {
    margin: 0;
  }

  .review-detail-pane {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
    overflow: auto;
    padding: 18px 20px;
  }

  .review-detail-header {
    align-items: flex-start;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 18px;
    justify-content: space-between;
    margin-bottom: 14px;
    padding-bottom: 14px;
  }

  .review-detail-header h1 {
    color: #eeeef8;
    font-size: 24px;
    letter-spacing: -.02em;
    line-height: 1.15;
    margin: 0 0 6px;
  }

  .review-detail-header p {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 11px;
    margin: 0;
  }

  .review-detail-status {
    align-items: flex-end;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 140px;
  }

  .review-detail-status span:last-child {
    color: var(--text-faint);
    font-family: var(--mono);
    font-size: 10px;
    text-transform: uppercase;
  }

  .review-detail-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .review-section-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    display: grid;
    gap: 10px;
    min-height: 190px;
    padding: 14px;
  }

  .review-section-head {
    align-items: center;
    display: flex;
    gap: 8px;
  }

  .review-section-head span {
    border-radius: 2px;
    height: 3px;
    width: 14px;
  }

  .review-section-card.orange .review-section-head span { background: var(--orange); }
  .review-section-card.purple .review-section-head span { background: var(--purple-lt); }
  .review-section-card.sky .review-section-head span { background: var(--sky); }
  .review-section-card.green .review-section-head span { background: var(--green); }

  .review-section-head h3 {
    color: #eeeef8;
    font-size: 13px;
    margin: 0;
  }

  .review-section-body {
    display: grid;
    gap: 10px;
  }

  .review-mini-meta {
    display: grid;
    gap: 7px;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    margin: 0;
  }

  .review-mini-meta div {
    background: rgba(10,10,20,.45);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    padding: 8px;
  }

  .review-mini-meta dt {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 8.5px;
    letter-spacing: .08em;
    margin-bottom: 5px;
    text-transform: uppercase;
  }

  .review-mini-meta dd {
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 10.5px;
    margin: 0;
    word-break: break-word;
  }

  .review-field-list {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .review-field-list li,
  .review-code-line {
    background: rgba(10,10,20,.45);
    border: 1px solid var(--border2);
    border-radius: 5px;
    color: var(--sky);
    font-family: var(--mono);
    font-size: 10px;
    padding: 6px 8px;
  }

  .review-check-results {
    display: grid;
    gap: 8px;
  }

  .review-check-result-card {
    background: rgba(10,10,20,.36);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    display: grid;
    gap: 8px;
    padding: 9px;
  }

  .review-check-result-top {
    align-items: center;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }

  .review-check-result-top strong {
    color: var(--text);
    font-family: var(--mono);
    font-size: 10.5px;
    word-break: break-word;
  }

  .review-decision-note,
  .review-reassign-box,
  .review-activation-check {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    margin-top: 12px;
    padding: 12px;
  }

  .review-decision-note label,
  .review-reassign-box label {
    display: grid;
    gap: 5px;
  }

  .review-reassign-box {
    align-items: end;
    display: grid;
    gap: 10px;
    grid-template-columns: minmax(180px, 1.1fr) repeat(4, minmax(130px, 1fr));
  }

  .review-reassign-box strong {
    color: #eeeef8;
    display: block;
    font-size: 12px;
    margin-bottom: 4px;
  }

  .review-reassign-box p {
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1.45;
    margin: 0;
  }

  .review-decision-note span,
  .review-reassign-box span {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: .08em;
    text-transform: uppercase;
  }

  .review-decision-note textarea,
  .review-reassign-box input,
  .review-reassign-box select {
    background: rgba(10,10,20,.55);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 11px;
    min-height: 34px;
    padding: 8px 9px;
  }

  .review-decision-note textarea {
    min-height: 70px;
    resize: vertical;
  }

  .review-activation-check {
    align-items: center;
    color: var(--text-dim);
    display: flex;
    font-family: var(--mono);
    font-size: 10.5px;
    gap: 8px;
  }

  .review-action-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 12px;
  }

  .review-action-btn {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: .05em;
    min-height: 34px;
    padding: 8px 13px;
    text-transform: uppercase;
    transition: all .14s;
  }

  .review-action-btn.approve {
    background: var(--green-dim);
    border-color: var(--green-brd);
    color: var(--green);
  }

  .review-action-btn.reject {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .review-action-btn.secondary {
    background: transparent;
    color: var(--text-dim);
  }

  .review-action-btn:hover:not(:disabled) {
    box-shadow: var(--glow-purple);
    transform: translateY(-1px);
  }

  .review-action-btn:disabled {
    cursor: not-allowed;
    opacity: .45;
  }

  .review-disabled-reason {
    margin-top: 8px;
    text-align: right;
  }

  .review-detail-empty {
    margin: auto;
    max-width: 520px;
    width: 100%;
  }

  .agcp-connected-content:has(.policy-studio-route) {
    padding: 0;
  }

  .policy-studio-route {
    height: calc(100vh - 48px);
    min-height: 0;
    overflow: hidden;
  }

  .policy-studio-route .ps2-shell {
    height: 100%;
  }

  .policy-studio-route .ps2-list-pane,
  .policy-studio-route .ps2-editor-pane,
  .policy-studio-route .ps2-inspector {
    height: calc(100vh - 48px);
  }

  .ps2-entry,
  .ps2-tmpl-card {
    font: inherit;
    text-align: left;
    width: 100%;
  }

  .ps2-entry-body {
    display: grid;
    min-width: 0;
  }

  .ps2-template-entry,
  .ps2-rule-entry {
    align-items: flex-start;
  }

  .ps2-template-dot {
    background: var(--orange);
    opacity: .85;
  }

  .ps2-rule-dot {
    background: var(--sky);
    opacity: .8;
  }

  .ps2-use-template {
    cursor: pointer;
  }

  .ps2-drawer-link {
    background: rgba(255,255,255,.025);
    border: 1px dashed var(--purple-brd);
    border-radius: var(--radius-sm);
    color: var(--purple-lt);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    margin: 8px 2px;
    padding: 8px;
    width: calc(100% - 4px);
  }

  .ps2-repo-state {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    display: grid;
    gap: 5px;
    margin: 6px 2px;
    padding: 10px;
  }

  .ps2-repo-state.compact {
    font-size: 10.5px;
    padding: 8px;
  }

  .ps2-repo-state strong {
    color: #eeeef8;
    font-size: 12px;
  }

  .ps2-repo-state span {
    font-family: var(--mono);
    font-size: 10px;
    line-height: 1.45;
    word-break: break-word;
  }

  .ps2-repo-state small {
    color: var(--text-faint);
    font-family: var(--mono);
    font-size: 9.5px;
    line-height: 1.45;
  }

  .ps2-repo-state.error {
    background: var(--red-dim);
    border-color: var(--red-brd);
    color: var(--red);
  }

  .ps2-step-wrap {
    align-items: center;
    display: contents;
  }

  .ps2-code-editor-wrap {
    background: #080811;
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    display: grid;
    grid-template-columns: 46px minmax(0, 1fr);
    min-height: 100%;
    overflow: hidden;
    overflow: clip;
    overscroll-behavior: contain;
    --ps2-code-font-size: 12.5px;
    --ps2-code-line-height: 1.75;
    --ps2-code-pad-y: 12px;
    --ps2-code-pad-x: 14px;
  }

  .ps2-code-gutter {
    background: rgba(255,255,255,.02);
    border-right: 1px solid var(--border2);
    color: var(--text-faint);
    display: block;
    font-family: var(--mono);
    font-size: var(--ps2-code-font-size);
    line-height: var(--ps2-code-line-height);
    overflow: auto;
    padding: 12px 10px 12px 0;
    scrollbar-width: none;
    text-align: right;
    user-select: none;
  }

  .ps2-code-gutter::-webkit-scrollbar {
    display: none;
  }

  .ps2-code-gutter span {
    display: block;
  }

  .ps2-code-input-layer {
    min-height: 460px;
    overflow: hidden;
    position: relative;
  }

  .ps2-code-highlight {
    color: #cfd8e3;
    font-family: var(--mono);
    font-size: var(--ps2-code-font-size);
    inset: 0;
    line-height: var(--ps2-code-line-height);
    margin: 0;
    min-height: 460px;
    overflow: auto;
    padding: var(--ps2-code-pad-y) var(--ps2-code-pad-x);
    pointer-events: none;
    position: absolute;
    scrollbar-width: none;
    tab-size: 2;
    white-space: pre;
  }

  .ps2-code-highlight::-webkit-scrollbar {
    display: none;
  }

  .ps2-code-highlight-line {
    display: block;
    min-height: 1.75em;
  }

  .ps2-token-keyword { color: #ff7ca9; }
  .ps2-token-control { color: #f0c14b; }
  .ps2-token-string { color: #9adf6f; }
  .ps2-token-number { color: #69adff; }
  .ps2-token-operator { color: #8b96a6; }
  .ps2-token-field { color: #d8dceb; }
  .ps2-token-type { color: #d8dceb; font-weight: 650; }

  .ps2-code-textarea {
    -webkit-text-fill-color: transparent;
    background: transparent;
    border: 0;
    caret-color: #d9e3ef;
    color: transparent;
    font-family: var(--mono);
    font-size: var(--ps2-code-font-size);
    inset: 0;
    height: 100%;
    line-height: var(--ps2-code-line-height);
    min-height: 460px;
    outline: none;
    overflow: auto;
    padding: var(--ps2-code-pad-y) var(--ps2-code-pad-x);
    position: absolute;
    resize: none;
    tab-size: 2;
    white-space: pre;
    width: 100%;
  }

  .ps2-code-textarea::selection {
    background: rgba(151, 120, 255, .25);
  }

  .ps2-code-legend {
    border-top: 1px solid var(--border2);
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    grid-column: 1 / -1;
    padding: 8px 14px;
  }

  .ps2-code-legend span {
    font-family: var(--mono);
    font-size: 10px;
  }

  .ps2-json-output {
    background: #090912;
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    margin-top: 8px;
    overflow: hidden;
  }

  .ps2-json-output summary {
    color: var(--sky);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    padding: 8px 10px;
  }

  .ps2-json-output pre {
    border-top: 1px solid var(--border2);
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 10.5px;
    line-height: 1.5;
    margin: 0;
    max-height: 220px;
    overflow: auto;
    padding: 10px;
    white-space: pre-wrap;
  }

  .ps2-sim-group + .ps2-sim-group {
    margin-top: 8px;
  }

  .ps2-sim-group-title {
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: 0;
    margin: 0 0 3px;
    text-transform: uppercase;
  }

  .ps2-sim-blocking {
    color: var(--red);
  }

  .ps2-save-state {
    border-radius: var(--radius-sm);
    font-family: var(--mono);
    font-size: 10px;
    line-height: 1.45;
    padding: 7px 9px;
  }

  .ps2-save-state.success {
    background: var(--green-dim);
    border: 1px solid var(--green-brd);
    color: var(--green);
  }

  .ps2-save-state.error {
    background: var(--red-dim);
    border: 1px solid var(--red-brd);
    color: var(--red);
  }

  .ps2-save-state.info {
    background: var(--sky-dim);
    border: 1px solid var(--sky-brd);
    color: var(--sky);
    display: grid;
    gap: 3px;
  }

  .ps2-save-state.attention {
    background: var(--orange-dim);
    border: 1px solid var(--orange-brd);
    color: var(--orange);
  }

  .ps2-act-btn:disabled {
    cursor: not-allowed;
    filter: grayscale(.25);
    opacity: .52;
    transform: none;
  }

  .policy-studio-route .ps2-shell {
    background:
      linear-gradient(135deg, rgba(91, 132, 153, .08), transparent 34%),
      linear-gradient(180deg, #0a1117 0%, #071017 100%);
    display: grid;
    grid-template-columns: 272px minmax(720px, 1fr) 224px;
    min-width: 1216px;
  }

  .policy-studio-route .ps2-list-pane {
    background: rgba(10, 18, 25, .96);
    border-right: 1px solid rgba(170, 190, 205, .16);
    border-left: 1px solid rgba(170, 190, 205, .08);
    box-sizing: border-box;
    padding-left: 8px;
    width: auto;
  }

  .ps2-repo-brand {
    align-items: center;
    color: #f3f6fa;
    display: flex;
    font-size: 17px;
    font-weight: 750;
    gap: 10px;
    height: 48px;
    letter-spacing: 0;
    margin: 0 -12px 12px;
    padding: 0 14px;
    border-bottom: 1px solid rgba(170, 190, 205, .16);
  }

  .ps2-repo-mark {
    align-items: center;
    color: #a78bfa;
    display: inline-flex;
    font-family: var(--mono);
    font-size: 18px;
    height: 24px;
    justify-content: center;
    width: 24px;
  }

  .ps2-repo-label {
    color: #a8b3c2;
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .09em;
    margin-bottom: 7px;
    text-transform: uppercase;
  }

  .ps2-repo-select {
    align-items: center;
    background: rgba(255, 255, 255, .035);
    border: 1px solid rgba(180, 198, 214, .15);
    border-radius: 6px;
    color: #d8e1ea;
    display: flex;
    font-size: 12px;
    gap: 8px;
    justify-content: space-between;
    margin-bottom: 9px;
    padding: 8px 10px;
  }

  .ps2-repo-select > span {
    display: grid;
    flex: 1;
    gap: 2px;
    min-width: 0;
  }

  .ps2-repo-select strong {
    color: #eef4fa;
    font-weight: 650;
    line-height: 1.2;
  }

  .ps2-repo-select small {
    color: #8693a4;
    font-size: 10px;
    line-height: 1.25;
  }

  .policy-studio-route .ps2-pane-head {
    border-bottom: 1px solid rgba(170, 190, 205, .14);
    padding: 0 12px 10px 14px;
  }

  .policy-studio-route .ps2-repo-label {
    padding-left: 1px;
  }

  .policy-studio-route .ps2-mode-row {
    display: none;
  }

  .policy-studio-route .ps2-search {
    flex: 1;
    height: 31px;
  }

  .ps2-repo-search-row {
    align-items: center;
    display: flex;
    gap: 7px;
  }

  .ps2-repo-search-row button {
    align-items: center;
    background: rgba(255, 255, 255, .035);
    border: 1px solid rgba(180, 198, 214, .15);
    border-radius: 5px;
    color: #aab5c2;
    cursor: pointer;
    display: inline-flex;
    font-family: var(--mono);
    font-size: 10px;
    height: 31px;
    justify-content: center;
    width: 31px;
  }

  .ps2-repo-search-row button:disabled {
    cursor: not-allowed;
    opacity: .45;
  }

  .ps2-search svg {
    color: #a78bfa;
    flex-shrink: 0;
  }

  .ps2-policy-folder {
    margin: 4px 0 8px;
  }

  .ps2-folder-row {
    align-items: center;
    color: #c4ccd7;
    display: flex;
    font-size: 11px;
    font-weight: 650;
    gap: 6px;
    padding: 7px 7px 4px;
  }

  .policy-studio-route .ps2-entry {
    background: transparent;
    border: 1px solid transparent;
    color: inherit;
    border-radius: 5px;
    gap: 7px;
    margin: 1px 4px;
    padding: 6px 8px;
  }

  .policy-studio-route .ps2-entry.active {
    background: rgba(147, 116, 255, .14);
    border-color: rgba(147, 116, 255, .55);
    box-shadow: inset 2px 0 0 #9b7cff;
  }

  .policy-studio-route .ps2-entry-dot {
    align-items: center;
    display: inline-flex;
    flex-shrink: 0;
    height: 16px;
    justify-content: center;
    margin-top: 1px;
    width: 16px;
  }

  .policy-studio-route .ps2-entry-dot svg {
    display: block;
  }

  .ps2-version-panel {
    border-top: 1px solid rgba(170, 190, 205, .14);
    padding: 8px 8px 7px;
  }

  .ps2-version-row {
    align-items: center;
    color: #9eabb9;
    display: flex;
    font-family: var(--mono);
    font-size: 10px;
    justify-content: space-between;
    padding: 6px 6px;
  }

  .ps2-version-row.active {
    background: rgba(147, 116, 255, .14);
    border-left: 2px solid #9b7cff;
    color: #e3e7ef;
  }

  .ps2-static-entry {
    cursor: default;
    opacity: 1;
  }

  .ps2-static-entry:hover {
    background: rgba(255,255,255,.025);
    border-color: transparent;
  }

  .policy-studio-route .ps2-editor-pane {
    background:
      radial-gradient(circle at 35% 22%, rgba(68, 118, 126, .16), transparent 44%),
      linear-gradient(180deg, rgba(12, 22, 30, .98), rgba(8, 16, 22, .98));
    border-right: 1px solid rgba(170, 190, 205, .14);
    min-width: 0;
  }

  .ps2-product-topbar {
    align-items: center;
    border-bottom: 1px solid rgba(170, 190, 205, .16);
    display: flex;
    flex-shrink: 0;
    height: 48px;
    padding: 0 14px;
  }

  .ps2-product-title {
    align-items: center;
    display: flex;
    gap: 10px;
    min-width: 0;
  }

  .ps2-product-title > span:last-child {
    display: grid;
    gap: 2px;
  }

  .ps2-product-title strong {
    color: #f2f6fb;
    font-size: 13px;
    line-height: 1;
  }

  .ps2-product-title small {
    color: #a4afbd;
    font-size: 11px;
    line-height: 1;
  }

  .ps2-policy-header {
    border-bottom: 1px solid rgba(170, 190, 205, .14);
    flex-shrink: 0;
    min-height: 74px;
    padding: 13px 18px 12px;
  }

  .ps2-policy-glyph {
    align-items: center;
    background: rgba(147, 116, 255, .22);
    border: 1px solid rgba(147, 116, 255, .36);
    border-radius: 5px;
    color: #bdaaff;
    display: inline-flex;
    font-family: var(--mono);
    font-size: 10px;
    height: 22px;
    justify-content: center;
    width: 22px;
  }

  .ps2-policy-title-row {
    align-items: flex-start;
    display: flex;
    gap: 16px;
    justify-content: space-between;
  }

  .ps2-policy-name-line {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 5px;
  }

  .ps2-policy-name-line h1 {
    color: #f3f6fa;
    font-size: 20px;
    font-weight: 760;
    letter-spacing: 0;
    line-height: 1.15;
  }

  .ps2-policy-title-copy p {
    color: #b7c0cc;
    font-size: 12px;
    line-height: 1.45;
    max-width: 720px;
  }

  .ps2-version-pill {
    color: #bfc8d4;
    font-family: var(--mono);
    font-size: 11px;
  }

  .ps2-policy-actions {
    align-items: center;
    display: flex;
    flex-shrink: 0;
    gap: 7px;
  }

  .ps2-header-btn,
  .ps2-header-icon,
  .ps2-structure-view {
    align-items: center;
    background: rgba(255, 255, 255, .035);
    border: 1px solid rgba(180, 198, 214, .18);
    border-radius: 5px;
    color: #dce5ee;
    cursor: pointer;
    display: inline-flex;
    font-size: 11px;
    font-weight: 650;
    gap: 7px;
    justify-content: center;
    padding: 7px 11px;
  }

  .ps2-header-btn.primary {
    background: rgba(147, 116, 255, .16);
    border-color: rgba(147, 116, 255, .56);
    color: #c9bbff;
  }

  .ps2-header-btn:disabled {
    cursor: not-allowed;
    opacity: .48;
  }

  .ps2-header-icon {
    width: 34px;
  }

  .ps2-structure-panel {
    border-bottom: 1px solid rgba(170, 190, 205, .14);
    flex-shrink: 0;
    padding: 10px 16px 12px;
  }

  .ps2-structure-head {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .ps2-structure-flow {
    align-items: stretch;
    background: rgba(255, 255, 255, .025);
    border: 1px solid rgba(180, 198, 214, .13);
    border-radius: 6px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 28px minmax(0, 1fr) 28px minmax(0, 1fr) 28px minmax(0, 1fr);
    min-height: 72px;
  }

  .ps2-structure-flow .ps2-step-sep {
    align-items: center;
    color: #a6b0bd;
    display: inline-flex;
    justify-content: center;
    opacity: .9;
  }

  .ps2-structure-wrap {
    align-items: center;
    display: contents;
  }

  .ps2-structure-card {
    align-items: center;
    display: flex;
    gap: 11px;
    min-width: 0;
    padding: 12px 14px;
    position: relative;
  }

  .ps2-structure-copy {
    display: grid;
    gap: 3px;
    min-width: 0;
  }

  .ps2-structure-copy strong {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .08em;
  }

  .ps2-structure-copy span {
    color: #aab5c2;
    font-size: 11px;
    line-height: 1.35;
  }

  .ps2-step-count {
    align-items: center;
    border: 1px solid currentColor;
    border-radius: 999px;
    display: inline-flex;
    flex-shrink: 0;
    font-size: 0;
    height: 24px;
    justify-content: center;
    width: 24px;
  }

  .ps2-structure-card.s-when strong,
  .ps2-structure-card.s-when .ps2-step-count { color: #a995ff; }
  .ps2-structure-card.s-check strong,
  .ps2-structure-card.s-check .ps2-step-count { color: #72dc99; }
  .ps2-structure-card.s-then strong,
  .ps2-structure-card.s-then .ps2-step-count { color: #f2bd4b; }
  .ps2-structure-card.s-prove strong,
  .ps2-structure-card.s-prove .ps2-step-count { color: #6eadff; }

  .ps2-editor-toolbar {
    align-items: center;
    border-bottom: 1px solid rgba(170, 190, 205, .14);
    display: flex;
    flex-shrink: 0;
    justify-content: space-between;
    min-height: 32px;
    padding: 0 16px;
  }

  .policy-studio-route .ps2-editor-toggle {
    background: rgba(255, 255, 255, .025);
    border-color: rgba(180, 198, 214, .14);
    border-radius: 5px;
    margin: 0;
  }

  .policy-studio-route .ps2-etbtn {
    align-items: center;
    gap: 6px;
    min-height: 26px;
    min-width: 108px;
    justify-content: center;
  }

  .ps2-canvas-tools {
    align-items: center;
    color: #9da9b6;
    display: flex;
    font-family: var(--mono);
    font-size: 10px;
    gap: 6px;
  }

  .ps2-canvas-tools span {
    align-items: center;
    border: 1px solid rgba(180, 198, 214, .13);
    border-radius: 4px;
    display: inline-flex;
    height: 26px;
    justify-content: center;
    padding: 5px 8px;
  }

  .policy-studio-route .ps2-editor-scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 0;
  }

  .ps2-editor-scroll.blocks-mode {
    padding: 8px 10px;
  }

  .ps2-editor-scroll.code-mode {
    padding: 0;
  }

  .ps2-block-workbench {
    display: grid;
    gap: 10px;
    grid-template-columns: 214px minmax(0, 1fr);
    min-height: 100%;
  }

  .ps2-block-library {
    background: rgba(255, 255, 255, .025);
    border: 1px solid rgba(180, 198, 214, .13);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }

  .ps2-block-library-head {
    align-items: center;
    color: #dfe6ee;
    display: flex;
    font-size: 11px;
    font-weight: 700;
    justify-content: space-between;
    padding: 9px 10px;
    text-transform: uppercase;
  }

  .ps2-block-library-head button {
    background: transparent;
    border: 1px solid rgba(180, 198, 214, .14);
    border-radius: 4px;
    color: #a995ff;
    cursor: pointer;
    height: 24px;
    width: 24px;
  }

  .ps2-library-search {
    align-items: center;
    background: rgba(255, 255, 255, .035);
    border: 1px solid rgba(180, 198, 214, .13);
    border-radius: 5px;
    display: flex;
    gap: 6px;
    margin: 0 8px 8px;
    padding: 6px 8px;
  }

  .ps2-library-search input {
    background: transparent;
    border: 0;
    color: #dfe6ee;
    font-size: 11px;
    min-width: 0;
    outline: 0;
    width: 100%;
  }

  .ps2-library-groups {
    overflow: auto;
    padding: 0 8px 8px;
  }

  .ps2-library-group {
    border-top: 1px solid rgba(180, 198, 214, .10);
    padding: 8px 0;
  }

  .ps2-library-group-title {
    align-items: center;
    color: #aab5c2;
    display: flex;
    font-size: 11px;
    justify-content: space-between;
    margin-bottom: 5px;
  }

  .ps2-library-item {
    align-items: center;
    background: rgba(255, 255, 255, .02);
    border: 1px solid rgba(180, 198, 214, .11);
    border-radius: 4px;
    color: #cbd5df;
    cursor: pointer;
    display: grid;
    font-family: var(--mono);
    font-size: 10px;
    gap: 6px;
    grid-template-columns: 14px minmax(0, 1fr) 18px;
    margin-bottom: 4px;
    padding: 6px;
    text-align: left;
    width: 100%;
  }

  .ps2-flow-canvas {
    background:
      linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 46px 46px;
    border: 1px solid rgba(180, 198, 214, .13);
    border-radius: 6px;
    min-width: 0;
    overflow: auto;
    padding: 18px 24px;
  }

  .ps2-flow-columns {
    align-items: start;
    display: grid;
    gap: 26px;
    grid-template-columns: 1.1fr 1.2fr 1fr 1fr;
    min-width: 720px;
  }

  .ps2-flow-column {
    display: grid;
    gap: 10px;
    position: relative;
  }

  .ps2-flow-column:not(.flow-prove)::after {
    border-top: 1px solid rgba(178, 193, 206, .48);
    content: "";
    height: 0;
    position: absolute;
    right: -27px;
    top: 58px;
    width: 27px;
    z-index: 0;
  }

  .ps2-flow-column:not(.flow-prove)::before {
    border-right: 1px solid rgba(178, 193, 206, .48);
    border-top: 1px solid rgba(178, 193, 206, .48);
    content: "";
    height: 7px;
    position: absolute;
    right: -28px;
    top: 54px;
    transform: rotate(45deg);
    width: 7px;
    z-index: 0;
  }

  .ps2-flow-column-title {
    align-items: center;
    color: var(--flow-color);
    display: flex;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    gap: 8px;
    letter-spacing: .07em;
    text-transform: uppercase;
  }

  .ps2-flow-column-title small {
    color: #a5afbd;
    font-family: var(--sans);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0;
    text-transform: none;
  }

  .ps2-flow-stack {
    display: grid;
    gap: 10px;
    position: relative;
  }

  .ps2-flow-stack::before {
    background: color-mix(in srgb, var(--flow-color) 32%, transparent);
    content: "";
    inset: 18px auto 18px 9px;
    position: absolute;
    width: 1px;
  }

  .ps2-flow-stack:has(.ps2-empty-flow-state)::before {
    display: none;
  }

  .ps2-flow-block {
    align-items: start;
    background: rgba(9, 20, 28, .9);
    border: 1px solid color-mix(in srgb, var(--flow-color) 42%, transparent);
    border-radius: 6px;
    color: #e7eef5;
    cursor: pointer;
    display: grid;
    gap: 8px;
    grid-template-columns: 18px minmax(0, 1fr) 18px;
    min-height: 42px;
    padding: 9px;
    position: relative;
    text-align: left;
    z-index: 1;
  }

  .ps2-flow-block::before {
    background: rgba(8, 16, 22, .98);
    border: 1px solid var(--flow-color);
    border-radius: 999px;
    content: "";
    height: 7px;
    left: -14px;
    position: absolute;
    top: 17px;
    width: 7px;
  }

  .ps2-flow-block.sel {
    box-shadow: 0 0 0 1px rgba(151, 120, 255, .8), 0 0 24px rgba(151, 120, 255, .14);
  }

  .ps2-flow-copy {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .ps2-flow-copy strong {
    color: #eef3f8;
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 650;
    line-height: 1.35;
    overflow-wrap: normal;
  }

  .ps2-flow-copy small {
    color: #9faabc;
    font-size: 10px;
    line-height: 1.25;
  }

  .ps2-flow-icon,
  .ps2-flow-menu {
    color: var(--flow-color);
    font-family: var(--mono);
    font-size: 10px;
  }

  .ps2-flow-icon {
    align-items: center;
    display: inline-flex;
    justify-content: center;
  }

  .ps2-flow-menu {
    align-items: center;
    display: inline-flex;
    justify-content: flex-end;
  }

  .ps2-empty-flow-state {
    border: 1px dashed rgba(180, 198, 214, .20);
    border-radius: 5px;
    color: #8f9baa;
    font-size: 10.5px;
    padding: 10px;
    position: relative;
    text-align: center;
    z-index: 1;
  }

  .ps2-flow-status {
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 9px;
    display: none;
    grid-column: 2 / 4;
    justify-self: start;
    padding: 2px 6px;
  }

  .ps2-add-flow-block {
    align-items: center;
    background: rgba(255, 255, 255, .02);
    border: 1px dashed rgba(180, 198, 214, .22);
    border-radius: 5px;
    color: #c5d0dc;
    cursor: pointer;
    display: inline-flex;
    font-size: 11px;
    gap: 7px;
    justify-content: center;
    padding: 7px 9px;
  }

  .ps2-code-shell {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }

  .ps2-code-path {
    align-items: center;
    border-bottom: 1px solid rgba(170, 190, 205, .12);
    color: #9faabc;
    display: flex;
    font-family: var(--mono);
    font-size: 11px;
    gap: 8px;
    min-height: 34px;
    padding: 0 14px;
  }

  .policy-studio-route .ps2-code-editor-wrap {
    background: rgba(8, 16, 22, .96);
    border: 0;
    border-radius: 0;
    display: grid;
    flex: 1;
    grid-template-columns: 50px minmax(0, 1fr) 96px;
    min-height: 0;
  }

  .policy-studio-route .ps2-code-gutter {
    background: rgba(255,255,255,.018);
    color: #778493;
    font-size: 13px;
    line-height: 1.85;
    padding: 14px 12px 14px 0;
  }

  .policy-studio-route .ps2-code-input-layer,
  .policy-studio-route .ps2-code-highlight {
    min-height: 520px;
  }

  .policy-studio-route .ps2-code-highlight {
    font-size: 13px;
    line-height: 1.85;
    padding: 14px 16px;
  }

  .policy-studio-route .ps2-code-textarea {
    color: transparent;
    font-size: 13px;
    line-height: 1.85;
    min-height: 520px;
    padding: 14px 16px;
  }

  .ps2-code-minimap {
    border-left: 1px solid rgba(170, 190, 205, .12);
    display: grid;
    gap: 5px;
    padding: 14px 12px;
    place-content: start stretch;
  }

  .ps2-code-minimap span {
    background: linear-gradient(90deg, #e45c7c 24%, #76d58f 24% 62%, #7fa7ff 62%);
    border-radius: 2px;
    height: 3px;
    justify-self: start;
    opacity: .55;
    max-width: 100%;
  }

  .ps2-code-status {
    align-items: center;
    border-top: 1px solid rgba(170, 190, 205, .12);
    color: #9faabc;
    display: flex;
    font-family: var(--mono);
    font-size: 10px;
    gap: 22px;
    justify-content: flex-end;
    min-height: 30px;
    padding: 0 14px;
  }

  .policy-studio-route .ps2-compile-bar {
    background: rgba(10, 20, 27, .92);
    border-top-color: rgba(170, 190, 205, .14);
    color: #b6c1ce;
    min-height: 34px;
    padding: 6px 14px;
  }

  .ps2-compile-action {
    background: rgba(147, 116, 255, .22);
    border: 1px solid rgba(147, 116, 255, .45);
    border-radius: 5px;
    color: #c9bbff;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    margin-left: auto;
    padding: 5px 12px;
  }

  .policy-studio-route .ps2-compile-pills {
    flex-wrap: nowrap;
    min-width: 0;
    overflow: hidden;
  }

  .policy-studio-route .ps2-co-pill {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .policy-studio-route .ps2-sim {
    background: rgba(8, 16, 22, .97);
    max-height: 245px;
  }

  .policy-studio-route .ps2-sim-body {
    display: grid;
    grid-template-columns: 1fr;
    max-height: 132px;
    overflow: auto;
    padding-bottom: 8px;
    padding-top: 6px;
  }

  .policy-studio-route .ps2-sim-head {
    align-items: center;
    gap: 12px;
    min-height: 40px;
  }

  .ps2-console-tabs {
    align-items: center;
    display: flex;
    gap: 6px;
    margin-left: auto;
  }

  .ps2-console-tabs button {
    background: transparent;
    border: 0;
    border-radius: 4px;
    color: #9da9b6;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    padding: 4px 8px;
  }

  .ps2-console-tabs button:first-child {
    background: rgba(147, 116, 255, .22);
    color: #c9bbff;
  }

  .ps2-console-tabs b {
    font-weight: 700;
  }

  .ps2-validation-grid {
    border-top: 1px solid rgba(170, 190, 205, .12);
    color: #b6c1ce;
    font-family: var(--mono);
    font-size: 10.5px;
  }

  .ps2-validation-row {
    display: grid;
    grid-template-columns: 120px 150px minmax(0, 1fr) 150px;
    min-height: 27px;
  }

  .ps2-validation-row span {
    align-items: center;
    border-bottom: 1px solid rgba(170, 190, 205, .10);
    display: flex;
    gap: 6px;
    min-width: 0;
    overflow: hidden;
    padding: 0 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ps2-validation-row.head {
    color: #7e8998;
    font-size: 9px;
    letter-spacing: .08em;
    text-transform: uppercase;
  }

  .ps2-validation-footer {
    align-items: center;
    color: #8f9baa;
    display: flex;
    font-family: var(--mono);
    font-size: 10px;
    gap: 20px;
    justify-content: space-between;
    min-height: 30px;
    padding: 0 12px;
  }

  .policy-studio-route .ps2-inspector {
    background: rgba(10, 18, 25, .97);
    border-left: 1px solid rgba(170, 190, 205, .16);
    width: auto;
  }

  .ps2-inspector-topbar {
    align-items: center;
    border-bottom: 1px solid rgba(170, 190, 205, .16);
    display: flex;
    flex-shrink: 0;
    gap: 12px;
    height: 48px;
    justify-content: flex-end;
    padding: 0 12px;
  }

  .ps2-inspector-topbar button {
    align-items: center;
    background: transparent;
    border: 1px solid rgba(180, 198, 214, .18);
    border-radius: 999px;
    color: #d7e0eb;
    cursor: pointer;
    display: inline-flex;
    font-family: var(--mono);
    font-size: 11px;
    height: 20px;
    justify-content: center;
    width: 20px;
  }

  .policy-studio-route .ps2-insp-top {
    align-items: end;
    gap: 16px;
    justify-content: center;
    min-height: 40px;
    padding: 0 12px;
  }

  .ps2-insp-tab {
    background: transparent;
    border: 0;
    border-bottom: 2px solid transparent;
    color: #9faabc;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .08em;
    padding: 0 4px 12px;
    text-transform: uppercase;
  }

  .ps2-insp-tab.active {
    border-bottom-color: #9b7cff;
    color: #c9bbff;
  }

  .policy-studio-route .ps2-insp-sec {
    padding: 14px 14px;
  }

  .policy-studio-route .ps2-review-card {
    background: transparent;
    border: 0;
    border-radius: 0;
    margin: 0;
    padding: 0;
  }

  .policy-studio-route .ps2-rc-row {
    align-items: start;
    border-bottom: 0;
    display: grid;
    gap: 12px;
    grid-template-columns: 92px minmax(0, 1fr);
    justify-content: start;
    padding: 5px 0;
  }

  .policy-studio-route .ps2-rc-key {
    color: #8d99aa;
    font-size: 11px;
    line-height: 1.35;
  }

  .policy-studio-route .ps2-rc-val {
    color: #d9e3ef;
    font-family: inherit;
    font-size: 11px;
    line-height: 1.4;
    overflow-wrap: anywhere;
    text-align: left;
  }

  .policy-studio-route .ps2-summary-box {
    background: transparent;
    border: 0;
    border-left: 0;
    border-radius: 0;
    color: #d2dbe6;
    font-size: 11px;
    line-height: 1.5;
    margin-top: 8px;
    padding: 6px 0 0;
  }

  .policy-studio-route .ps2-compiled-item,
  .policy-studio-route .ps2-dnode,
  .policy-studio-route .ps2-json-output {
    border-radius: 6px;
  }

  .ps2-tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .ps2-tag-row span {
    border: 1px solid rgba(180, 198, 214, .16);
    border-radius: 4px;
    color: #c8d2de;
    font-family: var(--mono);
    font-size: 10px;
    padding: 5px 7px;
  }

  @media (max-width: 900px) {
    .agcp-agent-hero,
    .agcp-evidence-lookup,
    .policy-workbench-grid,
    .policy-rule-grid {
      grid-template-columns: 1fr;
    }
  }

  .nav-item.disabled {
    cursor: default;
    opacity: .55;
  }

  .nav-item.disabled:hover {
    background: transparent;
    color: var(--text-muted);
  }
`;

/* ─── EXTENDED SIDEBAR ─── */
const ExtendedSidebar = ({ active, onNav, data }) => {
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
          label: "Access & Inventory",
          icon: "db",
          badge: null,
          href: "/access-data",
          children: [
            { label: "Access Matrix", href: "/access-data" },
            { label: "Data Sources", href: "/access-data" },
            { label: "Usage Profiles", href: "/access-data" }
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
  const isDataContext = activeItem.id === "data";
  const isPolicyContext = activeItem.id === "policies";
  const isEvidenceContext = activeItem.id === "evidence";
  const isReviewContext = activeItem.id === "reviews";
  const isIntegrationContext = activeItem.id === "integrations";
  const hasSavedView = activeItem.id === "data";
  const quickFilters = isEvidenceContext
    ? ["Runs with approvals", "Denied decisions", "Runs with escalations", "Exports created"]
    : isReviewContext
    ? ["Pending review", "Needs owner", "Exception request", "Recently approved"]
    : isIntegrationContext
    ? ["Connected", "Design-only", "Service actors", "Audit linked"]
    : ["Active", "Pending Review", "Suspended", "Expired"];

  return (
    <aside className={`sidebar ${isPolicyContext ? "rail-only" : ""}`}>
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

      {isPolicyContext ? null : (
      <div className="sidebar-context">
        <div className="logo-area">
          <div className="logo-mark">
            <div className="logo-text">
              <div className="brand">AGCP Studio</div>
            </div>
          </div>
        </div>

        <div className="context-panel">
          <div className="context-module">
            <span className="context-module-icon"><Icon name={activeItem.icon} size={24} /></span>
            <div>
              <div className="context-module-title">{activeItem.label}</div>
              <div className="context-module-sub">Agent Governance Control Plane</div>
            </div>
          </div>

          <div className="context-divider" />

          {isPolicyContext ? (
            <div className="policy-context-stack">
              <div className="policy-context-label">Studio focus</div>
              <div className="policy-repo-card">
                <Icon name="shield" size={18} />
                <div>
                  <div className="policy-repo-name">Policy authoring</div>
                  <div className="policy-repo-sub">Repository, blocks, code, versions, compile, and inspector live in the editor workspace.</div>
                </div>
              </div>
              <div className="policy-empty-note">Use the editor controls inside Policy Studio for search, refresh, save draft, submit review, compile, and new policy actions.</div>
            </div>
          ) : (
            <>
              <div className="context-filters">
                <div className="context-filter-head">
                  <span>Filters</span>
                  <button type="button">Clear</button>
                </div>

                {isDataContext ? (
                  <>
                    <label className="context-field">
                      <span>Agent</span>
                      <select defaultValue="all"><option value="all">All agents</option></select>
                    </label>
                    <label className="context-field search">
                      <span>Search</span>
                      <div><input placeholder="Search agents..." /><Icon name="search" size={14} /></div>
                    </label>
                    <label className="context-field">
                      <span>Access Grant status</span>
                      <select defaultValue="all"><option value="all">All</option></select>
                    </label>
                    <label className="context-field">
                      <span>Governance boundary</span>
                      <select defaultValue="all"><option value="all">All</option></select>
                    </label>
                  </>
                ) : (
                  <>
                    <label className="context-field">
                      <span>Environment</span>
                      <select defaultValue="production">
                        <option value="production">Production</option>
                        <option value="development">Development</option>
                      </select>
                    </label>
                    <label className="context-field">
                      <span>{isEvidenceContext ? "Policy Decision" : "Status"}</span>
                      <select defaultValue="all"><option value="all">All</option></select>
                    </label>
                  </>
                )}

                <div className="context-quick">
                  {quickFilters.map((filter, index) => (
                    <button type="button" key={filter}>
                      <span className={`dot dot-${index % 4}`} />
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              {hasSavedView ? (
                <button type="button" className="context-save">
                  <Icon name="archive" size={16} />
                  Save view
                </button>
              ) : null}
            </>
          )}
        </div>

      </div>
      )}
    </aside>
  );
};

/* ─── EXTENDED TOPBAR ─── */
const ExtendedTopbar = ({ title }) => (
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
        <span className="notif-dot">3</span>
      </Link>
      <Link className="icon-btn" href="/settings" aria-label="Help">
        <Icon name="help" size={18} />
      </Link>
      <Link className="topbar-profile" href="/settings" aria-label="User settings">
        <span className="topbar-avatar">AD</span>
        <span className="topbar-profile-copy">
          <span className="topbar-profile-name">Alex Dev</span>
          <span className="topbar-profile-role">Governance Admin</span>
        </span>
        <span className="topbar-profile-chevron" aria-hidden="true">
          <Icon name="chevron_down" size={12} />
        </span>
      </Link>
    </div>
  </header>
);

export function AGCPStudioDashboard() {
  const studioData = useAGCPStudioData();

  return <CommandView data={studioData} />;
}

export function AGCPStudioShell({ children }) {
  const [mode, setMode] = useState("live");
  const [theme, setTheme] = useState("dark");
  const [pendingApprovals, setPendingApprovals] = useState(0);
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

    return () => controller.abort();
  }, [pathname]);

  const shellData = { pendingApprovals, approvals: [] };
  const content =
    pathname === "/"
      ? children
      : <main className="content agcp-connected-content">{children}</main>;

  return (
    <>
      <style>{CSS}</style>
      <style>{CSS_STUDIO}</style>
      <style>{AGCP_CONNECTED_CSS}</style>
      <div
        className="shell"
        data-theme={theme}
        data-nav-density={navDensity}
      >
        <ExtendedSidebar active={routeView.view} onNav={() => undefined} data={shellData} />
        <div className="main">
          <ExtendedTopbar title={routeView.label} />
          {content}
        </div>
      </div>
    </>
  );
}

/* ─── ROOT ─── */
export function AGCPStudio() {
  return (
    <AGCPStudioShell>
      <AGCPStudioDashboard />
    </AGCPStudioShell>
  );
}

export default AGCPStudio;
