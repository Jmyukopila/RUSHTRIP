import { Link } from 'react-router-dom';
import { IconPlane } from './icons';

// Layout compartido para las paginas legales (/terminos y /privacidad):
// cabecera con titulo + fecha de actualizacion y secciones en prosa.
export default function LegalLayout({ titulo, actualizado, children }) {
  return (
    <div className="py-12 sm:py-20 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-10 animate-fade-slide-up">
          <h1 className="font-display text-3xl sm:text-4xl text-text">{titulo}</h1>
          <p className="mt-2 text-sm text-muted">
            Última actualización: <span className="font-mono">{actualizado}</span>
          </p>
          <div className="separator mt-5 max-w-[10rem] mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        <div
          className="card-base p-6 sm:p-10 animate-fade-slide-up"
          style={{ animationDelay: '100ms', animationFillMode: 'both' }}
        >
          <div className="flex flex-col gap-8">{children}</div>
        </div>

        <p className="text-center text-xs text-muted-300 mt-6">
          ¿Dudas sobre este documento? Escríbenos a{' '}
          <a href="mailto:rushtripsupport@gmail.com" className="hover:text-muted underline">
            rushtripsupport@gmail.com
          </a>
        </p>
      </div>
    </div>
  );
}

export function LegalSection({ titulo, children }) {
  return (
    <section>
      <h2 className="font-display text-xl text-text mb-3">{titulo}</h2>
      <div className="text-sm text-muted leading-relaxed flex flex-col gap-3">{children}</div>
    </section>
  );
}

export function LegalLink({ to, children }) {
  return (
    <Link to={to} className="text-accent hover:underline">
      {children}
    </Link>
  );
}
