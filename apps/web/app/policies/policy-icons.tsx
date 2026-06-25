"use client";

export type PolicyIconName =
  | "archive"
  | "arrowRight"
  | "blocks"
  | "check"
  | "chevronDown"
  | "code"
  | "error"
  | "expand"
  | "filter"
  | "folder"
  | "help"
  | "info"
  | "more"
  | "plus"
  | "policy"
  | "prove"
  | "refresh"
  | "repository"
  | "save"
  | "search"
  | "send"
  | "settings"
  | "sparkle"
  | "then"
  | "warning"
  | "when"
  | "zoom";

export function PolicyIcon({
  className,
  name,
  size = 16,
  title
}: {
  className?: string;
  name: PolicyIconName;
  size?: number;
  title?: string;
}) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.7
  };

  return (
    <svg
      aria-hidden={title ? undefined : true}
      aria-label={title}
      className={className}
      height={size}
      role={title ? "img" : undefined}
      viewBox="0 0 24 24"
      width={size}
    >
      {iconPath(name, common)}
    </svg>
  );
}

function iconPath(
  name: PolicyIconName,
  common: {
    fill: string;
    stroke: string;
    strokeLinecap: "round";
    strokeLinejoin: "round";
    strokeWidth: number;
  }
) {
  switch (name) {
    case "archive":
      return (
        <>
          <path {...common} d="M4 7h16" />
          <path {...common} d="M6 7v11a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7" />
          <path {...common} d="M8 4h8l2 3H6l2-3Z" />
          <path {...common} d="M10 12h4" />
        </>
      );
    case "arrowRight":
      return (
        <>
          <path {...common} d="M4 12h14" />
          <path {...common} d="m13 6 6 6-6 6" />
        </>
      );
    case "blocks":
      return (
        <>
          <rect {...common} height="6" rx="1.5" width="6" x="4" y="4" />
          <rect {...common} height="6" rx="1.5" width="6" x="14" y="4" />
          <rect {...common} height="6" rx="1.5" width="6" x="4" y="14" />
          <rect {...common} height="6" rx="1.5" width="6" x="14" y="14" />
        </>
      );
    case "check":
      return (
        <>
          <path {...common} d="M12 3 5 6v5c0 4.2 2.8 7.5 7 10 4.2-2.5 7-5.8 7-10V6l-7-3Z" />
          <path {...common} d="m8.8 12 2.1 2.1 4.4-4.8" />
        </>
      );
    case "chevronDown":
      return <path {...common} d="m7 10 5 5 5-5" />;
    case "code":
      return (
        <>
          <path {...common} d="m9 8-4 4 4 4" />
          <path {...common} d="m15 8 4 4-4 4" />
          <path {...common} d="m13 5-2 14" />
        </>
      );
    case "error":
      return (
        <>
          <circle {...common} cx="12" cy="12" r="8.5" />
          <path {...common} d="m9 9 6 6M15 9l-6 6" />
        </>
      );
    case "expand":
      return (
        <>
          <path {...common} d="M8 4H4v4" />
          <path {...common} d="M16 4h4v4" />
          <path {...common} d="M8 20H4v-4" />
          <path {...common} d="M16 20h4v-4" />
        </>
      );
    case "filter":
      return (
        <>
          <path {...common} d="M4 5h16l-6.5 7.2V18l-3 1.5v-7.3L4 5Z" />
        </>
      );
    case "folder":
      return (
        <>
          <path {...common} d="M3.5 7.5h6l2 2H20a1.5 1.5 0 0 1 1.5 1.5v6A2.5 2.5 0 0 1 19 19.5H5A2.5 2.5 0 0 1 2.5 17V9A1.5 1.5 0 0 1 4 7.5Z" />
          <path {...common} d="M3.5 9.5V6A1.5 1.5 0 0 1 5 4.5h4l2 2h5" />
        </>
      );
    case "help":
      return (
        <>
          <circle {...common} cx="12" cy="12" r="8.5" />
          <path {...common} d="M9.6 9a2.5 2.5 0 0 1 4.9.8c0 1.8-2.2 2-2.2 3.7" />
          <path {...common} d="M12 17h.01" />
        </>
      );
    case "info":
      return (
        <>
          <circle {...common} cx="12" cy="12" r="8.5" />
          <path {...common} d="M12 10v6" />
          <path {...common} d="M12 7.5h.01" />
        </>
      );
    case "more":
      return (
        <>
          <circle cx="6" cy="12" fill="currentColor" r="1.25" />
          <circle cx="12" cy="12" fill="currentColor" r="1.25" />
          <circle cx="18" cy="12" fill="currentColor" r="1.25" />
        </>
      );
    case "plus":
      return (
        <>
          <path {...common} d="M12 5v14" />
          <path {...common} d="M5 12h14" />
        </>
      );
    case "policy":
      return (
        <>
          <path {...common} d="M12 3 5 6.5v5.2c0 4 2.8 7 7 9.3 4.2-2.3 7-5.3 7-9.3V6.5L12 3Z" />
          <path {...common} d="M9 12h6" />
          <path {...common} d="M10 15h4" />
        </>
      );
    case "prove":
      return (
        <>
          <path {...common} d="M7 3.5h7l3 3V20a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 6 20V5A1.5 1.5 0 0 1 7.5 3.5Z" />
          <path {...common} d="M14 3.5V7h3" />
          <path {...common} d="M9 12h6M9 15h6" />
        </>
      );
    case "refresh":
      return (
        <>
          <path {...common} d="M20 11a8 8 0 0 0-14.2-4.8L4 8" />
          <path {...common} d="M4 4v4h4" />
          <path {...common} d="M4 13a8 8 0 0 0 14.2 4.8L20 16" />
          <path {...common} d="M20 20v-4h-4" />
        </>
      );
    case "repository":
      return (
        <>
          <rect {...common} height="15" rx="2" width="12" x="6" y="4.5" />
          <path {...common} d="M9 4.5v15" />
          <path {...common} d="M12 8h3M12 11h3" />
        </>
      );
    case "save":
      return (
        <>
          <path {...common} d="M5 4h11l3 3v13H5V4Z" />
          <path {...common} d="M8 4v6h7V4" />
          <path {...common} d="M8 20v-5h8v5" />
        </>
      );
    case "search":
      return (
        <>
          <circle {...common} cx="10.5" cy="10.5" r="5.8" />
          <path {...common} d="m15 15 4.5 4.5" />
        </>
      );
    case "send":
      return (
        <>
          <path {...common} d="M21 3 10 14" />
          <path {...common} d="m21 3-7 18-4-7-7-4 18-7Z" />
        </>
      );
    case "settings":
      return (
        <>
          <path {...common} d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" />
          <path {...common} d="M19 12a7.2 7.2 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a7.6 7.6 0 0 0-1.8-1L14.4 3h-4.8l-.3 3a7.6 7.6 0 0 0-1.8 1L5 6l-2 3.5L5 11a7.2 7.2 0 0 0 0 2l-2 1.5L5 18l2.5-1a7.6 7.6 0 0 0 1.8 1l.3 3h4.8l.3-3a7.6 7.6 0 0 0 1.8-1l2.4 1 2-3.5-2-1.5c.1-.3.1-.7.1-1Z" />
        </>
      );
    case "sparkle":
      return (
        <>
          <path {...common} d="M12 3v5" />
          <path {...common} d="M12 16v5" />
          <path {...common} d="M3 12h5" />
          <path {...common} d="M16 12h5" />
          <path {...common} d="m6.5 6.5 3 3" />
          <path {...common} d="m14.5 14.5 3 3" />
          <path {...common} d="m17.5 6.5-3 3" />
          <path {...common} d="m9.5 14.5-3 3" />
        </>
      );
    case "then":
      return (
        <>
          <circle {...common} cx="12" cy="12" r="8.5" />
          <path {...common} d="m8.8 12.2 2 2 4.5-5" />
        </>
      );
    case "warning":
      return (
        <>
          <path {...common} d="M12 4 3.5 19h17L12 4Z" />
          <path {...common} d="M12 9v5" />
          <path {...common} d="M12 17h.01" />
        </>
      );
    case "when":
      return (
        <>
          <circle {...common} cx="12" cy="12" r="8.5" />
          <path {...common} d="M12 7v5l3 2" />
        </>
      );
    case "zoom":
      return (
        <>
          <rect {...common} height="14" rx="2" width="14" x="5" y="5" />
          <path {...common} d="M9 12h6M12 9v6" />
        </>
      );
  }
}
