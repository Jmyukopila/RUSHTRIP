import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api/client';
import { IconLock, IconWarning, IconCheckCircle, IconPlane } from '../components/icons';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirmar, setConfirmar] = useState('');
  const [error, setError] = useState(null);
  const [listo, setListo] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (password !== confirmar) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setEnviando(true);
    try {
      await resetPassword({ token, password });
      setListo(true);
      setTimeout(() => navigate('/login', { replace: true }), 2200);
    } catch (err) {
      setError(err.userMessage || 'No pudimos restablecer tu contraseña. El enlace puede haber expirado.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="py-12 sm:py-20 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />

      <div className="max-w-md mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-8 animate-fade-slide-up">
          <h1 className="font-display text-3xl sm:text-4xl text-text">Elige una nueva contraseña</h1>
          <p className="mt-2 text-muted">Ingresa tu nueva contraseña para acceder a tu cuenta.</p>
          <div className="separator mt-5 max-w-[10rem] mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        <div className="card-base p-6 sm:p-8 animate-scale-in">
          {!token ? (
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-warning/10 text-warning flex items-center justify-center mx-auto mb-3">
                <IconWarning className="w-6 h-6" />
              </div>
              <p className="text-sm text-muted">
                El enlace no es válido. Vuelve a solicitar la recuperación de tu contraseña.
              </p>
              <Link to="/recuperar" className="btn-outline w-full mt-6">Pedir un enlace nuevo</Link>
            </div>
          ) : listo ? (
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-success/10 text-success flex items-center justify-center mx-auto mb-3">
                <IconCheckCircle className="w-6 h-6" />
              </div>
              <p className="text-sm text-muted">
                ¡Listo! Tu contraseña se cambió. Te llevamos a iniciar sesión…
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-text mb-1.5">
                  Nueva contraseña
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
                    <IconLock className="w-4 h-4" />
                  </span>
                  <input
                    id="password"
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Mínimo 8 caracteres"
                    className="input-field pl-10"
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="confirmar" className="block text-sm font-medium text-text mb-1.5">
                  Confirmar contraseña
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
                    <IconLock className="w-4 h-4" />
                  </span>
                  <input
                    id="confirmar"
                    type="password"
                    required
                    minLength={8}
                    value={confirmar}
                    onChange={(e) => setConfirmar(e.target.value)}
                    placeholder="Repite la contraseña"
                    className="input-field pl-10"
                    autoComplete="new-password"
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
                {enviando ? 'Guardando…' : 'Cambiar contraseña'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
