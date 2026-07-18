export const SESSION_TOKEN_KEY = "incrementality_session_token";
export const WORKSPACE_ID_KEY = "incrementality_workspace_id";

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

export class AuthenticationError extends Error {}

async function post<T>(path: string, body: object): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path, {
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
    );
  }

  return await response.json() as T;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return post<LoginResponse>("/api/v1/auth/login", { email, password });
}

export async function validateSession(token: string): Promise<SessionResponse> {
  const response = await fetch("/api/v1/auth/session", {
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
  const response = await fetch("/api/v1/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok && response.status !== 401) {
    throw new AuthenticationError("We couldn't sign you out cleanly.");
  }
}

export function register(input: {
  displayName: string;
  email: string;
  password: string;
}): Promise<RegistrationResponse> {
  return post<RegistrationResponse>("/api/v1/auth/register", {
    email: input.email,
    display_name: input.displayName,
    password: input.password,
  });
}
