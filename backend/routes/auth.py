# backend/routes/auth.py
# Endpoints de autenticacion: registro, login, logout y usuario actual.
# Usa tokens opacos (Bearer) gestionados en services/auth.py.

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from services import auth as auth_service
from core.errors import ValidationError

router = APIRouter(
    prefix="/auth",
    tags=["Autenticacion"],
    responses={422: {"description": "Error de validacion"}},
)


class RegistroRequest(BaseModel):
    email:    str = Field(..., min_length=3, max_length=120, description="Correo electronico")
    password: str = Field(..., min_length=8, max_length=200, description="Contrasena (min. 8 caracteres)")
    nombre:   str = Field(..., min_length=2, max_length=80, description="Nombre completo")
    telefono: str = Field("", max_length=20, description="Numero de telefono (opcional)")
    pais:     str = Field(..., min_length=2, max_length=60, description="Pais de residencia")


class LoginRequest(BaseModel):
    email:    str = Field(..., min_length=3, max_length=120, description="Correo electronico")
    password: str = Field(..., min_length=1, max_length=200, description="Contrasena")


class ReservaRequest(BaseModel):
    """Reserva confirmada por el usuario a partir de un plan generado."""
    origen:             str   = Field(..., min_length=3, max_length=3, description="IATA origen")
    destino:            str   = Field(..., min_length=3, max_length=3, description="IATA destino")
    fecha_salida:       str   = Field(..., description="YYYY-MM-DD")
    fecha_regreso:      str   = Field(..., description="YYYY-MM-DD")
    total:              float = Field(..., ge=0, description="Costo total del plan")
    pasajeros:          int   = Field(1, ge=1, le=9)
    tier:               str   = Field("estandar")
    presupuesto:        Optional[float] = Field(None, ge=0)
    dentro_presupuesto: bool  = Field(True)
    incluir_hotel:      bool  = Field(True)
    incluir_vehiculo:   bool  = Field(False)
    precision:          Optional[str] = Field(None)
    ciudad_destino:     str   = Field("", max_length=80)
    detalle:            Optional[dict[str, Any]] = Field(None, description="Snapshot del plan (vuelo+hotel+coche)")


def _token_de_header(authorization: Optional[str]) -> Optional[str]:
    """Extrae el token del header 'Authorization: Bearer <token>'."""
    if not authorization:
        return None
    partes = authorization.split(" ", 1)
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1].strip()
    return None


async def usuario_actual(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """Dependencia: devuelve el usuario del token, o None si no hay sesion valida."""
    token = _token_de_header(authorization)
    return auth_service.usuario_de_token(token)


async def requerir_usuario(usuario: Optional[dict] = Depends(usuario_actual)) -> dict:
    """Dependencia: exige una sesion valida; lanza 401 si no la hay."""
    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Debes iniciar sesion para usar esta funcion.",
        )
    return usuario


@router.post("/register", summary="Registrar una cuenta nueva")
async def register(body: RegistroRequest):
    try:
        return auth_service.registrar(
            body.email, body.password, body.nombre, body.telefono, body.pais
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.message)


@router.post("/login", summary="Iniciar sesion")
async def login(body: LoginRequest):
    try:
        return auth_service.iniciar_sesion(body.email, body.password)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.message)


@router.post("/logout", summary="Cerrar sesion")
async def logout(authorization: Optional[str] = Header(default=None)):
    auth_service.cerrar_sesion(_token_de_header(authorization))
    return {"ok": True}


@router.get("/me", summary="Perfil del usuario autenticado")
async def me(usuario: dict = Depends(requerir_usuario)):
    """Perfil enriquecido: datos + estadisticas (reservas, fecha de registro) + destinos preferidos."""
    return {"usuario": auth_service.perfil(usuario["id"]) or usuario}


@router.post("/reservas", summary="Guardar una reserva confirmada", status_code=201)
async def crear_reserva(body: ReservaRequest, usuario: dict = Depends(requerir_usuario)):
    reserva_id = auth_service.registrar_reserva(usuario["id"], body.model_dump())
    return {"ok": True, "reserva_id": reserva_id}


@router.get("/reservas", summary="Historial de reservas del usuario")
async def listar_reservas(usuario: dict = Depends(requerir_usuario)):
    return {"reservas": auth_service.listar_reservas(usuario["id"])}
