"""Capa de caso: registro de actores (identidades.yaml). El motor SOLO lee este fichero.

Sin identidades.yaml en la raíz del caso → Identidades() vacío = comportamiento genérico.
Diseño: docs/superpowers/specs/2026-06-25-email-atomize-fase3-capa-caso-design.md §4.1, §5.1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_ESTADOS = {"confirmada", "candidata"}


@dataclass
class Persona:
    id: str
    nombre: str = ""
    vigilada: bool = False
    direcciones: list[tuple[str, str]] = field(default_factory=list)  # (email_lower, estado)
    rol: str = ""
    notas: str = ""

    def emails(self) -> set[str]:
        return {e for e, _estado in self.direcciones}


@dataclass
class Identidades:
    vigiladas: frozenset[str] = frozenset()
    candidatas: frozenset[str] = frozenset()
    personas: dict[str, Persona] = field(default_factory=dict)
    # Índice inverso email→persona_id: DERIVADO de `personas`, nunca inyectable (invariante
    # imposible de romper desde fuera). Se reconstruye en __post_init__.
    _por_email: dict[str, str] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        idx: dict[str, str] = {}
        for pid, persona in self.personas.items():
            for email, _estado in persona.direcciones:
                idx[email] = pid
        self._por_email = idx

    def persona_de(self, email: str) -> str | None:
        return self._por_email.get((email or "").strip().lower())

    def persona(self, persona_id: str) -> Persona | None:
        return self.personas.get(persona_id)

    def estado_de(self, email: str) -> str:
        e = (email or "").strip().lower()
        pid = self._por_email.get(e)
        if not pid:
            return ""
        for addr, estado in self.personas[pid].direcciones:
            if addr == e:
                return estado
        return ""


def desde_dict(data: dict) -> Identidades:
    """Construye Identidades desde un dict ya parseado. Valida invariantes (§4.1):
    id presente y único, dirección con email, estado ∈ {confirmada, candidata}, y cada email
    aparece una sola vez en todo el registro (no se repite ni dentro ni entre personas)."""
    personas_raw = (data or {}).get("personas", []) or []
    if not isinstance(personas_raw, list):
        raise ValueError("identidades.yaml: 'personas' debe ser una lista")
    personas: dict[str, Persona] = {}
    por_email: dict[str, str] = {}
    vigiladas: set[str] = set()
    candidatas: set[str] = set()
    for raw in personas_raw:
        if not isinstance(raw, dict):
            raise ValueError("identidades.yaml: cada persona debe ser un mapa")
        pid = str(raw.get("id") or "").strip()
        if not pid:
            raise ValueError("identidades.yaml: persona sin 'id'")
        if pid in personas:
            raise ValueError(f"identidades.yaml: id duplicado {pid!r}")
        vigilada = bool(raw.get("vigilada", False))
        direcciones: list[tuple[str, str]] = []
        for d in raw.get("direcciones", []) or []:
            email = str(d.get("email") or "").strip().lower()
            estado = str(d.get("estado") or "").strip().lower()
            if not email:
                raise ValueError(f"identidades.yaml: dirección sin email en {pid!r}")
            if estado not in _ESTADOS:
                raise ValueError(
                    f"identidades.yaml: estado inválido {estado!r} en {email} ({pid!r})")
            if email in por_email:
                raise ValueError(
                    f"identidades.yaml: email {email} repetido "
                    f"(ya asignado a {por_email[email]!r}; ahora en {pid!r})")
            por_email[email] = pid
            direcciones.append((email, estado))
            if estado == "candidata":
                candidatas.add(email)
            elif estado == "confirmada" and vigilada:
                vigiladas.add(email)
        personas[pid] = Persona(
            id=pid, nombre=str(raw.get("nombre") or ""), vigilada=vigilada,
            direcciones=direcciones, rol=str(raw.get("rol") or ""),
            notas=str(raw.get("notas") or ""))
    return Identidades(vigiladas=frozenset(vigiladas), candidatas=frozenset(candidatas),
                       personas=personas)


def cargar_identidades(case_dir: Path | str) -> Identidades:
    """Lee <case_dir>/identidades.yaml. Sin fichero → Identidades() vacío (genérico)."""
    path = Path(case_dir) / "identidades.yaml"
    if not path.exists():
        return Identidades()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return desde_dict(data)
