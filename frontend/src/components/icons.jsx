// Iconos SVG inline compartidos — reemplazan los emojis en toda la app.
// Mismo estilo que el resto del proyecto: viewBox 24x24, stroke currentColor,
// sin librerías externas (ver CLAUDE.md).
import { useId } from 'react';

// Marca RushTrip: reloj de arena con avión en negativo. Artwork rasterizado en
// public/logo-mark.png (fondo transparente). Único lugar donde vive el logo.
export function LogoMark({ className = 'w-8 h-8' }) {
  return (
    <img
      src="/logo-mark.png"
      alt="RushTrip"
      className={`${className} object-contain select-none`}
      draggable="false"
    />
  );
}

export function IconWarning({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.3 3.9 L2.5 18 C2 18.9 2.7 20 3.7 20 L20.3 20 C21.3 20 22 18.9 21.5 18 L13.7 3.9 C13.2 3 11.8 3 11.3 3.9 Z" />
      <path d="M12 9.5 L12 13.5" />
      <circle cx="12" cy="16.5" r="0.75" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconCheckCircle({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5 L10.5 15 L16 8.5" />
    </svg>
  );
}

export function IconCheck({ className = 'w-3.5 h-3.5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.5 L9.5 17 L19 6.5" />
    </svg>
  );
}

export function IconStar({ className = 'w-4 h-4', filled = true }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={filled ? 0 : 1}>
      <path d="M8 0L9.796 5.528H15.608L10.906 8.944L12.702 14.472L8 11.056L3.298 14.472L5.094 8.944L0.392 5.528H6.204L8 0Z" />
    </svg>
  );
}

// Fila compacta de estrellas llenas/vacías — reemplaza los '★'.repeat(...) y strings 'N★'.
export function IconStarRow({ count, max = 5, className = 'w-3 h-3', gapClassName = 'gap-0.5' }) {
  return (
    <span className={`inline-flex items-center ${gapClassName}`}>
      {[...Array(max)].map((_, i) => (
        <IconStar key={i} className={`${className} ${i < count ? 'text-warning' : 'text-border-200'}`} />
      ))}
    </span>
  );
}

export function IconCrown({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 18 L4 9 L8.5 13 L12 6 L15.5 13 L20 9 L20 18 Z" />
      <path d="M4 18 L20 18" />
    </svg>
  );
}

export function IconWallet({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7.5 C3 6.4 3.9 5.5 5 5.5 L17.5 5.5 C18.6 5.5 19.5 6.4 19.5 7.5 L19.5 17 C19.5 18.1 18.6 19 17.5 19 L5 19 C3.9 19 3 18.1 3 17 Z" />
      <path d="M15.5 12.5 L20.5 12.5 L20.5 15.5 L15.5 15.5 C14.7 15.5 14 14.8 14 14 C14 13.2 14.7 12.5 15.5 12.5 Z" />
      <path d="M3 9 L15 9" />
    </svg>
  );
}

export function IconGem({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6.5 4 L17.5 4 L21.5 9 L12 20.5 L2.5 9 Z" />
      <path d="M2.5 9 L21.5 9" />
      <path d="M9 4 L12 9 L15 4" />
      <path d="M12 9 L9 20.5 M12 9 L15 20.5" opacity="0.55" />
    </svg>
  );
}

// ── Iconos metálicos de tier (bronce < plata < oro, de menos a más brillante) ──
// El degradado vertical (claro→medio→oscuro) da el brillo metálico. El brillo
// aumenta bronce→plata→oro (offset del reflejo más alto y stops más luminosos).
export const TIER_METAL = {
  economico: { stops: ['#E7C29A', '#B87333', '#7A451C'], shine: 0.35, tint: 'rgba(184,115,51,0.14)' }, // bronce
  estandar:  { stops: ['#FBFCFD', '#C4C9D0', '#8C929B'], shine: 0.5,  tint: 'rgba(150,158,170,0.18)' }, // plata
  premium:   { stops: ['#FFF3B0', '#EEBE28', '#B37D08'], shine: 0.7,  tint: 'rgba(212,160,23,0.16)' },  // oro
};

// Silueta rellena de cada tier (para que el degradado metálico se luzca).
const TIER_SHAPE = {
  economico: ( // billetera
    <>
      <path d="M3.5 8 C3.5 6.6 4.6 5.5 6 5.5 L18 5.5 C19.4 5.5 20.5 6.6 20.5 8 L20.5 16 C20.5 17.4 19.4 18.5 18 18.5 L6 18.5 C4.6 18.5 3.5 17.4 3.5 16 Z" />
      <circle cx="16.4" cy="12" r="1.5" fill="rgba(0,0,0,0.22)" />
    </>
  ),
  estandar: ( // estrella
    <path d="M12 2 L14.7 8.6 L21.8 9.2 L16.4 13.9 L18.1 20.9 L12 17.1 L5.9 20.9 L7.6 13.9 L2.2 9.2 L9.3 8.6 Z" />
  ),
  premium: ( // corona
    <>
      <path d="M3.5 8.5 L7.5 12.5 L12 6 L16.5 12.5 L20.5 8.5 L19 17.5 L5 17.5 Z" />
      <path d="M4.5 19 L19.5 19 L19.5 20.6 L4.5 20.6 Z" />
    </>
  ),
};

export function MetallicTierIcon({ tier = 'estandar', className = 'w-4 h-4' }) {
  const raw = useId();
  const gid = `metal-${tier}-${raw.replace(/[^a-zA-Z0-9]/g, '')}`;
  const cfg = TIER_METAL[tier] || TIER_METAL.estandar;
  return (
    <svg viewBox="0 0 24 24" className={className}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0.35" y2="1">
          <stop offset="0%" stopColor={cfg.stops[0]} />
          <stop offset={`${Math.round(cfg.shine * 100)}%`} stopColor={cfg.stops[1]} />
          <stop offset="100%" stopColor={cfg.stops[2]} />
        </linearGradient>
      </defs>
      <g fill={`url(#${gid})`} stroke="none">
        {TIER_SHAPE[tier]}
      </g>
    </svg>
  );
}

export function IconLeaf({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 19 C5 11 10 5 19 4 C19 13 14 18 6 19 Z" />
      <path d="M6 19 C9 15 12 12 17 8" />
    </svg>
  );
}

export function IconDroplet({ className = 'w-3.5 h-3.5' }) {
  // Azul suave horneado (excepción de clima); representa probabilidad de lluvia.
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="#7BA8C4" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3 C12 3 6 10.5 6 15 C6 18.3 8.7 21 12 21 C15.3 21 18 18.3 18 15 C18 10.5 12 3 12 3Z" fill="#7BA8C4" fillOpacity="0.2" />
    </svg>
  );
}

