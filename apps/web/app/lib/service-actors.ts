import { fetchApiArray } from "./api";

export type ServiceActorRecord = {
  id: string;
  actor_id: string;
  display_name: string;
  description: string | null;
  status: "active" | "disabled" | string;
  created_at: string;
  updated_at: string;
  disabled_at: string | null;
};

export type ServiceActorApiKeyRecord = {
  key_id: string;
  status: "active" | "retiring" | "revoked" | "expired" | string;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  last_used_at: string | null;
};

export type ServiceActorScopeRecord = {
  id: string;
  service_actor_id: string;
  scope: string;
  created_at: string;
};

export type ServiceActorScopeRuleRecord = {
  id: string;
  service_actor_id: string;
  agent_ids: string[];
  environments: string[];
  runtime_modes: string[];
  tool_names: string[];
  created_at: string;
  updated_at: string;
};

export type ServiceActorRegistrySummaryItem = {
  actor: ServiceActorRecord;
  apiKeys: ServiceActorApiKeyRecord[];
  scopeRules: ServiceActorScopeRuleRecord[];
  scopes: ServiceActorScopeRecord[];
};

export function fetchServiceActors(
  signal?: AbortSignal
): Promise<ServiceActorRecord[]> {
  return fetchApiArray<ServiceActorRecord>("/service-actors", {
    errorLabel: "GET /service-actors",
    signal
  });
}

export function fetchServiceActorApiKeys(
  serviceActorId: string,
  signal?: AbortSignal
): Promise<ServiceActorApiKeyRecord[]> {
  return fetchApiArray<ServiceActorApiKeyRecord>(
    `/service-actors/${encodeURIComponent(serviceActorId)}/api-keys`,
    {
      errorLabel: "GET /service-actors/{service_actor_id}/api-keys",
      signal
    }
  );
}

export function fetchServiceActorScopes(
  serviceActorId: string,
  signal?: AbortSignal
): Promise<ServiceActorScopeRecord[]> {
  return fetchApiArray<ServiceActorScopeRecord>(
    `/service-actors/${encodeURIComponent(serviceActorId)}/scopes`,
    {
      errorLabel: "GET /service-actors/{service_actor_id}/scopes",
      signal
    }
  );
}

export function fetchServiceActorScopeRules(
  serviceActorId: string,
  signal?: AbortSignal
): Promise<ServiceActorScopeRuleRecord[]> {
  return fetchApiArray<ServiceActorScopeRuleRecord>(
    `/service-actors/${encodeURIComponent(serviceActorId)}/scope-rules`,
    {
      errorLabel: "GET /service-actors/{service_actor_id}/scope-rules",
      signal
    }
  );
}

export async function fetchServiceActorRegistrySummary(
  signal?: AbortSignal
): Promise<ServiceActorRegistrySummaryItem[]> {
  const actors = await fetchServiceActors(signal);

  return Promise.all(
    actors.map(async (actor) => {
      const [apiKeys, scopes, scopeRules] = await Promise.all([
        fetchServiceActorApiKeys(actor.id, signal),
        fetchServiceActorScopes(actor.id, signal),
        fetchServiceActorScopeRules(actor.id, signal)
      ]);

      return {
        actor,
        apiKeys,
        scopes,
        scopeRules
      };
    })
  );
}
