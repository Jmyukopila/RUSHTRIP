import { useState, useEffect, useCallback } from 'react';
import AirportInput from './AirportInput';
import { getMinBudget } from '../api/client';

const INITIAL = {
  origen: '',
  destino: '',
  fecha_salida: '',
  fecha_regreso: '',
  presupuesto: '',
  pasajeros: '1',
};

const DEFAULT_BUDGET = 500;

function today() {
  return new Date().toISOString().slice(0, 10);
}

function nextWeek() {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 10);
}

function nextWeekPlus(days) {
  const d = new Date();
  d.setDate(d.getDate() + 7 + days);
  return d.toISOString().slice(0, 10);
}

export default function PlanForm({ onSubmit, loading, initialData = null }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    ...INITIAL,
    fecha_salida: nextWeek(),
    fecha_regreso: nextWeekPlus(7),
  });
  const [errors, setErrors] = useState({});
  const [incluirHotel, setIncluirHotel] = useState(true);
  const [incluirVehiculo, setIncluirVehiculo] = useState(false);
  const [tier, setTier] = useState('estandar');
  const [modoFlexible, setModoFlexible] = useState(false);
  const [duracionDias, setDuracionDias] = useState(7);
  const [minBudget, setMinBudget] = useState(null);
  const [minBudgetLoading, setMinBudgetLoading] = useState(false);

  // Restore from localStorage or initialData
  useEffect(() => {
    if (initialData) {
      setForm((prev) => ({ ...prev, ...initialData }));
      return;
    }
    try {
      const saved = localStorage.getItem('rushtrip_last_search');
      if (saved) {
        const parsed = JSON.parse(saved);
        setForm((prev) => ({ ...prev, ...parsed }));
        if (parsed.incluir_hotel !== undefined) setIncluirHotel(parsed.incluir_hotel);
        if (parsed.incluir_vehiculo !== undefined) setIncluirVehiculo(parsed.incluir_vehiculo);
        if (parsed.tier) setTier(parsed.tier);
        if (parsed.modo === 'flexible') setModoFlexible(true);
        if (parsed.duracion_dias) setDuracionDias(parsed.duracion_dias);
      }
    } catch {
      // ignore
    }
  }, [initialData]);

  // Fetch minimum suggested budget when entering Step 2
  useEffect(() => {
    if (step !== 2) return;
    if (!form.origen || !form.destino || !form.fecha_salida) return;

    const regreso = modoFlexible
      ? form.fecha_salida
      : form.fecha_regreso;
    if (!regreso) return;

    let cancelled = false;
    setMinBudgetLoading(true);

    getMinBudget({
      origen: form.origen,
      destino: form.destino,
      fecha_salida: form.fecha_salida,
      fecha_regreso: regreso,
      pasajeros: parseInt(form.pasajeros, 10) || 1,
      incluir_hotel: incluirHotel,
      incluir_vehiculo: incluirVehiculo,
    }).then((res) => {
      if (!cancelled) {
        setMinBudget(res);
        setMinBudgetLoading(false);
      }
    }).catch(() => {
      if (!cancelled) {
        setMinBudget(null);
        setMinBudgetLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [step, form.origen, form.destino, form.fecha_salida, form.fecha_regreso, modoFlexible, incluirHotel, incluirVehiculo, form.pasajeros]);

  function validateStep1() {
    const errs = {};
    const origenTrim = (form.origen || '').trim();
    const destinoTrim = (form.destino || '').trim();
    if (!origenTrim || origenTrim.length < 2) errs.origen = 'Ingresa al menos 2 caracteres (ciudad o código IATA)';
    if (!destinoTrim || destinoTrim.length < 2) errs.destino = 'Ingresa al menos 2 caracteres (ciudad o código IATA)';
    if (origenTrim && destinoTrim && origenTrim.toLowerCase() === destinoTrim.toLowerCase()) {
      errs.destino = 'El destino no puede ser igual al origen';
    }
    if (!form.fecha_salida) errs.fecha_salida = 'Selecciona fecha de salida';
    if (!modoFlexible) {
      if (!form.fecha_regreso) errs.fecha_regreso = 'Selecciona fecha de regreso';
      if (form.fecha_salida && form.fecha_regreso && form.fecha_regreso <= form.fecha_salida) {
        errs.fecha_regreso = 'Debe ser posterior a la salida';
      }
      if (form.fecha_salida && form.fecha_regreso) {
        const s = new Date(form.fecha_salida);
        const r = new Date(form.fecha_regreso);
        const diffDays = (r - s) / (1000 * 60 * 60 * 24);
        if (diffDays > 30) {
          errs.fecha_regreso = 'Máximo 30 días de estadía';
        }
      }
    }
    return errs;
  }

  function validateStep2() {
    const errs = {};
    const presupuesto = parseFloat(form.presupuesto);
    if (!presupuesto || presupuesto <= 0) errs.presupuesto = 'Ingresa un presupuesto válido';
    const pasajeros = parseInt(form.pasajeros, 10);
    if (!pasajeros || pasajeros < 1) errs.pasajeros = 'Mínimo 1 pasajero';
    return errs;
  }

  function handleNext() {
    const errs = validateStep1();
    setErrors(errs);
    if (Object.keys(errs).length === 0) {
      setStep(2);
      // Set default budget if empty
      setForm((p) => ({
        ...p,
        presupuesto: p.presupuesto || String(DEFAULT_BUDGET),
      }));
      setErrors({});
    }
  }

  function handleBack() {
    setStep(1);
    setErrors({});
  }

  function handleSubmit(e) {
    e.preventDefault();
    const errs = validateStep2();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    const payload = {
      origen: form.origen,
      destino: form.destino,
      fecha_salida: form.fecha_salida,
      fecha_regreso: modoFlexible ? form.fecha_salida : form.fecha_regreso,
      presupuesto: parseFloat(form.presupuesto),
      pasajeros: parseInt(form.pasajeros, 10),
      incluir_hotel: incluirHotel,
      incluir_vehiculo: incluirVehiculo,
      tier,
      modo: modoFlexible ? 'flexible' : 'exacto',
      duracion_dias: duracionDias,
    };

    // Save to localStorage
    try {
      localStorage.setItem('rushtrip_last_search', JSON.stringify(payload));
    } catch {
      // ignore
    }

    onSubmit(payload);
  }

  // Step indicator dots
  function StepIndicator() {
    return (
      <div className="flex items-center justify-center gap-3 mb-8">
        <div className={`flex items-center gap-2 ${step === 1 ? 'text-accent' : 'text-muted'}`}>
          <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 ${
            step === 1 ? 'bg-accent text-white border-accent' : 'bg-card text-muted border-border'
          }`}>
            1
          </span>
          <span className="text-sm font-medium hidden sm:inline">Destino</span>
        </div>
        <div className="w-12 h-px bg-border" />
        <div className={`flex items-center gap-2 ${step === 2 ? 'text-accent' : 'text-muted'}`}>
          <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 ${
            step === 2 ? 'bg-accent text-white border-accent' : 'bg-card text-muted border-border'
          }`}>
            2
          </span>
          <span className="text-sm font-medium hidden sm:inline">Presupuesto</span>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface rounded-xl card-shadow border border-border p-6 sm:p-8">
      <StepIndicator />

      {/* ── STEP 1: Destination & Dates ── */}
      <div className={`transition-all duration-500 ${step === 1 ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-[-20px] absolute pointer-events-none'}`}>
        <div className="text-center sm:text-left mb-6">
          <h2 className="font-display text-2xl sm:text-3xl text-text">
            ¿A dónde vas?
          </h2>
          <p className="text-muted text-sm mt-1">
            Busca tu ciudad de origen y destino
          </p>
        </div>

        <div className="space-y-5">
          <AirportInput
            label="Origen"
            placeholder="Ej: Bogotá, Medellín, Miami..."
            value={form.origen}
            onChange={(code) => setForm((p) => ({ ...p, origen: code }))}
            onSelect={(code, name) => setForm((p) => ({ ...p, origen: code }))}
            error={errors.origen}
            disabled={loading}
          />

          <AirportInput
            label="Destino"
            placeholder="Ej: Cancún, Madrid, Nueva York..."
            value={form.destino}
            onChange={(code) => setForm((p) => ({ ...p, destino: code }))}
            onSelect={(code, name) => setForm((p) => ({ ...p, destino: code }))}
            error={errors.destino}
            disabled={loading}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Fecha de salida</label>
              <input
                type="date"
                name="fecha_salida"
                value={form.fecha_salida}
                onChange={(e) => setForm((p) => ({ ...p, fecha_salida: e.target.value }))}
                min={today()}
                className={`input-field ${errors.fecha_salida ? 'ring-2 ring-warning/40 border-warning' : ''}`}
                disabled={loading}
              />
              {errors.fecha_salida && <p className="mt-1 text-xs text-warning">{errors.fecha_salida}</p>}
            </div>

            {!modoFlexible && (
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Fecha de regreso</label>
                <input
                  type="date"
                  name="fecha_regreso"
                  value={form.fecha_regreso}
                  onChange={(e) => setForm((p) => ({ ...p, fecha_regreso: e.target.value }))}
                  min={form.fecha_salida || today()}
                  className={`input-field ${errors.fecha_regreso ? 'ring-2 ring-warning/40 border-warning' : ''}`}
                  disabled={loading}
                />
                {errors.fecha_regreso && <p className="mt-1 text-xs text-warning">{errors.fecha_regreso}</p>}
              </div>
            )}
          </div>

          {/* Flexible dates toggle */}
          <div className="flex items-center gap-3 p-4 bg-card rounded-lg border border-border">
            <button
              type="button"
              onClick={() => setModoFlexible(!modoFlexible)}
              className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                modoFlexible
                  ? 'bg-accent border-accent'
                  : 'bg-white border-border hover:border-accent/50'
              }`}
            >
              {modoFlexible && (
                <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" strokeWidth="3">
                  <path d="M5 12 L10 17 L19 8" />
                </svg>
              )}
            </button>
            <div className="flex-1">
              <p className="text-sm font-medium text-text">Fechas flexibles</p>
              <p className="text-xs text-muted">Buscaremos los días más baratos del mes</p>
            </div>
            {modoFlexible && (
              <select
                value={duracionDias}
                onChange={(e) => setDuracionDias(parseInt(e.target.value, 10))}
                className="input-field w-auto text-sm py-2 px-3"
              >
                {[3, 5, 7, 10, 14].map((d) => (
                  <option key={d} value={d}>{d} días</option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text mb-1.5">Pasajeros</label>
            <select
              value={form.pasajeros}
              onChange={(e) => setForm((p) => ({ ...p, pasajeros: e.target.value }))}
              className="input-field w-auto"
              disabled={loading}
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
                <option key={n} value={n}>{n} {n === 1 ? 'pasajero' : 'pasajeros'}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-8">
          <button
            type="button"
            onClick={handleNext}
            disabled={loading}
            className="btn-primary w-full text-base px-8 py-3.5"
          >
            Siguiente →
          </button>
        </div>
      </div>

      {/* ── STEP 2: Budget & Preferences ── */}
      <div className={`transition-all duration-500 ${step === 2 ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-[20px] absolute pointer-events-none'}`}>
        <div className="text-center sm:text-left mb-6">
          <h2 className="font-display text-2xl sm:text-3xl text-text">
            ¿Cuál es tu presupuesto?
          </h2>
          <p className="text-muted text-sm mt-1">
            Te ayudamos a que rinda al máximo
          </p>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-text mb-2">Presupuesto total (USD)</label>

            {/* Amount display */}
            <div className="flex items-center justify-center gap-1 mb-4">
              <span className="text-2xl font-mono text-accent font-bold">
                ${Number(form.presupuesto || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
            </div>

            {/* Range slider */}
            <div className="px-1">
              <input
                type="range"
                name="presupuesto_slider"
                min={minBudget?.presupuesto_minimo_sugerido || 100}
                max={(minBudget?.presupuesto_minimo_sugerido || 1000) * 5}
                step={50}
                value={parseInt(form.presupuesto) || (minBudget?.presupuesto_minimo_sugerido || 500)}
                onChange={(e) => setForm((p) => ({ ...p, presupuesto: e.target.value }))}
                disabled={loading}
                className="w-full h-2 rounded-full appearance-none cursor-pointer bg-border accent-accent
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:shadow-warm
                  [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-transform
                  [&::-webkit-slider-thumb]:hover:scale-125
                  [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:rounded-full
                  [&::-moz-range-thumb]:bg-accent [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer"
              />
            </div>

            {/* Min/Max labels */}
            <div className="flex justify-between text-xs text-muted mt-1.5">
              <span>${(minBudget?.presupuesto_minimo_sugerido || 100).toLocaleString('en-US')} mín</span>
              <span className="text-accent2">←→</span>
              <span>${((minBudget?.presupuesto_minimo_sugerido || 1000) * 5).toLocaleString('en-US')} máx</span>
            </div>

            {/* Hidden number input for form validation */}
            <input
              type="hidden"
              name="presupuesto"
              value={form.presupuesto}
            />

            {/* Minimum budget suggestion */}
            {minBudgetLoading ? (
              <p className="text-xs text-muted mt-2 italic animate-pulse">
                Calculando presupuesto mínimo...
              </p>
            ) : minBudget?.presupuesto_minimo_sugerido ? (
              <p className="text-xs text-muted mt-2">
                {Number(form.presupuesto) < minBudget.presupuesto_minimo_sugerido ? (
                  <span className="text-warning">⚠️ </span>
                ) : (
                  <span className="text-success">✓ </span>
                )}
                Presupuesto mínimo sugerido: <span className="font-mono font-medium text-text">${minBudget.presupuesto_minimo_sugerido.toLocaleString('en-US')}</span>
                {Number(form.presupuesto) < minBudget.presupuesto_minimo_sugerido && (
                  <span className="text-warning"> — Muy bajo para este destino</span>
                )}
              </p>
            ) : null}
            {errors.presupuesto && <p className="mt-1 text-xs text-warning">{errors.presupuesto}</p>}
          </div>

          {/* Trip style / Tier */}
          <div>
            <label className="block text-sm font-medium text-text mb-3">Estilo de viaje</label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { key: 'economico', label: 'Económico', desc: 'Hoteles 1-3★', icon: '💚' },
                { key: 'estandar', label: 'Estándar', desc: 'Hoteles 3-4★', icon: '🔵' },
                { key: 'premium', label: 'Premium', desc: 'Hoteles 4-5★', icon: '🟡' },
              ].map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => setTier(opt.key)}
                  className={`flex flex-col items-center gap-1 p-4 rounded-xl border text-sm font-medium transition-all duration-200 cursor-pointer ${
                    tier === opt.key
                      ? 'bg-accent text-white border-accent shadow-warm'
                      : 'bg-card text-text border-border hover:bg-accent/5'
                  }`}
                >
                  <span className="text-lg">{opt.icon}</span>
                  <span>{opt.label}</span>
                  <span className={`text-xs ${tier === opt.key ? 'text-white/70' : 'text-muted'}`}>{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* What to include */}
          <div>
            <label className="block text-sm font-medium text-text mb-3">¿Qué incluir en tu plan?</label>
            <div className="space-y-2">
              <div className="flex items-center gap-3 p-3 bg-accent/5 rounded-lg border border-accent/10">
                <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 2L11 13" />
                  <path d="M22 2L15 22L11 13L2 9L22 2Z" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-medium text-text">Vuelo</p>
                  <p className="text-xs text-muted">Siempre incluido en tu plan</p>
                </div>
                <span className="badge bg-success/15 text-success border border-success/20 text-xs">Incluido</span>
              </div>

              <button
                type="button"
                onClick={() => setIncluirHotel(!incluirHotel)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 text-left ${
                  incluirHotel
                    ? 'bg-accent/5 border-accent/20'
                    : 'bg-card border-border hover:bg-accent/5'
                }`}
              >
                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                  incluirHotel ? 'bg-accent border-accent' : 'bg-white border-border'
                }`}>
                  {incluirHotel && (
                    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="M5 12 L10 17 L19 8" />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-text">🏨 Hotel</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setIncluirVehiculo(!incluirVehiculo)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 text-left ${
                  incluirVehiculo
                    ? 'bg-accent/5 border-accent/20'
                    : 'bg-card border-border hover:bg-accent/5'
                }`}
              >
                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                  incluirVehiculo ? 'bg-accent border-accent' : 'bg-white border-border'
                }`}>
                  {incluirVehiculo && (
                    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="M5 12 L10 17 L19 8" />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-text">🚗 Vehículo</p>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
          <button
            type="button"
            onClick={handleBack}
            disabled={loading}
            className="btn-outline w-full sm:w-auto text-sm"
          >
            ← Atrás
          </button>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full sm:w-auto text-base px-8 py-3.5 disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                  <path d="M12 2 A10 10 0 0 1 22 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
                Armando plan...
              </span>
            ) : (
              'Armar mi plan →'
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
