import httpx, json

r = httpx.get("http://localhost:8000/api/hotels/",
    params={"ciudad": "Bogota", "checkin": "2026-06-15", "checkout": "2026-06-20"})
d = r.json()
print("Precision:", d.get("precision", "N/A"))
print("Hoteles:", len(d.get("hoteles", [])))
print("Aviso:", d.get("aviso", ""))
h = d["hoteles"][0]
print("Nombre:", h["nombre"])
print("Tipo:", h["tipo"])
print("Link:", h["link_reserva"][:80])
print("Foto:", h["foto_url"][:80])
print("Amenities:", h["amenities"])
