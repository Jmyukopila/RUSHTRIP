import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
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
      error.userMessage = 'Demasiadas solicitudes. Espera un momento e intenta de nuevo.';
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

export async function searchAirports(params) {
  const response = await api.get('/airports/', { params });
  return response.data;
}

export async function getMinBudget(params) {
  const response = await api.get('/plan/min-budget/', { params });
  return response.data;
}

export default api;
