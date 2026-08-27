"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  getMe,
  loginWithEmail,
  listWorkspaces,
  createWorkspace as apiCreateWorkspace,
  setStoredWorkspace,
  setStoredToken,
  getStoredWorkspace,
  UserProfile,
  WorkspaceInfo,
  AuthMeResponse,
} from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  workspace: WorkspaceInfo | null;
  workspaces: WorkspaceInfo[];
  stats: {
    total_research_jobs: number;
    saved_reports: number;
    credits_used: number;
    credit_limit: number;
  };
  isLoading: boolean;
  refreshAuth: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  createNewWorkspace: (name: string) => Promise<void>;
  login: (email: string, name?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [stats, setStats] = useState({
    total_research_jobs: 0,
    saved_reports: 0,
    credits_used: 0,
    credit_limit: 50,
  });
  const [isLoading, setIsLoading] = useState(true);

  const fetchAuth = useCallback(async () => {
    try {
      const data: AuthMeResponse = await getMe();
      setUser(data.user);
      setWorkspace(data.workspace);
      setWorkspaces(data.workspaces || [data.workspace]);
      setStats(data.stats);
      if (data.workspace?.id) {
        setStoredWorkspace(data.workspace.id);
      }
    } catch (err) {
      console.warn("Failed to fetch auth me, falling back to guest demo mode:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAuth();
  }, [fetchAuth]);

  const switchWorkspace = async (workspaceId: string) => {
    setStoredWorkspace(workspaceId);
    await fetchAuth();
  };

  const createNewWorkspace = async (name: string) => {
    const ws = await apiCreateWorkspace(name);
    setStoredWorkspace(ws.id);
    await fetchAuth();
  };

  const login = async (email: string, name?: string) => {
    setIsLoading(true);
    await loginWithEmail(email, name);
    await fetchAuth();
  };

  const logout = () => {
    setStoredToken(null);
    setStoredWorkspace(null);
    setUser(null);
    setWorkspace(null);
    setWorkspaces([]);
    fetchAuth();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspace,
        workspaces,
        stats,
        isLoading,
        refreshAuth: fetchAuth,
        switchWorkspace,
        createNewWorkspace,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
