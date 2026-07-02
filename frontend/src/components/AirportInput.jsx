import { useState, useEffect, useRef, useCallback } from 'react';
import { searchAirports } from '../api/client';

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="9" cy="9" r="5.5" />
      <path d="M13 13 L17.5 17.5" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 10 L8 14 L16 6" />
    </svg>
  );
}

// Los navegadores en Windows no renderizan los emoji de bandera (muestran el
// código ISO en su lugar), así que usamos imágenes reales de bandera (flagcdn).
function FlagIcon({ code }) {
  if (!code) return null;
  const cc = code.slice(0, 2).toLowerCase();
  return (
    <img
      src={`https://flagcdn.com/24x18/${cc}.png`}
      srcSet={`https://flagcdn.com/48x36/${cc}.png 2x`}
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

export default function AirportInput({ label, value, onChange, placeholder = 'Buscar aeropuerto...', disabled = false }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [userInteracted, setUserInteracted] = useState(false);
  const [error, setError] = useState(false);

  const ref = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (value && value !== selected) {
      setSelected(value);
      setQuery(typeof value === 'string' ? value : _readItemName(value));
    } else if (!value && selected) {
      setSelected(null);
      setQuery('');
    }
  }, [value, selected]);

  const doSearch = useCallback(async (q) => {
    if (!q || q.length < 1) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(false);
    try {
      const data = await searchAirports({ q, locale: 'es', limit: 8 });
      const items = Array.isArray(data) ? data : data?.results || data?.data || [];
      setResults(items);
      if (items.length > 0) {
        setOpen(true);
      }
    } catch {
      setError(true);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    setUserInteracted(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 250);
    if (selected) {
      setSelected(null);
    }
    onChange(null, null);
  };

  function _readItemCode(item) {
    return item.code || item.iata || item.codigo || '';
  }
  function _readItemName(item) {
    return item.name || item.nombre || item.city_name || item.city || '';
  }
  function _readItemCountry(item) {
    return item.country_name || item.pais || item.country || '';
  }
  function _readItemCountryCode(item) {
    return item.pais_codigo || item.country_code || item.codigo_pais || '';
  }

  const handleSelect = (item) => {
    const code = _readItemCode(item);
    const name = _readItemName(item);
    const country = _readItemCountry(item);
    setSelected(item);
    setQuery(`${name} (${code})`);
    setOpen(false);
    setUserInteracted(false);
    onChange(item, code);
  };

  useEffect(() => {
    if (!open || userInteracted || results.length === 0 || selected || query.length < 2) return;
    const timer = setTimeout(() => {
      if (!userInteracted && results.length > 0 && !selected && query.length >= 2) {
        handleSelect(results[0]);
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [open, results, userInteracted, selected, query, handleSelect]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setOpen(false);
      if (e.key === 'Enter' && results.length > 0) {
        handleSelect(results[0]);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, results]);

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-muted-500 mb-1.5">
        {label}
      </label>
      <div className="relative">
        <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-300 pointer-events-none">
          {loading ? <Spinner /> : selected ? <CheckIcon /> : <SearchIcon />}
        </div>
        <input
          type="text"
          value={query}
          onChange={handleChange}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className={`input-field pl-10 ${
            disabled
              ? 'opacity-50 cursor-not-allowed'
              : error
                ? 'ring-2 ring-error/15 border-error/50'
                : selected
                  ? 'border-accent/50 bg-accent/[0.02]'
                  : ''
          }`}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-label={label}
        />
        {selected && (
          <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-accent/10 rounded text-xs font-mono text-accent font-medium">
              <span>{_readItemCode(selected)}</span>
            </div>
          </div>
        )}
      </div>

      {open && results.length > 0 && (
        <div className="absolute z-30 mt-1.5 w-full bg-white rounded-xl border border-border-200 card-shadow-lg overflow-hidden animate-fade-slide-up">
          <div className="py-1 max-h-64 overflow-y-auto">
            {results.map((item, i) => {
              const code = _readItemCode(item);
              const name = _readItemName(item);
              const country = _readItemCountry(item);
              const countryCode = _readItemCountryCode(item);
              const isActive = selected && (_readItemCode(selected) === code);
              return (
                <button
                  key={`${code}-${i}`}
                  onClick={() => handleSelect(item)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors duration-150 ${
                    isActive
                      ? 'bg-accent/5 text-accent'
                      : 'hover:bg-card text-text'
                  }`}
                >
                  <FlagIcon code={countryCode} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">{name}</span>
                      <span className="font-mono text-xs text-muted-300 shrink-0">{code}</span>
                    </div>
                    {country && (
                      <p className="text-xs text-muted-300 truncate mt-0.5">{country}</p>
                    )}
                  </div>
                  <svg className="w-4 h-4 text-muted-200 shrink-0" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M7 4 L14 10 L7 16" />
                  </svg>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {open && !loading && results.length === 0 && query.length > 0 && !error && (
        <div className="absolute z-30 mt-1.5 w-full bg-white rounded-xl border border-border-200 card-shadow-lg overflow-hidden animate-fade-slide-up">
          <div className="px-4 py-6 text-center text-sm text-muted-300">
            <p>No encontramos ese aeropuerto.</p>
            <p className="text-xs mt-1">Prueba con el nombre de la ciudad o el código IATA.</p>
          </div>
        </div>
      )}
    </div>
  );
}
