import LegalLayout, { LegalSection, LegalLink } from '../components/LegalLayout';

export default function Terminos() {
  return (
    <LegalLayout titulo="Términos de Servicio" actualizado="2026-07-02">
      <LegalSection titulo="1. Qué es RushTrip">
        <p>
          RushTrip es un planificador de viajes: a partir de tu presupuesto, fechas y destino,
          buscamos y comparamos vuelos, hoteles y coches de alquiler de proveedores externos, y te
          proponemos la combinación que mejor se ajusta. RushTrip <strong className="text-text">no vende,
          opera ni intermedia</strong> vuelos, alojamientos ni vehículos: somos un comparador.
        </p>
      </LegalSection>

      <LegalSection titulo="2. Reservas y compras">
        <p>
          Toda compra o reserva real se realiza <strong className="text-text">en el sitio del proveedor
          correspondiente</strong> (por ejemplo Aviasales, Booking.com, Hotels.nl, Localrent o
          EconomyBookings), bajo sus propios términos y condiciones. Cuando guardas un plan en tu
          cuenta de RushTrip, eso crea únicamente un registro personal del plan — no es una compra,
          no bloquea tarifas y no garantiza precio ni disponibilidad.
        </p>
        <p>
          Ante cualquier incidencia con un vuelo, hotel o coche (cambios, cancelaciones,
          reembolsos), el responsable es el proveedor con el que completaste la compra.
        </p>
      </LegalSection>

      <LegalSection titulo="3. Precios y precisión de los datos">
        <p>
          Los precios que mostramos provienen de proveedores externos o de estimaciones propias, y
          señalamos su calidad con una etiqueta de precisión (por ejemplo «exacta», «aproximada» o
          «estimada»). Los precios cambian constantemente: el importe final siempre es el que veas
          en el sitio del proveedor al completar la compra. No garantizamos la exactitud,
          integridad o vigencia de los datos mostrados.
        </p>
      </LegalSection>

      <LegalSection titulo="4. Enlaces de afiliado">
        <p>
          Algunos enlaces hacia proveedores son enlaces de afiliado (a través de la red
          Travelpayouts, entre otras). Si completas una compra a través de ellos, RushTrip puede
          recibir una comisión <strong className="text-text">sin ningún costo adicional para ti</strong>.
          Esto es lo que nos permite ofrecer el servicio gratis; no altera los precios ni el orden
          de los resultados que te mostramos.
        </p>
      </LegalSection>

      <LegalSection titulo="5. Tu cuenta">
        <p>
          Eres responsable de mantener la confidencialidad de tu contraseña y de la actividad que
          ocurra en tu cuenta. Aplicamos límites de uso razonables para proteger el servicio;
          podemos suspender cuentas que abusen del sistema (automatización masiva, intentos de
          acceso no autorizado o uso fraudulento). Puedes pedir la eliminación de tu cuenta en
          cualquier momento (ver la <LegalLink to="/privacidad">Política de Privacidad</LegalLink>).
        </p>
      </LegalSection>

      <LegalSection titulo="6. Limitación de responsabilidad">
        <p>
          RushTrip se ofrece «tal cual», sin garantías de ningún tipo. En la medida permitida por
          la ley, no somos responsables de pérdidas o daños derivados del uso del servicio, de
          decisiones tomadas con base en los datos mostrados, ni de incumplimientos de los
          proveedores externos con los que contrates.
        </p>
      </LegalSection>

      <LegalSection titulo="7. Cambios a estos términos">
        <p>
          Podemos actualizar estos términos cuando el servicio evolucione. Publicaremos la versión
          vigente en esta página con su fecha de actualización; el uso continuado del servicio
          implica la aceptación de la versión publicada.
        </p>
      </LegalSection>

      <LegalSection titulo="8. Contacto">
        <p>
          Para cualquier consulta sobre estos términos, escríbenos a{' '}
          <a href="mailto:rushtripsupport@gmail.com" className="text-accent hover:underline">
            rushtripsupport@gmail.com
          </a>.
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
