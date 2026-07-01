# backend/routes/plan.py
# API endpoint para generar planes de viaje optimizados por presupuesto
# Endpoint principal de RushTrip que combina todos los servicios

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from services.plan import generar_plan, resolver_iata, calcular_presupuesto_minimo
from services.hotels import _calcular_noches
from datetime import datetime
import re

# Router para endpoints de plan de viaje
# Prefix: /plan
# Tags: Plan de viaje (para documentación OpenAPI)
router = APIRouter(
    prefix="/plan",
    tags=["Plan de viaje"],
    responses={422: {"description": "Error de validación"}}
)


class PlanRequest(BaseModel):
    """
    Modelo de request para crear un plan de viaje.

    Attributes:
        origen: Código IATA del aeropuerto de origen (ej: BOG)
        destino: Código IATA del aeropuerto de destino (ej: MIA)
        fecha_salida: Fecha de salida en formato YYYY-MM-DD
        fecha_regreso: Fecha de regreso en formato YYYY-MM-DD
        presupuesto: Presupuesto total en USD
        pasajeros: Número de pasajeros (1-9)
        incluir_hotel: Si True, incluye búsqueda de hoteles
        incluir_vehiculo: Si True, incluye búsqueda de coches de alquiler
        tier: Nivel de calidad del viaje (economico/estandar/premium)
    """
    origen:        str   = Field(..., min_length=2, max_length=50, description="Ciudad o código IATA de origen (ej: Bogotá o BOG)")
    destino:       str   = Field(..., min_length=2, max_length=50, description="Ciudad o código IATA de destino (ej: Madrid o MAD)")
    fecha_salida:  str   = Field(..., description="Fecha de salida YYYY-MM-DD")
    fecha_regreso: str   = Field(..., description="Fecha de regreso YYYY-MM-DD")
    presupuesto:   float = Field(..., gt=0, description="Presupuesto total en USD")
    pasajeros:     int   = Field(1, ge=1, le=9, description="Número de pasajeros")
    incluir_hotel: bool  = Field(True, description="Incluir búsqueda de hoteles en el plan")
    incluir_vehiculo: bool = Field(False, description="Incluir búsqueda de coches de alquiler")
    tier:          str   = Field("estandar", description="Nivel de calidad: economico, estandar, premium")
    modo:          str   = Field("exacto", description="Modo de busqueda: exacto o flexible")
    duracion_dias: int   = Field(7, ge=1, le=14, description="Duracion en dias (modo flexible)")

    @field_validator("origen", "destino")
    @classmethod
    def ciudad_upper(cls, v: str) -> str:
        """Normaliza el texto de ciudad: mayúsculas y sin espacios extra."""
        return v.strip().upper()

    @field_validator("tier")
    @classmethod
    def validar_tier(cls, v: str) -> str:
        """Valida que el tier sea uno de los valores permitidos."""
        v = v.lower().strip()
        if v not in ("economico", "estandar", "premium"):
            raise ValueError("Tier invalido. Use: economico, estandar, premium")
        return v

    @field_validator("modo")
    @classmethod
    def validar_modo(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("exacto", "flexible"):
            raise ValueError("Modo invalido. Use: exacto, flexible")
        return v

    @field_validator("fecha_salida", "fecha_regreso")
    @classmethod
    def validar_fecha(cls, v: str) -> str:
        """Valida que las fechas tengan formato YYYY-MM-DD y sean válidas."""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD")
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Fecha inválida")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "origen":           "Bogotá",
                "destino":          "Madrid",
                "fecha_salida":     "2026-12-15",
                "fecha_regreso":    "2026-12-22",
                "presupuesto":      800,
                "pasajeros":        1,
                "incluir_hotel":    True,
                "incluir_vehiculo": False,
                "tier":             "estandar",
            }
        }
    }


