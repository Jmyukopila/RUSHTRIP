import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingPlane from './LoadingPlane';

// Envuelve rutas que requieren sesion. Mientras se valida el token muestra
// el loader; si no hay usuario redirige a /login recordando el destino.
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="py-24">
        <LoadingPlane />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
