"""
Logging estructurado JSON para Cloud Logging.
Cada record incluye level, message, time, y los extras que se pasen.
"""
from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> None:
    """Configura el root logger con formato JSON (1 línea = 1 log entry)."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Quitar handlers previos para evitar duplicados al reload de uvicorn.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "time", "levelname": "severity"},
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)

    # Bajar el ruido de uvicorn access en producción
    logging.getLogger("uvicorn.access").setLevel("WARNING")
