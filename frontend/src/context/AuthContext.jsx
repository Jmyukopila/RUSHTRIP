import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  getToken,
  setToken,
  registerUser,
  loginUser,
  logoutUser,
  fetchMe,
} from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Al montar: si hay token guardado, valida la sesion contra el backend.
  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const { usuario } = await fetchMe();
        if (!cancelado) setUser(usuario);
      } catch {
        // Token invalido o expirado: se descarta.
        setToken(null);
      } finally {
        if (!cancelado) setLoading(false);
      }
    }
    cargar();
    return () => { cancelado = true; };
  }, []);

  const login = useCallback(async (credenciales) => {
    const { usuario, token } = await loginUser(credenciales);
    setToken(token);
    setUser(usuario);
    return usuario;
  }, []);

  const register = useCallback(async (datos) => {
    const { usuario, token } = await registerUser(datos);
    setToken(token);
    setUser(usuario);
    return usuario;
  }, []);

  const logout = useCallback(async () => {
    await logoutUser();
    setToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  }
  return ctx;
}
