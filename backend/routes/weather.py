# backend/routes/weather.py
# API endpoint para el clima del destino
# Valida fechas y delega al servicio de clima (Open-Meteo)

from fastapi import APIRouter, HTTPException
from services.weather import obtener_clima
from datetime import datetime

# Router para endpoints de clima
# Prefix: /weather
# Tags: Clima (para documentación OpenAPI)
router = APIRouter(
    prefix="/weather",
    tags=["Clima"],
    responses={422: {"description": "Error de validación"}}
)


@router.get(
    "/",
    summary="Clima del destino",
    description="""
    Devuelve el clima día a día de una ciudad para un rango de fechas.

    - **ciudad**: Nombre de la ciudad (ej: Madrid, Bogotá, Miami)
    - **fecha_inicio**: Primer día en formato YYYY-MM-DD
    - **fecha_fin**: Último día en formato YYYY-MM-DD

    Si las fechas están dentro del horizonte de pronóstico (~16 días),
    devuelve pronóstico real (precision 'pronostico'). Para fechas más
    lejanas devuelve el clima típico de esos días calculado con datos
    históricos reales de años anteriores (precision 'tipico').
    No requiere API key (Open-Meteo).
    """,
    response_description="Clima día a día con temperaturas, probabilidad de lluvia y precision"
)
async def get_weather(
    ciudad: str,
    fecha_inicio: str,
    fecha_fin: str,
):
    """
    Endpoint para consultar el clima de un destino.

    Args:
        ciudad: Nombre de la ciudad
        fecha_inicio: Primer día (YYYY-MM-DD)
        fecha_fin: Último día (YYYY-MM-DD)

    Returns:
        Dict con 'ciudad', 'dias' (lista), 'precision' y 'aviso'

    Raises:
        HTTPException 422: Si las fechas son inválidas, fin < inicio o el rango supera 31 días
    """
    # Validar formato y coherencia de fechas
    try:
        f1 = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        f2 = datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Formato de fecha incorrecto. Usa YYYY-MM-DD"
        )

    if f2 < f1:
        raise HTTPException(
            status_code=422,
            detail="La fecha de fin debe ser igual o posterior a la de inicio"
        )

    if (f2 - f1).days > 31:
        raise HTTPException(
            status_code=422,
            detail="El rango máximo es de 31 días"
        )

    # Delegar al servicio de clima (degrada a aviso si no hay datos)
    resultado = await obtener_clima(ciudad, fecha_inicio, fecha_fin)
    if resultado is None:
        return {
            "aviso": "No pudimos obtener el clima para este destino en este momento.",
            "ciudad": ciudad,
            "dias": [],
            "precision": "sin_datos",
        }
    return resultado
