import React, { createContext, useContext, useState, useEffect } from "react";

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
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  role: RoleType;
  setRole: (role: RoleType) => void;
  login: (email: string, pass: string) => Promise<boolean>;
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
    // Default demo user is Farmer for instant ease of testing
    return {
      id: "FARMER-MH-001",
      email: "farmer@pashushield.gov.in",
      full_name: "Ramesh Tukaram Patil",
      role: "FARMER",
      district: "Pune",
      village: "Walwur"
    };
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

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/v1/ws?user_id=${user?.id || "anon"}&role=${user?.role || "FARMER"}&district=${user?.district || "Pune"}`;
      
      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setWsStatus("CONNECTED");
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            // Trigger storage or event
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
    try {
      const res = await fetch(`/api/v1/auth/demo-login/${targetRole.toLowerCase()}`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        setUser(data.user);
        localStorage.setItem("auth_token", data.access_token);
        localStorage.setItem("auth_user", JSON.stringify(data.user));
      } else {
        // Fallback local state if API is offline
        const fallbackUser: AuthUser = {
          id: `${targetRole}-DEMO`,
          email: `${targetRole.toLowerCase()}@pashushield.gov.in`,
          full_name: `Demo ${targetRole.replace("_", " ")}`,
          role: targetRole,
          district: "Pune",
          village: "Shirur"
        };
        setUser(fallbackUser);
        localStorage.setItem("auth_user", JSON.stringify(fallbackUser));
      }
    } catch {
      const fallbackUser: AuthUser = {
        id: `${targetRole}-DEMO`,
        email: `${targetRole.toLowerCase()}@pashushield.gov.in`,
        full_name: `Demo ${targetRole.replace("_", " ")}`,
        role: targetRole,
        district: "Pune",
        village: "Shirur"
      };
      setUser(fallbackUser);
      localStorage.setItem("auth_user", JSON.stringify(fallbackUser));
    }
  };

  const login = async (email: string, pass: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: pass })
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        setUser(data.user);
        localStorage.setItem("auth_token", data.access_token);
        localStorage.setItem("auth_user", JSON.stringify(data.user));
        return true;
      }
    } catch {
      // Login failed
    }
    return false;
  };

  const setRole = (newRole: RoleType) => {
    demoLogin(newRole);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        role: user?.role || "FARMER",
        setRole,
        login,
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
