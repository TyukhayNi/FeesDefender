"""Dobles de test compartidos de la Fase 0."""

from tests._dobles.fake_drive import (
    EjecutorActor,
    FakeDrive,
    FakeRclone,
    entorno_de_prueba,
)

__all__ = ["EjecutorActor", "FakeDrive", "FakeRclone", "entorno_de_prueba"]
