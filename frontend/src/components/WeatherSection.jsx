const BADGE_CLIMA = {
  pronostico: {
    label: 'Pronóstico',
    className: 'bg-success/15 text-success border border-success/20',
  },
  tipico: {
    label: 'Clima típico',
    className: 'bg-warning/15 text-warning border border-warning/20',
  },
  parcial: {
    label: 'Pronóstico + clima típico',
    className: 'bg-warning/15 text-warning border border-warning/20',
  },
  stale: {
    label: 'Datos de cache',
    className: 'bg-accent/15 text-accent border border-accent/20',
  },
};

function formatDia(fecha) {
  return new Date(fecha + 'T12:00:00').toLocaleDateString('es', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
}

export default function WeatherSection({ clima, delay = 300 }) {
  if (!clima?.dias?.length) return null;

  const badge = BADGE_CLIMA[clima.precision] || BADGE_CLIMA.tipico;
  const esParcial = clima.precision === 'parcial';

  return (
    <div
      className="animate-fade-slide-up"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <h3 className="font-display text-lg text-text">
          Clima en {clima.ciudad} durante tu viaje
        </h3>
        <span className={`badge ${badge.className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {badge.label}
        </span>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2">
        {clima.dias.map((dia, i) => (
          <div
            key={dia.fecha}
            className={`card-base p-3 text-center min-w-[100px] shrink-0 ${
              esParcial && dia.tipo === 'tipico' ? 'opacity-80' : ''
            }`}
            style={{
              animation: `fadeSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${delay + 100 + i * 60}ms forwards`,
              opacity: 0,
            }}
          >
            <p className="text-xs text-muted-300 capitalize mb-1">{formatDia(dia.fecha)}</p>
            <p className="text-3xl leading-none mb-1.5" title={dia.descripcion}>
              {dia.icono}
            </p>
            <p className="font-mono text-sm text-text">
              {Math.round(dia.temp_max)}°
              <span className="text-muted-300"> / {Math.round(dia.temp_min)}°</span>
            </p>
            {dia.prob_lluvia != null && (
              <p className={`text-xs mt-1 ${dia.prob_lluvia > 50 ? 'text-warning' : 'text-muted-300'}`}>
                💧 {dia.prob_lluvia}%
              </p>
            )}
          </div>
        ))}
      </div>

      {clima.aviso && (
        <p className="text-xs text-muted-300 mt-1">{clima.aviso}</p>
      )}
    </div>
  );
}
