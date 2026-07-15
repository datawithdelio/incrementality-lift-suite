export const SESSION_TOKEN_KEY = "incrementality_session_token";
export const WORKSPACE_ID_KEY = "incrementality_workspace_id";

type LoginResponse = {
  user_id: string;
  session_token: string;
  token_type: "bearer";
  expires_at: string;
};

type RegistrationResponse = {
  organization_id: string;
  workspace_id: string;
  owner_user_id: string;
  owner_membership_id: string;
};

export class AuthenticationError extends Error {}

async function post<T>(path: string, body: object): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new AuthenticationError(payload?.detail ?? "We couldn't complete that request. Please try again.");
  }

  return await response.json() as T;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return post<LoginResponse>("/api/v1/auth/login", { email, password });
}

export function register(input: {
  displayName: string;
  organizationName: string;
  email: string;
  password: string;
}): Promise<RegistrationResponse> {
  const baseSlug = input.organizationName
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "workspace";

  return post<RegistrationResponse>("/api/v1/tenants", {
    organization_name: input.organizationName,
    organization_slug: baseSlug,
    workspace_name: `${input.organizationName} Measurement`,
    workspace_slug: `${baseSlug}-measurement`,
    owner_email: input.email,
    owner_display_name: input.displayName,
    owner_password: input.password,
  });
}
