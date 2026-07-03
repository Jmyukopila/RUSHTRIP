import { useMemo, useState } from 'react';
import { AFFILIATE_LINKS } from '../constants';
import { IconTicket, IconPin, IconFilter, IconImage, ACTIVITY_ICON_MAP } from './icons';

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

const FILTROS = [
  { key: 'Todas', label: 'Todas' },
  { key: 'Gratis', label: 'Gratis' },
  { key: 'Museo', label: 'Museos' },
  { key: 'Parque / Naturaleza', label: 'Naturaleza' },
  { key: 'Sitio histórico', label: 'Histórico' },
  { key: 'Tour gastronómico', label: 'Gastronomía' },
  { key: 'Excursión', label: 'Excursiones' },
  { key: 'Playa', label: 'Playas' },
  { key: 'Espectáculo', label: 'Espectáculos' },
];

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function ActivityCard({ act, delay }) {
  const ActIcon = ACTIVITY_ICON_MAP[act.categoria] || IconPin;
  const hasFoto = act.foto_url && act.foto_url.startsWith('http');

  return (
    <div
      className="card-base p-0 overflow-hidden flex flex-col"
      style={{
        animation: `fadeSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms forwards`,
        opacity: 0,
      }}
    >
      {/* Imagen / fallback */}
      <div className="h-32 bg-accent2/10 relative overflow-hidden">
        {hasFoto ? (
          <img
            src={act.foto_url}
            alt={act.nombre}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-accent2/60">
            <IconImage className="w-10 h-10" />
          </div>
        )}
        <span className="absolute top-2 right-2 badge bg-white/90 text-text border border-border shadow-sm">
          {ActIcon && <ActIcon className="w-3.5 h-3.5 inline mr-1" />}
          {act.categoria}
        </span>
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        <div>
          <p className="text-sm font-medium text-text line-clamp-1">{act.nombre}</p>
          <p className="text-xs text-muted-300 mt-1 line-clamp-2">{act.descripcion}</p>
        </div>

        <div className="flex items-center justify-between gap-3 mt-auto pt-2">
          {act.gratis ? (
            <span className="badge bg-success/15 text-success border border-success/20">Gratis</span>
          ) : (
            <p className="font-mono text-sm text-text">
              {formatMoney(act.precio_estimado)}
              <span className="text-xs text-muted-300"> aprox./persona</span>
            </p>
          )}
          <div className="flex gap-2 shrink-0">
            <a
              href={act.link_klook}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary text-xs py-1.5 px-3"
            >
              Reservar →
            </a>
            <a
              href={act.link_kkday}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-outline text-xs py-1.5 px-3"
            >
              KKday
            </a>
          </div>
        </div>
      </div>
    </div>
  );
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
  const [filtro, setFiltro] = useState('Todas');

  if (!actividades?.actividades?.length) {
    return <FallbackCard ciudad={ciudad} delay={delay} />;
  }

  const badge = BADGE_ACTIVIDADES[actividades.precision] || BADGE_ACTIVIDADES.estimada;

  const actividadesFiltradas = useMemo(() => {
    if (filtro === 'Todas') return actividades.actividades;
    if (filtro === 'Gratis') return actividades.actividades.filter((a) => a.gratis);
    return actividades.actividades.filter((a) => a.categoria === filtro);
  }, [actividades.actividades, filtro]);

  const agrupadas = useMemo(() => {
    return actividadesFiltradas.reduce((acc, act) => {
      const key = act.categoria || 'Otras';
      if (!acc[key]) acc[key] = [];
      acc[key].push(act);
      return acc;
    }, {});
  }, [actividadesFiltradas]);

  const ordenCategorias = useMemo(() => {
    const orden = FILTROS.filter((f) => f.key !== 'Todas' && f.key !== 'Gratis').map((f) => f.key);
    return Object.keys(agrupadas).sort((a, b) => {
      const ia = orden.indexOf(a);
      const ib = orden.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
  }, [agrupadas]);

  return (
    <div className="animate-fade-slide-up" style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <h3 className="font-display text-lg text-text">Mejores actividades en {ciudad}</h3>
        <span className={`badge ${badge.className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {badge.label}
        </span>
      </div>
      <p className="text-sm text-muted-300 mb-4">
        Recomendaciones personalizadas según tu plan — el pago se hace directamente en cada sitio
      </p>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <IconFilter className="w-4 h-4 text-muted-300 mr-1" />
        {FILTROS.map((f) => {
          const active = filtro === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setFiltro(f.key)}
              className={`
                text-xs font-medium px-3 py-1.5 rounded-full border transition-colors
                ${active
                  ? 'bg-accent text-white border-accent'
                  : 'bg-white text-muted-300 border-border hover:border-accent hover:text-accent'
                }
              `}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Resultados agrupados por categoría */}
      {ordenCategorias.length === 0 ? (
        <p className="text-sm text-muted-300">Ninguna actividad coincide con el filtro seleccionado.</p>
      ) : (
        ordenCategorias.map((categoria, groupIndex) => (
          <div key={categoria} className="mb-6">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-300 mb-3">
              {categoria}
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {agrupadas[categoria].map((act, i) => (
                <ActivityCard
                  key={`${categoria}-${act.nombre}`}
                  act={act}
                  delay={delay + 100 + groupIndex * 80 + i * 60}
                />
              ))}
            </div>
          </div>
        ))
      )}

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
