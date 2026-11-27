import os
from dataclasses import dataclass
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


class ConfiguracionInvalidaError(ValueError):
    """Error lanzado cuando una variable en .env tiene un formato inválido."""


def _leer_texto(nombre: str, por_defecto: str) -> str:
    valor = os.getenv(nombre, "").strip()
    return valor or por_defecto


def _leer_entero(nombre: str, por_defecto: int) -> int:
    valor_crudo = os.getenv(nombre, "").strip()
    if not valor_crudo:
        return por_defecto
    try:
        return int(valor_crudo)
    except ValueError as err:
        raise ConfiguracionInvalidaError(
            f"La variable de entorno '{nombre}' debe ser un número entero (recibido: '{valor_crudo}')."
        ) from err


@dataclass(frozen=True)
class ConfiguracionApp:
    secret_key: str
    mongo_uri: str
    mongo_db_name: str
    mongo_timeout_ms: int
    redis_host: str
    redis_port: int
    redis_db: int
    redis_timeout_seg: int

    @classmethod
    def desde_entorno(cls) -> "ConfiguracionApp":
        return cls(
            secret_key=_leer_texto("SECRET_KEY", "clave-desarrollo-local-2026"),
            mongo_uri=_leer_texto("MONGO_URI", "mongodb://localhost:27017/"),
            mongo_db_name=_leer_texto("MONGO_DB_NAME", "cupones_db"),
            mongo_timeout_ms=_leer_entero("MONGO_TIMEOUT_MS", 3000),
            redis_host=_leer_texto("REDIS_HOST", "localhost"),
            redis_port=_leer_entero("REDIS_PORT", 6379),
            redis_db=_leer_entero("REDIS_DB", 0),
            redis_timeout_seg=_leer_entero("REDIS_TIMEOUT_SEG", 3),
        )


config = ConfiguracionApp.desde_entorno()
