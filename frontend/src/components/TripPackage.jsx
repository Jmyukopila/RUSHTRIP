import { useState } from 'react';
import { Link } from 'react-router-dom';
import HotelCard from './HotelCard';
import CarCard from './CarCard';
import PrecisionBadge from './PrecisionBadge';
import { crearReserva } from '../api/client';
import { AFFILIATE_LINKS } from '../constants';
import {
  IconPlane, IconHotel, IconCar, IconCheck, IconCheckCircle, IconWarning,
  IconLeaf, IconStarRow, TRANSPORT_ICONS, TRANSPORT_LABELS,
} from './icons';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

// ── Renglón del paquete (vuelo / hotel / coche) ──
function PackageRow({ icon: Icon, iconTone, title, subtitle, extra, price, link, linkLabel = 'Ver' }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <span className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${iconTone}`}>
        <Icon className="w-[18px] h-[18px]" />
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-medium text-text truncate">{title}</p>
          {extra}
        </div>
        {subtitle && <p className="text-xs text-muted-300 mt-0.5">{subtitle}</p>}
        {link && (
          <a href={link} target="_blank" rel="noopener noreferrer" className="inline-block text-xs text-accent hover:underline mt-1">
            {linkLabel} →
          </a>
        )}
      </div>
      <span className="font-mono text-sm font-semibold text-text shrink-0">{formatMoney(price)}</span>
    </div>
  );
}

// ── Panel colapsable "Cambiar hotel/coche" ──
function SwapPanel({ title, count, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-border-50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-5 sm:px-6 py-3.5 text-left hover:bg-card/50 transition-colors"
      >
        <span className="text-sm font-medium text-text">
          {title} <span className="text-muted-300 font-normal">({count})</span>
        </span>
        <svg viewBox="0 0 24 24" className={`w-4 h-4 text-muted-300 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="px-5 sm:px-6 pb-5 animate-fadeIn">
          {children}
        </div>
      )}
    </div>
  );
}

