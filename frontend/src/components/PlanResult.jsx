import TripPackage from './TripPackage';
import TierComparison from './TierComparison';
import PrecisionBadge from './PrecisionBadge';
import FlightCard from './FlightCard';
import WeatherSection from './WeatherSection';
import ActivitiesSection from './ActivitiesSection';
import { IconWarning, IconStarRow } from './icons';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function AvisoBanner({ mensaje }) {
  if (!mensaje) return null;
  return (
    <div className="flex items-start gap-3 p-4 rounded-xl border-l-4 border-accent bg-warning/5 border border-warning/10 animate-fade-slide-up">
      <IconWarning className="w-5 h-5 mt-0.5 shrink-0 text-warning" />
      <p className="text-sm text-text/80 leading-relaxed">{mensaje}</p>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted">{label}</span>
      <span className="font-mono text-text">{value}</span>
    </div>
  );
}

// Tarjeta compacta de plan alternativo (vuelo + hotel + coche resumidos).
function AltCard({ plan, label, delay = 0 }) {
  if (!plan || !plan.vuelo) return null;

  return (
    <div
      className="card-base overflow-hidden"
      style={{ animation: `fadeSlideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms forwards`, opacity: 0 }}
    >
      {label && (
        <div className="px-5 sm:px-6 pt-5 pb-0">
          <p className="text-xs text-muted-300 uppercase tracking-wider font-medium">{label}</p>
        </div>
      )}
      <div className="p-5 sm:p-6 pt-4">
        <FlightCard vuelo={plan.vuelo} variant="compact" />

        {plan.hotel && (
          <>
            <div className="border-t border-border-50 my-4" />
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0 text-accent2" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3 21 L21 21" /><path d="M5 21 L5 7 L12 3 L19 7 L19 21" /><path d="M9 21 L9 12 L15 12 L15 21" />
                </svg>
                <span className="text-sm text-text truncate">{plan.hotel.nombre}</span>
                {(plan.hotel.estrellas || 0) > 0 && <IconStarRow count={Math.min(plan.hotel.estrellas, 5)} />}
              </div>
              <span className="font-mono text-sm text-accent shrink-0">{formatMoney(plan.hotel.precio_total)}</span>
            </div>
          </>
        )}

        {plan.coche && (
          <>
            <div className="border-t border-border-50 my-4" />
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0 text-accent2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 17 L19 17" /><path d="M3 12 L5 7 L7 7 L9 12" /><path d="M21 12 L19 7 L17 7 L15 12" />
                  <circle cx="7" cy="14" r="2" fill="currentColor" /><circle cx="17" cy="14" r="2" fill="currentColor" />
                </svg>
                <span className="text-sm text-text truncate">{plan.coche.nombre}</span>
              </div>
              <span className="font-mono text-sm text-accent shrink-0">{formatMoney(plan.coche.precio_total)}</span>
            </div>
          </>
        )}

        <div className="border-t border-border-50 my-4" />
        <div className="flex justify-between font-medium text-sm">
          <span className="text-text">Total</span>
          <span className="font-mono text-text">{formatMoney(plan.total)}</span>
        </div>

        {plan.vuelo?.link_compra && (
          <div className="mt-4">
            <a href={plan.vuelo.link_compra} target="_blank" rel="noopener noreferrer" className="btn-outline w-full text-center text-sm">
              Ver esta opción →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PlanResult({ data, loading, error, onRetry, onModify }) {
  if (loading) return null;
  if (error) {
    return (
      <div className="card-base p-6 sm:p-8 text-center animate-scale-in">
        <div className="w-14 h-14 rounded-full bg-warning/10 text-warning flex items-center justify-center mx-auto mb-4">
          <IconWarning className="w-7 h-7" />
        </div>
        <h3 className="font-display text-lg text-text mb-2">Algo salió mal</h3>
        <p className="text-sm text-muted-300 mb-5 max-w-sm mx-auto">
          {error?.message || 'No pudimos armar tu plan. Intenta de nuevo.'}
        </p>
        {onRetry && <button onClick={onRetry} className="btn-primary">Reintentar</button>}
      </div>
    );
  }
  if (!data) return null;

  const { aviso, plan_optimo, alternativas, hoteles, coches, aeropuertos_alternativos, clima, actividades } = data;

  return (
    <div className="space-y-6">
      <AvisoBanner mensaje={aviso} />

      {plan_optimo ? (
        <TripPackage data={data} onModify={onModify} />
      ) : (
        <div className="text-center py-10 text-muted-300 animate-fade-slide-up card-base">
          <p className="text-sm">No encontramos un paquete para tu búsqueda.</p>
          <button onClick={onRetry} className="btn-outline mt-4">Intentar de nuevo</button>
        </div>
      )}

      {plan_optimo && (
        <TierComparison plan={plan_optimo} alternativas={alternativas} presupuesto={data.presupuesto} />
      )}

      <WeatherSection clima={clima} delay={300} />

      {aeropuertos_alternativos?.length > 0 && (
        <div className="animate-fade-slide-up" style={{ animationDelay: '400ms', animationFillMode: 'both' }}>
          <h3 className="font-display text-lg text-text mb-2">
            Aeropuertos alternativos cerca de {data.ciudad_destino || data.destino}
          </h3>
          <p className="text-sm text-muted-300 mb-4">
            Volar a un aeropuerto cercano puede ser más barato
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {aeropuertos_alternativos.map((alt, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-3 p-3 card-base"
                style={{ animation: `fadeSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${500 + i * 100}ms forwards`, opacity: 0 }}
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text">{alt.nombre}</p>
                  <p className="text-xs text-muted-300">{alt.iata}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-mono text-sm text-accent font-medium">{formatMoney(alt.vuelo_mas_barato)}</p>
                  {plan_optimo && alt.vuelo_mas_barato < plan_optimo.vuelo?.precio_total && (
                    <span className="badge bg-success/15 text-success border border-success/20 text-[10px]">
                      +{formatMoney(plan_optimo.vuelo?.precio_total - alt.vuelo_mas_barato)} ahorro
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {alternativas?.length > 0 && (
        <div className="animate-fade-slide-up" style={{ animationDelay: '600ms', animationFillMode: 'both' }}>
          <h3 className="font-display text-lg text-text mb-1">Otras combinaciones</h3>
          <p className="text-sm text-muted-300 mb-4">Paquetes alternativos por si quieres comparar</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {alternativas.map((alt, i) => (
              <AltCard key={i} plan={alt} label={`Opción ${i + 1}`} delay={700 + i * 150} />
            ))}
          </div>
        </div>
      )}

      {(data.ciudad_destino || data.destino) && (
        <ActivitiesSection
          actividades={actividades}
          ciudad={data.ciudad_destino || data.destino}
          delay={1300}
        />
      )}
    </div>
  );
}
