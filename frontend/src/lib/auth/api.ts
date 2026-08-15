export const SESSION_TOKEN_KEY = "incrementality_session_token";
export const WORKSPACE_ID_KEY = "incrementality_workspace_id";
const AUTH_REQUEST_TIMEOUT_MS = 45_000;

export type LoginResponse = {
  user_id: string;
  session_token: string;
  token_type: "bearer";
  expires_at: string;
};

export type SessionResponse = {
  session_id: string;
  user_id: string;
  expires_at: string;
};

type RegistrationResponse = {
  user_id: string;
};

export class AuthenticationError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "AuthenticationError";
  }
}

export class RegistrationConflictError extends AuthenticationError {
  constructor() {
    super(
      "An account with this email already exists.",
      409,
    );
    this.name = "RegistrationConflictError";
  }
}

async function authFetch(
  input: RequestInfo | URL,
  init: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  let didTimeOut = false;
  const timeout = window.setTimeout(() => {
    didTimeOut = true;
    controller.abort();
  }, AUTH_REQUEST_TIMEOUT_MS);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (didTimeOut) {
      throw new AuthenticationError(
        "The demo server is taking too long to respond. Please try again.",
      );
    }

    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function post<T>(path: string, body: object): Promise<T> {
  let response: Response;

  try {
    response = await authFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new AuthenticationError(
      "We couldn't reach the server. Please check your connection and try again.",
    );
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new AuthenticationError(
      payload?.detail ?? "We couldn't complete that request. Please try again.",
      response.status,
    );
  }

  return await response.json() as T;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return post<LoginResponse>("/api/v1/auth/login", { email, password });
}

export async function validateSession(token: string): Promise<SessionResponse> {
  const response = await authFetch("/api/v1/auth/session", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new AuthenticationError(
      payload?.detail ?? "Your session could not be restored. Please sign in again.",
    );
  }

  return await response.json() as SessionResponse;
}

export async function logout(token: string): Promise<void> {
  const response = await authFetch("/api/v1/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok && response.status !== 401) {
    throw new AuthenticationError("We couldn't sign you out cleanly.");
  }
}

export async function register(input: {
  displayName: string;
  email: string;
  password: string;
}): Promise<RegistrationResponse> {
  try {
    return await post<RegistrationResponse>("/api/v1/auth/register", {
      email: input.email,
      display_name: input.displayName,
      password: input.password,
    });
  } catch (error) {
    if (
      error instanceof AuthenticationError &&
      error.status === 409
    ) {
      throw new RegistrationConflictError();
    }

    throw error;
  }
}