export function IconTicket({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9 C4.1 9 5 8.1 5 7 C5 5.9 4.1 5 3 5 L3 5 L21 5 L21 9 C19.9 9 19 9.9 19 11 C19 12.1 19.9 13 21 13 L21 19 L3 19 L3 13 C4.1 13 5 12.1 5 11 C5 9.9 4.1 9 3 9 Z" />
      <path d="M13 5.5 L13 8" strokeDasharray="1.8 1.8" />
      <path d="M13 11 L13 13.5" strokeDasharray="1.8 1.8" />
      <path d="M13 16 L13 18.5" strokeDasharray="1.8 1.8" />
    </svg>
  );
}

export function IconPlane({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M21.5 15.5 L13.5 13 L13.5 5.5 C13.5 4.7 12.8 4 12 4 C11.2 4 10.5 4.7 10.5 5.5 L10.5 13 L2.5 15.5 L2.5 17.5 L10.5 15 L10.5 19.5 L8 21 L8 22.5 L12 21.5 L16 22.5 L16 21 L13.5 19.5 L13.5 15 L21.5 17.5 Z" />
    </svg>
  );
}

export function IconSparkle({ className = 'w-3.5 h-3.5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M12 2 C12.5 7 14.5 9.5 20 10.5 C14.5 11.5 12.5 14 12 19.5 C11.5 14 9.5 11.5 4 10.5 C9.5 9.5 11.5 7 12 2 Z" />
    </svg>
  );
}

