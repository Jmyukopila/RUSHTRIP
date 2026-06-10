import { useState } from 'react';
import SummaryCard from './SummaryCard';
import TierComparison from './TierComparison';
import PrecisionBadge from './PrecisionBadge';
import FlightCard from './FlightCard';
import HotelCard from './HotelCard';
import CarCard from './CarCard';
import WeatherSection from './WeatherSection';
import { AFFILIATE_LINKS } from '../constants';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function AvisoBanner({ mensaje }) {
  if (!mensaje) return null;
  return (
    <div className="flex items-start gap-3 p-4 rounded-xl border-l-4 border-accent bg-warning/5 border border-warning/10 animate-fade-slide-up">
      <span className="text-lg mt-0.5 shrink-0">⚠️</span>
      <p className="text-sm text-text/80 leading-relaxed">{mensaje}</p>
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
      className={`card-base overflow-hidden transition-all duration-500 ${
        isOptimo ? 'ring-1 ring-accent/20' : ''
      }`}
      style={{
        animation: `fadeSlideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms forwards`,
        opacity: 0,
      }}
    >
      {isOptimo && (
        <div className="bg-gradient-to-r from-accent/5 to-accent2/5 px-5 sm:px-6 py-3 flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-medium text-accent">
            <svg viewBox="0 0 20 20" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 2 L13 8 L19 9 L14.5 13.5 L16 20 L10 16.5 L4 20 L5.5 13.5 L1 9 L7 8 L10 2Z" />
            </svg>
            {dentro ? 'Mejor opción' : 'Más cercano a tu presupuesto'}
          </span>
          <PrecisionBadge precision={plan.vuelo?.tipo === 'estimado' ? 'estimada' : 'exacta'} />
        </div>
      )}

      {!isOptimo && label && (
        <div className="px-5 sm:px-6 pt-5 pb-0">
          <p className="text-xs text-muted-300 uppercase tracking-wider font-medium">{label}</p>
        </div>
      )}

      <div className={isOptimo || label ? 'p-5 sm:p-6 pt-4' : 'p-5 sm:p-6'}>
        <FlightCard vuelo={plan.vuelo} variant={isOptimo ? 'default' : 'compact'} />

        {plan.hotel && (
          <>
            <div className="border-t border-border-50 my-4" />
            {isOptimo ? (
              <div className={`rounded-xl p-4 border ${
                plan.hotel.tipo === 'recomendado'
                  ? 'bg-accent/5 border-accent/20'
                  : 'bg-card border-border-100'
              }`}>
                <div className="flex items-start gap-4">
                  {(plan.hotel.foto_url && !hotelImgError) ? (
                    <div className="relative w-24 h-16 sm:w-32 sm:h-20 rounded-lg overflow-hidden bg-accent/5 shrink-0">
                      <img
                        src={plan.hotel.foto_url}
                        alt={plan.hotel.nombre}
                        className="w-full h-full object-cover"
                        onError={() => setHotelImgError(true)}
                      />
                    </div>
                  ) : (
                    <div className="w-24 h-16 sm:w-32 sm:h-20 rounded-lg bg-accent2/10 text-accent2 shrink-0 flex items-center justify-center">
                      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M3 21 L21 21" /><path d="M5 21 L5 7 L12 3 L19 7 L19 21" /><path d="M9 21 L9 12 L15 12 L15 21" />
                      </svg>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-text truncate">{plan.hotel.nombre}</p>
                      {plan.hotel.tipo === 'recomendado' && (
                        <span className="badge bg-success/15 text-success border border-success/20 text-[10px] shrink-0">Recomendado</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      {(plan.hotel.estrellas || 0) > 0 && (
                        <span className="text-yellow-500 text-xs">
                          {'★'.repeat(Math.min(plan.hotel.estrellas, 5))}
                        </span>
                      )}
                      {plan.hotel.rating > 0 && (
                        <span className="px-1.5 py-0.5 rounded bg-success/15 text-success text-xs font-bold">{Number(plan.hotel.rating).toFixed(1)}</span>
                      )}
                    </div>
                    <p className="text-xs text-muted-300 mt-1">
                      <span className="font-mono text-accent font-medium">{formatMoney(plan.hotel.precio_noche)}</span> por noche
                      {plan.hotel.noches ? ` × ${plan.hotel.noches} noche${plan.hotel.noches > 1 ? 's' : ''}` : ''}
                      {plan.hotel.precio_total ? ` = ${formatMoney(plan.hotel.precio_total)}` : ''}
                    </p>
                    {plan.hotel.por_que && (
                      <p className="text-xs text-muted-300 mt-1 italic">{plan.hotel.por_que}</p>
                    )}
                  </div>
                  {plan.hotel.link_reserva && (
                    <a href={plan.hotel.link_reserva} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs py-1.5 px-3 shrink-0">
                      Reservar →
                    </a>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0 text-accent2" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M3 21 L21 21" /><path d="M5 21 L5 7 L12 3 L19 7 L19 21" /><path d="M9 21 L9 12 L15 12 L15 21" />
                  </svg>
                  <span className="text-sm text-text truncate">{plan.hotel.nombre}</span>
                  {plan.hotel.tipo === 'recomendado' && (
                    <span className="badge bg-success/15 text-success border border-success/20 text-[10px] shrink-0">Recomendado</span>
                  )}
                </div>
                <span className="font-mono text-sm text-accent shrink-0">{formatMoney(plan.hotel.precio_total)}</span>
              </div>
            )}
          </>
        )}

        {plan.coche && (
          <>
            <div className="border-t border-border-50 my-4" />
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0 text-accent2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 17 L19 17" /><path d="M3 12 L5 7 L7 7 L9 12" />
                  <path d="M21 12 L19 7 L17 7 L15 12" />
                  <circle cx="7" cy="14" r="2" fill="currentColor" /><circle cx="17" cy="14" r="2" fill="currentColor" />
                  <path d="M6 10 L18 10" />
                </svg>
                <div className="min-w-0">
                  <span className="text-sm text-text truncate block">{plan.coche.nombre}</span>
                  {plan.coche.tipo && <span className="text-xs text-muted-300">{plan.coche.tipo}</span>}
                </div>
                {plan.coche.fuera_presupuesto && (
                  <span className="badge bg-accent/15 text-accent border border-accent/20 text-[10px] shrink-0">Excede</span>
                )}
              </div>
              <span className="font-mono text-sm text-accent shrink-0">{formatMoney(plan.coche.precio_total)}</span>
            </div>
          </>
        )}

        {(plan.total != null || plan.presupuesto != null) && (
          <>
            <div className="border-t border-border-50 my-4" />
            <div className={isOptimo ? 'space-y-1.5 text-sm' : 'space-y-1 text-sm'}>
              {plan.vuelo?.precio_total != null && (
                <Row label="Vuelo" value={formatMoney(plan.vuelo.precio_total)} />
              )}
              {plan.hotel?.precio_total != null && (
                <Row label="Hotel" value={formatMoney(plan.hotel.precio_total)} />
              )}
              {plan.coche?.precio_total != null && (
                <Row label="Coche" value={formatMoney(plan.coche.precio_total)} />
              )}
              <div className={`flex justify-between font-medium ${isOptimo ? 'border-t border-border-100 pt-2 mt-2' : 'border-t border-border-50 pt-1.5 mt-1.5'}`}>
                <span className="text-text">Total</span>
                <span className={`font-mono ${!dentro ? 'text-accent' : 'text-text'}`}>{formatMoney(plan.total)}</span>
              </div>
              {isOptimo && (
                <>
                  <Row label="Presupuesto" value={formatMoney(plan.presupuesto)} muted />
                  {dentro ? (
                    <div className="flex justify-between text-xs pt-0.5">
                      <span className="text-success font-medium">Sobrante</span>
                      <span className="font-mono text-success">+{formatMoney(sobrante)}</span>
                    </div>
                  ) : (
                    <div className="flex justify-between text-xs pt-0.5">
                      <span className="text-accent font-medium">Exceso</span>
                      <span className="font-mono text-accent">-{formatMoney(diferencia)}</span>
                    </div>
                  )}
                  <div className="mt-2">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-300">Presupuesto usado</span>
                      <span className={`font-mono font-medium ${!dentro ? 'text-accent' : 'text-text'}`}>
                        {Math.round((plan.total / plan.presupuesto) * 100)}%
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className={`progress-bar-fill ${
                          (plan.total / plan.presupuesto) < 0.6 ? 'bg-success' :
                          (plan.total / plan.presupuesto) < 0.9 ? 'bg-warning' : 'bg-accent'
                        }`}
                        style={{ width: `${Math.min((plan.total / plan.presupuesto) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
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

function Row({ label, value, muted }) {
  return (
    <div className="flex justify-between">
      <span className={muted ? 'text-muted-300' : 'text-muted'}>{label}</span>
      <span className={`font-mono ${muted ? 'text-muted-300' : 'text-text'}`}>{value}</span>
    </div>
  );
}

function HotelSort({ value, onChange }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="text-xs text-muted-300">Ordenar:</span>
      <div className="flex bg-white rounded-lg border border-border-100 overflow-hidden">
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
                : 'text-muted-300 hover:text-text hover:bg-card'
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
      return h.sort((a, b) => (a.precio || a.precio_noche || 0) - (b.precio || b.precio_noche || 0));
    case 'precio_desc':
      return h.sort((a, b) => (b.precio || b.precio_noche || 0) - (a.precio || a.precio_noche || 0));
    case 'rating_desc':
      return h.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    default:
      return h;
  }
}

function HotelSearch({ value, onChange, total }) {
  return (
    <div className="relative">
      <svg viewBox="0 0 20 20" className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-300" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="9" cy="9" r="5.5" />
        <path d="M13 13 L17.5 17.5" />
      </svg>
      <input
        type="text"
        placeholder={`Buscar hotel (${total} disponible${total !== 1 ? 's' : ''})...`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input-field pl-9 pr-8 py-2.5 text-sm"
      />
      {value && (
        <button onClick={() => onChange('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-300 hover:text-text transition-colors">
          <svg viewBox="0 0 20 20" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M5 15L15 5M5 5l10 10" />
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
      <div className="card-base p-6 sm:p-8 text-center animate-scale-in">
        <div className="w-14 h-14 rounded-full bg-warning/10 text-warning flex items-center justify-center mx-auto mb-4">
          <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" /><path d="M12 8 L12 12" /><path d="M12 16 L12 16" />
          </svg>
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

  const { aviso, precision, plan_optimo, alternativas, hoteles, coches, aeropuertos_alternativos, clima } = data;

  const hotelesFiltrados = (hoteles || []).filter((h) => {
    if (!hotelSearch) return true;
    return h.nombre?.toLowerCase().includes(hotelSearch.toLowerCase());
  });
  const sortedHoteles = sortHotels(hotelesFiltrados, hotelSort);

  return (
    <div className="space-y-6">
      <AvisoBanner mensaje={aviso} />

      <SummaryCard data={data} onModify={onModify} />

      {plan_optimo && (
        <TierComparison
          plan={plan_optimo}
          alternativas={alternativas}
          presupuesto={data.presupuesto}
        />
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 animate-fade-slide-up">
        <h2 className="font-display text-xl sm:text-2xl text-text">
          Tu plan de viaje
        </h2>
        {precision && <PrecisionBadge precision={precision} />}
      </div>

      {plan_optimo && <PlanCard plan={plan_optimo} variant="optimo" delay={100} />}

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
          <h3 className="font-display text-lg text-text mb-4">Alternativas</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {alternativas.map((alt, i) => (
              <PlanCard key={i} plan={alt} variant="alternativa" label={`Opción ${i + 1}`} delay={700 + i * 150} />
            ))}
          </div>
        </div>
      )}

      {hoteles?.length > 0 && (
        <div className="animate-fade-slide-up" style={{ animationDelay: '900ms', animationFillMode: 'both' }}>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
            <div>
              <h3 className="font-display text-lg text-text">Más hoteles en {data.ciudad_destino || 'el destino'}</h3>
              <p className="text-sm text-muted-300">Otras opciones disponibles para tus fechas</p>
            </div>
          </div>
          <div className="space-y-3 mb-4">
            <HotelSearch value={hotelSearch} onChange={setHotelSearch} total={hoteles.length} />
            <HotelSort value={hotelSort} onChange={setHotelSort} />
          </div>
          {sortedHoteles.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {sortedHoteles.map((h, i) => (
                <div key={`${h.id || i}`} className="animate-fade-slide-up" style={{ animationDelay: `${1000 + i * 80}ms`, animationFillMode: 'both' }}>
                  <HotelCard hotel={h} />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 card-base">
              <p className="text-sm text-muted-300">No se encontraron hoteles que coincidan con "{hotelSearch}"</p>
              <button onClick={() => setHotelSearch('')} className="btn-outline text-xs mt-3">Limpiar filtro</button>
            </div>
          )}
        </div>
      )}

      {coches?.coches?.length > 0 && (
        <div className="animate-fade-slide-up" style={{ animationDelay: '1100ms', animationFillMode: 'both' }}>
          <h3 className="font-display text-lg text-text mb-4 mt-8">Alquiler de coches</h3>
          <p className="text-sm text-muted-300 mb-4">Opciones de alquiler en {coches.ciudad || 'el destino'}</p>
          <div className="grid grid-cols-1 gap-3">
            {coches.coches.slice(0, 5).map((c, i) => (
              <div key={i} className="animate-fade-slide-up" style={{ animationDelay: `${1200 + i * 80}ms`, animationFillMode: 'both' }}>
                <CarCard car={c} />
              </div>
            ))}
          </div>
          <div className="mt-4 p-4 card-base bg-accent2/[0.02]">
            <p className="text-xs text-muted-300 mb-2">Más opciones de alquiler:</p>
            <div className="flex flex-wrap gap-2">
              <a href={AFFILIATE_LINKS.localrent} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs py-1.5 px-3">
                Localrent →
              </a>
              <a href={AFFILIATE_LINKS.economybookings} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs py-1.5 px-3">
                EconomyBookings →
              </a>
            </div>
          </div>
        </div>
      )}

      {(data.ciudad_destino || data.destino) && (
        <div className="animate-fade-slide-up" style={{ animationDelay: '1300ms', animationFillMode: 'both' }}>
          <div className="card-base p-5 sm:p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center shrink-0">
                <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2 L15 9 L22 9 L16.5 14 L18 21 L12 17 L6 21 L7.5 14 L2 9 L9 9 L12 2Z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-display text-lg text-text">Actividades en {data.ciudad_destino || data.destino}</h3>
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
      )}

      {!plan_optimo && !alternativas?.length && !hoteles?.length && !coches?.coches?.length && (
        <div className="text-center py-10 text-muted-300 animate-fade-slide-up">
          <p className="text-sm">No encontramos opciones para tu búsqueda.</p>
          <button onClick={onRetry} className="btn-outline mt-4">Intentar de nuevo</button>
        </div>
      )}
    </div>
  );
}
