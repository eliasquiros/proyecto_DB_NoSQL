"""F5 - Consulta de cupones por departamento (Persona A)."""
from flask import Blueprint, render_template

from .db import mongo_db as db

bp = Blueprint("reportes", __name__)

# "Ana", "ana" y " Ana " se cuentan como el mismo cliente
CLIENTE_NORMALIZADO = {"$toLower": {"$trim": {"input": "$cliente"}}}


@bp.route("/consulta")
def consulta():
    # Agrupa los cupones por departamento:
    #  - total_cupones: cuántos cupones se obtuvieron
    #  - clientes: conjunto de clientes sin repetir ($addToSet)
    pipeline = [
        {"$group": {
            "_id": "$departamento",
            "total_cupones": {"$sum": 1},
            "clientes": {"$addToSet": CLIENTE_NORMALIZADO},
        }},
        {"$project": {
            "_id": 0,
            "departamento": "$_id",
            "total_cupones": 1,
            "clientes_distintos": {"$size": "$clientes"},
        }},
    ]
    resultados = {r["departamento"]: r for r in db["cupones"].aggregate(pipeline)}

    # Incluir también los departamentos del catálogo que aún no tienen cupones
    departamentos = set(db["promociones"].distinct("departamento")) | set(resultados)
    departamentos.discard(None)

    filas = [
        resultados.get(d, {"departamento": d, "total_cupones": 0, "clientes_distintos": 0})
        for d in departamentos
    ]
    filas.sort(key=lambda f: (-f["total_cupones"], str(f["departamento"])))

    # Clientes distintos en toda la tienda (no es la suma de la columna)
    total_tienda = list(db["cupones"].aggregate([
        {"$group": {"_id": None, "clientes": {"$addToSet": CLIENTE_NORMALIZADO}}},
        {"$project": {"_id": 0, "cantidad": {"$size": "$clientes"}}},
    ]))
    clientes_tienda = total_tienda[0]["cantidad"] if total_tienda else 0

    total_cupones = sum(f["total_cupones"] for f in filas)
    con_cupones = sum(1 for f in filas if f["total_cupones"] > 0)
    maximo = max((f["total_cupones"] for f in filas), default=0)

    return render_template(
        "reportes/consulta.html",
        filas=filas,
        total_cupones=total_cupones,
        clientes_tienda=clientes_tienda,
        con_cupones=con_cupones,
        maximo=maximo,
    )
