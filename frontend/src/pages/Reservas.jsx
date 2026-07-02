import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchReservas, fetchMe } from '../api/client';
import { useAuth } from '../context/AuthContext';
import PrecisionBadge from '../components/PrecisionBadge';
import {
  IconPlane, IconHotel, IconCar, IconUser, IconMapPin, IconCalendar, IconUsers,
  IconWarning, IconCheckCircle, MetallicTierIcon, TIER_METAL,
} from '../components/icons';

const TIER_LABELS = { economico: 'Económico', estandar: 'Estándar', premium: 'Premium' };

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

// created_at llega como epoch (SQLite) o como string ISO (Supabase).
function formatFechaGuardado(valor) {
  if (valor == null) return '';
  const fecha = typeof valor === 'number' ? new Date(valor * 1000) : new Date(valor);
  if (Number.isNaN(fecha.getTime())) return '';
  return fecha.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatFechaViaje(yyyymmdd) {
  if (!yyyymmdd) return '';
  const fecha = new Date(`${yyyymmdd}T00:00:00`);
  if (Number.isNaN(fecha.getTime())) return yyyymmdd;
  return fecha.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
}

function ReservaCard({ reserva, delay = 0 }) {
  const tierKey = TIER_METAL[reserva.tier] ? reserva.tier : 'estandar';
  const dentro = !!reserva.dentro_presupuesto;
  const vueloLink = reserva.detalle?.vuelo?.link_compra;

  return (
    <div
      className="card-base p-5 sm:p-6"
      style={{ animation: `fadeSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms forwards`, opacity: 0 }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-mono font-semibold text-text">{reserva.origen}</span>
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M5 12 H19" /><path d="M14 7 L19 12 L14 17" />
            </svg>
            <span className="font-mono font-semibold text-text">{reserva.destino}</span>
            {reserva.ciudad_destino && (
              <span className="text-muted-300 truncate">· {reserva.ciudad_destino}</span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-muted">
            <span className="flex items-center gap-1.5">
              <IconCalendar className="w-3.5 h-3.5 text-accent2" />
              <span className="font-mono">{formatFechaViaje(reserva.fecha_salida)} — {formatFechaViaje(reserva.fecha_regreso)}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <IconUsers className="w-3.5 h-3.5 text-accent2" />
              {reserva.pasajeros} {reserva.pasajeros === 1 ? 'pasajero' : 'pasajeros'}
            </span>
          </div>
        </div>

        <div className="text-right shrink-0">
          <p className="font-display text-2xl text-accent leading-tight">{formatMoney(reserva.total)}</p>
          {reserva.presupuesto != null && (
            <p className="text-xs text-muted-300 mt-0.5">
              de {formatMoney(reserva.presupuesto)} de presupuesto
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mt-4">
        <span
          className="badge text-[10px] text-text/80 border border-border-100"
          style={{ backgroundColor: TIER_METAL[tierKey].tint }}
        >
          <MetallicTierIcon tier={tierKey} className="w-3 h-3" />
          {TIER_LABELS[tierKey]}
        </span>
        <span className={`badge text-[10px] border ${dentro ? 'bg-success/15 text-success border-success/20' : 'bg-accent/15 text-accent border-accent/20'}`}>
          {dentro ? <IconCheckCircle className="w-3 h-3" /> : <IconWarning className="w-3 h-3" />}
          {dentro ? 'Dentro del presupuesto' : 'Excedía el presupuesto'}
        </span>
        {reserva.incluir_hotel ? (
          <span className="badge text-[10px] bg-accent2/10 text-accent2-700 border border-accent2/20">
            <IconHotel className="w-3 h-3" /> Hotel
          </span>
        ) : null}
        {reserva.incluir_vehiculo ? (
          <span className="badge text-[10px] bg-accent2/10 text-accent2-700 border border-accent2/20">
            <IconCar className="w-3 h-3" /> Coche
          </span>
        ) : null}
        {reserva.precision && <PrecisionBadge precision={reserva.precision} />}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 mt-4 pt-4 border-t border-border-50">
        <p className="text-xs text-muted-300">
          Guardado el <span className="font-mono">{formatFechaGuardado(reserva.created_at)}</span>
        </p>
        {vueloLink && (
          <a href={vueloLink} target="_blank" rel="noopener noreferrer" className="text-xs text-accent hover:underline font-medium">
            Ver precios actuales del vuelo →
          </a>
        )}
      </div>
    </div>
  );
}

export default function Reservas() {
  const { user } = useAuth();
  const [reservas, setReservas] = useState(null);
  const [perfil, setPerfil] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      try {
        const [resReservas, resMe] = await Promise.all([fetchReservas(), fetchMe()]);
        if (cancelado) return;
        setReservas(resReservas.reservas || []);
        setPerfil(resMe.usuario);
      } catch (err) {
        if (!cancelado) setError(err.userMessage || 'No pudimos cargar tus planes guardados.');
      }
    }
    cargar();
    return () => { cancelado = true; };
  }, []);

  const cargando = reservas === null && !error;

  return (
    <div className="py-12 sm:py-16 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-10 animate-fade-slide-up">
          <h1 className="font-display text-3xl sm:text-4xl text-text">Mis reservas</h1>
          <p className="mt-2 text-muted max-w-xl mx-auto">
            Los planes que has guardado en tu cuenta. Recuerda: la compra se completa
            en el sitio de cada proveedor — aquí solo queda tu registro.
          </p>
          <div className="separator mt-5 max-w-[10rem] mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        {/* Perfil */}
        <div
          className="card-base p-5 sm:p-6 mb-6 animate-fade-slide-up"
          style={{ animationDelay: '100ms', animationFillMode: 'both' }}
        >
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="w-10 h-10 rounded-full bg-accent/10 text-accent flex items-center justify-center shrink-0">
                <IconUser className="w-5 h-5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-text truncate">{perfil?.nombre || user?.nombre}</p>
                <p className="text-xs text-muted-300 truncate font-mono">{perfil?.email || user?.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-5 text-center">
              <div>
                <p className="font-mono text-lg font-semibold text-text leading-tight">
                  {perfil?.reservas_count ?? reservas?.length ?? '—'}
                </p>
                <p className="text-[11px] text-muted-300 uppercase tracking-wider">Planes</p>
              </div>
              {perfil?.pais && (
                <div>
                  <p className="text-sm text-text leading-tight mt-1">{perfil.pais}</p>
                  <p className="text-[11px] text-muted-300 uppercase tracking-wider">País</p>
                </div>
              )}
            </div>
          </div>

          {perfil?.destinos_preferidos?.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border-50">
              <p className="text-xs text-muted-300 mb-2">Tus destinos más buscados</p>
              <div className="flex flex-wrap gap-2">
                {perfil.destinos_preferidos.map((d) => (
                  <span key={d.destino_iata} className="badge text-[10px] bg-card text-muted border border-border-100 normal-case tracking-normal">
                    <IconMapPin className="w-3 h-3 text-accent" />
                    {d.ciudad || d.destino_iata}
                    <span className="font-mono text-muted-300">×{d.veces}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Estado de carga / error / vacío / lista */}
        {cargando && (
          <div className="flex flex-col gap-4">
            {[0, 1].map((i) => (
              <div key={i} className="card-base p-6 h-36 skeleton-shimmer" />
            ))}
          </div>
        )}

        {error && (
          <div className="card-base p-6 sm:p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-warning/10 text-warning flex items-center justify-center mx-auto mb-3">
              <IconWarning className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted">{error}</p>
          </div>
        )}

        {reservas?.length === 0 && (
          <div className="card-base p-8 sm:p-10 text-center animate-fade-slide-up">
            <p className="font-display text-lg text-text mb-2">Aún no has guardado ningún plan</p>
            <p className="text-sm text-muted-300 mb-5 max-w-sm mx-auto">
              Arma un viaje a tu presupuesto y pulsa «Guardar plan» para tenerlo siempre a mano.
            </p>
            <Link to="/plan" className="btn-primary">Armar mi viaje</Link>
          </div>
        )}

        {reservas?.length > 0 && (
          <div className="flex flex-col gap-4">
            {reservas.map((r, i) => (
              <ReservaCard key={r.id ?? i} reserva={r} delay={200 + i * 100} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