@router.post(
    "/",
    summary="Generar plan de viaje por presupuesto",
    description="""
    Genera el plan de viaje más ajustado a tu presupuesto.

    El sistema busca vuelos, hoteles y coches disponibles y los combina
    para encontrar la combinación óptima dentro de tu presupuesto total.

    - **origen**: Código IATA de la ciudad de origen (ej: BOG)
    - **destino**: Código IATA de la ciudad de destino (ej: MIA)
    - **fecha_salida**: Fecha de salida en formato YYYY-MM-DD
    - **fecha_regreso**: Fecha de regreso en formato YYYY-MM-DD
    - **presupuesto**: Presupuesto total en USD
    - **pasajeros**: Número de pasajeros (default: 1)
    - **incluir_hotel**: Si se debe incluir hotel en el plan (default: true)
    - **incluir_vehiculo**: Si se debe incluir coche de alquiler (default: false)
    - **tier**: Calidad del viaje: economico, estandar o premium (default: estandar)

    Devuelve:
    - **plan_optimo**: La mejor combinación vuelo + hotel + coche dentro del presupuesto
    - **alternativas**: Hasta 2 opciones adicionales para comparar
    - **hoteles**: Lista de hoteles reales encontrados en el destino
    - **coches**: Opciones de alquiler de coches disponibles
    - **precision**: Qué tan exactos son los precios (exacta / mes / aproximada)
    - **aviso**: Mensaje informativo si no hay resultados exactos
    """,
    response_description="Plan de viaje optimizado para el presupuesto dado",
)
async def crear_plan(body: PlanRequest):
    """
    Endpoint principal de RushTrip: genera un plan de viaje por presupuesto.

    Soporta dos modos:
    - exacto: requiere fecha_salida y fecha_regreso exactas
    - flexible: busca los dias mas baratos dentro del mes de fecha_salida,
                usando duracion_dias para calcular el regreso

    Args:
        body: Objeto PlanRequest con origen, destino, fechas, presupuesto,
              pasajeros, incluir_hotel, incluir_vehiculo, tier y modo

    Returns:
        Dict con plan_optimo, alternativas, hoteles, coches, aviso y precision
    """
    # Modo flexible: solo requiere fecha_salida (mes) y duracion_dias
    if body.modo == "flexible":
        from datetime import timedelta
        salida = datetime.strptime(body.fecha_salida, "%Y-%m-%d")
        regreso = salida + timedelta(days=body.duracion_dias)
        fecha_salida = body.fecha_salida
        fecha_regreso = regreso.strftime("%Y-%m-%d")
    else:
        fecha_salida = body.fecha_salida
        fecha_regreso = body.fecha_regreso

        # Validar que las fechas sean coherentes
        salida  = datetime.strptime(body.fecha_salida,  "%Y-%m-%d")
        regreso = datetime.strptime(body.fecha_regreso, "%Y-%m-%d")

        if regreso <= salida:
            raise HTTPException(
                status_code=422,
                detail="La fecha de regreso debe ser posterior a la de salida."
            )

        if (regreso - salida).days > 30:
            raise HTTPException(
                status_code=422,
                detail="El rango entre salida y regreso no puede superar 30 dias."
            )

    # Validar que origen y destino sean diferentes
    if body.origen == body.destino:
        raise HTTPException(
            status_code=422,
            detail="El origen y el destino no pueden ser la misma ciudad."
        )

    # Resolver ciudad/aeropuerto a código IATA
    try:
        origen_iata = await resolver_iata(body.origen)
        destino_iata = await resolver_iata(body.destino)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Generar el plan de viaje usando el servicio
    resultado = await generar_plan(
        origen=           origen_iata,
        destino=          destino_iata,
        fecha_salida=     fecha_salida,
        fecha_regreso=    fecha_regreso,
        presupuesto=      body.presupuesto,
        pasajeros=        body.pasajeros,
        incluir_hotel=    body.incluir_hotel,
        incluir_vehiculo= body.incluir_vehiculo,
        tier=             body.tier,
        modo=             body.modo,
        duracion_dias=    body.duracion_dias,
    )

    return resultado


@router.get(
    "/min-budget/",
    summary="Calcular presupuesto mínimo sugerido",
    description="""
    Calcula un presupuesto mínimo sugerido usando precios de referencia.
    No hace llamadas a APIs externas — solo usa datos estáticos.

    Args:
        origen: Código IATA o ciudad de origen
        destino: Código IATA o ciudad de destino
        fecha_salida: Fecha de salida (YYYY-MM-DD)
        fecha_regreso: Fecha de regreso (YYYY-MM-DD)
        pasajeros: Número de pasajeros (default: 1)
        incluir_hotel: Incluir hotel (default: true)
        incluir_vehiculo: Incluir vehículo (default: false)
    """,
)
async def min_budget(
    origen: str,
    destino: str,
    fecha_salida: str,
    fecha_regreso: str,
    pasajeros: int = 1,
    incluir_hotel: bool = True,
    incluir_vehiculo: bool = False,
):
    try:
        origen_iata = await resolver_iata(origen)
        destino_iata = await resolver_iata(destino)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    noches = _calcular_noches(fecha_salida, fecha_regreso)

    resultado = calcular_presupuesto_minimo(
        origen=origen_iata,
        destino=destino_iata,
        noches=noches,
        pasajeros=pasajeros,
        incluir_hotel=incluir_hotel,
        incluir_vehiculo=incluir_vehiculo,
    )

    return resultado