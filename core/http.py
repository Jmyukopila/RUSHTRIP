# core/http.py
# Cliente HTTP compartido con retry y backoff exponencial
# Reutiliza conexiones y maneja fallos transitorios de APIs externas

import asyncio
import time
import httpx
from core.config import settings
from core.errors import ExternalAPIError

_DEFAULT_TIMEOUT = 10.0
_MAX_RETRIES = 3
_BASE_DELAY = 0.5  # segundos iniciales de backoff


http_client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)


# Límites de salida por proveedor: (llamadas concurrentes máx, intervalo mínimo en s).
# Evita que ráfagas propias (plan con aeropuertos alternativos, modo flexible, etc.)
# agoten el rate limit del proveedor y provoquen 429 en cadena.
_THROTTLE_CONFIG: dict[str, tuple[int, float]] = {
    "travelpayouts": (4, 0.25),
    "rapidapi":      (2, 1.0),
    "hotelsnl":      (2, 12.0),  # free tier: 5 req/min
    "opentripmap":   (4, 0.25),
    "pexels":        (2, 2.0),
}
_THROTTLE_DEFAULT = (8, 0.0)


class _ProviderThrottle:
    """Limita concurrencia e intervalo mínimo entre llamadas a un proveedor."""

    def __init__(self, max_concurrentes: int, intervalo_min: float):
        self._sem = asyncio.Semaphore(max_concurrentes)
        self._intervalo = intervalo_min
        self._ultima = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._sem.acquire()
        if self._intervalo > 0:
            async with self._lock:
                espera = self._ultima + self._intervalo - time.monotonic()
                if espera > 0:
                    await asyncio.sleep(espera)
                self._ultima = time.monotonic()
        return self

    async def __aexit__(self, *exc):
        self._sem.release()


# Un throttle por (proveedor, event loop): los primitivos de asyncio quedan
# ligados al loop donde se usan por primera vez (los tests crean loops nuevos).
_throttles: dict[tuple[str, int], _ProviderThrottle] = {}


def _get_throttle(provider: str) -> _ProviderThrottle:
    loop_id = id(asyncio.get_running_loop())
    key = (provider, loop_id)
    throttle = _throttles.get(key)
    if throttle is None:
        throttle = _ProviderThrottle(*_THROTTLE_CONFIG.get(provider, _THROTTLE_DEFAULT))
        _throttles[key] = throttle
    return throttle


async def request_with_retry(
    method: str,
    url: str,
    *,
    provider: str = "external_api",
    max_retries: int = _MAX_RETRIES,
    base_delay: float = _BASE_DELAY,
    **kwargs,
) -> httpx.Response:
    """
    Realiza una peticion HTTP con retry y backoff exponencial + jitter.

    Reintenta automaticamente en errores transitorios:
    - Timeouts
    - Errores de conexion
    - Errores 5xx del servidor
    - Errores 429 (rate limit)

    Args:
        method: Metodo HTTP (GET, POST, etc.)
        url: URL de la peticion
        provider: Nombre del proveedor externo para logging/errores
        max_retries: Numero maximo de reintentos (default: 3)
        base_delay: Delay inicial en segundos para backoff (default: 0.5)
        **kwargs: Argumentos adicionales para httpx.AsyncClient.request()

    Returns:
        httpx.Response en caso de exito

    Raises:
        ExternalAPIError: Si todos los reintentos fallan
    """
    last_error = None
    throttle = _get_throttle(provider)

    for attempt in range(max_retries + 1):
        try:
            async with throttle:
                response = await http_client.request(method, url, **kwargs)

            if response.status_code < 500 and response.status_code != 429:
                return response

            if response.status_code == 429:
                last_error = ExternalAPIError(
                    f"Rate limit excedido en {provider}",
                    provider=provider,
                    status_code=429,
                )
                if attempt < max_retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

            elif response.status_code >= 500:
                last_error = ExternalAPIError(
                    f"Error de servidor en {provider} (HTTP {response.status_code})",
                    provider=provider,
                    status_code=response.status_code,
                )

        except httpx.TimeoutException:
            last_error = ExternalAPIError(
                f"Timeout al conectar con {provider}",
                provider=provider,
            )
        except httpx.ConnectError as e:
            last_error = ExternalAPIError(
                f"Error de conexion con {provider}: {e}",
                provider=provider,
            )
        except httpx.RequestError as e:
            last_error = ExternalAPIError(
                f"Error de red al llamar a {provider}: {e}",
                provider=provider,
            )

        if attempt < max_retries:
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

    raise last_error
