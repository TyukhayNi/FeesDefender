"""Asignación de IDs neutros congelados por contenido + control persistente.

``_registro.json``: mapa congelado Message-ID→MSG-id y sha256→ATT-id, más la lista de
``.eml`` procesados. Re-ejecutar NUNCA renumera: las claves existentes mandan; lo nuevo
toma el siguiente número libre.
"""
from __future__ import annotations

import json
from pathlib import Path

_REGISTRO_NAME = "_registro.json"
_README = (
    "Generado por core.email_atomize — NO editar a mano. Mapa congelado de identidad "
    "(Message-ID→MSG-id, sha256→ATT-id) + .eml procesados. Re-ejecutar no renumera."
)


def _norm_mid(message_id: str) -> str:
    return (message_id or "").strip().strip("<>").strip()


class Registro:
    def __init__(self, base_dir: Path, data: dict) -> None:
        self.base_dir = base_dir
        self.mensajes: dict[str, dict] = data.get("mensajes", {})   # mid -> {"id","sha256"}
        self.adjuntos: dict[str, dict] = data.get("adjuntos", {})   # sha -> {"id"}
        self.procesados: list[str] = list(data.get("eml_procesados", []))
        cont = data.get("_contadores", {})
        self._next_msg = int(cont.get("msg", 0))
        self._next_att = int(cont.get("att", 0))

    def msg_id_for(self, message_id: str, *, sha: str) -> str:
        key = _norm_mid(message_id)
        entry = self.mensajes.get(key)
        if entry is not None:
            entry["sha256"] = sha  # upgrade de fidelidad: id estable, sha al día
            return entry["id"]
        self._next_msg += 1
        nuevo = f"MSG-{self._next_msg:05d}"
        self.mensajes[key] = {"id": nuevo, "sha256": sha}
        return nuevo

    def att_id_for(self, sha: str) -> str:
        entry = self.adjuntos.get(sha)
        if entry is not None:
            return entry["id"]
        self._next_att += 1
        nuevo = f"ATT-{self._next_att:05d}"
        self.adjuntos[sha] = {"id": nuevo}
        return nuevo

    def marcar_procesado(self, eml_name: str) -> None:
        if eml_name not in self.procesados:
            self.procesados.append(eml_name)

    def save(self) -> None:
        payload = {
            "_README": _README,
            "_no_editar": True,
            "version": 1,
            "_contadores": {"msg": self._next_msg, "att": self._next_att},
            "mensajes": self.mensajes,
            "adjuntos": self.adjuntos,
            "eml_procesados": sorted(self.procesados),
        }
        (self.base_dir / _REGISTRO_NAME).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_registro(base_dir: Path | str) -> Registro:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    p = base / _REGISTRO_NAME
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {}
    return Registro(base, data if isinstance(data, dict) else {})
