"use client";

import { AGCPStudioDashboard, AGCPStudioShell } from "./AGCPStudioShell";

export { AGCPStudioDashboard, AGCPStudioShell };

export function AGCPStudio() {
  return (
    <AGCPStudioShell>
      <AGCPStudioDashboard />
    </AGCPStudioShell>
  );
}

export default AGCPStudio;
