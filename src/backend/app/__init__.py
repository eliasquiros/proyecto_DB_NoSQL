from flask import Flask, redirect, url_for

from .config import config


def create_app() -> Flask:
    app = Flask(__name__)
    _configurar_app(app)
    _registrar_blueprints(app)
    _registrar_ruta_raiz(app)
    return app


def _configurar_app(app: Flask) -> None:
    app.config["SECRET_KEY"] = config.secret_key


def _registrar_blueprints(app: Flask) -> None:
    from .activar import activar_bp

    app.register_blueprint(activar_bp)


def _registrar_ruta_raiz(app: Flask) -> None:
    @app.get("/")
    def index():
        return redirect(url_for("activar_bp.mostrar_formulario"))