function HotelSort({ value, onChange }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-xs text-muted-300">Ordenar:</span>
      <div className="flex bg-white rounded-lg border border-border-100 overflow-hidden flex-wrap">
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
              value === opt.key ? 'bg-accent text-white' : 'text-muted-300 hover:text-text hover:bg-card'
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

export default function TripPackage({ data, onModify }) {
  const [copied, setCopied] = useState(false);
  const [hotelSort, setHotelSort] = useState('recomendado');
  const [hotelSearch, setHotelSearch] = useState('');
  // 'idle' | 'guardando' | 'guardado' | 'error'
  const [saveState, setSaveState] = useState('idle');
  const [saveError, setSaveError] = useState(null);

  const plan = data.plan_optimo;
  if (!plan || !plan.vuelo) return null;

  // Medio de transporte del renglón principal ('avion' | 'bus' | 'tren')
  const medio = plan.vuelo.medio || data.medio_transporte || 'avion';

  const presupuesto = data.presupuesto || 0;
  const total = plan.total || 0;
  const dentro = plan.dentro_presupuesto ?? (total <= presupuesto);
  const pct = presupuesto > 0 ? Math.min((total / presupuesto) * 100, 100) : 0;
  const sobrante = presupuesto - total;
  const pctColor = pct < 60 ? 'bg-success' : pct < 90 ? 'bg-warning' : 'bg-accent';
  const co2Total = (plan.vuelo?.co2_kg || 0) * (data.pasajeros || 1);

  const hoteles = data.hoteles || [];
  const coches = data.coches?.coches || [];

  function handleShare() {
    const params = new URLSearchParams({
      origen: data.origen,
      destino: data.destino,
      salida: data.fecha_salida,
      regreso: data.fecha_regreso,
      presupuesto: data.presupuesto,
      pasajeros: data.pasajeros,
    });
    const url = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleSave() {
    if (saveState === 'guardando' || saveState === 'guardado') return;
    setSaveState('guardando');
    setSaveError(null);
    try {
      await crearReserva({
        origen: data.origen,
        destino: data.destino,
        fecha_salida: data.fecha_salida,
        fecha_regreso: data.fecha_regreso,
        total: plan.total || 0,
        pasajeros: data.pasajeros || 1,
        tier: data.tier || 'estandar',
        presupuesto: data.presupuesto ?? null,
        dentro_presupuesto: dentro,
        incluir_hotel: !!plan.hotel,
        incluir_vehiculo: !!plan.coche,
        precision: data.precision || null,
        ciudad_destino: data.ciudad_destino || '',
        detalle: { vuelo: plan.vuelo, hotel: plan.hotel, coche: plan.coche },
      });
      setSaveState('guardado');
    } catch (err) {
      setSaveState('error');
      setSaveError(err.userMessage || 'No pudimos guardar el plan. Intenta de nuevo.');
    }
  }

  const hotelesFiltrados = hoteles.filter((h) =>
    !hotelSearch ? true : h.nombre?.toLowerCase().includes(hotelSearch.toLowerCase())
  );
  const sortedHoteles = sortHotels(hotelesFiltrados, hotelSort);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border-100 card-shadow-lg bg-gradient-to-br from-accent/[0.04] via-surface to-accent2/[0.04] animate-scale-in">
      <div className="absolute top-0 right-0 w-48 h-48 bg-accent/3 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-32 h-32 bg-accent2/5 rounded-full blur-3xl pointer-events-none" />

      {/* Encabezado */}
      <div className="relative p-5 sm:p-6 pb-0">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-300 mb-1.5">
              <span className="font-mono font-semibold text-text">{data.origen}</span>
              <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M5 12 H19" /><path d="M14 7 L19 12 L14 17" />
              </svg>
              <span className="font-mono font-semibold text-text">{data.destino}</span>
              <span className="text-muted-300 mx-1">·</span>
              <span>{data.noches || 7} noches</span>
              {data.pasajeros && (
                <>
                  <span className="text-muted-300 mx-1">·</span>
                  <span>{data.pasajeros} {data.pasajeros === 1 ? 'pasajero' : 'pasajeros'}</span>
                </>
              )}
            </div>
            <h3 className="font-display text-xl sm:text-2xl text-text flex items-center gap-2">
              Tu paquete de viaje
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <PrecisionBadge precision={plan.vuelo?.tipo === 'estimado' ? 'estimada' : (data.precision || 'exacta')} />
          </div>
        </div>
      </div>

      {/* Renglones del paquete */}
      <div className="relative px-5 sm:px-6">
        <div className="rounded-xl bg-white/60 border border-border-50 px-4 divide-y divide-border-50">
          <PackageRow
            icon={TRANSPORT_ICONS[medio] || IconPlane}
            iconTone="bg-accent/10 text-accent"
            title={plan.vuelo.aerolinea_nombre || (medio === 'avion' ? 'Vuelo' : TRANSPORT_LABELS[medio])}
            subtitle={[
              medio !== 'avion' ? `En ${TRANSPORT_LABELS[medio].toLowerCase()}` : null,
              plan.vuelo.escalas_texto || (plan.vuelo.escalas === 0 ? 'Directo' : plan.vuelo.escalas ? `${plan.vuelo.escalas} escala${plan.vuelo.escalas > 1 ? 's' : ''}` : null),
              plan.vuelo.co2_kg != null ? `${plan.vuelo.co2_kg} kg CO₂/pers.` : null,
            ].filter(Boolean).join(' · ')}
            price={plan.vuelo.precio_total}
            link={plan.vuelo.link_compra}
            linkLabel={medio === 'avion' ? 'Ver vuelo' : `Ver ${TRANSPORT_LABELS[medio].toLowerCase()}`}
          />

          {plan.hotel && (
            <PackageRow
              icon={IconHotel}
              iconTone="bg-accent2/10 text-accent2-700"
              title={plan.hotel.nombre}
              extra={
                <>
                  {plan.hotel.tipo === 'recomendado' && (
                    <span className="badge bg-success/15 text-success border border-success/20 text-[10px]">Recomendado</span>
                  )}
                  {(plan.hotel.estrellas || 0) > 0 && <IconStarRow count={Math.min(plan.hotel.estrellas, 5)} />}
                </>
              }
              subtitle={`${formatMoney(plan.hotel.precio_noche)}/noche${plan.hotel.noches ? ` × ${plan.hotel.noches} noche${plan.hotel.noches > 1 ? 's' : ''}` : ''}`}
              price={plan.hotel.precio_total}
              link={plan.hotel.link_reserva}
              linkLabel="Ver hotel"
            />
          )}

          {plan.coche && (
            <PackageRow
              icon={IconCar}
              iconTone="bg-accent2/10 text-accent2-700"
              title={plan.coche.nombre}
              extra={plan.coche.fuera_presupuesto && (
                <span className="badge bg-accent/15 text-accent border border-accent/20 text-[10px]">Excede</span>
              )}
              subtitle={plan.coche.tipo || 'Alquiler de coche'}
              price={plan.coche.precio_total}
              link={plan.coche.link_reserva}
              linkLabel="Ver coche"
            />
          )}
        </div>
      </div>

      {/* Total + presupuesto */}
      <div className="relative p-5 sm:p-6">
        <div className="flex items-end justify-between gap-3 mb-3">
          <div>
            <p className="text-xs text-muted-300 uppercase tracking-wider">Total del paquete</p>
            <p className="font-display text-3xl sm:text-4xl text-accent leading-tight">{formatMoney(total)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-300">Presupuesto: {formatMoney(presupuesto)}</p>
            <p className={`font-mono text-sm font-semibold ${!dentro ? 'text-accent' : 'text-text'}`}>{Math.round(pct)}% usado</p>
          </div>
        </div>

        <div className="progress-bar">
          <div className={`progress-bar-fill ${pctColor}`} style={{ width: `${pct}%` }} />
        </div>
        <p className={`flex items-center gap-1.5 text-sm mt-2 font-medium ${dentro ? 'text-success' : 'text-accent'}`}>
          {dentro ? <IconCheckCircle className="w-4 h-4 shrink-0" /> : <IconWarning className="w-4 h-4 shrink-0" />}
          {dentro
            ? `Dentro de tu presupuesto${sobrante > 0 ? ` — te sobran ${formatMoney(sobrante)}` : ''}`
            : `Excede el presupuesto por ${formatMoney(Math.abs(sobrante))}`}
        </p>

        {co2Total > 0 && (
          <p className="flex items-center gap-1.5 text-xs text-muted-300 mt-2">
            <IconLeaf className="w-3.5 h-3.5 text-success" />
            Huella estimada del viaje: <span className="font-mono text-text">{co2Total.toFixed(0)} kg CO₂</span>
          </p>
        )}

        {/* Acciones */}
        <div className="flex flex-col sm:flex-row gap-3 mt-5">
          {plan.vuelo?.link_compra && (
            <a href={plan.vuelo.link_compra} target="_blank" rel="noopener noreferrer" className="btn-primary flex-1 text-center">
              Reservar paquete →
            </a>
          )}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={handleSave}
              disabled={saveState === 'guardando' || saveState === 'guardado'}
              className="btn-outline text-sm gap-1.5 disabled:opacity-60"
              title="Guardar este plan en tu cuenta"
            >
              {saveState === 'guardado' && <IconCheck className="w-3.5 h-3.5" />}
              {saveState === 'guardando'
                ? 'Guardando…'
                : saveState === 'guardado'
                ? 'Guardado'
                : 'Guardar plan'}
            </button>
            <button onClick={handleShare} className="btn-outline text-sm gap-1.5" title="Copiar enlace">
              {copied && <IconCheck className="w-3.5 h-3.5" />}
              {copied ? 'Copiado' : 'Compartir'}
            </button>
            <button onClick={onModify} className="btn-outline text-sm" title="Modificar búsqueda">
              Modificar
            </button>
          </div>
        </div>

        {saveState === 'guardado' && (
          <p className="flex items-center gap-1.5 text-sm text-success mt-3 animate-fadeIn">
            <IconCheckCircle className="w-4 h-4 shrink-0" />
            Plan guardado en tu cuenta.{' '}
            <Link to="/reservas" className="text-accent hover:underline font-medium">Ver mis planes →</Link>
          </p>
        )}
        {saveState === 'error' && saveError && (
          <p className="flex items-center gap-1.5 text-sm text-accent mt-3 animate-fadeIn">
            <IconWarning className="w-4 h-4 shrink-0" />
            {saveError}
          </p>
        )}

        <p className="text-xs text-muted-300 mt-4 leading-relaxed">
          «Reservar paquete» te lleva al sitio del proveedor para completar la compra.
          «Guardar plan» solo registra este plan en tu cuenta — no compra ni bloquea tarifas.
        </p>
      </div>

      {/* Paneles colapsables: cambiar piezas del paquete */}
      {hoteles.length > 0 && (
        <SwapPanel title="Cambiar hotel" count={hoteles.length}>
          <div className="mb-3">
            <div className="relative mb-3">
              <svg viewBox="0 0 20 20" className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-300" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <circle cx="9" cy="9" r="5.5" /><path d="M13 13 L17.5 17.5" />
              </svg>
              <input
                type="text"
                placeholder={`Buscar hotel (${hoteles.length} disponible${hoteles.length !== 1 ? 's' : ''})...`}
                value={hotelSearch}
                onChange={(e) => setHotelSearch(e.target.value)}
                className="input-field pl-9 py-2.5 text-sm"
              />
            </div>
            <HotelSort value={hotelSort} onChange={setHotelSort} />
          </div>
          {sortedHoteles.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {sortedHoteles.map((h, i) => (
                <HotelCard
                  key={`${h.id || i}`}
                  hotel={h}
                  checkin={data.fecha_salida}
                  checkout={data.fecha_regreso}
                  adultos={data.pasajeros}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-sm text-muted-300">No se encontraron hoteles que coincidan con "{hotelSearch}"</p>
              <button onClick={() => setHotelSearch('')} className="btn-outline text-xs mt-3">Limpiar filtro</button>
            </div>
          )}
        </SwapPanel>
      )}

      {coches.length > 0 && (
        <SwapPanel title="Cambiar coche" count={coches.length}>
          <div className="grid grid-cols-1 gap-3">
            {coches.slice(0, 5).map((c, i) => (
              <CarCard key={i} car={c} />
            ))}
          </div>
          <div className="mt-4 p-4 rounded-xl bg-accent2/[0.03] border border-border-50">
            <p className="text-xs text-muted-300 mb-2">Más opciones de alquiler:</p>
            <div className="flex flex-wrap gap-2">
              <a href={AFFILIATE_LINKS.localrent} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs py-1.5 px-3">Localrent →</a>
              <a href={AFFILIATE_LINKS.economybookings} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs py-1.5 px-3">EconomyBookings →</a>
            </div>
          </div>
        </SwapPanel>
      )}
    </div>
  );
}
