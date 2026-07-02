import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { verifyEmail } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { IconWarning, IconCheckCircle, IconPlane } from '../components/icons';

export default function VerificarEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const { isAuthenticated, refreshUser } = useAuth();
  const [estado, setEstado] = useState('cargando'); // 'cargando' | 'ok' | 'error'
  const [error, setError] = useState('');
  const yaCorrio = useRef(false);

  useEffect(() => {
    if (yaCorrio.current) return; // evita doble ejecución en StrictMode
    yaCorrio.current = true;

    if (!token) {
      setEstado('error');
      setError('El enlace de verificación no es válido.');
      return;
    }
    (async () => {
      try {
        await verifyEmail(token);
        if (isAuthenticated) await refreshUser();
        setEstado('ok');
      } catch (err) {
        setError(err.userMessage || 'El enlace es inválido o ha expirado.');
        setEstado('error');
      }
    })();
  }, [token, isAuthenticated, refreshUser]);

  return (
    <div className="py-12 sm:py-20 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />

      <div className="max-w-md mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-8 animate-fade-slide-up">
          <h1 className="font-display text-3xl sm:text-4xl text-text">Verificación de correo</h1>
          <div className="separator mt-5 max-w-[10rem] mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        <div className="card-base p-6 sm:p-8 text-center animate-scale-in">
          {estado === 'cargando' && (
            <p className="text-sm text-muted">Verificando tu correo…</p>
          )}

          {estado === 'ok' && (
            <>
              <div className="w-12 h-12 rounded-full bg-success/10 text-success flex items-center justify-center mx-auto mb-3">
                <IconCheckCircle className="w-6 h-6" />
              </div>
              <p className="text-sm text-muted">
                ¡Tu correo quedó verificado! Ya puedes armar tus viajes con la cuenta confirmada.
              </p>
              <Link to={isAuthenticated ? '/plan' : '/login'} className="btn-primary w-full mt-6">
                {isAuthenticated ? 'Armar mi viaje' : 'Iniciar sesión'}
              </Link>
            </>
          )}

          {estado === 'error' && (
            <>
              <div className="w-12 h-12 rounded-full bg-warning/10 text-warning flex items-center justify-center mx-auto mb-3">
                <IconWarning className="w-6 h-6" />
              </div>
              <p className="text-sm text-muted">{error}</p>
              <p className="text-xs text-muted-300 mt-3">
                Puedes pedir un enlace nuevo desde tu cuenta.
              </p>
              <Link to={isAuthenticated ? '/reservas' : '/login'} className="btn-outline w-full mt-6">
                {isAuthenticated ? 'Ir a mi cuenta' : 'Iniciar sesión'}
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
