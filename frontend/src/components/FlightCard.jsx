import FlightRoute from './FlightRoute';

const ESCALAS_TEXT = {
  0: 'Directo',
  1: '1 escala',
};

export default function FlightCard({ vuelo, variant = 'default' }) {
  if (!vuelo) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-ES', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const escalasText = vuelo.escalas_text || ESCALAS_TEXT[vuelo.escalas] || `${vuelo.escalas} escalas`;

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border hover-lift">
        {vuelo.logo_url && (
          <img
            src={vuelo.logo_url}
            alt={vuelo.aerolinea_nombre}
            className="w-8 h-8 object-contain rounded"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text truncate">
            {vuelo.aerolinea_nombre}
          </p>
          {vuelo.descripcion && (
            <p className="text-xs text-muted truncate">{vuelo.descripcion}</p>
          )}
          <p className="text-xs text-muted">
            <FlightRoute vuelo={vuelo} compact />
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm text-accent font-medium">
            ${vuelo.precio_por_persona?.toFixed(0)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 bg-card rounded-lg border border-border hover-lift">
      <div className="flex items-start gap-4 w-full sm:w-auto">
        {vuelo.logo_url && (
          <img
            src={vuelo.logo_url}
            alt={vuelo.aerolinea_nombre}
            className="w-12 h-12 object-contain rounded-lg bg-white p-1 border border-border shrink-0"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        )}
        <div className="flex-1 min-w-0 sm:hidden">
          <p className="font-medium text-text">
            {vuelo.aerolinea_nombre}
          </p>
          {vuelo.descripcion && (
            <p className="text-xs text-muted mt-0.5">{vuelo.descripcion}</p>
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0 w-full">
        <div className="hidden sm:block">
          <p className="font-medium text-text">
            {vuelo.aerolinea_nombre}
          </p>
          {vuelo.descripcion && (
            <p className="text-xs text-muted mt-0.5">{vuelo.descripcion}</p>
          )}
        </div>

        {/* Flight route visualization */}
        <div className="my-2 sm:my-3">
          <FlightRoute vuelo={vuelo} compact={false} />
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <span>Salida: {formatDate(vuelo.salida)}</span>
          {vuelo.regreso && <span>Regreso: {formatDate(vuelo.regreso)}</span>}
          <span className={`inline-flex items-center gap-1 ${
            vuelo.escalas === 0 ? 'text-success' : 'text-muted'
          }`}>
            <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="3" cy="8" r="1.5" fill="currentColor" />
              <circle cx="8" cy="8" r="1.5" fill="currentColor" />
              <circle cx="13" cy="8" r="1.5" fill="currentColor" />
            </svg>
            {escalasText}
          </span>
        </div>
      </div>

      <div className="text-right shrink-0 w-full sm:w-auto mt-2 sm:mt-0">
        <p className="font-mono text-xl sm:text-2xl text-accent font-medium leading-tight">
          ${vuelo.precio_por_persona?.toFixed(0)}
        </p>
        <p className="text-xs text-muted">por persona</p>
        {vuelo.co2_kg != null && (
          <p className="text-xs text-muted mt-1" title="Huella de carbono estimada por pasajero">
            🌱 {vuelo.co2_kg} kg CO₂
          </p>
        )}
      </div>
    </div>
  );
}
