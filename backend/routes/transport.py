# backend/routes/transport.py
# API endpoint para búsqueda de transporte terrestre (bus y tren)
# Validaciones de medio y fechas antes de llamar al servicio

from fastapi import APIRouter, HTTPException
from services.transport import buscar_transporte, MEDIOS
from datetime import datetime
import re

# Router para endpoints de transporte terrestre
# Prefix: /transport
# Tags: Transporte terrestre (para documentación OpenAPI)
router = APIRouter(
    prefix="/transport",
    tags=["Transporte terrestre"],
    responses={422: {"description": "Error de validación"}}
)


@router.get(
    "/",
    summary="Buscar transporte terrestre",
    description="""
    Busca opciones de bus o tren entre dos ciudades en las fechas especificadas.

    - **medio**: Medio de transporte ('bus' o 'tren')
    - **origen**: Código IATA de la ciudad de origen (ej: MAD)
    - **destino**: Código IATA de la ciudad de destino (ej: BCN)
    - **fecha_salida**: Fecha de salida en formato YYYY-MM-DD
    - **fecha_regreso**: Fecha de regreso en formato YYYY-MM-DD
    - **pasajeros**: Número de pasajeros (opcional, default: 1)

    Los precios son estimados por distancia; si la ruta no es viable en el
    medio elegido (p. ej. transoceánica) se devuelven opciones vacías con aviso.
    """,
    response_description="Opciones de transporte encontradas o mensaje de aviso"
)
async def search_transport(
    medio: str,
    origen: str,
    destino: str,
    fecha_salida: str,
    fecha_regreso: str,
    pasajeros: int = 1,
):
    """
    Endpoint para buscar transporte terrestre entre dos ciudades.

    Returns:
        Dict con 'aviso', 'opciones' y 'precision'

    Raises:
        HTTPException 422: Si el medio o las fechas son inválidos
    """
    # Validar medio de transporte
    medio = medio.strip().lower()
    if medio not in MEDIOS:
        raise HTTPException(
            status_code=422,
            detail=f"Medio de transporte inválido. Opciones: {', '.join(MEDIOS)}"
        )

    # Validar formato de fecha (YYYY-MM-DD)
    patron = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(patron, fecha_salida) or not re.match(patron, fecha_regreso):
        raise HTTPException(
            status_code=422,
            detail="Las fechas deben tener formato YYYY-MM-DD. Ej: 2026-05-15"
        )

    # Validar que las fechas sean válidas y coherentes
    try:
        salida  = datetime.strptime(fecha_salida, "%Y-%m-%d")
        regreso = datetime.strptime(fecha_regreso, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Formato de fecha inválido. Use YYYY-MM-DD"
        )

    # Validar que la fecha de regreso sea posterior a la de salida
    if regreso <= salida:
        raise HTTPException(
            status_code=422,
            detail="La fecha de regreso debe ser posterior a la de salida."
        )

    # Validar que el rango no supere 30 días
    if (regreso - salida).days > 30:
        raise HTTPException(
            status_code=422,
            detail="El rango entre salida y regreso no puede superar 30 días."
        )

    # Delegar al servicio de transporte
    return await buscar_transporte(medio, origen, destino, fecha_salida, fecha_regreso, pasajeros)
