import { fetchApiJson } from "./api";

export type CurrentActorRecord = {
  actor_type: string;
  actor_id: string;
  roles: string[];
  display_name: string | null;
  environment: string;
  dev_mode_caveat: string | null;
};

export async function fetchCurrentActor(
  signal?: AbortSignal
): Promise<CurrentActorRecord> {
  return fetchApiJson<CurrentActorRecord>("/me", {
    errorLabel: "GET /me",
    signal
  });
}
