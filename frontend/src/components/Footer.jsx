import { Link } from 'react-router-dom';
import { IconSparkle, LogoMark } from './icons';

export default function Footer() {
  return (
    <>
      <div
        className="h-20 w-full"
        style={{
          background: 'linear-gradient(to bottom, var(--bg) 0%, #1A1208 100%)',
        }}
      />
      <footer className="bg-[#1A1208]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-14 sm:py-20">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-10 lg:gap-12">
            <div className="sm:col-span-2 lg:col-span-1">
              <Link to="/" className="inline-flex items-center gap-2.5 group">
                <LogoMark className="w-6 h-6" />
                <span className="font-display text-xl tracking-tight text-[#FAF7F2]">
                  Rush<span className="text-[#E8611A]">Trip</span>
                </span>
              </Link>
              <p className="mt-4 text-sm text-[#8C7B6B] leading-relaxed max-w-xs">
                Dinos tu presupuesto. Nosotros armamos el plan de viaje perfecto para ti — vuelo, hotel y todo lo que necesitas.
              </p>
            </div>

            <div>
              <h4 className="font-display text-xs uppercase tracking-widest text-[#C4A882] mb-5">
                Navegar
              </h4>
              <div className="flex flex-col gap-3">
                <Link to="/" className="text-sm text-[#8C7B6B] hover:text-[#FAF7F2] transition-colors duration-200">
                  Inicio
                </Link>
                <Link to="/plan" className="text-sm text-[#8C7B6B] hover:text-[#FAF7F2] transition-colors duration-200">
                  Buscar plan
                </Link>
              </div>
            </div>

            <div>
              <h4 className="font-display text-xs uppercase tracking-widest text-[#C4A882] mb-5">
                Legal
              </h4>
              <div className="flex flex-col gap-3">
                <Link to="/terminos" className="text-sm text-[#8C7B6B] hover:text-[#FAF7F2] transition-colors duration-200">
                  Términos de Servicio
                </Link>
                <Link to="/privacidad" className="text-sm text-[#8C7B6B] hover:text-[#FAF7F2] transition-colors duration-200">
                  Política de Privacidad
                </Link>
              </div>
            </div>

            <div>
              <h4 className="font-display text-xs uppercase tracking-widest text-[#C4A882] mb-5">
                Contacto
              </h4>
              <div className="flex flex-col gap-3">
                <a href="mailto:rushtripsupport@gmail.com" className="text-sm text-[#8C7B6B] hover:text-[#FAF7F2] transition-colors duration-200">
                  rushtripsupport@gmail.com
                </a>
              </div>
            </div>

            <div>
              <h4 className="font-display text-xs uppercase tracking-widest text-[#C4A882] mb-5">
                Síguenos
              </h4>
              <div className="flex gap-3">
                {['Instagram', 'Twitter', 'TikTok'].map((social) => (
                  <a
                    key={social}
                    href="#"
                    className="w-9 h-9 rounded-lg border border-white/10 flex items-center justify-center text-[#8C7B6B] hover:text-[#FAF7F2] hover:border-white/20 transition-all duration-200"
                    aria-label={social}
                  >
                    <svg viewBox="0 0 20 20" className="w-4 h-4" fill="currentColor">
                      <circle cx="10" cy="10" r="8" opacity="0.3" />
                      <circle cx="10" cy="10" r="3" />
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-14 pt-8 border-t border-white/[0.06]">
            <p className="text-xs text-[#6B5D4D] leading-relaxed max-w-3xl">
              RushTrip es un comparador: las reservas se completan en los sitios de los
              proveedores. Algunos enlaces son de afiliado (Travelpayouts y otros) y podemos
              recibir una comisión por tu compra, sin costo adicional para ti.
            </p>
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-xs text-[#6B5D4D]">
                &copy; {new Date().getFullYear()} RushTrip. Todos los derechos reservados.
              </p>
              <div className="flex items-center gap-2 text-xs text-[#6B5D4D]">
                <span>Hecho con</span>
                <IconSparkle className="w-3 h-3 text-[#E8611A]" />
                <span>para viajeros</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
