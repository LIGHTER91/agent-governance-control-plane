"use client";

import { POLICY_TEMPLATES, PolicyTemplate } from "./policy-dsl";

export function PolicyTemplatesDrawer({
  onClose,
  onUseTemplate
}: {
  onClose: () => void;
  onUseTemplate: (template: PolicyTemplate) => void;
}) {
  return (
    <div className="ps2-drawer" onClick={onClose}>
      <div className="ps2-drawer-panel" onClick={(event) => event.stopPropagation()}>
        <div className="ps2-drawer-head">
          <div>
            <div className="ps2-drawer-title">Policy Templates</div>
            <div className="ps2-drawer-sub">
              Built-in authoring helpers. Using one creates an unsaved local
              draft only.
            </div>
          </div>
          <button className="ps2-drawer-close" onClick={onClose} type="button">
            x
          </button>
        </div>
        <div className="ps2-drawer-cats">
          {["All", "Access", "Review", "Evidence", "Risk"].map((category) => (
            <button
              className={`ps2-drawer-cat ${category === "All" ? "active" : ""}`}
              key={category}
              type="button"
            >
              {category}
            </button>
          ))}
        </div>
        <div className="ps2-tmpl-grid">
          {POLICY_TEMPLATES.map((template) => (
            <button
              className={`ps2-tmpl-card ${template.className}`}
              key={template.id}
              onClick={() => {
                onUseTemplate(template);
                onClose();
              }}
              type="button"
            >
              <span className="ps2-tmpl-name">{template.name}</span>
              <span className="ps2-tmpl-desc">{template.description}</span>
              <span className="ps2-tmpl-footer">
                {template.tags.map((tag) => (
                  <span className="ps2-tmpl-tag" key={tag}>
                    {tag}
                  </span>
                ))}
                <span className="ps2-tmpl-use">Use template</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
