import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { IconMail, IconLock, IconUser, IconPhone, IconWarning, IconPlane } from '../components/icons';
import CountrySelect from '../components/CountrySelect';

export default function Login() {
  const [modo, setModo] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [pais, setPais] = useState('');
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = location.state?.from || '/plan';

  const esRegistro = modo === 'register';

  function alternarModo() {
    setModo(esRegistro ? 'login' : 'register');
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      if (esRegistro) {
        await register({ email, password, nombre, telefono, pais });
      } else {
        await login({ email, password });
      }
      navigate(destino, { replace: true });
    } catch (err) {
      setError(err.userMessage || 'No pudimos completar la operacion. Intenta de nuevo.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="py-12 sm:py-20 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />
      <div className="absolute top-8 -left-20 w-72 h-72 bg-accent/3 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-24 -right-16 w-64 h-64 bg-accent2/5 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-8 animate-fade-slide-up">
          <h1 className="font-display text-3xl sm:text-4xl text-text">
            {esRegistro ? 'Crea tu cuenta' : 'Inicia sesión'}
          </h1>
          <p className="mt-2 text-muted">
            {esRegistro
              ? 'Regístrate para armar tus planes de viaje por presupuesto.'
              : 'Inicia sesión para armar tu plan de viaje.'}
          </p>
          <div className="separator mt-5 max-w-[10rem] mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        <div className="card-base p-6 sm:p-8 animate-scale-in">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {esRegistro && (
              <>
                <div>
                  <label htmlFor="nombre" className="block text-sm font-medium text-text mb-1.5">
                    Nombre completo
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
                      <IconUser className="w-4 h-4" />
                    </span>
                    <input
                      id="nombre"
                      type="text"
                      required
                      minLength={2}
                      value={nombre}
                      onChange={(e) => setNombre(e.target.value)}
                      placeholder="Tu nombre y apellido"
                      className="input-field pl-10"
                      autoComplete="name"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="telefono" className="block text-sm font-medium text-text mb-1.5">
                    Teléfono <span className="text-muted-300 font-normal">(opcional)</span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
                      <IconPhone className="w-4 h-4" />
                    </span>
                    <input
                      id="telefono"
                      type="tel"
                      value={telefono}
                      onChange={(e) => setTelefono(e.target.value)}
                      placeholder="+57 300 123 4567"
                      className="input-field pl-10 font-mono text-sm"
                      autoComplete="tel"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="pais" className="block text-sm font-medium text-text mb-1.5">
                    País
                  </label>
                  <CountrySelect id="pais" required value={pais} onChange={setPais} />
                </div>
              </>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text mb-1.5">
                Correo electrónico
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
                  <IconMail className="w-4 h-4" />
                </span>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tucorreo@ejemplo.com"
                  className="input-field pl-10 font-mono text-sm"
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
                  <IconLock className="w-4 h-4" />
                </span>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={esRegistro ? 8 : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={esRegistro ? 'Mínimo 8 caracteres' : 'Tu contraseña'}
                  className="input-field pl-10"
                  autoComplete={esRegistro ? 'new-password' : 'current-password'}
                />
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 text-sm text-accent bg-accent/5 border border-accent/20 rounded-lg px-3 py-2.5">
                <IconWarning className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" disabled={enviando} className="btn-primary w-full mt-1 disabled:opacity-60">
              {enviando
                ? 'Un momento…'
                : esRegistro
                ? 'Crear cuenta'
                : 'Iniciar sesión'}
            </button>
          </form>

          <div className="separator my-5" />

          <p className="text-center text-sm text-muted">
            {esRegistro ? '¿Ya tienes cuenta?' : '¿Aún no tienes cuenta?'}{' '}
            <button
              type="button"
              onClick={alternarModo}
              className="text-accent font-medium hover:underline"
            >
              {esRegistro ? 'Inicia sesión' : 'Regístrate gratis'}
            </button>
          </p>
        </div>

        <p className="text-center text-xs text-muted-300 mt-6">
          ¿Solo mirando?{' '}
          <Link to="/" className="hover:text-muted underline">Volver al inicio</Link>
        </p>
      </div>
    </div>
  );
}
