import { useState } from 'react';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

export default function SummaryCard({ data, onModify }) {
  const [copied, setCopied] = useState(false);

  if (!data || !data.plan_optimo) return null;

  const plan = data.plan_optimo;
  const dentro = plan.dentro_presupuesto;
  const pct = data.presupuesto > 0 ? Math.min((plan.total / data.presupuesto) * 100, 100) : 0;
  const sobrante = data.presupuesto - plan.total;

  const colorClass = pct < 60 ? 'bg-success' : pct < 90 ? 'bg-warning' : 'bg-accent';
  const statusText = dentro
    ? `✅ Dentro de tu presupuesto${sobrante > 0 ? ` — te sobran ${formatMoney(sobrante)}` : ''}`
    : `⚠️ Excede el presupuesto por ${formatMoney(Math.abs(sobrante))}`;

  const co2Total =
    (plan.vuelo?.co2_kg || 0) * (data.pasajeros || 1);

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

  return (
    <div className="bg-surface rounded-xl card-shadow-lg border border-border p-5 sm:p-6 animate-popIn">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted mb-1">
            <span className="font-mono font-medium text-text">{data.origen}</span>
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12 H19" />
              <path d="M14 7 L19 12 L14 17" />
            </svg>
            <span className="font-mono font-medium text-text">{data.destino}</span>
            <span className="mx-1">·</span>
            <span>{data.noches || 7} noches</span>
            <span className="mx-1">·</span>
            <span>{data.pasajeros} {data.pasajeros === 1 ? 'pasajero' : 'pasajeros'}</span>
          </div>
          <h3 className="font-display text-2xl text-text">
            Total estimado: <span className="text-accent">{formatMoney(plan.total)}</span>
          </h3>
          <p className="text-sm text-muted mt-1">
            Presupuesto: {formatMoney(data.presupuesto)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleShare}
            className="btn-outline text-xs px-3 py-2"
            title="Copiar enlace para compartir"
          >
            {copied ? '✓ Copiado' : '🔗 Compartir'}
          </button>
          <button
            onClick={onModify}
            className="btn-outline text-xs px-3 py-2"
            title="Modificar búsqueda"
          >
            ✏️ Modificar
          </button>
        </div>
      </div>

      {/* Budget progress bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs mb-1.5">
          <span className="text-muted">Presupuesto usado</span>
          <span className={`font-mono font-medium ${!dentro ? 'text-accent' : 'text-text'}`}>
            {Math.round(pct)}%
          </span>
        </div>
        <div className="progress-bar">
          <div
            className={`progress-bar-fill ${colorClass}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className={`text-sm mt-2 ${dentro ? 'text-success' : 'text-accent'}`}>
          {statusText}
        </p>
      </div>

      {/* Minimum budget hint */}
      {data.presupuesto_minimo_sugerido && (
        <div className="mt-3 text-xs text-muted flex items-center gap-2">
          <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
          <span>
            Presupuesto mínimo sugerido: <span className="font-mono text-text">${Number(data.presupuesto_minimo_sugerido).toLocaleString('en-US')}</span>
            {data.presupuesto < data.presupuesto_minimo_sugerido && (
              <span className="text-warning"> — Por debajo del mínimo estimado</span>
            )}
          </span>
        </div>
      )}

      {/* Quick stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-4 border-t border-border">
        <div className="text-center">
          <p className="text-xs text-muted mb-0.5">Vuelo</p>
          <p className="font-mono text-sm text-text font-medium">
            {formatMoney(plan.vuelo?.precio_total || 0)}
          </p>
        </div>
        {plan.hotel?.precio_total > 0 && (
          <div className="text-center">
            <p className="text-xs text-muted mb-0.5">Hotel</p>
            <p className="font-mono text-sm text-text font-medium">
              {formatMoney(plan.hotel.precio_total)}
            </p>
          </div>
        )}
        {plan.coche?.precio_total > 0 && (
          <div className="text-center">
            <p className="text-xs text-muted mb-0.5">Coche</p>
            <p className="font-mono text-sm text-text font-medium">
              {formatMoney(plan.coche.precio_total)}
            </p>
          </div>
        )}
        {co2Total > 0 && (
          <div className="text-center">
            <p className="text-xs text-muted mb-0.5">CO₂ total</p>
            <p className="font-mono text-sm text-text font-medium" title="Huella de carbono estimada">
              🌱 {co2Total.toFixed(0)} kg
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
