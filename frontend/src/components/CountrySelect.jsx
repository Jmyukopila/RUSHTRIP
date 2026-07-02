import { useState, useRef, useEffect } from 'react';
import { IconGlobe } from './icons';

// Lista de países con su código ISO-2 (para la bandera de flagcdn).
// Orden: hispanohablantes primero, luego otros comunes; "Otro" al final sin bandera.
export const PAISES = [
  { nombre: 'Argentina', iso2: 'ar' },
  { nombre: 'Bolivia', iso2: 'bo' },
  { nombre: 'Chile', iso2: 'cl' },
  { nombre: 'Colombia', iso2: 'co' },
  { nombre: 'Costa Rica', iso2: 'cr' },
  { nombre: 'Cuba', iso2: 'cu' },
  { nombre: 'Ecuador', iso2: 'ec' },
  { nombre: 'El Salvador', iso2: 'sv' },
  { nombre: 'España', iso2: 'es' },
  { nombre: 'Guatemala', iso2: 'gt' },
  { nombre: 'Honduras', iso2: 'hn' },
  { nombre: 'México', iso2: 'mx' },
  { nombre: 'Nicaragua', iso2: 'ni' },
  { nombre: 'Panamá', iso2: 'pa' },
  { nombre: 'Paraguay', iso2: 'py' },
  { nombre: 'Perú', iso2: 'pe' },
  { nombre: 'Puerto Rico', iso2: 'pr' },
  { nombre: 'República Dominicana', iso2: 'do' },
  { nombre: 'Uruguay', iso2: 'uy' },
  { nombre: 'Venezuela', iso2: 've' },
  { nombre: 'Alemania', iso2: 'de' },
  { nombre: 'Australia', iso2: 'au' },
  { nombre: 'Brasil', iso2: 'br' },
  { nombre: 'Canadá', iso2: 'ca' },
  { nombre: 'China', iso2: 'cn' },
  { nombre: 'Estados Unidos', iso2: 'us' },
  { nombre: 'Francia', iso2: 'fr' },
  { nombre: 'India', iso2: 'in' },
  { nombre: 'Italia', iso2: 'it' },
  { nombre: 'Japón', iso2: 'jp' },
  { nombre: 'Países Bajos', iso2: 'nl' },
  { nombre: 'Portugal', iso2: 'pt' },
  { nombre: 'Reino Unido', iso2: 'gb' },
  { nombre: 'Otro', iso2: '' },
];

// Los navegadores en Windows no renderizan los emoji de bandera (muestran el
// código ISO en su lugar), así que usamos imágenes reales de bandera (flagcdn).
function Flag({ iso2 }) {
  if (!iso2) {
    return <span className="w-5 h-[18px] rounded-[2px] bg-card border border-border-200 shrink-0" aria-hidden="true" />;
  }
  return (
    <img
      src={`https://flagcdn.com/24x18/${iso2}.png`}
      srcSet={`https://flagcdn.com/48x36/${iso2}.png 2x`}
      width="24"
      height="18"
      alt=""
      aria-hidden="true"
      loading="lazy"
      className="w-5 h-auto rounded-[2px] shrink-0 object-cover"
      onError={(e) => { e.currentTarget.style.display = 'none'; }}
    />
  );
}

// Dropdown accesible de países con bandera. `value`/`onChange` manejan el
// nombre del país (string) para enviarlo tal cual al backend.
export default function CountrySelect({ value, onChange, id = 'pais', required = false }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const seleccionado = PAISES.find((p) => p.nombre === value) || null;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function seleccionar(nombre) {
    onChange(nombre);
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <div className="relative">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none z-10">
          <IconGlobe className="w-4 h-4" />
        </span>
        <button
          type="button"
          id={id}
          onClick={() => setOpen((o) => !o)}
          className="input-field pl-10 pr-10 flex items-center gap-2 text-left"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
        >
          {seleccionado ? (
            <>
              <Flag iso2={seleccionado.iso2} />
              <span className="text-text truncate">{seleccionado.nombre}</span>
            </>
          ) : (
            <span className="text-muted-300/60">Selecciona tu país</span>
          )}
        </button>
        {/* Input oculto para validación nativa de formulario (required). */}
        {required && (
          <input
            tabIndex={-1}
            aria-hidden="true"
            className="sr-only"
            required
            value={value || ''}
            onChange={() => {}}
          />
        )}
        <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
          <svg viewBox="0 0 24 24" className={`w-4 h-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </span>
      </div>

      {open && (
        <div className="absolute z-30 mt-1.5 w-full bg-white rounded-xl border border-border-200 card-shadow-lg overflow-hidden animate-fade-slide-up">
          <ul className="py-1 max-h-60 overflow-y-auto" role="listbox">
            {PAISES.map((p) => {
              const activo = p.nombre === value;
              return (
                <li key={p.nombre} role="option" aria-selected={activo}>
                  <button
                    type="button"
                    onClick={() => seleccionar(p.nombre)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors duration-150 ${
                      activo ? 'bg-accent/5 text-accent' : 'hover:bg-card text-text'
                    }`}
                  >
                    <Flag iso2={p.iso2} />
                    <span className="text-sm truncate">{p.nombre}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
