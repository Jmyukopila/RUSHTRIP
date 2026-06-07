export default function FlightRoute({ vuelo, compact = false }) {
  if (!vuelo) return null;

  const origen = vuelo.origen || '???';
  const destino = vuelo.destino || '???';
  const escalas = vuelo.escalas ?? 0;
  const aerolinea = vuelo.aerolinea || '';

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted">
        <span className="font-mono font-medium text-text">{origen}</span>
        <svg viewBox="0 0 24 12" className="w-12 h-3 text-accent2">
          <path
            d="M1 6 Q12 0 23 6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeDasharray={escalas > 0 ? '3 2' : ''}
          />
          {escalas > 0 && (
            <circle cx="12" cy="4" r="1.5" fill="currentColor" />
          )}
          <polygon points="23,6 18,3 18,9" fill="currentColor" />
          <circle cx="1" cy="6" r="2" fill="currentColor" />
        </svg>
        <span className="font-mono font-medium text-text">{destino}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center w-full">
      <svg viewBox="0 0 200 64" className="w-full max-w-[200px] h-12">
        {/* Curved arc path */}
        <path
          d="M 16 40 Q 100 8 184 40"
          fill="none"
          stroke="var(--accent2, #C4A882)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray={escalas > 0 ? '4 3' : ''}
          className="animate-drawLine"
          style={{
            strokeDasharray: escalas > 0 ? '4 3' : '1000',
            strokeDashoffset: 0,
            animation: 'drawRoute 1.5s ease-out forwards',
          }}
        />

        {/* Origin dot */}
        <circle cx="16" cy="40" r="5" fill="var(--accent, #E8611A)" />
        <text x="16" y="54" textAnchor="middle" className="text-[8px]" fill="var(--text, #1A1208)" fontWeight="600" fontFamily="DM Mono, monospace">
          {origen}
        </text>

        {/* Plane icon on the arc */}
        <g transform="translate(100, 16) rotate(-90)">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="var(--accent2, #C4A882)">
            <path d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2v0A1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
          </svg>
        </g>

        {/* Destination dot */}
        <circle cx="184" cy="40" r="5" fill="var(--accent, #E8611A)" />
        <text x="184" y="54" textAnchor="middle" className="text-[8px]" fill="var(--text, #1A1208)" fontWeight="600" fontFamily="DM Mono, monospace">
          {destino}
        </text>

        {/* Connection dots for escalas */}
        {escalas > 0 && (
          <>
            <circle cx="68" cy="20" r="3" fill="var(--muted, #8C7B6B)" />
            <text x="68" y="16" textAnchor="middle" className="text-[6px]" fill="var(--muted, #8C7B6B)" fontFamily="DM Sans, sans-serif">
              {aerolinea}
            </text>
            {escalas > 1 && (
              <circle cx="132" cy="20" r="2.5" fill="var(--muted, #8C7B6B)" />
            )}
          </>
        )}
      </svg>

      {/* Escalas text below */}
      {vuelo.escalas_text && (
        <p className="text-xs text-muted -mt-1">
          {vuelo.escalas_text}
        </p>
      )}
    </div>
  );
}
