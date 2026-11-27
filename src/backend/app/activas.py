from dataclasses import dataclass
from typing import Any
from flask import Blueprint, current_app, flash, render_template
from redis import Redis
from redis.exceptions import RedisError

from .db import redis_client

activas_bp = Blueprint("activas_bp", __name__)


@dataclass(frozen=True)
class PromocionActiva:
    nombre: str
    departamento: str
    cupones_disponibles: int
    segundos_restantes: int

    @property
    def tiempo_restante_texto(self) -> str:
        minutos, segundos = divmod(self.segundos_restantes, 60)
        if minutos > 0:
            return f"{minutos} min {segundos} s"
        return f"{segundos} s"


class ServicioPromocionesActivas:
    PATRON_CLAVES = "promo:activa:*"

    def __init__(self, cliente_redis: Redis) -> None:
        self._redis = cliente_redis

    def listar_vigentes(self) -> list[PromocionActiva]:
        claves = self._obtener_claves()
        if not claves:
            return []

        respuestas = self._leer_lote(claves)
        vigentes: list[PromocionActiva] = []

        # Cada clave encoló 2 comandos en el pipeline: [hgetall, ttl]
        for i in range(0, len(respuestas), 2):
            promocion = self._construir_si_vigente(respuestas[i], respuestas[i + 1])
            if promocion is not None:
                vigentes.append(promocion)

        vigentes.sort(key=lambda promo: promo.segundos_restantes)
        return vigentes

    def _obtener_claves(self) -> list[str]:
        return list(self._redis.scan_iter(match=self.PATRON_CLAVES))

    def _leer_lote(self, claves: list[str]) -> list[Any]:
        with self._redis.pipeline(transaction=False) as pipe:
            for clave in claves:
                pipe.hgetall(clave)
                pipe.ttl(clave)
            return pipe.execute()

    @staticmethod
    def _construir_si_vigente(datos_hash: dict[str, str], ttl: int) -> PromocionActiva | None:
        if not datos_hash or ttl <= 0:
            return None

        try:
            cupones = int(datos_hash.get("cupones_disponibles", "0"))
        except ValueError:
            return None

        if cupones <= 0:
            return None

        return PromocionActiva(
            nombre=datos_hash.get("nombre", "Sin nombre"),
            departamento=datos_hash.get("departamento", "Sin departamento"),
            cupones_disponibles=cupones,
            segundos_restantes=ttl,
        )


servicio_activas = ServicioPromocionesActivas(redis_client)


@activas_bp.get("/activas")
def listar_promociones_activas():
    try:
        promociones = servicio_activas.listar_vigentes()
    except RedisError:
        current_app.logger.exception("Error de Redis al consultar promociones activas.")
        promociones = []
        flash("No fue posible consultar las promociones activas en este momento.", "danger")

    return render_template("activas/activas.html", promociones=promociones)
