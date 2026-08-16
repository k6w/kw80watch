import { create } from "zustand";

interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: string;
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  fetchUser: () => Promise<void>;
  signUp: (username: string, email: string, password: string) => Promise<boolean>;
  signIn: (email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,

  fetchUser: async () => {
    try {
      const res = await fetch("/api/me");
      const data = await res.json();
      set({ user: data.user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  signUp: async (username, email, password) => {
    try {
      const res = await fetch("/api/auth/sign-up", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username,
          email,
          password,
          name: username,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        console.error(err);
        return false;
      }
      await useAuth.getState().fetchUser();
      return true;
    } catch (e) {
      console.error(e);
      return false;
    }
  },

  signIn: async (email, password) => {
    try {
      const res = await fetch("/api/auth/sign-in", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) return false;
      await useAuth.getState().fetchUser();
      return true;
    } catch {
      return false;
    }
  },

  signOut: async () => {
    await fetch("/api/auth/sign-out", { method: "POST", credentials: "include" });
    set({ user: null });
  },
}));

useAuth.getState().fetchUser();
