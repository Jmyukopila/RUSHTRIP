import { useState, useEffect } from 'react';
import AirportInput from './AirportInput';
import { getMinBudget } from '../api/client';
import {
  IconWallet, IconStar, IconStarRow, IconCheckCircle, MetallicTierIcon, TIER_METAL,
  IconMapPin, IconCalendar, IconClock, IconUsers, IconHotel, IconCar, IconCheck, IconPlane,
} from './icons';

// Metal por tier (neuromarketing): bronce → plata → oro, de menos a más brillante.
const TIERS = [
  {
    key: 'economico',
    label: 'Económico',
    stars: 3,
    desc: 'Viaje funcional, vuelo directo + hoteles 1-3 estrellas',
  },
  {
    key: 'estandar',
    label: 'Estándar',
    stars: 4,
    desc: 'Balance calidad/precio, hoteles 3-4 estrellas',
  },
  {
    key: 'premium',
    label: 'Premium',
    stars: 5,
    desc: 'Máxima comodidad, hoteles 4-5 estrellas, sin low-cost',
  },
];

function SectionHeader({ icon: Icon, step, title, subtitle }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="w-9 h-9 rounded-xl bg-accent/10 text-accent flex items-center justify-center shrink-0">
        <Icon className="w-[18px] h-[18px]" />
      </span>
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-accent2-600 font-semibold">{step}</span>
          <h3 className="font-display text-lg text-text leading-none">{title}</h3>
        </div>
        {subtitle && <p className="text-xs text-muted-300 mt-1">{subtitle}</p>}
      </div>
    </div>
  );
}

