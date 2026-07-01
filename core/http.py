# core/http.py
# Cliente HTTP compartido con retry y backoff exponencial
# Reutiliza conexiones y maneja fallos transitorios de APIs externas

import asyncio
import httpx
from core.config import settings
from core.errors import ExternalAPIError

_DEFAULT_TIMEOUT = 10.0
_MAX_RETRIES = 3
_BASE_DELAY = 0.5  # segundos iniciales de backoff


http_client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)


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

    for attempt in range(max_retries + 1):
        try:
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
