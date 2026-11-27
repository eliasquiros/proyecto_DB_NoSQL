from flask import Flask, render_template

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
    # Persona A: F1 carga inicial y F5 consulta de cupones
    from .carga import bp as carga_bp
    from .reportes import bp as reportes_bp

    app.register_blueprint(carga_bp)
    app.register_blueprint(reportes_bp)

    # Persona B: F2 activar y F3 promociones activas
    from .activar import activar_bp
    from .activas import activas_bp

    app.register_blueprint(activar_bp)
    app.register_blueprint(activas_bp)


def _registrar_ruta_raiz(app: Flask) -> None:
    @app.get("/")
    def index():
        return render_template("inicio.html")
