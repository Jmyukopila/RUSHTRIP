import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Token de sesion ──────────────────────────────────────────────────────
const TOKEN_KEY = 'rushtrip_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

// Adjunta el token Bearer a cada request si existe.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      error.userMessage = 'La solicitud tardo demasiado. Verifica tu conexion e intenta de nuevo.';
    } else if (!error.response) {
      error.userMessage = 'No se pudo conectar con el servidor. Verifica tu conexion a internet.';
    } else if (error.response.status >= 500) {
      const data = error.response.data;
      error.userMessage = data?.detail || 'Error interno del servidor. Intenta nuevamente.';
    } else if (error.response.status === 429) {
      const data = error.response.data;
      error.userMessage = data?.detail || 'Demasiadas solicitudes. Espera un momento e intenta de nuevo.';
    } else if (error.response.status === 401) {
      const data = error.response.data;
      error.userMessage = data?.detail || 'Debes iniciar sesion para continuar.';
    } else if (error.response.status === 422) {
      const detail = error.response.data?.detail;
      error.userMessage = Array.isArray(detail)
        ? detail.map((d) => d.msg).join('. ')
        : detail || 'Datos invalidos. Revisa los campos.';
    } else {
      const data = error.response.data;
      error.userMessage = data?.detail || error.message || 'Error inesperado.';
    }
    return Promise.reject(error);
  }
);

export async function createPlan(data) {
  const response = await api.post('/plan/', data);
  return response.data;
}

// ── Autenticacion ─────────────────────────────────────────────────────────
export async function registerUser({ email, password, nombre, telefono, pais, aceptaTerminos }) {
  const response = await api.post('/auth/register', {
    email, password, nombre, telefono, pais, acepta_terminos: !!aceptaTerminos,
  });
  return response.data;
}

export async function loginUser({ email, password }) {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
}

export async function logoutUser() {
  try {
    await api.post('/auth/logout');
  } catch {
    // Cerrar sesion es idempotente en el cliente aunque falle la red.
  }
}

export async function forgotPassword(email) {
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
}

export async function resetPassword({ token, password }) {
  const response = await api.post('/auth/reset-password', { token, password });
  return response.data;
}

export async function verifyEmail(token) {
  const response = await api.post('/auth/verify-email', { token });
  return response.data;
}

export async function resendVerification() {
  const response = await api.post('/auth/resend-verification');
  return response.data;
}

export async function fetchMe() {
  const response = await api.get('/auth/me');
  return response.data;
}

// ── Reservas (planes guardados en la cuenta) ─────────────────────────────
export async function crearReserva(data) {
  const response = await api.post('/auth/reservas', data);
  return response.data;
}

export async function fetchReservas() {
  const response = await api.get('/auth/reservas');
  return response.data;
}

export async function searchCars(params) {
  const response = await api.get('/cars/', { params });
  return response.data;
}

export async function searchFlights(params) {
  const response = await api.get('/flights/', { params });
  return response.data;
}

export async function searchHotels(params) {
  const response = await api.get('/hotels/', { params });
  return response.data;
}

export async function getHotelDetail(params) {
  const response = await api.get('/hotels/detalle', { params });
  return response.data;
}

export async function searchAirports(params) {
  const response = await api.get('/airports/', { params });
  return response.data;
}

export async function getMinBudget(params) {
  const response = await api.get('/plan/min-budget/', { params });
  return response.data;
}

export default api;
