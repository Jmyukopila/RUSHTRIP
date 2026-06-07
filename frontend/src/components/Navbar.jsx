import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

const NAV_LINKS = [
  { label: 'Inicio', path: '/' },
  { label: 'Buscar plan', path: '/plan' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (docHeight > 0) {
        setScrollProgress(Math.min((window.scrollY / docHeight) * 100, 100));
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      {/* Scroll progress bar */}
      <div className="fixed top-0 left-0 right-0 z-[60] h-0.5">
        <div
          className="h-full bg-accent transition-all duration-150 ease-out"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>

      <nav
        className={`fixed top-0 left-0 right-0 z-50 bg-bg/90 backdrop-blur-sm border-b border-border transition-all duration-300 ${
          scrolled ? 'shadow-warm h-14 sm:h-16' : 'h-16 sm:h-20'
        }`}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-full">
          <div className="flex items-center justify-between h-full">
            <Link to="/" className="font-display text-2xl sm:text-3xl tracking-tight">
              Rush<span className="text-accent">Trip</span>
            </Link>

            <div className="hidden sm:flex items-center gap-8">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`text-sm font-medium transition-colors duration-200 relative
                    after:absolute after:bottom-[-4px] after:left-0 after:h-px after:bg-accent after:transition-all after:duration-300
                    ${location.pathname === link.path
                      ? 'text-accent after:w-full'
                      : 'text-muted hover:text-text after:w-0 hover:after:w-full'
                    }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <button
              onClick={() => setOpen(!open)}
              className="sm:hidden flex flex-col gap-1.5 p-2"
              aria-label="Menú"
            >
              <span className={`block w-6 h-px bg-text transition-all duration-300 ${open ? 'rotate-45 translate-y-[3.5px]' : ''}`} />
              <span className={`block w-6 h-px bg-text transition-all duration-300 ${open ? 'opacity-0' : ''}`} />
              <span className={`block w-6 h-px bg-text transition-all duration-300 ${open ? '-rotate-45 -translate-y-[3.5px]' : ''}`} />
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile slide-in drawer */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-text/30 backdrop-blur-sm animate-fadeSlideUp"
            onClick={() => setOpen(false)}
          />
          <div className="fixed top-0 right-0 bottom-0 w-72 z-50 bg-surface border-l border-border shadow-warm-xl transform translate-x-0 animate-fadeSlideUp">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <span className="font-display text-xl tracking-tight">
                Rush<span className="text-accent">Trip</span>
              </span>
              <button
                onClick={() => setOpen(false)}
                className="p-2 text-muted hover:text-text transition-colors"
                aria-label="Cerrar menú"
              >
                <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="px-4 py-6 flex flex-col gap-3">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setOpen(false)}
                  className={`text-base font-medium py-3 px-4 rounded-lg transition-colors ${
                    location.pathname === link.path
                      ? 'text-accent bg-accent/5'
                      : 'text-muted hover:text-text hover:bg-card'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}
