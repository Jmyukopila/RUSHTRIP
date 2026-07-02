# tests/test_rate_limiter.py
# Tests del rate limiter por IP (SQLite). Usa el temp_dbs autouse de conftest.

from core import rate_limiter as rl


def test_endpoint_group():
    assert rl._endpoint_group("/hotels/detalle") == "hotels"
    assert rl._endpoint_group("/hotels/") == "hotels"
    assert rl._endpoint_group("/plan/") == "plan"
    assert rl._endpoint_group("/desconocido") == "default"


def test_endpoint_group_con_prefijo_api():
    # En producción el middleware ve el path ANTES del strip de /api
    assert rl._endpoint_group("/api/plan/") == "plan"
    assert rl._endpoint_group("/api/hotels/detalle") == "hotels"
    assert rl._endpoint_group("/api/airports/") == "airports"


def test_normalizar_path():
    assert rl.normalizar_path("/api/plan/") == "/plan/"
    assert rl.normalizar_path("/plan/") == "/plan/"
    assert rl.normalizar_path("/api") == "/"
    assert rl.normalizar_path("/") == "/"


def test_es_ruta_api():
    assert rl.es_ruta_api("/api/plan/") is True
    assert rl.es_ruta_api("/plan/") is True
    assert rl.es_ruta_api("/flights/") is True
    # Estáticos y utilitarios no consumen cupo
    assert rl.es_ruta_api("/") is False
    assert rl.es_ruta_api("/health") is False
    assert rl.es_ruta_api("/docs") is False
    assert rl.es_ruta_api("/assets/logo.png") is False


def test_ip_cliente():
    # Detrás de proxy: primer salto de X-Forwarded-For
    assert rl.ip_cliente("1.2.3.4, 10.0.0.1", "9.9.9.9") == "1.2.3.4"
    assert rl.ip_cliente("1.2.3.4", "9.9.9.9") == "1.2.3.4"
    # Sin header: IP de la conexión directa
    assert rl.ip_cliente(None, "9.9.9.9") == "9.9.9.9"
    assert rl.ip_cliente("", "9.9.9.9") == "9.9.9.9"


def test_segundos_hasta_reinicio():
    s = rl.segundos_hasta_reinicio()
    assert 60 <= s <= 86400


def test_rate_limit_incrementa():
    allowed, _ = rl.check_rate_limit("1.2.3.4", "/hotels/")
    assert allowed is True
    remaining, limit = rl.get_remaining("1.2.3.4", "/hotels/")
    assert limit == rl.LIMITS["hotels"]
    assert remaining == limit - 1


def test_rate_limit_bloquea(monkeypatch):
    monkeypatch.setitem(rl.LIMITS, "hotels", 2)
    ip = "9.9.9.9"
    assert rl.check_rate_limit(ip, "/hotels/")[0] is True   # 1ª
    assert rl.check_rate_limit(ip, "/hotels/")[0] is True   # 2ª
    allowed, limit = rl.check_rate_limit(ip, "/hotels/")     # 3ª → bloqueada
    assert allowed is False
    assert limit == 2


def test_rate_limit_independiente_por_ip(monkeypatch):
    monkeypatch.setitem(rl.LIMITS, "hotels", 1)
    assert rl.check_rate_limit("a", "/hotels/")[0] is True
    assert rl.check_rate_limit("a", "/hotels/")[0] is False  # 'a' agotó su límite
    assert rl.check_rate_limit("b", "/hotels/")[0] is True   # 'b' tiene el suyo