export function IconBed({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 18 L3 9.5 C3 8.7 3.7 8 4.5 8 L10 8 C10.8 8 11.5 8.7 11.5 9.5 L11.5 12" />
      <path d="M12.5 12 L19.5 12 C20.3 12 21 12.7 21 13.5 L21 18" />
      <path d="M3 12 L21 12" />
      <path d="M3 18 L3 20 M21 18 L21 20" />
      <circle cx="6.5" cy="10.3" r="1.3" />
    </svg>
  );
}

// Coche de perfil (estilo Lucide "car"): carrocería, parabrisas y dos ruedas.
export function IconCar({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 17 L4.5 17 A1.5 1.5 0 0 1 3 15.5 L3 13 C3 12.6 3.1 12.3 3.3 12 L4.9 8.8 A2 2 0 0 1 6.7 7.7 L17.3 7.7 A2 2 0 0 1 19.1 8.8 L20.7 12 C20.9 12.3 21 12.6 21 13 L21 15.5 A1.5 1.5 0 0 1 19.5 17 L19 17" />
      <path d="M4 12 L20 12" />
      <path d="M9 17 L15 17" />
      <circle cx="7" cy="17" r="2" />
      <circle cx="17" cy="17" r="2" />
    </svg>
  );
}

// Hotel: edificio de varias plantas con hileras de ventanas y puerta central.
export function IconHotel({ className = 'w-5 h-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 21 L4 5 C4 4.4 4.4 4 5 4 L19 4 C19.6 4 20 4.4 20 5 L20 21" />
      <path d="M2.5 21 L21.5 21" />
      <path d="M10 21 L10 16.8 C10 16 10.7 15.3 11.5 15.3 L12.5 15.3 C13.3 15.3 14 16 14 16.8 L14 21" />
      <path d="M12 4 L12 2.2" />
      <path d="M7.5 8 L7.5 8.01 M12 8 L12 8.01 M16.5 8 L16.5 8.01" />
      <path d="M7.5 11.5 L7.5 11.51 M12 11.5 L12 11.51 M16.5 11.5 L16.5 11.51" />
    </svg>
  );
}

export function IconMapPin({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21 C12 21 5 14.5 5 9.5 C5 5.9 8.1 3 12 3 C15.9 3 19 5.9 19 9.5 C19 14.5 12 21 12 21Z" />
      <circle cx="12" cy="9.5" r="2.3" />
    </svg>
  );
}

export function IconCalendar({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M3.5 9.5 L20.5 9.5" />
      <path d="M8 3 L8 6.5 M16 3 L16 6.5" />
    </svg>
  );
}

export function IconClock({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5 L12 12 L15 14" />
    </svg>
  );
}

export function IconUsers({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 19 C3.5 15.5 6 13.5 9 13.5 C12 13.5 14.5 15.5 14.5 19" />
      <circle cx="17" cy="9" r="2.3" />
      <path d="M15.5 13.7 C18 14.1 19.8 15.9 20 19" />
    </svg>
  );
}

export function IconUser({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="3.3" />
      <path d="M5 20 C5 16 8 13.7 12 13.7 C16 13.7 19 16 19 20" />
    </svg>
  );
}

export function IconMail({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3.5 6.5 L12 12.5 L20.5 6.5" />
    </svg>
  );
}

export function IconLock({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4.5" y="10.5" width="15" height="10" rx="2" />
      <path d="M8 10.5 V7.5 C8 5.3 9.8 3.5 12 3.5 C14.2 3.5 16 5.3 16 7.5 V10.5" />
      <circle cx="12" cy="15" r="1.3" />
    </svg>
  );
}

