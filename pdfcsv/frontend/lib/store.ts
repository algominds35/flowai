import { create } from 'zustand';

interface User {
  id: number;
  email: string;
  full_name?: string;
  subscription_tier: string;
  pages_processed_this_month: number;
  quickbooks_connected: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  
  setUser: (user) => set({ 
    user, 
    isAuthenticated: !!user,
    isLoading: false 
  }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  logout: () => {
    localStorage.removeItem('access_token');
    set({ user: null, isAuthenticated: false });
  },
}));
