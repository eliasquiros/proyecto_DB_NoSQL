from typing import Any
from bson import ObjectId
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from redis import Redis
from redis.exceptions import RedisError

from .db import col_promociones, redis_client

activar_bp = Blueprint("activar_bp", __name__)


class ErrorActivacionPromocion(Exception):
    """Excepción base para reglas de negocio al activar promociones."""
    categoria_alerta = "warning"


class DatosEntradaInvalidosError(ErrorActivacionPromocion):
    categoria_alerta = "danger"


class PromocionYaActivaError(ErrorActivacionPromocion):
    categoria_alerta = "warning"


class PromocionNoEncontradaError(ErrorActivacionPromocion):
    categoria_alerta = "danger"


class ServicioActivacionPromociones:
    PREFIJO_CLAVE = "promo:activa"
    SEGUNDOS_POR_MINUTO = 60

    def __init__(self, coleccion_promociones: Collection, cliente_redis: Redis) -> None:
        self._coleccion = coleccion_promociones
        self._redis = cliente_redis

    def obtener_catalogo(self) -> list[dict[str, Any]]:
        return list(self._coleccion.find().sort("id", 1))

    def activar(self, promocion_id_raw: str, cupones_raw: str, duracion_raw: str) -> str:
        promocion_id, cupones, duracion_min = self._validar_entrada(
            promocion_id_raw, cupones_raw, duracion_raw
        )
        clave_redis = self._construir_clave(promocion_id)

        if self._esta_activa(clave_redis):
            raise PromocionYaActivaError("La promoción seleccionada ya se encuentra activa.")

        promocion = self._buscar_en_catalogo(promocion_id)
        self._guardar_hash_con_ttl(clave_redis, promocion, cupones, duracion_min)
        return str(promocion.get("nombre", promocion_id))

    def _validar_entrada(
        self, promocion_id_raw: str, cupones_raw: str, duracion_raw: str
    ) -> tuple[str, int, int]:
        promocion_id = promocion_id_raw.strip()
        if not promocion_id:
            raise DatosEntradaInvalidosError("Debe seleccionar una promoción del catálogo.")

        cupones = self._parsear_entero_positivo(cupones_raw, "cantidad de cupones")
        duracion_min = self._parsear_entero_positivo(duracion_raw, "duración en minutos")
        return promocion_id, cupones, duracion_min

    @staticmethod
    def _parsear_entero_positivo(valor_raw: str, nombre_campo: str) -> int:
        try:
            valor = int(valor_raw.strip())
        except ValueError as err:
            raise DatosEntradaInvalidosError(
                f"El campo '{nombre_campo}' debe ser un número entero válido."
            ) from err

        if valor <= 0:
            raise DatosEntradaInvalidosError(
                f"El campo '{nombre_campo}' debe ser mayor que cero."
            )
        return valor

    def _construir_clave(self, promocion_id: str) -> str:
        return f"{self.PREFIJO_CLAVE}:{promocion_id}"

    def _esta_activa(self, clave_redis: str) -> bool:
        cupones_actuales = self._redis.hget(clave_redis, "cupones_disponibles")
        if cupones_actuales is None:
            return False
        try:
            return int(cupones_actuales) > 0
        except ValueError:
            return False

    def _buscar_en_catalogo(self, promocion_id: str) -> dict[str, Any]:
        documento = self._coleccion.find_one({"id": promocion_id})
        if not documento and promocion_id.isdigit():
            documento = self._coleccion.find_one({"id": int(promocion_id)})
        if not documento and ObjectId.is_valid(promocion_id):
            documento = self._coleccion.find_one({"_id": ObjectId(promocion_id)})
        if not documento:
            raise PromocionNoEncontradaError("La promoción no existe en el catálogo.")
        return documento

    def _guardar_hash_con_ttl(
        self, clave_redis: str, promocion: dict[str, Any], cupones: int, duracion_min: int
    ) -> None:
        ttl_segundos = duracion_min * self.SEGUNDOS_POR_MINUTO
        datos_hash = {
            "nombre": str(promocion.get("nombre", "Sin nombre")),
            "departamento": str(promocion.get("departamento", "Sin departamento")),
            "cupones_disponibles": cupones,
        }
        with self._redis.pipeline() as pipe:
            pipe.hset(clave_redis, mapping=datos_hash)
            pipe.expire(clave_redis, ttl_segundos)
            pipe.execute()


servicio_activacion = ServicioActivacionPromociones(col_promociones, redis_client)


@activar_bp.get("/activar")
def mostrar_formulario():
    try:
        promociones = servicio_activacion.obtener_catalogo()
    except PyMongoError:
        current_app.logger.exception("Fallo al consultar el catálogo de promociones en MongoDB.")
        promociones = []
        flash("No fue posible cargar el catálogo de promociones en este momento.", "danger")

    return render_template("activar/activar.html", promociones=promociones)


@activar_bp.post("/activar")
def procesar_activacion():
    promocion_id = request.form.get("promocion_id", "")
    cupones = request.form.get("cupones", "")
    duracion = request.form.get("duracion", "")

    try:
        nombre_promo = servicio_activacion.activar(promocion_id, cupones, duracion)
        flash(f"Promoción '{nombre_promo}' activada exitosamente.", "success")
    except ErrorActivacionPromocion as err:
        flash(str(err), err.categoria_alerta)
    except PyMongoError:
        current_app.logger.exception("Error de MongoDB al intentar activar promoción.")
        flash("No fue posible consultar el catálogo de promociones. Intentá nuevamente.", "danger")
    except RedisError:
        current_app.logger.exception("Error de Redis al intentar guardar promoción activa.")
        flash("No fue posible activar la promoción en este momento. Intentá nuevamente.", "danger")

    return redirect(url_for("activar_bp.mostrar_formulario"))
