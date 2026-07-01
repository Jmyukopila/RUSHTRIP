# tests/test_rate_limiter.py
# Tests del rate limiter por IP (SQLite). Usa el temp_dbs autouse de conftest.

from core import rate_limiter as rl


def test_endpoint_group():
    assert rl._endpoint_group("/hotels/detalle") == "hotels"
    assert rl._endpoint_group("/hotels/") == "hotels"
    assert rl._endpoint_group("/plan/") == "plan"
    assert rl._endpoint_group("/desconocido") == "default"


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
