import React, { createContext, useContext, useState, useEffect } from "react";
import { apiErrorMessage, clearSession, storeSession } from "../services/apiAuth";

export type RoleType =
  | "FARMER"
  | "VETERINARIAN"
  | "LAB_TECHNICIAN"
  | "DISTRICT_OFFICER"
  | "STATE_OFFICER"
  | "SYSTEM_ADMIN";

export interface AuthUser {
  id: string;
  email: string;
  phone?: string;
  full_name: string;
  role: RoleType;
  district?: string;
  village?: string;
  license_number?: string;
  qualification?: string;
  designation?: string;
  department?: string;
}

export interface AuthResult {
  success: boolean;
  error?: string;
  user?: AuthUser;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  role: RoleType;
  setRole: (role: RoleType) => void;
  login: (email: string, pass: string) => Promise<AuthResult>;
  signup: (roleCategory: "farmer" | "vet" | "lab" | "government", payload: any) => Promise<AuthResult>;
  demoLogin: (role: RoleType) => Promise<void>;
  logout: () => void;
  wsStatus: "CONNECTED" | "RECONNECTING" | "OFFLINE" | "SYNCING";
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("auth_token"));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem("auth_user");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    // No implicit default user: unauthenticated visitors must sign in.
    return null;
  });

  const [wsStatus, setWsStatus] = useState<"CONNECTED" | "RECONNECTING" | "OFFLINE" | "SYNCING">("CONNECTED");

  // WebSocket real-time connection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: any = null;

    const connectWebSocket = () => {
      if (!navigator.onLine) {
        setWsStatus("OFFLINE");
        return;
      }

      const accessToken = localStorage.getItem("auth_token");
      if (!user || !accessToken) {
        setWsStatus("OFFLINE");
        return;
      }
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      // Identity is derived server-side from the token (sent as a subprotocol, not in the URL).
      const wsUrl = `${protocol}//${window.location.host}/api/v1/ws`;

      try {
        ws = new WebSocket(wsUrl, ["bearer", accessToken]);

        ws.onopen = () => {
          setWsStatus("CONNECTED");
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            window.dispatchEvent(new CustomEvent("pashu_realtime_event", { detail: data }));
          } catch {
            // raw msg
          }
        };

        ws.onclose = () => {
          setWsStatus(navigator.onLine ? "RECONNECTING" : "OFFLINE");
          reconnectTimer = setTimeout(connectWebSocket, 4000);
        };

        ws.onerror = () => {
          setWsStatus("OFFLINE");
        };
      } catch {
        setWsStatus("OFFLINE");
      }
    };

    connectWebSocket();

    const handleOnline = () => {
      setWsStatus("SYNCING");
      connectWebSocket();
    };
    const handleOffline = () => setWsStatus("OFFLINE");

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [user]);

  const demoLogin = async (targetRole: RoleType) => {
    // Only works when the backend explicitly enables demo login (never in production).
    // No client-side fallback identity is fabricated if it is unavailable.
    try {
      const res = await fetch(`/api/v1/auth/demo-login/${targetRole.toLowerCase()}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        storeSession(data);
        setToken(data.access_token);
        setUser(data.user);
      } else {
        window.dispatchEvent(new CustomEvent("pashu_toast", { detail: { type: "error", message: "Demo login is not enabled on this server." } }));
      }
    } catch {
      window.dispatchEvent(new CustomEvent("pashu_toast", { detail: { type: "error", message: "Server unreachable — cannot sign in while offline." } }));
    }
  };

  const login = async (email: string, pass: string): Promise<AuthResult> => {
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password: pass })
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        storeSession(data);
        setToken(data.access_token);
        setUser(data.user);
        return { success: true, user: data.user };
      }
      return { success: false, error: apiErrorMessage(data, "Invalid credentials. Please check your username and password.") };
    } catch (err: any) {
      return { success: false, error: err.message || "Network error during login." };
    }
  };

  const signup = async (
    roleCategory: "farmer" | "vet" | "lab" | "government",
    payload: any
  ): Promise<AuthResult> => {
    try {
      const endpoint =
        roleCategory === "farmer"
          ? "/api/v1/auth/signup/farmer"
          : roleCategory === "vet"
          ? "/api/v1/auth/signup/vet"
          : roleCategory === "lab"
          ? "/api/v1/auth/signup/lab"
          : "/api/v1/auth/signup/government";

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        storeSession(data);
        setToken(data.access_token);
        setUser(data.user);
        return { success: true, user: data.user };
      }
      return { success: false, error: apiErrorMessage(data, "Registration failed. Please check the entered fields.") };
    } catch (err: any) {
      return { success: false, error: err.message || "Network error during registration." };
    }
  };

  const setRole = (newRole: RoleType) => {
    demoLogin(newRole);
  };

  const logout = () => {
    // Revoke the server session (best effort), then clear local credentials.
    fetch("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    clearSession();
    setToken(null);
    setUser(null);
  };

  useEffect(() => {
    const onExpired = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("pashu_auth_expired", onExpired);
    return () => window.removeEventListener("pashu_auth_expired", onExpired);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        role: user?.role || "FARMER",
        setRole,
        login,
        signup,
        demoLogin,
        logout,
        wsStatus
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
