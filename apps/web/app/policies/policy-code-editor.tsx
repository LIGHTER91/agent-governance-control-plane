"use client";

import { useLayoutEffect, useRef, type WheelEvent } from "react";

export function PolicyCodeEditor({
  dsl,
  onChange,
  policyTitle,
  policyVersion
}: {
  dsl: string;
  onChange: (dsl: string) => void;
  policyTitle: string;
  policyVersion: string;
}) {
  const lines = Math.max(1, dsl.split(/\r?\n/).length);
  const policyPath = slugifyPathSegment(policyTitle);
  const versionPath = slugifyPathSegment(policyVersion);
  const highlightedLines = dsl.split(/\r?\n/);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const highlightRef = useRef<HTMLPreElement | null>(null);
  const gutterRef = useRef<HTMLDivElement | null>(null);
  const editorWrapRef = useRef<HTMLDivElement | null>(null);

  const syncCodeScroll = () => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    if (editorWrapRef.current) {
      editorWrapRef.current.scrollTop = 0;
      editorWrapRef.current.scrollLeft = 0;
    }
    if (highlightRef.current) {
      highlightRef.current.scrollTop = textarea.scrollTop;
      highlightRef.current.scrollLeft = textarea.scrollLeft;
    }
    if (gutterRef.current) {
      gutterRef.current.scrollTop = textarea.scrollTop;
    }
  };

  const handleEditorWheel = (event: WheelEvent<HTMLDivElement>) => {
    const textarea = textareaRef.current;
    if (!textarea || event.target === textarea) {
      return;
    }

    event.preventDefault();
    textarea.scrollTop += event.deltaY;
    textarea.scrollLeft += event.deltaX;
    syncCodeScroll();
  };

  useLayoutEffect(() => {
    syncCodeScroll();
  }, [dsl]);

  return (
    <div className="ps2-code-shell">
      <div className="ps2-code-path">
        <span>policies</span>
        <span>/</span>
        <span>{policyPath}</span>
        <span>/</span>
        <strong>{versionPath}</strong>
      </div>
      <div className="ps2-code-editor-wrap" onWheel={handleEditorWheel} ref={editorWrapRef}>
        <div className="ps2-code-gutter" aria-hidden="true" ref={gutterRef}>
          {Array.from({ length: lines }, (_, index) => (
            <span key={index}>{index + 1}</span>
          ))}
        </div>
        <div className="ps2-code-input-layer">
          <pre className="ps2-code-highlight" aria-hidden="true" ref={highlightRef}>
            {highlightedLines.map((line, lineIndex) => (
              <span className="ps2-code-highlight-line" key={`${lineIndex}-${line}`}>
                {renderHighlightedDslLine(line)}
              </span>
            ))}
          </pre>
          <textarea
            aria-label="Code DSL editor"
            className="ps2-code-textarea"
            onChange={(event) => onChange(event.target.value)}
            onScroll={syncCodeScroll}
            ref={textareaRef}
            spellCheck={false}
            value={dsl}
            wrap="off"
          />
        </div>
        <div className="ps2-code-minimap" aria-hidden="true">
          {Array.from({ length: Math.min(lines, 22) }, (_, index) => (
            <span
              key={index}
              style={{ width: `${minimapLineWidth(highlightedLines[index] || "")}%` }}
            />
          ))}
        </div>
      </div>
      <div className="ps2-code-status" aria-hidden="true">
        <span>DSL</span>
        <span>{lines} lines</span>
        <span>UTF-8</span>
        <span>Spaces: 2</span>
        <span>Local editor state</span>
      </div>
    </div>
  );
}

function minimapLineWidth(line: string) {
  const trimmedLength = line.trim().length;
  if (trimmedLength === 0) {
    return 14;
  }
  return Math.min(92, Math.max(18, trimmedLength * 2));
}

function renderHighlightedDslLine(line: string) {
  const parts = line.split(
    /(".*?"|\bpolicy\b|\bversion\b|\bwhen\b|\bcheck\b|\bthen\b|\bprove\b|\bmeta\b|\brequires\b|\brequired\b|\breason\b|\breviewer_group\b|\binclude\b|\bdays\b|\bowner\b|\bdescription\b|\btrue\b|\bfalse\b|\d+|==|=|\b[A-Za-z_][A-Za-z0-9_.]*\b)/g
  );

  return parts.map((part, index) => {
    if (!part) {
      return null;
    }

    const className = dslTokenClass(part);
    return className ? (
      <span className={className} key={`${part}-${index}`}>
        {part}
      </span>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    );
  });
}

function dslTokenClass(token: string) {
  if (/^".*"$/.test(token)) {
    return "ps2-token-string";
  }
  if (/^\d+$/.test(token)) {
    return "ps2-token-number";
  }
  if (token === "==" || token === "=") {
    return "ps2-token-operator";
  }
  if (/^(policy|when|check|then|prove|meta)$/.test(token)) {
    return "ps2-token-keyword";
  }
  if (/^(version|requires|required|reason|reviewer_group|include|days|owner|description)$/.test(token)) {
    return "ps2-token-control";
  }
  if (/^(true|false)$/.test(token)) {
    return "ps2-token-number";
  }
  if (token.includes(".")) {
    return "ps2-token-field";
  }
  if (/^[A-Z][A-Za-z0-9_]*$/.test(token)) {
    return "ps2-token-type";
  }
  return "";
}

function slugifyPathSegment(value: string) {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "draft"
  );
}
