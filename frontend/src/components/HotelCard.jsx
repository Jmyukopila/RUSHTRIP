import { useState, useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { getHotelDetail } from '../api/client';
import { IconCheck } from './icons';

function StarRating({ stars, large = false }) {
  const fullStars = Math.min(Math.floor(stars), 5);
  const hasHalf = stars % 1 >= 0.5;
  const emptyStars = Math.max(0, 5 - fullStars - (hasHalf ? 1 : 0));
  const size = large ? 'w-5 h-5' : 'w-3.5 h-3.5';

  return (
    <span className="inline-flex items-center gap-0.5">
      {[...Array(fullStars)].map((_, i) => (
        <svg key={`f${i}`} viewBox="0 0 16 16" className={`${size} text-yellow-500`} fill="currentColor">
          <path d="M8 0L9.796 5.528H15.608L10.906 8.944L12.702 14.472L8 11.056L3.298 14.472L5.094 8.944L0.392 5.528H6.204L8 0Z" />
        </svg>
      ))}
      {hasHalf && (
        <svg key="h" viewBox="0 0 16 16" className={`${size} text-yellow-500`} fill="none">
          <defs>
            <linearGradient id="halfGrad">
              <stop offset="50%" stopColor="currentColor" />
              <stop offset="50%" stopColor="transparent" />
            </linearGradient>
          </defs>
          <path d="M8 0L9.796 5.528H15.608L10.906 8.944L12.702 14.472L8 11.056L3.298 14.472L5.094 8.944L0.392 5.528H6.204L8 0Z" fill="url(#halfGrad)" stroke="currentColor" strokeWidth="0.5" />
        </svg>
      )}
      {[...Array(emptyStars)].map((_, i) => (
        <svg key={`e${i}`} viewBox="0 0 16 16" className={`${size} text-yellow-500/25`} fill="none" stroke="currentColor" strokeWidth="0.5">
          <path d="M8 0L9.796 5.528H15.608L10.906 8.944L12.702 14.472L8 11.056L3.298 14.472L5.094 8.944L0.392 5.528H6.204L8 0Z" />
        </svg>
      ))}
    </span>
  );
}

function Lightbox({ images, currentIndex, onClose }) {
  const [idx, setIdx] = useState(currentIndex);

  const goPrev = useCallback(() => setIdx((i) => (i - 1 + images.length) % images.length), [images.length]);
  const goNext = useCallback(() => setIdx((i) => (i + 1) % images.length), [images.length]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
    };
    document.addEventListener('keydown', handleKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [onClose, goPrev, goNext]);

  return createPortal(
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/90 animate-lightboxFade"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 text-white/80 hover:text-white hover:bg-white/20 flex items-center justify-center transition-all z-10"
        aria-label="Cerrar"
      >
        <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {images.length > 1 && (
        <>
          <button
            onClick={(e) => { e.stopPropagation(); goPrev(); }}
            className="absolute left-3 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 text-white/80 hover:text-white hover:bg-white/20 flex items-center justify-center transition-all z-10"
            aria-label="Anterior"
          >
            <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M15 18L9 12L15 6" />
            </svg>
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); goNext(); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 text-white/80 hover:text-white hover:bg-white/20 flex items-center justify-center transition-all z-10"
            aria-label="Siguiente"
          >
            <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M9 18L15 12L9 6" />
            </svg>
          </button>
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-black/50 text-white/80 text-sm px-4 py-1.5 rounded-full backdrop-blur-sm">
            {idx + 1} / {images.length}
          </div>
        </>
      )}

      <img
        key={idx}
        src={images[idx]}
        alt=""
        className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg animate-imageReveal"
        onClick={(e) => e.stopPropagation()}
      />
    </div>,
    document.body
  );
}

