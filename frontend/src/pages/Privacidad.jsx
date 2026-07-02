import LegalLayout, { LegalSection, LegalLink } from '../components/LegalLayout';

export default function Privacidad() {
  return (
    <LegalLayout titulo="Política de Privacidad" actualizado="2026-07-02">
      <LegalSection titulo="1. Qué datos recopilamos">
        <p>Solo pedimos lo necesario para que el servicio funcione:</p>
        <ul className="list-disc pl-5 flex flex-col gap-1.5">
          <li>
            <strong className="text-text">Datos de cuenta:</strong> correo electrónico, nombre,
            país y, si decides darlo, teléfono. Tu contraseña se guarda únicamente como hash
            criptográfico — nunca en texto plano y nadie del equipo puede leerla.
          </li>
          <li>
            <strong className="text-text">Tu actividad en RushTrip:</strong> los planes que guardas
            y los destinos que buscas con sesión iniciada, para mostrarte tu historial y
            preferencias.
          </li>
          <li>
            <strong className="text-text">Datos técnicos:</strong> tu dirección IP, usada solo para
            aplicar límites diarios de uso y proteger el servicio.
          </li>
        </ul>
      </LegalSection>

      <LegalSection titulo="2. Para qué los usamos">
        <p>
          Para mantener tu sesión iniciada, guardar tus planes, personalizar tus búsquedas y
          proteger la plataforma contra abusos. <strong className="text-text">No vendemos ni
          alquilamos tus datos a terceros</strong>, y no te enviaremos correos comerciales que no
          hayas pedido.
        </p>
      </LegalSection>

      <LegalSection titulo="3. Dónde se almacenan">
        <p>
          Las cuentas, sesiones y planes guardados se almacenan en nuestra base de datos
          (infraestructura de Supabase/PostgreSQL o equivalente). Aplicamos medidas razonables de
          seguridad, como el hashing de contraseñas y conexiones cifradas.
        </p>
      </LegalSection>

      <LegalSection titulo="4. Servicios de terceros">
        <p>
          Para armar tu plan consultamos proveedores externos de precios, fotos, clima y
          actividades (entre otros: Travelpayouts/Aviasales, Hotels.nl, Pexels, Open-Meteo,
          OpenTripMap). Estas consultas no incluyen tus datos de cuenta.
        </p>
        <p>
          Al pulsar «Reservar» sales de RushTrip hacia el sitio del proveedor, que tiene su propia
          política de privacidad. Algunos de esos enlaces son de afiliado: podemos recibir una
          comisión por tu compra, sin costo adicional para ti (ver{' '}
          <LegalLink to="/terminos">Términos de Servicio</LegalLink>).
        </p>
      </LegalSection>

      <LegalSection titulo="5. Cookies y almacenamiento local">
        <p>
          RushTrip guarda tu token de sesión en el almacenamiento local de tu navegador para
          mantenerte con la sesión iniciada. No usamos cookies de publicidad ni rastreadores de
          terceros propios; los sitios de los proveedores a los que llegues pueden usar los suyos.
        </p>
      </LegalSection>

      <LegalSection titulo="6. Tus derechos">
        <p>
          Puedes pedirnos en cualquier momento acceder a tus datos, corregirlos o eliminar tu
          cuenta por completo (incluyendo tus planes guardados y destinos preferidos). Escríbenos a{' '}
          <a href="mailto:rushtripsupport@gmail.com" className="text-accent hover:underline">
            rushtripsupport@gmail.com
          </a>{' '}
          desde el correo de tu cuenta y lo gestionamos.
        </p>
      </LegalSection>

      <LegalSection titulo="7. Cambios a esta política">
        <p>
          Si cambiamos esta política, publicaremos aquí la versión vigente con su fecha de
          actualización. Si el cambio afecta de forma sustancial cómo tratamos tus datos, te lo
          avisaremos al iniciar sesión.
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
