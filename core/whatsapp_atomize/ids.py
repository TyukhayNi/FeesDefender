"""IDs congelados por contenido para WhatsApp + control persistente (_registro.json).

fingerprint = sha256(timestamp_iso|autor|texto). Re-ejecutar NUNCA renumera.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_REGISTRO_NAME = "_registro.json"
_README = (
    "Generado por core.whatsapp_atomize — NO editar a mano. Mapa congelado "
    "fingerprint→MSG-id, sha256→ATT-id, ENT-id. Re-ejecutar no renumera."
)


def fingerprint(timestamp_iso: str, autor: str, texto: str) -> str:
    base = f"{timestamp_iso}|{autor or ''}|{texto or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


class RegistroWA:
    def __init__(self, base_dir: Path, data: dict) -> None:
        self.base_dir = base_dir
        self.mensajes_fp: dict[str, dict] = data.get("mensajes_fp", {})  # fp -> {"id"}
        self.adjuntos: dict[str, dict] = data.get("adjuntos", {})        # sha -> {"id"}
        self.enterrados: dict[str, dict] = data.get("enterrados", {})    # key -> {"id"}
        self.chats: list[str] = list(data.get("chats", []))
        self.chat_sha: dict[str, str] = data.get("chat_sha", {})
        cont = data.get("_contadores", {})
        self._next_msg = int(cont.get("msg", 0))
        self._next_att = int(cont.get("att", 0))
        self._next_ent = int(cont.get("ent", 0))

    def msg_id_for_fp(self, fp: str) -> str:
        entry = self.mensajes_fp.get(fp)
        if entry is not None:
            return entry["id"]
        self._next_msg += 1
        nuevo = f"MSG-{self._next_msg:05d}"
        self.mensajes_fp[fp] = {"id": nuevo}
        return nuevo

    def att_id_for(self, sha: str) -> str:
        entry = self.adjuntos.get(sha)
        if entry is not None:
            return entry["id"]
        self._next_att += 1
        nuevo = f"ATT-{self._next_att:05d}"
        self.adjuntos[sha] = {"id": nuevo}
        return nuevo

    def ent_id_for(self, key: str) -> str:
        entry = self.enterrados.get(key)
        if entry is not None:
            return entry["id"]
        self._next_ent += 1
        nuevo = f"ENT-{self._next_ent:05d}"
        self.enterrados[key] = {"id": nuevo}
        return nuevo

    def registrar_chat(self, chat_id: str, sha_chat_txt: str) -> None:
        if chat_id not in self.chats:
            self.chats.append(chat_id)
        self.chat_sha[chat_id] = sha_chat_txt

    def save(self) -> None:
        payload = {
            "_README": _README,
            "_no_editar": True,
            "version": 1,
            "_contadores": {"msg": self._next_msg, "att": self._next_att, "ent": self._next_ent},
            "mensajes_fp": self.mensajes_fp,
            "adjuntos": self.adjuntos,
            "enterrados": self.enterrados,
            "chats": sorted(self.chats),
            "chat_sha": self.chat_sha,
        }
        (self.base_dir / _REGISTRO_NAME).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_registro_wa(base_dir: Path | str) -> RegistroWA:
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
    return RegistroWA(base, data if isinstance(data, dict) else {})