function BudgetSlider({ value, min, max, suggested, onChange }) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="relative pt-2 pb-1">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted-300">${min}</span>
        <span className="text-xs text-muted-300">${max}</span>
      </div>
      <div className="relative h-12 flex items-center">
        <input
          type="range"
          min={min}
          max={max}
          step={10}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer bg-border-100
            [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
            [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
            [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-accent/30
            [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white
            [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-200
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5
            [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-accent
            [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white
            [&::-moz-range-thumb]:shadow-lg"
          style={{
            background: `linear-gradient(to right, #E8611A 0%, #E8611A ${pct}%, #E8DDD0 ${pct}%, #E8DDD0 100%)`,
          }}
        />
        <div
          className="absolute -top-3 font-mono text-sm font-bold text-accent bg-white px-2 py-0.5 rounded-md shadow-sm border border-border-100 transition-all duration-150"
          style={{ left: `calc(${pct}% - 20px)` }}
        >
          ${value}
        </div>
      </div>
      {suggested > min && suggested <= max && (
        <div className="flex items-center gap-2 mt-3">
          <div className="w-px h-8 bg-accent2/30" />
          <div className="text-xs text-muted-300">
            <span className="text-accent font-medium">Sugerido: ${suggested}</span>
            {value < suggested && (
              <span className="ml-2 text-warning">— Por debajo de lo recomendado</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Panel lateral "Tu plan": refleja en vivo los datos del formulario.
function LivePlanPanel({ form, minBudgetData, loadingMinBudget, noches }) {
  const origen = form.origenCode || '—';
  const destino = form.destinoCode || '—';
  const tier = TIERS.find((t) => t.key === form.tier) || TIERS[1];
  const suficiente = minBudgetData
    ? form.presupuesto >= minBudgetData.presupuesto_minimo_sugerido
    : null;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border-100 card-shadow-lg bg-gradient-to-br from-accent/[0.05] via-white to-accent2/[0.06]">
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-accent/5 rounded-full blur-2xl pointer-events-none" />

      <div className="relative p-5">
        <div className="flex items-center gap-2 mb-4">
          <IconPlane className="w-4 h-4 text-accent" />
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-400">Tu plan</span>
        </div>

        {/* Ruta */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <span className="font-mono text-2xl font-bold text-text">{origen}</span>
          <span className="flex-1 relative flex items-center px-1">
            <span className="flex-1 border-t border-dashed border-accent2-400/60" />
            <IconPlane className="w-4 h-4 text-accent shrink-0 mx-1 rotate-90" />
            <span className="flex-1 border-t border-dashed border-accent2-400/60" />
          </span>
          <span className="font-mono text-2xl font-bold text-text">{destino}</span>
        </div>

        <div className="space-y-2.5 text-sm border-t border-border-50 pt-4">
          <LiveRow icon={IconCalendar} label="Salida" value={form.fecha_salida || 'Sin fecha'} />
          <LiveRow icon={IconClock} label="Duración" value={`${noches} noche${noches === 1 ? '' : 's'}`} />
          <LiveRow icon={IconUsers} label="Pasajeros" value={`${form.pasajeros}`} />
          <LiveRow icon={(p) => <MetallicTierIcon tier={form.tier} {...p} />} label="Estilo" value={tier.label} />
        </div>

        <div className="mt-4 pt-4 border-t border-border-50">
          <p className="text-[11px] uppercase tracking-wider text-muted-300 mb-1">Presupuesto</p>
          <p className="font-mono text-3xl font-bold text-accent leading-none">${form.presupuesto}</p>
          {loadingMinBudget ? (
            <p className="text-xs text-muted-300 mt-2">Calculando mínimo…</p>
          ) : suficiente === true ? (
            <p className="flex items-center gap-1 text-xs text-success mt-2">
              <IconCheckCircle className="w-3.5 h-3.5" /> Presupuesto suficiente
            </p>
          ) : suficiente === false ? (
            <p className="text-xs text-warning mt-2">
              Mínimo sugerido: ${minBudgetData.presupuesto_minimo_sugerido}
            </p>
          ) : (
            <p className="text-xs text-muted-300 mt-2">Completa origen, destino y fecha</p>
          )}
        </div>
      </div>
    </div>
  );
}

function LiveRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="flex items-center gap-2 text-muted-400">
        <Icon className="w-3.5 h-3.5 text-accent2-600" />
        {label}
      </span>
      <span className="font-medium text-text text-right truncate max-w-[55%]">{value}</span>
    </div>
  );
}

export default function PlanForm({ onPlanCreated, onPlanError, onPlanLoading }) {
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const [form, setForm] = useState({
    origen: null,
    origenCode: '',
    destino: null,
    destinoCode: '',
    fecha_salida: '',
    pasajeros: 2,
    presupuesto: 800,
    tier: 'estandar',
    incluir_hotel: true,
    incluir_vehiculo: false,
    duracion_dias: 7,
  });

  const [minBudgetData, setMinBudgetData] = useState(null);
  const [loadingMinBudget, setLoadingMinBudget] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('rushtrip_last_search');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const cleaned = { ...parsed };
        delete cleaned.modo;
        delete cleaned.fecha_regreso;
        setForm((prev) => ({ ...prev, ...cleaned }));
      } catch {
        // ignore
      }
    }
  }, []);

  useEffect(() => {
    if (!form.origenCode || !form.destinoCode || !form.fecha_salida) return;
    const fecha_regreso = _calcularRegreso(form.fecha_salida, form.duracion_dias);
    setLoadingMinBudget(true);
    getMinBudget({
      origen: form.origenCode,
      destino: form.destinoCode,
      fecha_salida: form.fecha_salida,
      fecha_regreso,
      pasajeros: form.pasajeros,
      incluir_hotel: form.incluir_hotel,
      incluir_vehiculo: form.incluir_vehiculo,
      tier: form.tier,
    })
      .then((data) => {
        setMinBudgetData(data);
        const suggested = data?.presupuesto_minimo_sugerido || 800;
        const maxSug = data?.presupuesto_maximo_sugerido;
        setForm((prev) => {
          let p = Math.max(prev.presupuesto, suggested);
          if (maxSug) p = Math.min(p, maxSug);
          return { ...prev, presupuesto: p };
        });
      })
      .catch(() => {
        setMinBudgetData(null);
      })
      .finally(() => setLoadingMinBudget(false));
  }, [form.origenCode, form.destinoCode, form.fecha_salida, form.duracion_dias, form.pasajeros, form.incluir_hotel, form.incluir_vehiculo, form.tier]);

  const update = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const min = minBudgetData?.presupuesto_minimo_sugerido || 300;
  const max = minBudgetData?.presupuesto_maximo_sugerido || Math.max(min * 4, 2000);

  function _calcularRegreso(salida, dias) {
    if (!salida) return '';
    const d = new Date(salida);
    d.setDate(d.getDate() + dias);
    return d.toISOString().split('T')[0];
  }

  // Fecha de hoy en hora local (no UTC, para no bloquear el día actual por la tarde/noche)
  const today = (() => {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().split('T')[0];
  })();

  const validate = () => {
    const e = {};
    if (!form.origenCode) e.origen = 'Selecciona un origen';
    if (!form.destinoCode) e.destino = 'Selecciona un destino';
    if (!form.fecha_salida) e.fecha_salida = 'Selecciona fecha de salida';
    else if (form.fecha_salida < today) e.fecha_salida = 'La fecha no puede ser anterior a hoy';
    if (form.origenCode && form.destinoCode && form.origenCode === form.destinoCode) {
      e.destino = 'El destino debe ser diferente al origen';
    }
    if (form.duracion_dias > 30) e.duracion_dias = 'Máximo 30 días';
    if (form.presupuesto < min) e.presupuesto = `Mínimo sugerido: $${min}`;
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      // lleva al usuario al primer campo con error
      document.querySelector('.plan-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    setSubmitting(true);
    if (onPlanLoading) onPlanLoading(true);
    try {
      const fecha_regreso = _calcularRegreso(form.fecha_salida, form.duracion_dias);
      const payload = {
        origen: form.origenCode,
        destino: form.destinoCode,
        fecha_salida: form.fecha_salida,
        fecha_regreso,
        presupuesto: form.presupuesto,
        pasajeros: form.pasajeros,
        incluir_hotel: form.incluir_hotel,
        incluir_vehiculo: form.incluir_vehiculo,
        tier: form.tier,
        modo: 'exacto',
        duracion_dias: form.duracion_dias,
      };

      localStorage.setItem('rushtrip_last_search', JSON.stringify({
        origenCode: form.origenCode,
        destinoCode: form.destinoCode,
        pasajeros: form.pasajeros,
        tier: form.tier,
        incluir_hotel: form.incluir_hotel,
        incluir_vehiculo: form.incluir_vehiculo,
      }));

      const { createPlan } = await import('../api/client');
      const data = await createPlan(payload);
      if (onPlanError) onPlanError(null);
      // El backend no devuelve el tier en la respuesta: se conserva el del
      // formulario para que "Guardar plan" lo registre en la reserva.
      if (onPlanCreated) onPlanCreated({ ...data, tier: form.tier });
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Error al crear el plan';
      setErrors((prev) => ({ ...prev, submit: msg }));
      if (onPlanError) onPlanError(new Error(msg));
    } finally {
      setSubmitting(false);
      if (onPlanLoading) onPlanLoading(false);
    }
  };

  return (
    <div className="plan-form grid grid-cols-1 lg:grid-cols-[1fr_19rem] gap-6 lg:gap-8 items-start">
      {/* Columna izquierda: formulario en secciones */}
      <div className="bg-white rounded-2xl border border-border-100 card-shadow-lg divide-y divide-border-50">
        {/* Sección: destino */}
        <section className="p-6 sm:p-7">
          <SectionHeader icon={IconMapPin} step="01" title="¿A dónde vamos?" subtitle="Elige tu punto de partida y tu destino" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AirportInput
              label="Origen"
              placeholder="Ej: Bogotá, Medellín..."
              value={form.origen}
              onChange={(item, code) => {
                update('origen', item);
                update('origenCode', code);
              }}
            />
            <AirportInput
              label="Destino"
              placeholder="Ej: Madrid, Miami..."
              value={form.destino}
              onChange={(item, code) => {
                update('destino', item);
                update('destinoCode', code);
              }}
            />
          </div>
          {errors.origen && <p className="text-xs text-error mt-2">{errors.origen}</p>}
          {errors.destino && <p className="text-xs text-error mt-1">{errors.destino}</p>}
        </section>

        {/* Sección: fechas */}
        <section className="p-6 sm:p-7">
          <SectionHeader icon={IconCalendar} step="02" title="¿Cuándo viajas?" subtitle="Fecha de salida, duración y cuántos van" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-muted-500 mb-1.5">
                <IconCalendar className="w-3.5 h-3.5 text-accent2-600" />
                Fecha de salida
              </label>
              <input
                type="date"
                min={today}
                value={form.fecha_salida}
                onChange={(e) => update('fecha_salida', e.target.value)}
                className="input-field"
              />
              {errors.fecha_salida && <p className="text-xs text-error mt-1">{errors.fecha_salida}</p>}
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-muted-500 mb-1.5">
                <IconClock className="w-3.5 h-3.5 text-accent2-600" />
                Duración
              </label>
              <select
                value={form.duracion_dias}
                onChange={(e) => update('duracion_dias', Number(e.target.value))}
                className="input-field"
              >
                <option value={3}>3 días</option>
                <option value={5}>5 días</option>
                <option value={7}>1 semana</option>
                <option value={10}>10 días</option>
                <option value={14}>2 semanas</option>
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="flex items-center gap-1.5 text-sm font-medium text-muted-500 mb-1.5">
              <IconUsers className="w-3.5 h-3.5 text-accent2-600" />
              Pasajeros
            </label>
            <select
              value={form.pasajeros}
              onChange={(e) => update('pasajeros', Number(e.target.value))}
              className="input-field max-w-[140px]"
            >
              {[...Array(9)].map((_, i) => (
                <option key={i + 1} value={i + 1}>
                  {i + 1} {i === 0 ? 'pasajero' : 'pasajeros'}
                </option>
              ))}
            </select>
          </div>
        </section>

        {/* Sección: presupuesto */}
        <section className="p-6 sm:p-7">
          <SectionHeader icon={IconWallet} step="03" title="¿Cuánto quieres gastar?" subtitle="Ajusta el total y lo hacemos rendir al máximo" />
          <BudgetSlider
            value={form.presupuesto}
            min={Math.floor(min / 10) * 10}
            max={Math.ceil(max / 10) * 10}
            suggested={minBudgetData?.presupuesto_minimo_sugerido || min}
            onChange={(v) => update('presupuesto', v)}
          />
          {errors.presupuesto && <p className="text-xs text-error mt-1">{errors.presupuesto}</p>}
        </section>

        {/* Sección: estilo */}
        <section className="p-6 sm:p-7">
          <SectionHeader icon={IconStar} step="04" title="Estilo de viaje" subtitle="Define la comodidad y qué incluye tu plan" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {TIERS.map((tier) => {
              const active = form.tier === tier.key;
              return (
                <button
                  key={tier.key}
                  type="button"
                  onClick={() => update('tier', tier.key)}
                  className={`relative rounded-xl border-2 p-4 text-left transition-all duration-200 ease-smooth ${
                    active
                      ? 'border-accent bg-accent/5 card-shadow-md'
                      : 'border-border-100 bg-white hover:border-border-300 hover:card-shadow'
                  }`}
                >
                  <div className="flex items-center gap-2.5 mb-2">
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                      style={{ backgroundColor: TIER_METAL[tier.key].tint }}
                    >
                      <MetallicTierIcon tier={tier.key} className="w-4 h-4" />
                    </span>
                    <span className={`font-semibold text-sm ${active ? 'text-accent' : 'text-text'}`}>
                      {tier.label}
                    </span>
                  </div>
                  <div className="mb-2">
                    <IconStarRow count={tier.stars} />
                  </div>
                  <p className="text-xs text-muted-300 leading-relaxed">{tier.desc}</p>
                  {active && (
                    <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-accent flex items-center justify-center">
                      <IconCheck className="w-3 h-3 text-white" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          <div className="mt-5">
            <label className="block text-sm font-medium text-muted-500 mb-3">¿Qué incluye tu viaje?</label>
            <div className="flex flex-wrap gap-3">
              <IncludeToggle
                active={form.incluir_hotel}
                icon={IconHotel}
                label="Incluir hotel"
                onClick={() => update('incluir_hotel', !form.incluir_hotel)}
              />
              <IncludeToggle
                active={form.incluir_vehiculo}
                icon={IconCar}
                label="Incluir vehículo"
                onClick={() => update('incluir_vehiculo', !form.incluir_vehiculo)}
              />
            </div>
          </div>
        </section>

        {/* Envío */}
        <section className="p-6 sm:p-7">
          {errors.submit && (
            <div className="mb-4 p-3 rounded-lg bg-error/5 border border-error/20 text-sm text-error">
              {errors.submit}
            </div>
          )}
          {/* En móvil, el panel "Tu plan" aparece aquí, encima del botón */}
          <div className="lg:hidden mb-5">
            <LivePlanPanel form={form} minBudgetData={minBudgetData} loadingMinBudget={loadingMinBudget} noches={form.duracion_dias} />
          </div>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="btn-primary w-full text-base py-3.5"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
                Armando plan...
              </span>
            ) : (
              'Armar mi plan →'
            )}
          </button>
        </section>
      </div>

      {/* Columna derecha: panel en vivo (solo desktop, sticky) */}
      <aside className="hidden lg:block lg:sticky lg:top-24">
        <LivePlanPanel form={form} minBudgetData={minBudgetData} loadingMinBudget={loadingMinBudget} noches={form.duracion_dias} />
      </aside>
    </div>
  );
}

function IncludeToggle({ active, icon: Icon, label, onClick }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      onClick={onClick}
      className={`group relative flex items-center gap-2.5 pl-3 pr-4 py-2.5 rounded-xl border-2 transition-all duration-200 ease-smooth ${
        active ? 'border-accent bg-accent/5' : 'border-border-100 bg-white hover:border-border-300'
      }`}
    >
      <span className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors duration-200 ${
        active ? 'bg-accent text-white' : 'bg-border-50 text-muted-300'
      }`}>
        <Icon className="w-4 h-4" />
      </span>
      <span className={`text-sm font-medium ${active ? 'text-accent' : 'text-muted-400'}`}>{label}</span>
      {active && (
        <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-accent flex items-center justify-center">
          <IconCheck className="w-2.5 h-2.5 text-white" />
        </span>
      )}
    </button>
  );
}
