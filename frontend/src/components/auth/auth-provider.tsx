"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  type LoginResponse,
  logout,
  SESSION_TOKEN_KEY,
  validateSession,
  WORKSPACE_ID_KEY,
} from "../../lib/auth/api";

type AuthStatus = "checking" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  userId: string | null;
  sessionNotice: string | null;
  establishSession: (session: LoginResponse) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function clearStoredAuthentication() {
  window.localStorage.removeItem(SESSION_TOKEN_KEY);
  window.localStorage.removeItem("incrementality_session_expires_at");
  window.localStorage.removeItem(WORKSPACE_ID_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const token = window.localStorage.getItem(
      SESSION_TOKEN_KEY,
    );

    if (!token) {
      void Promise.resolve().then(() => {
        if (!active) return;

        setSessionNotice(null);
        setStatus("unauthenticated");
      });

      return () => {
        active = false;
      };
    }

    void validateSession(token)
      .then((session) => {
        if (!active) return;

        setUserId(session.user_id);
        setSessionNotice(null);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!active) return;

        clearStoredAuthentication();
        setUserId(null);
        setSessionNotice(
          "Your session expired. Please sign in again.",
        );
        setStatus("unauthenticated");
      });

    return () => {
      active = false;
    };
  }, []);

  const establishSession = useCallback(
    (session: LoginResponse) => {
      window.localStorage.setItem(
        SESSION_TOKEN_KEY,
        session.session_token,
      );
      window.localStorage.setItem(
        "incrementality_session_expires_at",
        session.expires_at,
      );

      setUserId(session.user_id);
      setSessionNotice(null);
      setStatus("authenticated");
    },
    [],
  );

  const signOut = useCallback(async () => {
    const token = window.localStorage.getItem(
      SESSION_TOKEN_KEY,
    );

    try {
      if (token) {
        await logout(token);
      }
    } finally {
      clearStoredAuthentication();
      setUserId(null);
      setSessionNotice(null);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      userId,
      sessionNotice,
      establishSession,
      signOut,
    }),
    [
      status,
      userId,
      sessionNotice,
      establishSession,
      signOut,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
}
