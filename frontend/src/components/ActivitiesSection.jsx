import { AFFILIATE_LINKS } from '../constants';
import { IconTicket, IconPin, ACTIVITY_ICON_MAP } from './icons';

const BADGE_ACTIVIDADES = {
  real: {
    label: 'Datos reales',
    className: 'bg-success/15 text-success border border-success/20',
  },
  stale: {
    label: 'Datos de cache',
    className: 'bg-accent/15 text-accent border border-accent/20',
  },
  estimada: {
    label: 'Selección RushTrip',
    className: 'bg-warning/15 text-warning border border-warning/20',
  },
};

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function FallbackCard({ ciudad, delay }) {
  return (
    <div className="animate-fade-slide-up" style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}>
      <div className="card-base p-5 sm:p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center shrink-0">
            <IconTicket className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-display text-lg text-text">Actividades en {ciudad}</h3>
            <p className="text-sm text-muted-300 mt-1">Explora tours, atracciones y experiencias en tu destino</p>
            <div className="flex flex-wrap gap-2 mt-4">
              <a href={AFFILIATE_LINKS.klook} target="_blank" rel="noopener noreferrer" className="btn-primary text-sm py-2 px-4">
                Ver en Klook →
              </a>
              <a href={AFFILIATE_LINKS.kkday} target="_blank" rel="noopener noreferrer" className="btn-outline text-sm py-2 px-4">
                KKday →
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ActivitiesSection({ actividades, ciudad, delay = 1300 }) {
  if (!actividades?.actividades?.length) {
    return <FallbackCard ciudad={ciudad} delay={delay} />;
  }

  const badge = BADGE_ACTIVIDADES[actividades.precision] || BADGE_ACTIVIDADES.estimada;

  return (
    <div className="animate-fade-slide-up" style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <h3 className="font-display text-lg text-text">
          Mejores actividades en {ciudad}
        </h3>
        <span className={`badge ${badge.className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {badge.label}
        </span>
      </div>
      <p className="text-sm text-muted-300 mb-4">
        Recomendaciones para tu llegada — el pago se hace directamente en cada sitio
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {actividades.actividades.map((act, i) => (
          <div
            key={act.nombre}
            className="card-base p-4 flex flex-col gap-3"
            style={{
              animation: `fadeSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${delay + 100 + i * 80}ms forwards`,
              opacity: 0,
            }}
          >
            <div className="flex items-start gap-3">
              <span className="w-11 h-11 rounded-xl bg-accent2/10 text-accent2-700 flex items-center justify-center shrink-0">
                {(() => {
                  const ActIcon = ACTIVITY_ICON_MAP[act.categoria] || IconPin;
                  return <ActIcon className="w-5 h-5" />;
                })()}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-text truncate">{act.nombre}</p>
                  <span className="badge bg-accent2/10 text-muted-300 border border-border">{act.categoria}</span>
                </div>
                <p className="text-xs text-muted-300 mt-1 line-clamp-2">{act.descripcion}</p>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 mt-auto">
              {act.gratis ? (
                <span className="badge bg-success/15 text-success border border-success/20">Gratis</span>
              ) : (
                <p className="font-mono text-sm text-text">
                  {formatMoney(act.precio_estimado)}
                  <span className="text-xs text-muted-300"> aprox./persona</span>
                </p>
              )}
              <div className="flex gap-2 shrink-0">
                <a href={act.link_klook} target="_blank" rel="noopener noreferrer" className="btn-primary text-xs py-1.5 px-3">
                  Reservar →
                </a>
                <a href={act.link_kkday} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs py-1.5 px-3">
                  KKday
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 mt-3">
        {actividades.aviso && (
          <p className="text-xs text-muted-300">{actividades.aviso}</p>
        )}
        <p className="text-xs text-muted-300">
          Más actividades:{' '}
          <a href={AFFILIATE_LINKS.klook} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">Klook</a>
          {' · '}
          <a href={AFFILIATE_LINKS.kkday} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">KKday</a>
        </p>
      </div>
    </div>
  );
}
