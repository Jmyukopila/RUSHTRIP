import FlightRoute from './FlightRoute';
import { TRANSPORT_ICONS } from './icons';

const ESCALAS_TEXT = {
  0: 'Directo',
  1: '1 escala',
};

// Sin logo de operadora (bus/tren), mostramos el icono del medio en su lugar
function MedioBadge({ medio, size = 'w-8 h-8' }) {
  const Icon = TRANSPORT_ICONS[medio];
  if (!Icon) return null;
  return (
    <span className={`${size} rounded-lg bg-accent/10 text-accent flex items-center justify-center shrink-0`}>
      <Icon className="w-4 h-4" />
    </span>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
    });
  } catch {
    return dateStr;
  }
}

export default function FlightCard({ vuelo, variant = 'default' }) {
  if (!vuelo) return null;

  const escalasText = vuelo.escalas_texto || vuelo.escalas_text || ESCALAS_TEXT[vuelo.escalas] || `${vuelo.escalas} escalas`;

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border-100 hover-lift">
        {vuelo.logo_url ? (
          <img
            src={vuelo.logo_url}
            alt={vuelo.aerolinea_nombre}
            className="w-8 h-8 object-contain rounded shrink-0"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        ) : (
          <MedioBadge medio={vuelo.medio} />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text truncate">{vuelo.aerolinea_nombre}</p>
          <div className="text-xs text-muted-300 mt-0.5">
            <FlightRoute vuelo={vuelo} compact />
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="font-mono text-sm text-accent font-semibold">
            ${vuelo.precio_por_persona?.toFixed(0)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-base p-4 sm:p-5">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-start gap-4 sm:gap-3 shrink-0">
          {vuelo.logo_url ? (
            <img
              src={vuelo.logo_url}
              alt={vuelo.aerolinea_nombre}
              className="w-11 h-11 object-contain rounded-lg bg-white border border-border-100 p-1.5 shrink-0"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          ) : (
            <MedioBadge medio={vuelo.medio} size="w-11 h-11" />
          )}
          <div className="sm:hidden">
            <p className="font-medium text-text text-sm">{vuelo.aerolinea_nombre}</p>
            {vuelo.descripcion && (
              <p className="text-xs text-muted-300 mt-0.5">{vuelo.descripcion}</p>
            )}
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="hidden sm:flex items-center gap-3 mb-1">
            <p className="font-medium text-text text-sm">{vuelo.aerolinea_nombre}</p>
            {vuelo.descripcion && (
              <span className="text-xs text-muted-300">{vuelo.descripcion}</span>
            )}
          </div>

          <div className="my-2">
            <FlightRoute vuelo={vuelo} compact={false} />
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-300">
            <span>{formatDate(vuelo.salida)}</span>
            {vuelo.regreso && <span>→ {formatDate(vuelo.regreso)}</span>}
            <span className={vuelo.escalas === 0 ? 'text-success font-medium' : ''}>
              {escalasText}
            </span>
          </div>
        </div>

        <div className="text-right shrink-0 flex sm:flex-col items-center sm:items-end gap-2 sm:gap-1 pt-2 sm:pt-0 border-t sm:border-t-0 border-border-100 sm:border-l sm:border-border-100 sm:pl-5">
          <p className="font-mono text-xl sm:text-2xl text-accent font-bold leading-tight">
            ${vuelo.precio_por_persona?.toFixed(0)}
          </p>
          <p className="text-xs text-muted-300">por persona</p>
          {vuelo.co2_kg != null && (
            <p className="text-xs text-muted-300/70" title="Huella de carbono estimada por pasajero">
              {vuelo.co2_kg} kg CO2
            </p>
          )}
          {vuelo.link_compra && (
            <a
              href={vuelo.link_compra}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary text-xs py-1 px-3 mt-1 whitespace-nowrap"
            >
              Comprar →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
