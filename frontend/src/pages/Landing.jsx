import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useScrollReveal } from '../hooks/useScrollReveal';
import SearchWidget from '../components/SearchWidget';
import HowItWorks from '../components/HowItWorks';
import PopularDestinations from '../components/PopularDestinations';
import { IconIsland, IconCheck, IconPlane, IconStar } from '../components/icons';

function TrustStats() {
  const stats = [
    { number: '50+', label: 'Destinos' },
    { number: '15K', label: 'Planes creados' },
    { number: '4.8', label: 'Valoración', icon: IconStar },
  ];
  return (
    <div className="flex flex-wrap items-center gap-8 sm:gap-12 mt-10 pt-8 border-t border-border-100">
      {stats.map((stat) => (
        <div key={stat.label} className="flex items-baseline gap-2">
          <span className="flex items-center gap-1 font-display text-2xl sm:text-3xl text-text">
            {stat.number}
            {stat.icon && <stat.icon className="w-4 h-4 text-warning" />}
          </span>
          <span className="text-sm text-muted-400">{stat.label}</span>
        </div>
      ))}
    </div>
  );
}

// Collage fotográfico del hero: foto grande de destino + mini tarjeta de vuelo
// flotante, para transmitir "viaje real" en el primer vistazo.
function HeroCollage() {
  const [imgError, setImgError] = useState(false);

  return (
    <div className="relative w-72 sm:w-80 lg:w-[26rem] select-none">
      <div className="absolute inset-0 bg-gradient-radial from-accent/10 to-transparent rounded-full blur-2xl scale-110" />

      <div className="relative rounded-3xl overflow-hidden aspect-[4/5] card-shadow-xl rotate-[2deg] border-4 border-white">
        {!imgError ? (
          <img
            src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=70"
            alt="Playa paradisíaca al atardecer"
            className="w-full h-full object-cover animate-kenburns"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-accent/20 via-card to-accent2/30 flex items-center justify-center text-accent">
            <IconIsland className="w-20 h-20" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-text/60 via-transparent to-transparent" />
        <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-2">
          <div>
            <p className="text-white font-display text-xl leading-tight drop-shadow">Bali, Indonesia</p>
            <p className="text-white/80 text-xs mt-0.5">7 noches · vuelo + hotel</p>
          </div>
          <span className="font-mono text-sm font-bold text-white bg-accent/90 px-2.5 py-1 rounded-lg shadow-lg shrink-0">
            $780
          </span>
        </div>
      </div>

      {/* Mini pase de abordar flotante */}
      <div className="absolute -top-5 -left-6 sm:-left-10 glass-strong rounded-2xl px-4 py-3 card-shadow-lg rotate-[-4deg] animate-fade-slide-up" style={{ animationDelay: '400ms', animationFillMode: 'both' }}>
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-bold text-text">BOG</span>
          <span className="relative flex items-center w-14">
            <span className="flex-1 border-t border-dashed border-accent2-400" />
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent absolute left-1/2 -translate-x-1/2" fill="currentColor">
              <g transform="rotate(90 12 12)">
                <path d="M21.5 15.5 L13.5 13 L13.5 5.5 C13.5 4.7 12.8 4 12 4 C11.2 4 10.5 4.7 10.5 5.5 L10.5 13 L2.5 15.5 L2.5 17.5 L10.5 15 L10.5 19.5 L8 21 L8 22.5 L12 21.5 L16 22.5 L16 21 L13.5 19.5 L13.5 15 L21.5 17.5 Z" />
              </g>
            </svg>
            <span className="flex-1 border-t border-dashed border-accent2-400" />
          </span>
          <span className="font-mono text-sm font-bold text-text">DPS</span>
        </div>
        <p className="text-[10px] text-muted-300 mt-1 text-center">Vuelo directo · 2 pasajeros</p>
      </div>

      {/* Chip flotante de presupuesto */}
      <div className="absolute -bottom-4 -right-3 sm:-right-6 bg-white rounded-xl px-3.5 py-2.5 card-shadow-lg rotate-[3deg] border border-border-100 animate-fade-slide-up" style={{ animationDelay: '700ms', animationFillMode: 'both' }}>
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 rounded-full bg-success/15 text-success flex items-center justify-center">
            <IconCheck className="w-3.5 h-3.5" />
          </span>
          <div className="leading-tight">
            <p className="text-[10px] text-muted-300">Presupuesto</p>
            <p className="text-xs font-medium text-success">Te sobran <span className="font-mono">$120</span></p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Estilos por acento con clases LITERALES (Tailwind no detecta clases construidas
// dinámicamente como `bg-${accent}`, así que las definimos completas aquí).
const ACCENT_STYLES = {
  accent: {
    hoverBorder: 'hover:border-accent/30',
    iconBg: 'bg-accent/10',
    iconText: 'text-accent',
    blob: 'bg-accent',
    cta: 'bg-accent hover:bg-accent-600 hover:shadow-accent/25',
  },
  accent2: {
    hoverBorder: 'hover:border-accent2/40',
    iconBg: 'bg-accent2/15',
    iconText: 'text-accent2-700',
    blob: 'bg-accent2',
    cta: 'bg-accent2-600 hover:bg-accent2-700 hover:shadow-accent2/25',
  },
};

function ToolCard({ icon, title, description, features, cta, href, onClick, accent = 'accent' }) {
  const a = ACCENT_STYLES[accent] || ACCENT_STYLES.accent;
  const content = (
    <div
      className={`group relative overflow-hidden rounded-2xl p-6 sm:p-8 transition-all duration-500 cursor-pointer border border-border-100 ${a.hoverBorder} h-full flex flex-col`}
      style={{
        background: `linear-gradient(135deg, rgba(250, 247, 242, 0.95) 0%, rgba(255, 255, 255, 0.6) 100%)`,
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 24px rgba(26, 18, 8, 0.06), 0 1px 4px rgba(26, 18, 8, 0.04)',
      }}
    >
      <div className={`absolute -top-20 -right-20 w-40 h-40 rounded-full opacity-[0.06] pointer-events-none ${a.blob}`} />
      <div className={`absolute -bottom-16 -left-16 w-32 h-32 rounded-full opacity-[0.04] pointer-events-none ${a.blob}`} />

      <div className="flex items-start gap-5 mb-5">
        <div className={`w-14 h-14 rounded-xl ${a.iconBg} flex items-center justify-center shrink-0 ${a.iconText} transition-transform duration-300 group-hover:scale-110 group-hover:rotate-[-4deg]`}>
          {icon}
        </div>
        <div className="min-w-0">
          <h3 className="font-display text-xl sm:text-2xl text-text mb-1">{title}</h3>
          <p className="text-sm text-muted-400 leading-relaxed">{description}</p>
        </div>
      </div>

      <div className="space-y-2.5 mb-6 flex-1">
        {features.map((f, i) => (
          <div key={i} className="flex items-center gap-3 text-sm text-muted-300">
            <svg viewBox="0 0 16 16" className="w-4 h-4 shrink-0 text-success" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 8 L7 12 L13 4" />
            </svg>
            {f}
          </div>
        ))}
      </div>

      <div className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all duration-300 ${a.cta} text-white hover:shadow-lg group-hover:translate-x-0.5 self-start`}>
        {cta}
        <svg viewBox="0 0 16 16" className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 8 L13 8" /><path d="M9 4 L13 8 L9 12" />
        </svg>
      </div>

      <div className="absolute inset-0 rounded-2xl transition-opacity duration-500 opacity-0 group-hover:opacity-100 pointer-events-none" style={{
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 32px rgba(232, 97, 26, 0.08)',
      }} />
    </div>
  );

  if (href) {
    return <Link to={href} className="block">{content}</Link>;
  }
  return <div onClick={onClick} className="cursor-pointer h-full">{content}</div>;
}

function useScrollTo() {
  const scrollToWidget = () => {
    const el = document.getElementById('search-widget-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };
  return scrollToWidget;
}

export default function Landing() {
  const heroRef = useScrollReveal();
  const toolsRef = useScrollReveal();
  const destinationsRef = useScrollReveal();
  const searchRef = useScrollReveal();
  const howItWorksRef = useScrollReveal();
  const scrollToWidget = useScrollTo();

  return (
    <div className="relative">
      <section className="pt-20 sm:pt-24 lg:pt-28 pb-12 sm:pb-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-warm-glow pointer-events-none" />
        <div className="absolute top-10 right-0 w-96 h-96 bg-accent/3 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent2/4 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div ref={heroRef.ref} className={`reveal ${heroRef.isVisible ? 'visible' : ''}`}>
            <div className="flex flex-col lg:flex-row items-center gap-8 lg:gap-14">
              <div className="flex-1 text-center lg:text-left">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-accent/10 text-accent text-xs font-medium rounded-full mb-5">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                  Metabuscador de viajes inteligente
                </div>
                <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl text-text leading-[1.15] tracking-tight">
                  Viaja más,
                  <br />
                  <span className="text-accent">gasta menos.</span>
                </h1>
                <p className="mt-4 text-base sm:text-lg text-muted-400 leading-relaxed max-w-lg mx-auto lg:mx-0">
                  Elige cómo quieres planear: busca vuelos al instante o deja que armes el plan perfecto con tu presupuesto.
                </p>
                <TrustStats />
              </div>
              <div className="shrink-0 py-6 lg:py-0">
                <HeroCollage />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="pb-16 sm:pb-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <div ref={toolsRef.ref} className={`reveal ${toolsRef.isVisible ? 'visible' : ''}`}>
            <div className="text-center mb-8">
              <h2 className="font-display text-2xl sm:text-3xl text-text">¿Cómo quieres viajar?</h2>
              <p className="mt-2 text-muted-400 text-sm sm:text-base">Dos formas de encontrar tu próximo destino</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 sm:gap-6">
              <ToolCard
                icon={
                  <svg viewBox="0 0 28 28" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="8" />
                    <path d="M17 17 L22 22" />
                    <path d="M9 12 L15 12" />
                    <path d="M12 9 L12 15" />
                  </svg>
                }
                title="Buscador rápido"
                description="Encuentra vuelos y hoteles al instante con nuestro buscador integrado."
                features={[
                  'Resultados en segundos',
                  'Compara precios al instante',
                  'Sin registro necesario',
                  'Enlace directo a reserva',
                ]}
                cta="Buscar ahora"
                onClick={scrollToWidget}
                accent="accent"
              />
              <ToolCard
                icon={
                  <svg viewBox="0 0 28 28" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 14 L8 10 L14 12 L20 6 L24 8 L18 16 L12 14 L8 18 L4 14Z" />
                    <path d="M14 12 L18 8" />
                    <path d="M4 20 L8 18" />
                    <path d="M20 6 L24 4" />
                    <path d="M8 10 L4 14 L8 18" />
                    <path d="M12 14 L14 12" />
                    <path d="M20 6 L18 16" />
                  </svg>
                }
                title="Armador de planes"
                description="Dinos tu presupuesto y armamos el viaje completo — vuelo, hotel y coche."
                features={[
                  'Plan personalizado con presupuesto',
                  'Vuelo + hotel + coche en un solo plan',
                  'Compara alternativas lado a lado',
                  'Ahorro garantizado',
                ]}
                cta="Armar mi plan"
                href="/plan"
                accent="accent2"
              />
            </div>
          </div>
        </div>
      </section>

      <div className="relative">
        <div className="absolute top-10 right-0 w-80 h-80 bg-accent/3 rounded-full blur-3xl pointer-events-none" />
        <div ref={destinationsRef.ref} className={`reveal ${destinationsRef.isVisible ? 'visible' : ''}`}>
          <PopularDestinations />
        </div>
      </div>

      <div className="relative" id="search-widget-section">
        <div className="absolute top-0 left-1/4 w-72 h-72 bg-accent/3 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent2/5 rounded-full blur-3xl pointer-events-none" />
        <div ref={searchRef.ref} className={`reveal ${searchRef.isVisible ? 'visible' : ''}`}>
          <section className="pb-16 sm:pb-24">
            <div className="max-w-4xl mx-auto px-4 sm:px-6">
              <div className="text-center mb-8">
                <h2 className="font-display text-2xl sm:text-3xl text-text">
                  Búsqueda rápida
                </h2>
                <p className="mt-2 text-muted-400 text-sm sm:text-base">
                  Encuentra vuelos y hoteles sin complicaciones
                </p>
                <div className="separator mt-5 max-w-xs mx-auto">
                  <IconPlane className="w-3.5 h-3.5 text-accent" />
                </div>
              </div>
              <SearchWidget />
            </div>
          </section>
        </div>
      </div>

      <div className="relative">
        <div className="absolute top-1/2 left-0 w-64 h-64 bg-accent2/4 rounded-full blur-3xl pointer-events-none" />
        <div ref={howItWorksRef.ref} className={`reveal ${howItWorksRef.isVisible ? 'visible' : ''}`}>
          <HowItWorks />
        </div>
      </div>
    </div>
  );
}
