import { useState } from 'react';
import { Link } from 'react-router-dom';
import { IconTower, IconPalmBeach, IconCityscape, IconColumns, IconToriiGate, IconIsland } from './icons';

function formatMoney(n) {
  if (n == null || n === 0) return '$0';
  return `$${Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

// Fotos de Unsplash con fallback local (gradiente + icono) si no cargan.
const DESTINOS = [
  {
    ciudad: 'París',
    pais: 'Francia',
    desde: 520,
    icon: IconTower,
    tag: 'Romántico',
    foto: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=700&q=65',
  },
  {
    ciudad: 'Cancún',
    pais: 'México',
    desde: 310,
    icon: IconPalmBeach,
    tag: 'Playa',
    foto: 'https://images.unsplash.com/photo-1512813195386-6cf811ad3542?auto=format&fit=crop&w=700&q=65',
  },
  {
    ciudad: 'Nueva York',
    pais: 'EE. UU.',
    desde: 430,
    icon: IconCityscape,
    tag: 'Ciudad',
    foto: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&w=700&q=65',
  },
  {
    ciudad: 'Roma',
    pais: 'Italia',
    desde: 560,
    icon: IconColumns,
    tag: 'Historia',
    foto: 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=700&q=65',
  },
  {
    ciudad: 'Tokio',
    pais: 'Japón',
    desde: 890,
    icon: IconToriiGate,
    tag: 'Aventura',
    foto: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=700&q=65',
  },
  {
    ciudad: 'Bali',
    pais: 'Indonesia',
    desde: 780,
    icon: IconIsland,
    tag: 'Naturaleza',
    foto: 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=700&q=65',
  },
];

// Layout editorial: 2 tarjetas grandes, 3 medianas y 1 panorámica al cierre
const CARD_LAYOUT = [
  'sm:col-span-3 aspect-[16/10] sm:aspect-[16/9]',
  'sm:col-span-3 aspect-[16/10] sm:aspect-[16/9]',
  'sm:col-span-2 aspect-[16/10] sm:aspect-[4/5]',
  'sm:col-span-2 aspect-[16/10] sm:aspect-[4/5]',
  'sm:col-span-2 aspect-[16/10] sm:aspect-[4/5]',
  'sm:col-span-6 aspect-[16/10] sm:aspect-[21/8]',
];

function DestinoCard({ destino, index }) {
  const [imgError, setImgError] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);
  const destacada = index < 2 || index === 5;

  return (
    <Link
      to="/plan"
      className={`group relative rounded-2xl overflow-hidden card-shadow hover:card-shadow-lg transition-all duration-300 ease-smooth hover:-translate-y-1 ${CARD_LAYOUT[index] || 'sm:col-span-2 aspect-[4/5]'}`}
    >
      {!imgError ? (
        <>
          {!imgLoaded && <div className="absolute inset-0 image-placeholder" />}
          <img
            src={destino.foto}
            alt={`${destino.ciudad}, ${destino.pais}`}
            loading="lazy"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
            className={`absolute inset-0 w-full h-full object-cover transition-all duration-700 ease-smooth group-hover:scale-105 ${
              imgLoaded ? 'opacity-100' : 'opacity-0'
            }`}
          />
        </>
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-accent/15 via-card to-accent2/25 flex items-center justify-center text-accent">
          <destino.icon className="w-14 h-14" />
        </div>
      )}

      <div className="absolute inset-0 bg-gradient-to-t from-text/70 via-text/10 to-transparent" />

      <span className="absolute top-3 left-3 badge bg-white/85 text-text backdrop-blur-sm border-0 text-[10px]">
        <destino.icon className="w-3 h-3" />
        {destino.tag}
      </span>

      <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-5 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h3 className={`font-display text-white leading-tight drop-shadow ${destacada ? 'text-2xl sm:text-3xl' : 'text-xl'}`}>
            {destino.ciudad}
          </h3>
          <p className="text-white/75 text-xs sm:text-sm mt-0.5">{destino.pais}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-white/70 text-[10px] uppercase tracking-wider">Desde</p>
          <p className="font-mono text-white font-bold text-lg sm:text-xl drop-shadow">
            {formatMoney(destino.desde)}
          </p>
        </div>
      </div>

      <div className="absolute inset-0 ring-inset ring-2 ring-accent/0 group-hover:ring-accent/40 rounded-2xl transition-all duration-300 pointer-events-none" />
    </Link>
  );
}

export default function PopularDestinations() {
  return (
    <section className="pb-16 sm:pb-24">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
          <div>
            <h2 className="section-title">Destinos que inspiran</h2>
            <p className="section-subtitle">
              Precios de referencia por persona, vuelo ida y vuelta. Arma tu plan y ajústalo a tu presupuesto.
            </p>
          </div>
          <Link to="/plan" className="btn-outline text-sm shrink-0">
            Ver todos →
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-6 gap-4 sm:gap-5">
          {DESTINOS.map((destino, i) => (
            <DestinoCard key={destino.ciudad} destino={destino} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