export function IconPhone({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6.5 3.5 H9 L10.5 8 L8.5 9.5 C9.4 11.5 11 13.1 13 14 L14.5 12 L19 13.5 V16 C19 17.4 17.9 18.5 16.5 18.4 C9.6 18 5 13.4 4.6 6.5 C4.5 5.1 5.6 4 6.5 3.5 Z" />
    </svg>
  );
}

export function IconGlobe({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M3.5 12 H20.5" />
      <path d="M12 3.5 C14.5 6 15.7 9 15.7 12 C15.7 15 14.5 18 12 20.5 C9.5 18 8.3 15 8.3 12 C8.3 9 9.5 6 12 3.5 Z" />
    </svg>
  );
}

export function IconLogout({ className = 'w-4 h-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 4.5 H6.5 C5.4 4.5 4.5 5.4 4.5 6.5 V17.5 C4.5 18.6 5.4 19.5 6.5 19.5 H15" />
      <path d="M18.5 12 H10" />
      <path d="M15.5 8.5 L19 12 L15.5 15.5" />
    </svg>
  );
}

// ── Iconos de destino (fallback cuando la foto no carga / badge de categoría) ──

export function IconTower({ className = 'w-10 h-10' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2.5 L9.5 9 L11 9 L10 21.5 L14 21.5 L13 9 L14.5 9 Z" />
      <path d="M8.5 12 L15.5 12 M7.5 16 L16.5 16 M9.5 9 L14.5 9" />
    </svg>
  );
}

export function IconPalmBeach({ className = 'w-10 h-10' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21 L12 11" />
      <path d="M12 11 C10 9 7 9 5 10.5 C7.5 11.5 10 11.5 12 11" />
      <path d="M12 11 C13 8.5 15.5 7.5 18 8 C16.5 10.5 14.5 11.5 12 11" />
      <path d="M12 11 C11 8.5 8.5 7.5 6.5 8.5 C8 10.5 10 11.5 12 11" />
      <path d="M2.5 19 C6 20.5 18 20.5 21.5 19" />
    </svg>
  );
}

export function IconCityscape({ className = 'w-10 h-10' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21 L3 11 L7 11 L7 21" />
      <path d="M8.5 21 L8.5 6 L13.5 6 L13.5 21" />
      <path d="M15 21 L15 13 L19.5 13 L19.5 21" />
      <path d="M10.3 9 L11.7 9 M10.3 12 L11.7 12 M10.3 15 L11.7 15" />
    </svg>
  );
}

export function IconColumns({ className = 'w-10 h-10' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21 L21 21" />
      <path d="M3.5 9 L20.5 9" />
      <path d="M2.5 6 L12 2.5 L21.5 6" />
      <path d="M5.5 9 L5.5 19 M9.5 9 L9.5 19 M14.5 9 L14.5 19 M18.5 9 L18.5 19" />
    </svg>
  );
}

export function IconToriiGate({ className = 'w-10 h-10' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 6.5 L22 6.5" />
      <path d="M2.8 4 L21.2 4" />
      <path d="M6.5 4 L5.5 21.5 M17.5 4 L18.5 21.5" />
      <path d="M11 6.5 L11 15" />
    </svg>
  );
}

export function IconIsland({ className = 'w-10 h-10' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 15 L14 6.5" />
      <path d="M14 6.5 C15.5 7.5 17 9 17 11.5 C15 11.5 14.5 10.5 14 9" />
      <path d="M14 9 C12.5 8.5 11 8.5 10 9.5 C11.5 10.8 13 11 14 10.5" />
      <path d="M3 18.5 C6 15 9 14 12 15.5 C15 14 18 15 21 18.5" />
      <path d="M2 21 L22 21" />
    </svg>
  );
}

// ── Iconos de categoría de actividad (mapean `categoria` del backend) ──

export function IconFerrisWheel({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="11" r="7.5" />
      <circle cx="12" cy="11" r="1.3" fill="currentColor" stroke="none" />
      <path d="M12 3.5 L12 18.5 M4.5 11 L19.5 11 M6.6 5.6 L17.4 16.4 M17.4 5.6 L6.6 16.4" opacity="0.7" />
      <path d="M12 18.5 L9.5 21.5 M12 18.5 L14.5 21.5" />
    </svg>
  );
}

