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
  detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

async function errorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return undefined;
    }
  }

  try {
    return await response.text();
  } catch {
    return undefined;
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
    const detail = await errorDetail(response);
    throw new ApiRequestError(
      `${options.errorLabel} failed with status ${response.status}`,
      response.status,
      detail
    );
  }

  return (await response.json()) as T;
}

export async function postApiJson<T>(
  path: string,
  options: {
    body?: object;
    errorLabel: string;
    signal?: AbortSignal;
  }
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json"
  };
  const body =
    options.body === undefined ? undefined : JSON.stringify(options.body);

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    body,
    headers,
    method: "POST",
    signal: options.signal
  });

  if (!response.ok) {
    const detail = await errorDetail(response);
    throw new ApiRequestError(
      `${options.errorLabel} failed with status ${response.status}`,
      response.status,
      detail
    );
  }

  return (await response.json()) as T;
}

export async function patchApiJson<T>(
  path: string,
  options: {
    body: object;
    errorLabel: string;
    signal?: AbortSignal;
  }
): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    body: JSON.stringify(options.body),
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    method: "PATCH",
    signal: options.signal
  });

  if (!response.ok) {
    const detail = await errorDetail(response);
    throw new ApiRequestError(
      `${options.errorLabel} failed with status ${response.status}`,
      response.status,
      detail
    );
  }

  return (await response.json()) as T;
}
