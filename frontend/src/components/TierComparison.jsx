import { IconStar, IconCheckCircle, IconWarning, IconGem, MetallicTierIcon, TIER_METAL } from './icons';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

const TIERS = [
  { key: 'economico', label: 'Económico', stars: '1-3 estrellas', basePct: 0.65 },
  { key: 'estandar', label: 'Estándar', stars: '3-4 estrellas', basePct: 0.85 },
  { key: 'premium', label: 'Premium', stars: '4-5 estrellas', basePct: 1.15 },
];

export default function TierComparison({ plan, alternativas, presupuesto }) {
  if (!presupuesto) return null;

  const total = plan?.total || 0;
  const pct = presupuesto > 0 ? Math.min((total / presupuesto) * 100, 100) : 0;
  const dentro = plan?.dentro_presupuesto ?? false;

  return (
    <div className="card-base p-5 sm:p-6 animate-scale-in">
      <h3 className="font-display text-lg text-text mb-1">
        Opciones para tu presupuesto
      </h3>
      <p className="text-sm text-muted-300 mb-5">
        Con {formatMoney(presupuesto)} puedes elegir entre estas combinaciones:
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {TIERS.map((tier) => {
          const tierTotal = presupuesto * tier.basePct;
          const tierPct = Math.min((tierTotal / presupuesto) * 100, 100);
          const isSelected =
            (tier.key === 'economico' && dentro && pct < 60) ||
            (tier.key === 'estandar' && dentro && pct >= 60 && pct < 90) ||
            (tier.key === 'premium' && !dentro);

          return (
            <div
              key={tier.key}
              className={`relative rounded-xl border-2 p-4 transition-all duration-200 ${
                isSelected
                  ? tier.key === 'economico'
                    ? 'border-success/30 bg-success/5'
                    : tier.key === 'estandar'
                      ? 'border-accent/30 bg-accent/5'
                      : 'border-accent2/30 bg-accent2/5'
                  : 'border-border-100 bg-white hover:border-border-200'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                  style={{ backgroundColor: TIER_METAL[tier.key].tint }}
                >
                  <MetallicTierIcon tier={tier.key} className="w-3.5 h-3.5" />
                </span>
                <span className="text-sm font-semibold text-text">{tier.label}</span>
              </div>
              <p className="text-xs text-muted-300 mb-1">Hoteles {tier.stars}</p>
              <p className="font-mono text-xl font-bold text-text">
                {formatMoney(tierTotal)}
              </p>

              <div className="mt-3 h-1.5 rounded-full bg-border-50 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    tierPct <= 60 ? 'bg-success' : tierPct <= 90 ? 'bg-warning' : 'bg-accent'
                  }`}
                  style={{ width: `${tierPct}%` }}
                />
              </div>

              <div className="mt-2">
                {tier.key === 'economico' && dentro && pct < 60 && (
                  <span className="badge bg-success/15 text-success border border-success/20 text-[10px]">
                    <IconCheckCircle className="w-3 h-3" /> Dentro
                  </span>
                )}
                {tier.key === 'estandar' && dentro && (
                  <span className="badge bg-accent/15 text-accent border border-accent/20 text-[10px]">
                    <IconStar className="w-3 h-3" /> Recomendado
                  </span>
                )}
                {tier.key === 'estandar' && !dentro && (
                  <span className="badge bg-warning/15 text-warning border border-warning/20 text-[10px]">
                    <IconWarning className="w-3 h-3" /> Excede
                  </span>
                )}
                {tier.key === 'premium' && dentro && (
                  <span className="badge bg-accent2/15 text-accent2-600 border border-accent2/20 text-[10px]">
                    <IconGem className="w-3 h-3" /> Disponible
                  </span>
                )}
                {tier.key === 'premium' && !dentro && (
                  <span className="badge bg-warning/15 text-warning border border-warning/20 text-[10px]">
                    <IconGem className="w-3 h-3" /> Sobre presupuesto
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