export function IconMasks({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3.5 6 C3.5 9.5 5 12.5 8 13.5 C11 12.5 12.5 9.5 12.5 6 C9.5 7 6.5 7 3.5 6Z" />
      <path d="M11.5 8 C11.5 11 13 13.5 15.8 14.3 C18.6 13.5 20.5 11 20.5 8 C17.5 8.8 14.5 8.8 11.5 8Z" />
      <circle cx="6" cy="8.3" r="0.6" fill="currentColor" stroke="none" />
      <circle cx="9.3" cy="8.3" r="0.6" fill="currentColor" stroke="none" />
      <circle cx="14.5" cy="10.3" r="0.6" fill="currentColor" stroke="none" />
      <circle cx="17.8" cy="10.3" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconMountain({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2.5 19 L9 8.5 L13 14.5 L15.5 11 L21.5 19 Z" />
      <circle cx="17.5" cy="6.5" r="2" />
    </svg>
  );
}

export function IconChurch({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2.5 L12 5.5 M10.5 4 L13.5 4" />
      <path d="M12 5.5 L12 10 L6 13 L6 20 L18 20 L18 13 Z" />
      <path d="M9.5 20 L9.5 15.5 L14.5 15.5 L14.5 20" />
      <path d="M3.5 20 L20.5 20" />
    </svg>
  );
}

export function IconTree({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21 L12 14.5" />
      <path d="M12 3 L17 10 L14.5 10 L18.5 15.5 L5.5 15.5 L9.5 10 L7 10 Z" />
    </svg>
  );
}

export function IconCastle({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 21 L4 11 L2.5 11 L2.5 8 L5.5 8 L5.5 6 L7.5 6 L7.5 8 L9.5 8 L9.5 6 L11.5 6 L11.5 8 L9.5 8" />
      <path d="M4 11 L20 11 M4 21 L20 21 L20 11" />
      <path d="M20 11 L20 8 L18.5 8 L18.5 6 L16.5 6 L16.5 8 L14.5 8 L14.5 6 L12.5 6 L12.5 8 L14.5 8" />
      <path d="M10 21 L10 16 L14 16 L14 21" />
    </svg>
  );
}

export function IconPin({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21 C12 21 5.5 14.5 5.5 9.7 C5.5 6 8.4 3 12 3 C15.6 3 18.5 6 18.5 9.7 C18.5 14.5 12 21 12 21Z" />
      <circle cx="12" cy="9.7" r="2.4" />
    </svg>
  );
}

export function IconWalking({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="13.5" cy="4.5" r="1.5" />
      <path d="M11.5 8 L14.5 8.5 L16.5 11.5 M14.5 8.5 L12 12 L8.5 13.5 M12 12 L14 15 L12.5 20 M14 15 L18 17.5" />
      <path d="M9 21 L11 16.5" />
    </svg>
  );
}

export function IconBus({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 17 L4 6.5 C4 5.7 4.7 5 5.5 5 L18.5 5 C19.3 5 20 5.7 20 6.5 L20 17 Z" />
      <path d="M4 17 L4 19 L6.5 19 L6.5 17 M17.5 17 L17.5 19 L20 19 L20 17" />
      <path d="M4 12 L20 12" />
      <path d="M7 9 L7 9.01 M17 9 L17 9.01" />
      <circle cx="7" cy="17.5" r="1.3" />
      <circle cx="17" cy="17.5" r="1.3" />
    </svg>
  );
}

export function IconTrain({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 3.5 L18 3.5 C19.1 3.5 20 4.4 20 5.5 L20 15 C20 16.1 19.1 17 18 17 L6 17 C4.9 17 4 16.1 4 15 L4 5.5 C4 4.4 4.9 3.5 6 3.5 Z" />
      <path d="M4 10.5 L20 10.5" />
      <path d="M9 3.5 L9 10.5 M15 3.5 L15 10.5" opacity="0.5" />
      <circle cx="8" cy="13.8" r="1.1" />
      <circle cx="16" cy="13.8" r="1.1" />
      <path d="M8 17 L5.5 20.5 M16 17 L18.5 20.5" />
    </svg>
  );
}

export function IconBoat({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3 L12 12.5" />
      <path d="M12 4.5 L17 8" />
      <path d="M3.5 12.5 L20.5 12.5 L18 18 L6 18 Z" />
      <path d="M2 18.5 C4.5 20.2 7 20.2 9.5 18.5 C12 20.2 14.5 20.2 17 18.5 C19.5 20.2 21 20.2 22 18.5" opacity="0.6" />
    </svg>
  );
}

export function IconWineGlass({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3 L16 3 C16 7.5 14.5 10.5 12 10.5 C9.5 10.5 8 7.5 8 3Z" />
      <path d="M12 10.5 L12 19" />
      <path d="M8.5 21 L15.5 21" />
    </svg>
  );
}

// ── Iconos de clima (mapean el emoji `icono` de la API por su valor) ──
// Multi-tono con colores horneados para que se lean naturales sin depender del
// color del contenedor. El azul de lluvia/nieve es una excepción deliberada y
// acotada a los glifos de clima (la paleta cálida no tiene azul). Ver CLAUDE.md.
const CLIMA = {
  sol:        '#E0AD3E', // ámbar (warning-400)
  nube:       '#B8A999', // gris cálido (muted-300)
  nubeFill:   '#EDE5DB', // relleno gris claro (border-100)
  lluvia:     '#7BA8C4', // azul suave (solo clima)
  nieve:      '#A9C7DA', // azul claro
  rayo:       '#D4A017', // ámbar dorado (warning-500)
};

export function IconSun({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke={CLIMA.sol} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4.5" fill={CLIMA.sol} fillOpacity="0.25" />
      <path d="M12 2.5 L12 4.5 M12 19.5 L12 21.5 M2.5 12 L4.5 12 M19.5 12 L21.5 12 M5 5 L6.4 6.4 M17.6 17.6 L19 19 M5 19 L6.4 17.6 M17.6 6.4 L19 5" />
    </svg>
  );
}

export function IconCloudSun({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <g stroke={CLIMA.sol}>
        <circle cx="8" cy="8" r="3.2" fill={CLIMA.sol} fillOpacity="0.25" />
        <path d="M8 2.5 L8 3.8 M3.3 8 L4.6 8 M4.9 4.3 L5.8 5.2" />
      </g>
      <path d="M8.5 13 C7 13 6 11.9 6 10.6 C6 9.4 6.9 8.4 8.1 8.3 C8.5 6.9 9.8 6 11.3 6 C13.1 6 14.6 7.4 14.7 9.1 C16.2 9.3 17.3 10.5 17.3 12 C17.3 13.7 16 15 14.3 15 L8.5 15 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
    </svg>
  );
}

export function IconCloud({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 17.5 C5 17.5 3.5 16 3.5 14.1 C3.5 12.3 4.9 10.9 6.6 10.7 C7.1 8.6 9 7 11.3 7 C13.9 7 16 9.1 16.1 11.6 C18.2 11.9 19.8 13.6 19.8 15.7 C19.8 17.9 18 19.5 15.9 19.5 L7 19.5 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
    </svg>
  );
}

export function IconFog({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6.5 12 C4.8 12 3.5 10.7 3.5 9.1 C3.5 7.6 4.6 6.4 6 6.2 C6.5 4.5 8.1 3.3 10 3.3 C12.2 3.3 14 5 14.1 7.1 C15.8 7.4 17 8.8 17 10.5 L6.5 10.5 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
      <path d="M3 15 L21 15 M4.5 18 L19.5 18 M6.5 21 L17.5 21" stroke={CLIMA.nube} />
    </svg>
  );
}

export function IconDrizzle({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 14.5 C5 14.5 3.5 13 3.5 11.1 C3.5 9.3 4.9 7.9 6.6 7.7 C7.1 5.6 9 4 11.3 4 C13.9 4 16 6.1 16.1 8.6 C18.2 8.9 19.8 10.6 19.8 12.7 C19.8 13.4 19.6 14 19.3 14.5 L7 14.5 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
      <path d="M8 18 L7 20.5 M12 18 L11 20.5 M16 18 L15 20.5" stroke={CLIMA.lluvia} />
    </svg>
  );
}

export function IconRain({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 13.5 C5 13.5 3.5 12 3.5 10.1 C3.5 8.3 4.9 6.9 6.6 6.7 C7.1 4.6 9 3 11.3 3 C13.9 3 16 5.1 16.1 7.6 C18.2 7.9 19.8 9.6 19.8 11.7 C19.8 12.4 19.6 13 19.3 13.5 L7 13.5 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
      <path d="M7.5 17 L6.2 20.5 M12 17 L10.7 20.5 M16.5 17 L15.2 20.5" stroke={CLIMA.lluvia} />
    </svg>
  );
}

export function IconSnow({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 13.5 C5 13.5 3.5 12 3.5 10.1 C3.5 8.3 4.9 6.9 6.6 6.7 C7.1 4.6 9 3 11.3 3 C13.9 3 16 5.1 16.1 7.6 C18.2 7.9 19.8 9.6 19.8 11.7 C19.8 12.4 19.6 13 19.3 13.5 L7 13.5 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
      <path d="M8 17.5 L8 21.5 M6.3 18.5 L9.7 20.5 M9.7 18.5 L6.3 20.5" stroke={CLIMA.nieve} />
      <path d="M16 17.5 L16 21.5 M14.3 18.5 L17.7 20.5 M17.7 18.5 L14.3 20.5" stroke={CLIMA.nieve} />
    </svg>
  );
}

export function IconStorm({ className = 'w-8 h-8' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 12.5 C5 12.5 3.5 11 3.5 9.1 C3.5 7.3 4.9 5.9 6.6 5.7 C7.1 3.6 9 2 11.3 2 C13.9 2 16 4.1 16.1 6.6 C18.2 6.9 19.8 8.6 19.8 10.7 C19.8 11.4 19.6 12 19.3 12.5 L7 12.5 Z" fill={CLIMA.nubeFill} stroke={CLIMA.nube} />
      <path d="M13 15 L10 19.5 L12.5 19.5 L10.5 23" fill={CLIMA.rayo} stroke="none" />
    </svg>
  );
}

export const WEATHER_ICON_MAP = {
  '☀️': IconSun,
  '🌤️': IconCloudSun,
  '⛅': IconCloudSun,
  '☁️': IconCloud,
  '🌥️': IconCloud,
  '🌫️': IconFog,
  '🌦️': IconDrizzle,
  '🌧️': IconRain,
  '🌨️': IconSnow,
  '❄️': IconSnow,
  '⛈️': IconStorm,
};

// Iconos y labels por medio de transporte del plan (campo `medio` del backend)
export const TRANSPORT_ICONS = {
  avion: IconPlane,
  bus: IconBus,
  tren: IconTrain,
};

export const TRANSPORT_LABELS = {
  avion: 'Avión',
  bus: 'Bus',
  tren: 'Tren',
};

export const ACTIVITY_ICON_MAP = {
  'Parque de atracciones': IconFerrisWheel,
  'Museo': IconColumns,
  'Espectáculo': IconMasks,
  'Mirador': IconMountain,
  'Playa': IconPalmBeach,
  'Templo / Iglesia': IconChurch,
  'Parque / Naturaleza': IconTree,
  'Sitio histórico': IconCastle,
  'Tour guiado': IconWalking,
  'Excursión': IconBus,
  'Paseo en barca': IconBoat,
  'Paseo en barco': IconBoat,
  'Tour gastronómico': IconWineGlass,
  'Atracción': IconPin,
};
