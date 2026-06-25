const DEFAULT_API_BASE_URL = "http://localhost:8000";

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

  const response = await fetchAgcpApi(
    url,
    {
      headers: {
        Accept: "application/json"
      },
      signal: options.signal
    },
    options.errorLabel
  );

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

export class ApiNetworkError extends Error {
  url: string;

  constructor(message: string, url: string) {
    super(message);
    this.name = "ApiNetworkError";
    this.url = url;
  }
}

async function fetchAgcpApi(
  url: string,
  init: RequestInit,
  errorLabel: string
) {
  try {
    return await fetch(url, init);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }

    throw new ApiNetworkError(
      `${errorLabel} could not reach AGCP API at ${getApiBaseUrl()}.`,
      url
    );
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
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetchAgcpApi(
    url,
    {
      headers: {
        Accept: "application/json"
      },
      signal: options.signal
    },
    options.errorLabel
  );

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

  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetchAgcpApi(
    url,
    {
      body,
      headers,
      method: "POST",
      signal: options.signal
    },
    options.errorLabel
  );

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
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetchAgcpApi(
    url,
    {
      body: JSON.stringify(options.body),
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      method: "PATCH",
      signal: options.signal
    },
    options.errorLabel
  );

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

export async function deleteApi(
  path: string,
  options: {
    errorLabel: string;
    signal?: AbortSignal;
  }
): Promise<void> {
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetchAgcpApi(
    url,
    {
      headers: {
        Accept: "application/json"
      },
      method: "DELETE",
      signal: options.signal
    },
    options.errorLabel
  );

  if (!response.ok) {
    const detail = await errorDetail(response);
    throw new ApiRequestError(
      `${options.errorLabel} failed with status ${response.status}`,
      response.status,
      detail
    );
  }
}
