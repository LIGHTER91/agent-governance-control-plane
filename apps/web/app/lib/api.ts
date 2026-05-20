const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_AGCP_API_BASE_URL;
  return (configuredUrl || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export async function fetchApiArray<T>(
  path: string,
  options: {
    errorLabel: string;
    searchParams?: URLSearchParams;
    signal?: AbortSignal;
  }
): Promise<T[]> {
  const query = options.searchParams?.toString();
  const url = `${getApiBaseUrl()}${path}${query ? `?${query}` : ""}`;

  const response = await fetch(url, {
    headers: {
      Accept: "application/json"
    },
    signal: options.signal
  });

  if (!response.ok) {
    throw new Error(`${options.errorLabel} failed with status ${response.status}`);
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new Error(`${options.errorLabel} returned an unexpected response shape`);
  }

  return data as T[];
}

export class ApiRequestError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export async function fetchApiJson<T>(
  path: string,
  options: {
    errorLabel: string;
    signal?: AbortSignal;
  }
): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: {
      Accept: "application/json"
    },
    signal: options.signal
  });

  if (!response.ok) {
    throw new ApiRequestError(
      `${options.errorLabel} failed with status ${response.status}`,
      response.status
    );
  }

  return (await response.json()) as T;
}