export default function HotelCard({ hotel, variant = 'default', checkin = '', checkout = '', adultos = 2 }) {
  if (!hotel) return null;

  const [imgIndex, setImgIndex] = useState(0);
  const [imgLoaded, setImgLoaded] = useState({});
  const [imgErrors, setImgErrors] = useState({});
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxStart, setLightboxStart] = useState(0);
  const [detalle, setDetalle] = useState(null);
  const [detalleLoading, setDetalleLoading] = useState(false);
  const [detalleAbierto, setDetalleAbierto] = useState(false);

  // Solo los hoteles reales de Hotels.nl tienen id para pedir galería + habitaciones
  const puedeDetalle = Boolean(hotel.id_hotelsnl && checkin && checkout);

  const cargarDetalle = useCallback(async () => {
    if (!puedeDetalle || detalle || detalleLoading) return detalle;
    setDetalleLoading(true);
    try {
      const data = await getHotelDetail({
        id: hotel.id_hotelsnl,
        checkin,
        checkout,
        adultos,
        ciudad: hotel.ciudad || '',
      });
      setDetalle(data);
      return data;
    } catch {
      setDetalle({ fotos_urls: [], habitaciones: [] });
    } finally {
      setDetalleLoading(false);
    }
  }, [puedeDetalle, detalle, detalleLoading, hotel.id_hotelsnl, hotel.ciudad, checkin, checkout, adultos]);

  // Galería: usa la del detalle (más fotos) cuando esté cargada; si no, la base.
  const fotosBase = hotel.fotos_urls?.length > 0 ? hotel.fotos_urls : (hotel.foto_url ? [hotel.foto_url] : []);
  const fotos = detalle?.fotos_urls?.length > 0 ? detalle.fotos_urls : fotosBase;
  const habitaciones = detalle?.habitaciones || [];
  const currentFoto = fotos[imgIndex] || '';

  const handleImgLoad = (url) => setImgLoaded((p) => ({ ...p, [url]: true }));
  const handleImgError = (url) => setImgErrors((p) => ({ ...p, [url]: true }));

  const openLightbox = (startIdx) => {
    setLightboxStart(startIdx);
    setLightboxOpen(true);
    cargarDetalle();  // enriquece la galería con más fotos del hotel (on-demand)
  };

  const toggleDetalle = () => {
    setDetalleAbierto((v) => !v);
    cargarDetalle();
  };

  const stars = hotel.estrellas || 0;
  const rating = hotel.rating || 0;
  const amenities = hotel.amenities?.filter(Boolean) || [];

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-3 card-base p-3">
        {currentFoto && !imgErrors[currentFoto] ? (
          <div className="w-16 h-12 rounded-lg overflow-hidden shrink-0 bg-accent/5">
            <img
              src={currentFoto}
              alt={hotel.nombre}
              className="w-full h-full object-cover"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          </div>
        ) : (
          <div className="w-16 h-12 rounded-lg bg-accent/10 shrink-0 flex items-center justify-center">
            <svg viewBox="0 0 20 20" className="w-5 h-5 text-accent/50" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M2 18 L18 18" /><path d="M4 18 L4 6 L10 2 L16 6 L16 18" /><path d="M8 18 L8 10 L12 10 L12 18" />
            </svg>
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text truncate">{hotel.nombre}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {stars > 0 && <StarRating stars={stars} />}
            {rating > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-success/15 text-success text-[10px] font-bold">{Number(rating).toFixed(1)}</span>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          {hotel.precio_noche > 0 && (
            <p className="font-mono text-accent font-semibold text-sm">${Number(hotel.precio_noche).toFixed(0)}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="card-base overflow-hidden">
      <div
        className="relative aspect-[3/2] bg-accent/5 cursor-pointer group overflow-hidden"
        onClick={() => openLightbox(imgIndex)}
      >
        {currentFoto && !imgErrors[currentFoto] ? (
          <>
            {!imgLoaded[currentFoto] && (
              <div className="absolute inset-0 image-placeholder" />
            )}
            <img
              key={currentFoto}
              src={currentFoto}
              alt={hotel.nombre}
              loading="lazy"
              onLoad={() => handleImgLoad(currentFoto)}
              onError={() => handleImgError(currentFoto)}
              className={`w-full h-full object-cover transition-all duration-500 group-hover:scale-105 ${
                imgLoaded[currentFoto] ? 'opacity-100' : 'opacity-0'
              }`}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-accent/10 text-accent">
            <svg viewBox="0 0 24 24" className="w-10 h-10" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 21 L21 21" /><path d="M5 21 L5 7 L12 3 L19 7 L19 21" /><path d="M9 21 L9 12 L15 12 L15 21" />
            </svg>
          </div>
        )}

        {fotos.length > 1 && (
          <div className="absolute bottom-2 right-2 bg-black/50 text-white text-[10px] px-2.5 py-1 rounded-full backdrop-blur-sm flex items-center gap-1">
            <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            {fotos.length}
          </div>
        )}

        {hotel.tipo === 'recomendado' && (
          <div className="absolute top-2 left-2 badge bg-success/80 text-white border-0 text-[10px] backdrop-blur-sm">
            Recomendado
          </div>
        )}
      </div>

      {fotos.length > 1 && (
        <div className="flex gap-1.5 px-3 pt-3 overflow-x-auto no-scrollbar">
          {fotos.map((url, i) => (
            <button
              key={`${url}-${i}`}
              onClick={() => setImgIndex(i)}
              className={`relative w-16 h-10 rounded-lg overflow-hidden shrink-0 ring-2 transition-all duration-200 ${
                i === imgIndex
                  ? 'ring-accent ring-offset-1'
                  : 'ring-transparent opacity-60 hover:opacity-100'
              }`}
            >
              <img
                src={url}
                alt=""
                loading="lazy"
                className="w-full h-full object-cover"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </button>
          ))}
        </div>
      )}

      <div className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-text text-sm sm:text-base leading-tight truncate">
                  {hotel.nombre}
                </h3>
                {hotel.tipo === 'estimado' && (
                  <span className="badge bg-accent/10 text-accent border border-accent/20 text-[10px] shrink-0">Cotización</span>
                )}
                {hotel.tipo === 'recomendado' && (
                  <span className="badge bg-success/15 text-success border border-success/20 text-[10px] shrink-0">Recomendado</span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                {stars > 0 && <StarRating stars={stars} />}
                {stars > 0 && <span className="text-xs text-muted-300">{stars} estrellas</span>}
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              {hotel.link_kkday && (
                <a
                  href={hotel.link_kkday}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-outline text-[10px] py-1 px-2 whitespace-nowrap"
                  title="Reservar en KKday"
                >
                  KKday
                </a>
              )}
              {hotel.link_klook && (
                <a
                  href={hotel.link_klook}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-outline text-[10px] py-1 px-2 whitespace-nowrap"
                  title="Reservar en Klook"
                >
                  Klook
                </a>
              )}
              {hotel.link_reserva && (
                <a
                  href={hotel.link_reserva}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary text-xs py-1.5 px-3 whitespace-nowrap"
                  title="Reservar este hotel"
                >
                  Reservar
                </a>
              )}
            </div>
          </div>

        {rating > 0 && (
          <div className="flex items-center gap-2 mt-2">
            <span className="px-2 py-0.5 rounded-md bg-success/15 text-success text-xs font-bold">
              {Number(rating).toFixed(1)}
            </span>
            <div className="text-xs text-muted-300">
              <span className="font-medium text-text">{hotel.reviewScoreWord || ''}</span>
              {hotel.reviewCount ? ` · ${Number(hotel.reviewCount).toLocaleString('es')} opiniones` : ''}
            </div>
          </div>
        )}

        {amenities.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {amenities.slice(0, 4).map((a, i) => (
              <span key={i} className="px-2 py-0.5 bg-accent2/8 text-accent2-600 text-[10px] font-medium rounded-md border border-accent2/15">
                {a}
              </span>
            ))}
            {amenities.length > 4 && (
              <span className="px-2 py-0.5 text-muted-300 text-[10px]">+{amenities.length - 4}</span>
            )}
          </div>
        )}

        <div className="flex items-baseline gap-2 mt-3 pt-3 border-t border-border-50">
          {hotel.precio_noche > 0 && (
            <span className="font-mono text-accent font-bold text-lg">
              ${Number(hotel.precio_noche).toFixed(0)}
              <span className="text-xs text-muted-300 font-normal">/noche</span>
            </span>
          )}
          {hotel.precio_total > 0 && (
            <span className="text-xs text-muted-300">
              · ${Number(hotel.precio_total).toFixed(0)} total
              {hotel.noches ? ` · ${hotel.noches} noche${hotel.noches > 1 ? 's' : ''}` : ''}
            </span>
          )}
        </div>

        {hotel.adultos > 0 && (
          <p className="text-xs text-muted-300 mt-1">
            {hotel.adultos} adulto{hotel.adultos > 1 ? 's' : ''}
          </p>
        )}

        {hotel.por_que && (
          <p className="text-xs text-muted-300 mt-2 italic leading-relaxed">{hotel.por_que}</p>
        )}

        {puedeDetalle && (
          <div className="mt-3 pt-3 border-t border-border-50">
            <button
              onClick={toggleDetalle}
              className="text-xs font-medium text-accent hover:underline flex items-center gap-1"
            >
              {detalleLoading
                ? 'Cargando…'
                : detalleAbierto
                ? 'Ocultar habitaciones'
                : 'Ver habitaciones y más fotos'}
              {!detalleLoading && (
                <svg viewBox="0 0 24 24" className={`w-3.5 h-3.5 transition-transform ${detalleAbierto ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M6 9l6 6 6-6" />
                </svg>
              )}
            </button>

            {detalleAbierto && !detalleLoading && (
              <div className="mt-3 space-y-2 animate-fadeIn">
                {habitaciones.length > 0 ? (
                  habitaciones.map((hab, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-bg/60 border border-border-50 hover:border-accent/30 hover:bg-bg transition-colors duration-200"
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-text truncate">{hab.nombre}</p>
                        <p className="text-[10px] mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                          {hab.cama && <span className="text-muted-300">{hab.cama}</span>}
                          <span className={`flex items-center gap-1 ${hab.reembolsable ? 'text-success font-medium' : 'text-muted-300'}`}>
                            {hab.reembolsable && <IconCheck className="w-2.5 h-2.5" />}
                            {hab.reembolsable ? 'Cancelación gratis' : 'No reembolsable'}
                          </span>
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {hab.precio_total > 0 && (
                          <div className="text-right leading-none">
                            <span className="font-mono text-accent font-semibold text-sm">
                              ${Number(hab.precio_total).toFixed(0)}
                            </span>
                            <span className="block text-[9px] text-muted-300 mt-0.5">total</span>
                          </div>
                        )}
                        {hab.link_reserva && (
                          <a
                            href={hab.link_reserva}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-primary text-[10px] py-1 px-2.5 whitespace-nowrap"
                          >
                            Reservar
                          </a>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-300">No hay habitaciones disponibles para estas fechas.</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {lightboxOpen && fotos.length > 0 && (
        <Lightbox
          images={fotos}
          currentIndex={lightboxStart}
          onClose={() => setLightboxOpen(false)}
        />
      )}
    </div>
  );
}
