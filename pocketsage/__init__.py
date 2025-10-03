"""PocketSage application factory."""

from __future__ import annotations

from importlib import import_module
from typing import Iterable

from flask import Flask

from .config import BaseConfig, DevConfig
from .extensions import init_db

_CONFIG_MAP = {
    "development": DevConfig,
    "default": BaseConfig,
}


def _resolve_config(name: str | None) -> type[BaseConfig]:
    """Return the config class for the provided environment name."""

    if not name:
        return BaseConfig
    return _CONFIG_MAP.get(name.lower(), BaseConfig)


def _blueprint_paths() -> Iterable[str]:
    """Yield blueprint import paths registered by the framework owner."""

    yield "pocketsage.blueprints.ledger"
    yield "pocketsage.blueprints.habits"
    yield "pocketsage.blueprints.liabilities"
    yield "pocketsage.blueprints.portfolio"
    yield "pocketsage.blueprints.admin"


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application instance."""

    app = Flask(__name__, instance_relative_config=True)
    config_cls = _resolve_config(config_name or app.config.get("ENV"))
    config_obj = config_cls()
    app.config.from_object(config_obj)
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", config_obj.sqlalchemy_engine_options())
    app.config["POCKETSAGE_CONFIG"] = config_obj

    # TODO(@ops-team): layer instance config + environment overrides using `app.config.from_envvar`.

    _register_blueprints(app)
    init_db(app)

    # TODO(@framework-owner): register CLI commands, logging, and background services.

    return app


def _register_blueprints(app: Flask) -> None:
    """Import and register all blueprints declared in `_blueprint_paths`."""

    for dotted_path in _blueprint_paths():
        module = import_module(dotted_path)
        blueprint = getattr(module, "bp")
        app.register_blueprint(blueprint)
    # TODO(@qa-team): add coverage ensuring blueprint endpoints respond with 200
    #   and include expected template context variables.
