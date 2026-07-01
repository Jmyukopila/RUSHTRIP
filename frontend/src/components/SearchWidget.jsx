import { useState, useEffect, useRef } from 'react';
import { IconWarning, IconSparkle } from './icons';

export default function SearchWidget() {
  const [status, setStatus] = useState('loading');
  const [errorDetail, setErrorDetail] = useState('');
  const moduleScriptRef = useRef(null);

  useEffect(() => {
    const searchEl = document.getElementById('tpwl-search');
    const ticketsEl = document.getElementById('tpwl-tickets');
    if (searchEl?.children?.length || ticketsEl?.children?.length) {
      setStatus('loaded');
      return;
    }

    document.querySelectorAll('script[src*="tpwidg.com"]').forEach((s) => s.remove());

    // Inject inline script that creates the module script
    const inlineScript = document.createElement('script');
    inlineScript.setAttribute('nowprocket', '');
    inlineScript.setAttribute('data-noptimize', '1');
    inlineScript.setAttribute('data-cfasync', 'false');
    inlineScript.setAttribute('data-wpfc-render', 'false');
    inlineScript.setAttribute('seraph-accel-crit', '1');
    inlineScript.setAttribute('data-no-defer', '1');
    inlineScript.textContent = `
      (function () {
        var s = document.createElement("script");
        s.async = 1;
        s.type = "module";
        s.src = "https://tpwidg.com/wl_web/main.js?wl_id=17242";
        s.onerror = function() {
          document.dispatchEvent(new CustomEvent('tpwidg:error', { detail: 'Module script failed to load' }));
        };
        s.onload = function() {
          document.dispatchEvent(new CustomEvent('tpwidg:load'));
        };
        document.head.appendChild(s);
        window.__tpwidgScript = s;
      })();
    `;
    document.head.appendChild(inlineScript);

    // Listen for custom events from the inline script
    function onError(e) {
      setErrorDetail(e.detail || 'Error desconocido');
    }
    document.addEventListener('tpwidg:error', onError);

    // Detect if we're on localhost (most widgets block localhost)
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    // Polling: check if widget rendered into the divs
    const checkLoaded = () => {
      const s = document.getElementById('tpwl-search');
      const t = document.getElementById('tpwl-tickets');
      const hasContent = (s?.children?.length > 0) || (t?.children?.length > 0);
      if (hasContent) {
        setStatus('loaded');
        return true;
      }
      return false;
    };

    const pollInterval = setInterval(() => {
      if (checkLoaded()) {
        clearInterval(pollInterval);
      }
    }, 1000);

    // Timeout after 15s
    const timeout = setTimeout(() => {
      clearInterval(pollInterval);
      setStatus((s) => {
        if (s === 'loading') {
          // Check if the module script element exists but didn't fire events
          const moduleScript = document.querySelector('script[src*="tpwidg.com"]');
          if (moduleScript && !isLocalhost) {
            return 'error';
          }
          return 'error';
        }
        return s;
      });
      // Log diagnostic info to console
      console.debug('[SearchWidget] Timeout reached. Diagnostic info:', {
        isLocalhost,
        hasModuleScript: !!document.querySelector('script[src*="tpwidg.com"]'),
        searchChildren: document.getElementById('tpwl-search')?.children?.length || 0,
        ticketsChildren: document.getElementById('tpwl-tickets')?.children?.length || 0,
        inlineScriptInHead: !!document.querySelector('script[nowprocket]'),
      });
    }, 15000);

    return () => {
      clearInterval(pollInterval);
      clearTimeout(timeout);
      document.removeEventListener('tpwidg:error', onError);
      if (inlineScript.parentNode) {
        inlineScript.parentNode.removeChild(inlineScript);
      }
      document.querySelectorAll('script[src*="tpwidg.com"]').forEach((s) => s.remove());
    };
  }, []);

  const isLocalhost = typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  return (
    <div className="card-base p-6 sm:p-8">
      {status === 'loading' && (
        <div className="flex flex-col items-center justify-center py-10">
          <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin mb-4" />
          <p className="text-sm text-muted animate-pulse">Cargando buscador...</p>
          {isLocalhost && (
            <p className="flex items-start gap-1.5 text-xs text-warning/70 mt-3 max-w-sm text-left mx-auto">
              <IconWarning className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              Estás en localhost. Algunos widgets externos solo se activan en dominio público.
              Puede que veas el mensaje de error aunque funcione en producción.
            </p>
          )}
        </div>
      )}

      {status === 'error' && (
        <div className="text-center py-6">
          <p className="text-sm text-muted mb-2">
            El buscador no pudo cargarse.
          </p>
          {errorDetail && (
            <p className="text-xs text-warning/70 mb-4 font-mono">
              {errorDetail}
            </p>
          )}
          {isLocalhost && (
            <p className="flex items-start gap-1.5 text-xs text-warning/70 mb-4 max-w-sm mx-auto text-left">
              <IconWarning className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              Los widgets de Travelpayouts suelen bloquear localhost.
              Sube el proyecto a un dominio público para que funcione.
            </p>
          )}
          <div className="flex flex-wrap justify-center gap-3 mt-3">
            <a
              href="https://www.aviasales.com"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-outline text-sm"
            >
              Buscar vuelos en Aviasales →
            </a>
            <a
              href="https://www.booking.com"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-outline text-sm"
            >
              Buscar hoteles en Booking →
            </a>
          </div>
        </div>
      )}

      <div id="tpwl-search" className="min-h-[120px]" />
      <div className="separator my-6">
        <IconSparkle className="w-3 h-3 text-accent2" />
      </div>
      <div id="tpwl-tickets" className="min-h-[120px]" />
    </div>
  );
}
