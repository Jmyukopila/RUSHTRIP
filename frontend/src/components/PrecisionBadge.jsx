const BADGE_CONFIG = {
  exacta: {
    label: 'Precios exactos',
    className: 'bg-success/15 text-success border border-success/20',
  },
  mes: {
    label: 'Precios del mes',
    className: 'bg-warning/15 text-warning border border-warning/20',
  },
  aproximada: {
    label: 'Precios aproximados',
    className: 'bg-accent/15 text-accent border border-accent/20',
  },
  estimada: {
    label: 'Precios estimados',
    className: 'bg-error/15 text-error border border-error/20',
  },
  parcial: {
    label: 'Precios parcialmente estimados',
    className: 'bg-warning/15 text-warning border border-warning/20',
  },
  stale: {
    label: 'Datos de cache',
    className: 'bg-accent/15 text-accent border border-accent/20',
  },
};

export default function PrecisionBadge({ precision }) {
  const config = BADGE_CONFIG[precision] || BADGE_CONFIG.aproximada;

  return (
    <span className={`badge ${config.className}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {config.label}
    </span>
  );
}
