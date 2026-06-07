# backend/routes/hotels.py
# API endpoint para búsqueda de hoteles
# Valida fechas y delega al servicio de hoteles

from fastapi import APIRouter, HTTPException
from services.hotels import buscar_hoteles
from datetime import datetime

# Router para endpoints de hoteles
# Prefix: /hotels
# Tags: Hoteles (para documentación OpenAPI)
router = APIRouter(
    prefix="/hotels",
    tags=["Hoteles"],
    responses={422: {"description": "Error de validación"}}
)


@router.get(
    "/",
    summary="Buscar hoteles",
    description="""
    Busca hoteles disponibles en una ciudad para las fechas especificadas.

    - **ciudad**: Nombre de la ciudad (ej: Miami, Bogotá, París)
    - **checkin**: Fecha de entrada en formato YYYY-MM-DD
    - **checkout**: Fecha de salida en formato YYYY-MM-DD
    - **adultos**: Número de adultos (opcional, default: 2)

    El endpoint primero busca el ID de la ciudad en Hotellook y luego consulta
    los hoteles disponibles con sus precios y enlaces de reserva.
    """,
    response_description="Lista de hoteles encontrados con precios y enlaces de reserva"
)
async def search_hotels(
    ciudad: str,
    checkin: str,
    checkout: str,
    adultos: int = 2,
    q: str = "",
):
    """
    Endpoint para buscar hoteles en una ciudad específica.

    Args:
        ciudad: Nombre de la ciudad a buscar
        checkin: Fecha de entrada (YYYY-MM-DD)
        checkout: Fecha de salida (YYYY-MM-DD)
        adultos: Número de adultos (default: 2)
        q: Filtro opcional por nombre de hotel (case-insensitive)

    Returns:
        Dict con 'aviso', 'ciudad' y 'hoteles' (lista)

    Raises:
        HTTPException 422: Si las fechas son inválidas o checkout <= checkin
    """
    # Validar formato y coherencia de fechas
    try:
        f1 = datetime.strptime(checkin, "%Y-%m-%d")
        f2 = datetime.strptime(checkout, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Formato de fecha incorrecto. Usa YYYY-MM-DD"
        )

    if f2 <= f1:
        raise HTTPException(
            status_code=422,
            detail="El checkout debe ser posterior al checkin"
        )

    # Delegar al servicio de hotels
    resultado = await buscar_hoteles(ciudad, checkin, checkout, adultos, q=q)
    return resultado