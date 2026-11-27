"""F1 - Carga inicial de datos (Persona A)."""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pymongo.errors import BulkWriteError

from .db import mongo_db as db

bp = Blueprint("carga", __name__)

CAMPOS_OBLIGATORIOS = ["id", "nombre", "departamento", "descuento"]


def _etiqueta(campo):
    """garantia_meses -> Garantia meses"""
    return str(campo).replace("_", " ").capitalize()


def _formatear(valor):
    """Convierte cualquier valor a texto legible (nunca JSON)."""
    if isinstance(valor, list):
        return ", ".join(_formatear(v) for v in valor)
    if isinstance(valor, dict):
        return ", ".join(f"{_etiqueta(k)}: {_formatear(v)}" for k, v in valor.items())
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return str(valor)


def _validar(datos):
    """Devuelve un mensaje de error, o None si el contenido es válido."""
    if not isinstance(datos, list):
        return "El archivo debe contener una lista de promociones."
    if not datos:
        return "El archivo no contiene promociones."
    for i, promo in enumerate(datos, start=1):
        if not isinstance(promo, dict):
            return f"El elemento {i} del archivo no es una promoción válida."
        faltan = [c for c in CAMPOS_OBLIGATORIOS if promo.get(c) in (None, "")]
        if faltan:
            return f"La promoción {i} no tiene: {', '.join(faltan)}."
    return None


@bp.route("/carga", methods=["GET", "POST"])
def carga():
    coleccion = db["promociones"]

    if request.method == "POST":
        archivo = request.files.get("archivo")

        if not archivo or archivo.filename == "":
            flash("Seleccioná un archivo JSON antes de cargar.", "error")
            return redirect(url_for("carga.carga"))

        if not archivo.filename.lower().endswith(".json"):
            flash("El archivo debe tener extensión .json.", "error")
            return redirect(url_for("carga.carga"))

        contenido = archivo.read()
        if not contenido.strip():
            flash("El archivo está vacío.", "error")
            return redirect(url_for("carga.carga"))

        try:
            datos = json.loads(contenido.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            flash("El archivo no tiene un formato JSON válido.", "error")
            return redirect(url_for("carga.carga"))

        error = _validar(datos)
        if error:
            flash(error, "error")
            return redirect(url_for("carga.carga"))

        # Evita promociones duplicadas si se carga el mismo archivo otra vez
        coleccion.create_index("id", unique=True)
        for promo in datos:
            promo.pop("_id", None)

        try:
            resultado = coleccion.insert_many(datos, ordered=False)
            insertadas, repetidas = len(resultado.inserted_ids), 0
        except BulkWriteError as e:
            insertadas = e.details.get("nInserted", 0)
            repetidas = sum(1 for err in e.details.get("writeErrors", []) if err.get("code") == 11000)

        if insertadas:
            flash(f"Se cargaron {insertadas} promociones desde {archivo.filename}.", "success")
        if repetidas:
            flash(f"{repetidas} promociones ya existían en el catálogo y se omitieron.", "warning")
        return redirect(url_for("carga.carga"))

    # GET: mostrar el catálogo actual
    promociones = list(coleccion.find({}, {"_id": 0}).sort("id", 1))
    filas = []
    for p in promociones:
        otros = [(_etiqueta(k), _formatear(v)) for k, v in p.items() if k not in CAMPOS_OBLIGATORIOS]
        filas.append({
            "id": p.get("id"),
            "nombre": p.get("nombre"),
            "departamento": p.get("departamento"),
            "descuento": _formatear(p.get("descuento")),
            "otros": otros,
        })
    departamentos = {p.get("departamento") for p in promociones}

    return render_template(
        "carga/carga.html",
        filas=filas,
        total=len(promociones),
        total_departamentos=len(departamentos),
    )
