import { useEffect, useRef, useState } from 'react';

const STEPS = [
  {
    number: '01',
    title: 'Elige tu destino',
    desc: 'Selecciona origen, destino y las fechas de tu viaje. Tú decides a dónde ir.',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 21 C12 21 5 14.5 5 9.5 C5 5.9 8.1 3 12 3 C15.9 3 19 5.9 19 9.5 C19 14.5 12 21 12 21Z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </svg>
    ),
  },
  {
    number: '02',
    title: 'Pon tu presupuesto',
    desc: '¿Cuánto quieres gastar en total? Ajusta el slider y nosotros hacemos que rinda al máximo.',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 7 C4 5.9 4.9 5 6 5 L18 5 C19.1 5 20 5.9 20 7 L20 17 C20 18.1 19.1 19 18 19 L6 19 C4.9 19 4 18.1 4 17 Z" />
        <path d="M15 12 L20 12" /><circle cx="15.5" cy="12" r="0.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    number: '03',
    title: 'Recibe tu plan',
    desc: 'Te mostramos el vuelo ideal y hoteles ajustados a tu presupuesto. Todo listo para reservar.',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 8 C5.1 8 6 8.9 6 10 C6 11.1 5.1 12 4 12 L4 15 C4 15.6 4.4 16 5 16 L19 16 C19.6 16 20 15.6 20 15 L20 12 C18.9 12 18 11.1 18 10 C18 8.9 18.9 8 20 8 L20 5 C20 4.4 19.6 4 19 4 L5 4 C4.4 4 4 4.4 4 5 Z" transform="translate(0 2)" />
        <path d="M13 8 L13 18" strokeDasharray="2 2.5" transform="translate(0 0)" />
      </svg>
    ),
  },
];

function StepCard({ step, index, isVisible }) {
  return (
    <div
      className="flex gap-5 sm:gap-6 group"
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
        transition: `all 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${index * 0.15}s`,
      }}
    >
      <div className="flex flex-col items-center">
        <div className="w-12 h-12 rounded-xl bg-accent text-white flex items-center justify-center font-display text-lg font-bold shadow-lg shadow-accent/25 shrink-0 transition-transform duration-300 group-hover:scale-105 group-hover:rotate-[-3deg]">
          {step.number}
        </div>
        {index < STEPS.length - 1 && (
          <div className="w-px flex-1 bg-gradient-to-b from-accent/30 to-accent2/20 mt-2" />
        )}
      </div>
      <div className="pb-8 sm:pb-12">
        <div className="flex items-center gap-2.5 mt-1.5 mb-2">
          <span className="w-8 h-8 rounded-lg bg-accent/10 text-accent flex items-center justify-center shrink-0">
            {step.icon}
          </span>
          <h3 className="font-display text-xl sm:text-2xl text-text">
            {step.title}
          </h3>
        </div>
        <p className="text-sm sm:text-base text-muted-400 leading-relaxed max-w-sm">
          {step.desc}
        </p>
      </div>
    </div>
  );
}

export default function HowItWorks() {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="py-16 sm:py-24" ref={ref}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <div
          className="mb-12 sm:mb-16 text-center"
          style={{
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? 'translateY(0)' : 'translateY(16px)',
            transition: 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <h2 className="section-title">¿Cómo funciona?</h2>
          <p className="section-subtitle mx-auto">
            Tres pasos simples para encontrar el viaje perfecto dentro de tu presupuesto.
          </p>
        </div>

        <div className="max-w-lg mx-auto">
          {STEPS.map((step, i) => (
            <StepCard key={i} step={step} index={i} isVisible={isVisible} />
          ))}
        </div>
      </div>
    </section>
  );
}
