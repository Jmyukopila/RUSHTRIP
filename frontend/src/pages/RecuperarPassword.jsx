import { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../api/client';
import { IconMail, IconWarning, IconCheckCircle, IconPlane } from '../components/icons';

export default function RecuperarPassword() {
  const [email, setEmail] = useState('');
  const [enviado, setEnviado] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const res = await forgotPassword(email);
      setMensaje(res.mensaje || 'Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.');
      setEnviado(true);
    } catch (err) {
      setError(err.userMessage || 'No pudimos procesar la solicitud. Intenta de nuevo.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="py-12 sm:py-20 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />

      <div className="max-w-md mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-8 animate-fade-slide-up">
          <h1 className="font-display text-3xl sm:text-4xl text-text">Recupera tu contraseña</h1>
          <p className="mt-2 text-muted">
            Escribe el correo de tu cuenta y te enviaremos un enlace para elegir una nueva.
          </p>
          <div className="separator mt-5 max-w-[10rem] mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        <div className="card-base p-6 sm:p-8 animate-scale-in">
          {enviado ? (
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-success/10 text-success flex items-center justify-center mx-auto mb-3">
                <IconCheckCircle className="w-6 h-6" />
              </div>
              <p className="text-sm text-muted">{mensaje}</p>
              <p className="text-xs text-muted-300 mt-3">
                Revisa también la carpeta de spam. El enlace vence en 1 hora.
              </p>
              <Link to="/login" className="btn-outline w-full mt-6">Volver a iniciar sesión</Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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

              {error && (
                <div className="flex items-start gap-2 text-sm text-accent bg-accent/5 border border-accent/20 rounded-lg px-3 py-2.5">
                  <IconWarning className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button type="submit" disabled={enviando} className="btn-primary w-full mt-1 disabled:opacity-60">
                {enviando ? 'Enviando…' : 'Enviar enlace'}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-muted-300 mt-6">
          <Link to="/login" className="hover:text-muted underline">Volver a iniciar sesión</Link>
        </p>
      </div>
    </div>
  );
}
