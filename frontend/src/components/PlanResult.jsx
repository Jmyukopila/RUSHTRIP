import { useState } from 'react';
import SummaryCard from './SummaryCard';
import TierComparison from './TierComparison';
import PrecisionBadge from './PrecisionBadge';
import FlightCard from './FlightCard';
import HotelCard from './HotelCard';
import CarCard from './CarCard';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function AvisoBanner({ mensaje }) {
  if (!mensaje) return null;
  return (
    <div className="flex items-start gap-3 p-4 bg-[#FFF3CD] border-l-4 border-accent rounded-r-lg animate-popIn">
      <span className="text-lg mt-0.5">⚠️</span>
      <p className="text-sm text-text/80 leading-relaxed">{mensaje}</p>
    </div>
  );
}

function BudgetProgressBar({ used, total }) {
  if (!total || total <= 0) return null;
  const pct = Math.min((used / total) * 100, 100);
  const colorClass = pct < 60 ? 'bg-success' : pct < 90 ? 'bg-warning' : 'bg-accent';

  return (
    <div className="mt-3">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-muted">Presupuesto usado</span>
        <span className={`font-mono font-medium ${pct > 100 ? 'text-accent' : 'text-text'}`}>
          {Math.round(pct)}%
        </span>
      </div>
      <div className="progress-bar">
        <div
          className={`progress-bar-fill ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function CelebrationParticles({ show }) {
  if (!show) return null;
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-10">
      {[...Array(8)].map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full animate-popIn"
          style={{
            width: `${4 + i * 2}px`,
            height: `${4 + i * 2}px`,
            backgroundColor: i % 2 === 0 ? 'rgba(232, 97, 26, 0.4)' : 'rgba(196, 168, 130, 0.5)',
            left: `${10 + i * 12}%`,
            top: `${5 + (i % 3) * 30}%`,
            animationDelay: `${i * 80}ms`,
            animationDuration: '0.6s',
          }}
        />
      ))}
    </div>
  );
}

function PlanCard({ plan, label, variant, delay = 0 }) {
  if (!plan || !plan.vuelo) return null;

  const [hotelImgError, setHotelImgError] = useState(false);

  const isOptimo = variant === 'optimo';

  const dentro = plan.dentro_presupuesto;
  const diferencia = Math.abs(plan.total - plan.presupuesto);
  const sobrante = plan.presupuesto - plan.total;

  return (
    <div
      className={`relative bg-surface rounded-xl border ${
        isOptimo ? 'border-l-[4px] border-l-accent card-shadow-lg' : 'border-border card-shadow'
      } transition-all duration-500`}
      style={{
        opacity: 1,
        transform: 'translateY(0)',
        animation: `fadeSlideUp 0.6s ease-out ${delay}ms forwards`,
      }}
    >
      <CelebrationParticles show={isOptimo} />

      {isOptimo && (
        <div className="p-5 sm:p-6 pb-0">
          <div className="flex items-center justify-between">
            <span className={`badge ${dentro ? 'bg-success/15 text-success border border-success/20' : 'bg-accent/15 text-accent border border-accent/20'}`}>
              {dentro ? 'Mejor opción ✦' : 'Más cercano'}
            </span>
          </div>
        </div>
      )}

      {!isOptimo && label && (
        <div className="p-5 sm:p-6 pb-0">
          <p className="text-xs text-muted uppercase tracking-wider font-medium">{label}</p>
        </div>
      )}

      <div className={isOptimo || label ? 'p-5 sm:p-6 pt-4' : 'p-5 sm:p-6'}>
        <FlightCard vuelo={plan.vuelo} variant={isOptimo ? 'default' : 'compact'} />

        {plan.hotel && (
          <>
            <div className="border-t border-border my-4" />

            {isOptimo ? (
              <div className={`rounded-lg p-4 border ${
                plan.hotel.tipo === 'recomendado'
                  ? 'bg-accent/5 border-accent/20'
                  : 'bg-card border-border'
              }`}>
                <div className="flex items-start gap-4">
                  {(plan.hotel.foto_url && !hotelImgError) ? (
                    <div className="relative w-24 h-16 sm:w-32 sm:h-20 rounded-lg overflow-hidden bg-accent/5 flex-shrink-0">
                      <img
                        src={plan.hotel.foto_url}
                        alt={plan.hotel.nombre}
                        className="w-full h-full object-cover"
                        onError={() => setHotelImgError(true)}
                      />
                    </div>
                  ) : (
                    <div className="w-24 h-16 sm:w-32 sm:h-20 rounded-lg bg-accent2/10 text-accent2 flex items-center justify-center flex-shrink-0">
                      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M3 21 L21 21" />
                        <path d="M5 21 L5 7 L12 3 L19 7 L19 21" />
                        <path d="M9 21 L9 12 L15 12 L15 21" />
                      </svg>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-text truncate">{plan.hotel.nombre}</p>
                      {plan.hotel.tipo === 'recomendado' && (
                        <span className="badge bg-success/15 text-success border border-success/20 text-xs shrink-0">
                          Recomendado
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {(plan.hotel.estrellas || 0) > 0 && (
                        <span className="text-yellow-500 text-xs">
                          {'★'.repeat(Math.min(plan.hotel.estrellas, 5))}{'☆'.repeat(Math.max(0, 5 - plan.hotel.estrellas))}
                        </span>
                      )}
                      {plan.hotel.rating > 0 && (
                        <span className="px-1.5 py-0.5 rounded bg-success/15 text-success text-xs font-bold">{Number(plan.hotel.rating).toFixed(1)}</span>
                      )}
                    </div>
                    <p className="text-xs text-muted mt-1">
                      <span className="font-mono text-accent font-medium">{formatMoney(plan.hotel.precio_noche)}</span> por noche
                      {plan.hotel.noches ? ` × ${plan.hotel.noches} noche${plan.hotel.noches > 1 ? 's' : ''}` : ''}
                      {plan.hotel.precio_total ? ` = ${formatMoney(plan.hotel.precio_total)}` : ''}
                    </p>
                    {plan.hotel.por_que && (
                      <p className="text-xs text-muted mt-1 italic">{plan.hotel.por_que}</p>
                    )}
                  </div>
                  {plan.hotel.link_reserva && (
                    <a
                      href={plan.hotel.link_reserva}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-outline text-xs shrink-0"
                    >
                      Reservar →
                    </a>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0 text-accent2" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M3 21 L21 21" />
                    <path d="M5 21 L5 7 L12 3 L19 7 L19 21" />
                    <path d="M9 21 L9 12 L15 12 L15 21" />
                  </svg>
                  <span className="text-sm text-text truncate">{plan.hotel.nombre}</span>
                  {plan.hotel.tipo === 'recomendado' && (
                    <span className="badge bg-success/15 text-success border border-success/20 text-xs shrink-0">Recomendado</span>
                  )}
                </div>
                <span className="font-mono text-sm text-accent shrink-0">
                  {formatMoney(plan.hotel.precio_total)}
                </span>
              </div>
            )}
          </>
        )}

        {plan.coche && (
          <>
            <div className="border-t border-border my-4" />
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0 text-accent2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 17 L19 17" />
                  <path d="M3 12 L5 7 L7 7 L9 12" />
                  <path d="M21 12 L19 7 L17 7 L15 12" />
                  <circle cx="7" cy="14" r="2" fill="currentColor" />
                  <circle cx="17" cy="14" r="2" fill="currentColor" />
                  <path d="M6 10 L18 10" />
                </svg>
                <div className="min-w-0">
                  <span className="text-sm text-text truncate block">{plan.coche.nombre}</span>
                  {plan.coche.tipo && <span className="text-xs text-muted">{plan.coche.tipo}</span>}
                </div>
                {plan.coche.fuera_presupuesto && (
                  <span className="badge bg-accent/15 text-accent border border-accent/20 text-xs shrink-0">Excede</span>
                )}
              </div>
              <span className="font-mono text-sm text-accent shrink-0">
                {formatMoney(plan.coche.precio_total)}
              </span>
            </div>
          </>
        )}

        {(plan.total != null || plan.presupuesto != null) && (
          <>
            <div className="border-t border-border my-4" />

            <div className={isOptimo ? 'space-y-1.5 text-sm' : 'space-y-1 text-sm'}>
              {plan.vuelo?.precio_total != null && (
                <div className="flex justify-between">
                  <span className="text-muted">Vuelo</span>
                  <span className="font-mono text-text">{formatMoney(plan.vuelo.precio_total)}</span>
                </div>
              )}
              {plan.hotel?.precio_total != null && (
                <div className="flex justify-between">
                  <span className="text-muted">Hotel</span>
                  <span className="font-mono text-text">{formatMoney(plan.hotel.precio_total)}</span>
                </div>
              )}
              {plan.coche?.precio_total != null && (
                <div className="flex justify-between">
                  <span className="text-muted">Coche</span>
                  <span className="font-mono text-text">{formatMoney(plan.coche.precio_total)}</span>
                </div>
              )}
              <div className={`flex justify-between font-medium ${isOptimo ? 'border-t border-border pt-1.5 mt-1.5' : 'border-t border-border pt-1 mt-1'}`}>
                <span className="text-text">Total</span>
                <span className={`font-mono ${!dentro ? 'text-accent' : 'text-text'}`}>
                  {formatMoney(plan.total)}
                </span>
              </div>
              {isOptimo && (
                <>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted">Presupuesto</span>
                    <span className="font-mono text-muted">{formatMoney(plan.presupuesto)}</span>
                  </div>
                  {dentro ? (
                    <div className="flex justify-between text-xs pt-1">
                      <span className="text-success">Sobrante</span>
                      <span className="font-mono text-success">+{formatMoney(sobrante)}</span>
                    </div>
                  ) : !dentro ? (
                    <div className="flex justify-between text-xs pt-1">
                      <span className="text-accent">Exceso</span>
                      <span className="font-mono text-accent">-{formatMoney(diferencia)}</span>
                    </div>
                  ) : null}
                  <BudgetProgressBar used={plan.total} total={plan.presupuesto} />
                </>
              )}
            </div>
          </>
        )}

        {plan.vuelo?.link_compra && (
          <div className={isOptimo ? 'mt-5' : 'mt-4'}>
            <a
              href={plan.vuelo.link_compra}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary w-full text-center"
            >
              Ver vuelo →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

function HotelSort({ value, onChange }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="text-xs text-muted">Ordenar por:</span>
      <div className="flex bg-card rounded-lg border border-border overflow-hidden">
        {[
          { key: 'recomendado', label: 'Recomendado' },
          { key: 'precio_asc', label: 'Precio ↑' },
          { key: 'precio_desc', label: 'Precio ↓' },
          { key: 'rating_desc', label: 'Valoración' },
        ].map((opt) => (
          <button
            key={opt.key}
            onClick={() => onChange(opt.key)}
            className={`px-3 py-1.5 text-xs font-medium transition-colors ${
              value === opt.key
                ? 'bg-accent text-white'
                : 'text-muted hover:text-text'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function sortHotels(hoteles, sortBy) {
  const h = [...hoteles];
  switch (sortBy) {
    case 'precio_asc':
      return h.sort((a, b) => (a.precio || 0) - (b.precio || 0));
    case 'precio_desc':
      return h.sort((a, b) => (b.precio || 0) - (a.precio || 0));
    case 'rating_desc':
      return h.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    default:
      return h;
  }
}

function HotelSearch({ value, onChange, total }) {
  return (
    <div className="relative">
      <svg viewBox="0 0 24 24" className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8" />
        <path d="M21 21L16.65 16.65" />
      </svg>
      <input
        type="text"
        placeholder={`Buscar hotel por nombre (${total} disponible${total !== 1 ? 's' : ''})...`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full pl-9 pr-4 py-2.5 bg-white border border-border rounded-lg text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent transition-all"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text transition-colors"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

export default function PlanResult({ data, loading, error, onRetry, onModify }) {
  const [hotelSort, setHotelSort] = useState('recomendado');
  const [hotelSearch, setHotelSearch] = useState('');

  if (loading) return null;
  if (error) {
    return (
      <div className="bg-surface rounded-xl card-shadow border border-warning/30 p-6 sm:p-8 text-center animate-popIn">
        <div className="w-14 h-14 rounded-full bg-warning/10 text-warning flex items-center justify-center mx-auto mb-4 animate-gentlePulse">
          <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8 L12 12" />
            <path d="M12 16 L12 16" />
          </svg>
        </div>
        <h3 className="font-display text-lg text-text mb-2">Algo salió mal</h3>
        <p className="text-sm text-muted mb-5 max-w-sm mx-auto">
          {error?.message || 'No pudimos armar tu plan. Intenta de nuevo.'}
        </p>
        {onRetry && (
          <button onClick={onRetry} className="btn-primary">
            Reintentar
          </button>
        )}
      </div>
    );
  }
  if (!data) return null;

  const { aviso, precision, plan_optimo, alternativas, hoteles, coches, aeropuertos_alternativos } = data;

  // Filter hotels by search term (local, no API call)
  const hotelesFiltrados = (hoteles || []).filter((h) => {
    if (!hotelSearch) return true;
    return h.nombre?.toLowerCase().includes(hotelSearch.toLowerCase());
  });
  const sortedHoteles = sortHotels(hotelesFiltrados, hotelSort);

  return (
    <div className="space-y-6">
      <AvisoBanner mensaje={aviso} />

      {/* Summary at top */}
      <SummaryCard data={data} onModify={onModify} />

      {/* Tier comparison - budget options */}
      {plan_optimo && (
        <TierComparison
          plan={plan_optimo}
          alternativas={alternativas}
          presupuesto={data.presupuesto}
        />
      )}

      <div
        className="flex flex-wrap items-center justify-between gap-4"
        style={{ animation: 'fadeSlideUp 0.5s ease-out forwards' }}
      >
        <h2 className="font-display text-xl sm:text-2xl text-text">
          Tu plan de viaje
        </h2>
        {precision && <PrecisionBadge precision={precision} />}
      </div>

      {plan_optimo && <PlanCard plan={plan_optimo} variant="optimo" delay={100} />}

      {aeropuertos_alternativos?.length > 0 && (
        <div
          style={{ animation: 'fadeSlideUp 0.5s ease-out 400ms forwards', opacity: 0 }}
        >
          <h3 className="font-display text-lg text-text mb-2">
            🌍 Aeropuertos alternativos cerca de {data.ciudad_destino || data.destino}
          </h3>
          <p className="text-sm text-muted mb-4">
            Volar a un aeropuerto cercano puede ser mas barato
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {aeropuertos_alternativos.map((alt, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-3 p-3 bg-card rounded-lg border border-border hover-lift"
                style={{ animation: `fadeSlideUp 0.5s ease-out ${500 + i * 100}ms forwards`, opacity: 0 }}
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text">{alt.nombre}</p>
                  <p className="text-xs text-muted">
                    {alt.iata}
                    {alt.precision === 'exacta' ? ' • Precio exacto' : alt.precision === 'mes' ? ' • Precio del mes' : ''}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-mono text-sm text-accent font-medium">
                    {formatMoney(alt.vuelo_mas_barato)}
                  </p>
                  {plan_optimo && alt.vuelo_mas_barato < plan_optimo.vuelo?.precio_total && (
                    <span className="badge bg-success/15 text-success border border-success/20 text-xs">
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
        <div
          style={{ animation: 'fadeSlideUp 0.5s ease-out 600ms forwards', opacity: 0 }}
        >
          <h3 className="font-display text-lg text-text mb-4">Alternativas</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {alternativas.map((alt, i) => (
              <PlanCard
                key={i}
                plan={alt}
                variant="alternativa"
                label={`Opción ${i + 1}`}
                delay={700 + i * 150}
              />
            ))}
          </div>
        </div>
      )}

      {hoteles?.length > 0 && (
        <div
          style={{ animation: 'fadeSlideUp 0.5s ease-out 900ms forwards', opacity: 0 }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
            <div>
              <h3 className="font-display text-lg text-text">Más hoteles en {data.ciudad_destino || 'el destino'}</h3>
              <p className="text-sm text-muted">Otras opciones disponibles para tus fechas</p>
            </div>
          </div>
          <div className="space-y-3 mb-4">
            <HotelSearch value={hotelSearch} onChange={setHotelSearch} total={hoteles.length} />
            <HotelSort value={hotelSort} onChange={setHotelSort} />
          </div>
          {sortedHoteles.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {sortedHoteles.map((h, i) => (
                <div key={`${h.id || i}`} style={{ animation: `fadeSlideUp 0.4s ease-out ${1000 + i * 80}ms forwards`, opacity: 0 }}>
                  <HotelCard hotel={h} />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 bg-card rounded-lg border border-border">
              <p className="text-sm text-muted">No se encontraron hoteles que coincidan con "{hotelSearch}"</p>
              <button onClick={() => setHotelSearch('')} className="btn-outline text-xs mt-3">Limpiar filtro</button>
            </div>
          )}
        </div>
      )}

      {coches?.coches?.length > 0 && (
        <div
          style={{ animation: 'fadeSlideUp 0.5s ease-out 1100ms forwards', opacity: 0 }}
        >
          <h3 className="font-display text-lg text-text mb-4 mt-8">Alquiler de coches</h3>
          <p className="text-sm text-muted mb-4">
            Opciones de alquiler de coches en {coches.ciudad || 'el destino'}
          </p>
          <div className="grid grid-cols-1 gap-3">
            {coches.coches.slice(0, 5).map((c, i) => (
              <div key={i} style={{ animation: `fadeSlideUp 0.4s ease-out ${1200 + i * 80}ms forwards`, opacity: 0 }}>
                <CarCard car={c} />
              </div>
            ))}
          </div>
        </div>
      )}

      {!plan_optimo && !alternativas?.length && !hoteles?.length && !coches?.coches?.length && (
        <div className="text-center py-10 text-muted animate-popIn">
          <p className="text-sm">No encontramos opciones para tu búsqueda.</p>
          <button onClick={onRetry} className="btn-outline mt-4">
            Intentar de nuevo
          </button>
        </div>
      )}
    </div>
  );
}
