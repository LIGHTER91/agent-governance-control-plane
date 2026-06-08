"use client";

export function PolicyCodeEditor({
  dsl,
  onChange
}: {
  dsl: string;
  onChange: (dsl: string) => void;
}) {
  const lines = Math.max(1, dsl.split(/\r?\n/).length);

  return (
    <div className="ps2-code-editor-wrap">
      <div className="ps2-code-gutter" aria-hidden="true">
        {Array.from({ length: lines }, (_, index) => (
          <span key={index}>{index + 1}</span>
        ))}
      </div>
      <textarea
        aria-label="Code DSL editor"
        className="ps2-code-textarea"
        onChange={(event) => onChange(event.target.value)}
        spellCheck={false}
        value={dsl}
      />
      <div className="ps2-code-legend" aria-hidden="true">
        <span className="ps2-ck">policy</span>
        <span className="ps2-ck2">scope</span>
        <span className="ps2-cn">field</span>
        <span className="ps2-cs">"value"</span>
        <span className="ps2-cr">required</span>
        <span className="ps2-cf">then</span>
      </div>
    </div>
  );
}
