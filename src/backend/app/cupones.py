
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pymongo.errors import PyMongoError

from .db import redis_client, col_cupones


cupones_bp = Blueprint("cupones", __name__)

PREFIJO_PROMOCION = "promo:activa"


def listar_promociones_activas():
    promociones_activas = []

    claves = redis_client.scan_iter(
        match=f"{PREFIJO_PROMOCION}:*"
    )

    for clave in claves:
        datos = redis_client.hgetall(clave)
        tiempo_restante = redis_client.ttl(clave)

        disponibles = int(datos.get("cupones_disponibles", 0))

        if datos and tiempo_restante > 0 and disponibles > 0:
            promocion = {
                "id": clave.split(":")[-1],
                "nombre": datos.get("nombre"),
                "departamento": datos.get("departamento"),
            }

            promociones_activas.append(promocion)

    return sorted(
        promociones_activas,
        key=lambda promocion: (promocion["nombre"] or "").lower()
    )


@cupones_bp.route("/cupon", methods=["GET", "POST"])
def obtener_cupon():
    promociones_activas = listar_promociones_activas()

    if request.method == "POST":
        cliente = request.form.get("cliente", "").strip()
        promocion_id = request.form.get("promocion_id", "").strip()

        clave = f"{PREFIJO_PROMOCION}:{promocion_id}"

        # 1. Verificar que la promoción siga existiendo en Redis.
        if not promocion_id or not redis_client.exists(clave):
            flash("La promoción ya venció.", "danger")

        else:
            # 2. Verificar que el cliente no tenga un cupón previo.
            cupon_existente = None

            if cliente:
                cupon_existente = col_cupones.find_one({
                    "cliente": cliente,
                    "promocion_id": promocion_id,
                })

            if not cliente:
                flash("Debe ingresar el nombre del cliente.", "warning")

            elif cupon_existente:
                flash(
                    "Cliente ya tiene un cupón de esta promoción.",
                    "warning",
                )

            else:
                # 3. Descontar un cupón disponible en Redis.
                disponibles = redis_client.hincrby(
                    clave,
                    "cupones_disponibles",
                    -1,
                )

                if disponibles < 0:
                    redis_client.hincrby(
                        clave,
                        "cupones_disponibles",
                        1,
                    )

                    flash("No hay cupones disponibles.", "danger")

                else:
                    try:
                        datos = redis_client.hgetall(clave)

                        cantidad_cupones = col_cupones.count_documents({
                            "promocion_id": promocion_id,
                        })

                        codigo = (
                            f"{promocion_id}-{cantidad_cupones + 1:04d}"
                        )

                        nuevo_cupon = {
                            "codigo": codigo,
                            "cliente": cliente,
                            "promocion_id": promocion_id,
                            "promocion_nombre": datos.get("nombre"),
                            "departamento": datos.get("departamento"),
                            "fecha_obtencion": datetime.now(timezone.utc),
                        }

                        col_cupones.insert_one(nuevo_cupon)

                    except PyMongoError:
                        # Restaurar la disponibilidad si falla MongoDB.
                        redis_client.hincrby(
                            clave,
                            "cupones_disponibles",
                            1,
                        )

                        flash(
                            "No fue posible guardar el cupón. Intente nuevamente.",
                            "danger",
                        )

                    else:
                        flash(
                            f"¡Cupón obtenido correctamente! Código: {codigo}",
                            "success",
                        )

        return redirect(url_for("cupones.obtener_cupon"))

    return render_template(
        "cupones/obtener.html",
        promociones=promociones_activas,
    )
