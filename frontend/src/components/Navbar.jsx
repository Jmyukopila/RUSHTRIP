import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { IconUser, IconLogout } from './icons';

const NAV_LINKS = [
  { label: 'Inicio', path: '/' },
  { label: 'Buscar plan', path: '/plan' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate('/');
  }

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

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  return (
    <>
      <div className="fixed top-0 left-0 right-0 z-[60] h-0.5">
        <div
          className="h-full transition-all duration-150 ease-out"
          style={{
            width: `${scrollProgress}%`,
            background: 'linear-gradient(90deg, #E8611A 0%, #C4A882 100%)',
          }}
        />
      </div>

      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ease-smooth ${
          scrolled
            ? 'glass-strong shadow-warm-md h-14 sm:h-16'
            : 'bg-transparent h-16 sm:h-20'
        }`}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-full">
          <div className="flex items-center justify-between h-full">
            <Link to="/" className="flex items-center gap-2.5 group">
              <svg viewBox="0 0 32 32" className="w-7 h-7 sm:w-8 sm:h-8" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="16" cy="16" r="14" stroke="#E8611A" strokeWidth="1.5" opacity="0.3" fill="#E8611A" fillOpacity="0.05" />
                <path d="M10 20 L16 8 L22 20 M12 16 H20" stroke="#E8611A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="font-display text-xl sm:text-2xl tracking-tight">
                Rush<span className="text-accent">Trip</span>
              </span>
            </Link>

            <div className="hidden sm:flex items-center gap-1">
              {NAV_LINKS.map((link) => {
                const active = location.pathname === link.path;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    className={`relative px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                      active
                        ? 'text-accent bg-accent/5'
                        : 'text-muted hover:text-text hover:bg-black/[0.02]'
                    }`}
                  >
                    {link.label}
                    {active && (
                      <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-accent" />
                    )}
                  </Link>
                );
              })}

              <span className="w-px h-5 bg-border-200 mx-2" />

              {isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 text-sm text-muted max-w-[12rem] truncate">
                    <IconUser className="w-4 h-4 text-accent shrink-0" />
                    <span className="truncate">{user?.nombre || user?.email}</span>
                  </span>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-muted hover:text-accent rounded-lg transition-all duration-200"
                    aria-label="Cerrar sesión"
                  >
                    <IconLogout className="w-4 h-4" />
                    Salir
                  </button>
                </div>
              ) : (
                <Link to="/login" className="btn-primary px-4 py-2 text-sm">
                  Iniciar sesión
                </Link>
              )}
            </div>

            <button
              onClick={() => setOpen(!open)}
              className="sm:hidden relative z-50 w-10 h-10 flex items-center justify-center"
              aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
            >
              <span className="sr-only">{open ? 'Cerrar' : 'Abrir'}</span>
              <span className={`block absolute w-5 h-px bg-text transition-all duration-300 ease-smooth ${open ? 'rotate-45' : '-translate-y-1.5'}`} />
              <span className={`block absolute w-5 h-px bg-text transition-all duration-300 ease-smooth ${open ? 'opacity-0' : ''}`} />
              <span className={`block absolute w-5 h-px bg-text transition-all duration-300 ease-smooth ${open ? '-rotate-45' : 'translate-y-1.5'}`} />
            </button>
          </div>
        </div>
      </nav>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-text/20 backdrop-blur-sm animate-fadeIn"
            onClick={() => setOpen(false)}
          />
          <div className="fixed top-0 right-0 bottom-0 w-72 z-50 bg-white/90 backdrop-blur-xl border-l border-border-200 shadow-xl animate-slide-up-reveal">
            <div className="flex items-center justify-between p-5 border-b border-border-100">
              <Link to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
                <svg viewBox="0 0 32 32" className="w-6 h-6" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="16" cy="16" r="14" stroke="#E8611A" strokeWidth="1.5" opacity="0.3" fill="#E8611A" fillOpacity="0.05" />
                  <path d="M10 20 L16 8 L22 20 M12 16 H20" stroke="#E8611A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="font-display text-lg tracking-tight">
                  Rush<span className="text-accent">Trip</span>
                </span>
              </Link>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 text-muted hover:text-text transition-colors rounded-lg hover:bg-card"
                aria-label="Cerrar menú"
              >
                <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 flex flex-col gap-1">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setOpen(false)}
                  className={`text-base font-medium py-3 px-4 rounded-lg transition-all ${
                    location.pathname === link.path
                      ? 'text-accent bg-accent/5'
                      : 'text-muted hover:text-text hover:bg-card'
                  }`}
                >
                  {link.label}
                </Link>
              ))}

              <div className="h-px bg-border-100 my-2" />

              {isAuthenticated ? (
                <>
                  <div className="flex items-center gap-2 py-2 px-4 text-sm text-muted">
                    <IconUser className="w-4 h-4 text-accent shrink-0" />
                    <span className="truncate">{user?.nombre || user?.email}</span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 text-base font-medium py-3 px-4 rounded-lg text-muted hover:text-accent hover:bg-card transition-all"
                  >
                    <IconLogout className="w-4 h-4" />
                    Cerrar sesión
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setOpen(false)}
                  className="btn-primary w-full mt-1"
                >
                  Iniciar sesión
                </Link>
              )}
            </div>
            <div className="absolute bottom-0 left-0 right-0 p-5 border-t border-border-100">
              <p className="text-xs text-muted-300">© {new Date().getFullYear()} RushTrip</p>
            </div>
          </div>
        </>
      )}
    </>
  );
}
