"""`FakeDrive` / `FakeRclone`: doble contractual de rclone **v1.73.5 (Windows amd64)**.

Promueve el doble embrionario de los PRs #156/#160 y cierra sus dos defectos de
contrato, ambos encontrados por revisión adversarial.

## Defecto 1 — la circularidad (A-1 de la 2ª pasada)

El doble anterior llamaba a `rc.esta_excluido(rel)`: **importaba las reglas de
producción para decidir la transferencia**. Si alguien quitara `_exclusiones_rclone()`
del comando, el doble seguiría excluyendo y el test seguiría verde. Contrato nuevo:

- el `copy` decide **solo por los flags presentes en `cmd`**;
- **sin flags, transfiere también protocolo y notas**;
- este módulo **no importa `core.repository_checkout` ni `core.config`**. Si algún día
  aparece un `from core...` aquí, la circularidad ha vuelto.

## Defecto 2 — la semántica de fallo era insuficiente (B0-3 de la 3ª pasada)

`_sub_falla` devolvía `rc=3` con `stdout="["` para **cualquier** subcomando. Eso hacía
imposible la fila obligatoria de la matriz «`rc != 0` con `stdout` **parseable**», y
además **aplanaba `moveto` (rc real 1) con `copyto` (rc real 3)**, que es justo lo que
el contrato de rclone llama mentira. De ahí el canal **`resultados`**, guionizado por
`(subcomando, ocurrencia)`, que devuelve el resultado tal cual y **no muta el Drive**.
El `hook` no podía suplirlo: su firma devuelve `None`, así que muta el Drive pero no
sustituye el resultado de una operación.

## El hook, y por qué se arma con `armar(n_objetivo, callback)`

La rev. 3 lo dejó como `hook=` de constructor con desarme «al invocarse». Con eso el
`xfail` del *rollback ajeno* es inconstruible: necesita disparar tras la **tercera**
operación relevante y un one-shot sin objetivo se consume en la primera. Y el instante
importa: si el callback corriese **antes** de materializar el CP0 de A, B escribiría
`prestado`, A lo leería y abortaría bien — el defecto no se reproduce y un
`xfail(strict=True)` rompería la suite. Por eso:

- `armar(n_objetivo, callback)` es la **única** forma de armarlo;
- dispara **después de los efectos y del resultado** de la operación objetivo y
  **antes de devolver al caller**;
- **las operaciones que fallan también cuentan** (incluidas las guionizadas y las
  abortadas en la validación de flags), para que `n_objetivo` sea estable;
- es **one-shot**: se desarma al dispararse, o un actor que reentre recursaría.

## Actor

Ni la firma del callback ni `FakeRclone.__call__(cmd)` llevan actor, así que con una
instancia compartida entre A y B nada distinguiría `(A, copyto)` de `(B, copyto)`. Lo
resuelve `EjecutorActor(fake, "A")`: comparte Drive y contador, y etiqueta cada llamada.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tests._barrera import REMOTO_SINTETICO, assert_operandos_sinteticos

#: Flags que el frontal puede emitir. Uno desconocido es `AssertionError`, nunca un
#: éxito permisivo: un doble que ignora en silencio lo que no entiende deja pasar
#: cambios de producción sin que ningún test se entere.
FLAGS_CONOCIDOS = frozenset({
    "--checksum", "--drive-skip-shortcuts", "--transfers", "--log-level", "--log-file",
    "--exclude", "--include", "--files-from", "--backup-dir", "--one-way",
    "--fast-list", "-R", "--recursive", "--hash",
})

SUBCOMANDOS = frozenset({"copy", "copyto", "moveto", "check", "lsjson", "rmdirs"})


class FakeDrive:
    """Drive en memoria: `{ruta_relativa_posix: bytes}`.

    **No modela directorios**, y es deliberado: el frontal solo pregunta por ficheros.
    La consecuencia está escrita en la matriz de fallos — el aserto del `rmdirs` no
    puede afirmar «quedan directorios vacíos», así que afirma lo comprobable (retorno
    descartado, comando emitido, lock liberado).
    """

    def __init__(self, inicial: dict[str, bytes] | None = None) -> None:
        #: **Se guarda la REFERENCIA, no una copia**, y es un requisito de paridad, no
        #: un descuido. El doble embrionario de #156/#160 mutaba el mismo `dict` que el
        #: test tenía en la mano, y los 16 tests asertan sobre esa variable
        #: (`assert drive["00_Input/_caso.md"] == original`). Copiar aquí habría dejado
        #: esos asertos mirando un objeto congelado: seguirían verdes sin comprobar
        #: nada. Es exactamente la regresión silenciosa que la comprobación de paridad
        #: de la Task 2 existe para cazar (A-4 de la 2ª pasada).
        self._d: dict[str, bytes] = inicial if inicial is not None else {}

    # -- lectura
    def leer(self, rel: str) -> bytes | None:
        return self._d.get(rel)

    def rutas(self) -> list[str]:
        return sorted(self._d)

    def existe(self, rel: str) -> bool:
        return rel in self._d

    def hay_prefijo(self, rel: str) -> bool:
        pre = rel.rstrip("/") + "/"
        return any(k.startswith(pre) for k in self._d)

    def md5(self, rel: str) -> str | None:
        """MD5 **a propósito**: paridad con lo que expone la Drive API."""
        b = self._d.get(rel)
        return hashlib.md5(b).hexdigest() if b is not None else None

    def snapshot(self) -> dict[str, str]:
        """`{ruta: md5}` — para asertar que una operación NO tocó el Drive."""
        return {k: hashlib.md5(v).hexdigest() for k, v in self._d.items()}

    def bytes_snapshot(self) -> dict[str, bytes]:
        """Copia de los bytes: para exigir que sobrevivan **idénticos**."""
        return dict(self._d)

    # -- escritura
    def escribir(self, rel: str, data: bytes) -> None:
        self._d[rel] = data

    def borrar(self, rel: str) -> None:
        self._d.pop(rel, None)

    def __contains__(self, rel: object) -> bool:
        return rel in self._d

    def __len__(self) -> int:
        return len(self._d)


def _excluido_por_flags(rel: str, patrones: list[str]) -> bool:
    """Subconjunto de la semántica de filtros de rclone, suficiente y declarado.

    - `dir/**` → todo lo que cuelga de `dir/`;
    - patrón con `/` → `fnmatch` contra la ruta completa;
    - patrón sin `/` → `fnmatch` contra el **basename**, a cualquier profundidad.

    Es un subconjunto: no cubre `{a,b}` ni `**` en medio. Si producción empezara a
    usarlos, este doble tiene que crecer — y el test que lo pille será uno que falle,
    no uno que pase de más.
    """
    base = rel.rsplit("/", 1)[-1]
    for p in patrones:
        if p.endswith("/**"):
            if rel.startswith(p[:-2]):
                return True
        elif "/" in p:
            if fnmatch.fnmatch(rel, p):
                return True
        elif fnmatch.fnmatch(base, p):
            return True
    return False


class _Flags:
    """Vista de los flags de un comando. El doble decide SOLO desde aquí."""

    def __init__(self, cmd: list[str]) -> None:
        self.excludes: list[str] = []
        self.files_from: str | None = None
        self.log_file: str | None = None
        self.backup_dir: str | None = None
        self.one_way = False
        i = 2
        while i < len(cmd):
            tok = str(cmd[i])
            if not tok.startswith("-"):
                i += 1
                continue
            assert tok in FLAGS_CONOCIDOS, (
                f"flag no soportado por el doble: {tok!r}. Añádelo al contrato en vez "
                f"de dejarlo pasar: un doble permisivo esconde cambios de producción."
            )
            if tok in ("--exclude", "--include"):
                self.excludes.append(str(cmd[i + 1])); i += 2
            elif tok == "--files-from":
                self.files_from = str(cmd[i + 1]); i += 2
            elif tok == "--log-file":
                self.log_file = str(cmd[i + 1]); i += 2
            elif tok == "--backup-dir":
                self.backup_dir = str(cmd[i + 1]); i += 2
            elif tok in ("--transfers", "--log-level"):
                i += 2
            else:
                self.one_way = self.one_way or tok == "--one-way"
                i += 1


class FakeRclone:
    """Doble llamable en el lugar de `run_rclone`.

    Orden de procesamiento, en este orden y no otro (ver el `README.md` de las
    fixtures para las mediciones que lo fijan):

    1. validar operandos sintéticos → `BarreraViolada`;
    2. validar combinaciones ilegales de flags (`--files-from` con filtros → `rc=1`,
       sin crear log ni transferir nada);
    3. crear el `--log-file` si el comando es válido — un fallo **operativo** SÍ deja
       log (medido: `copy` de origen ausente → rc 3 con log de 1408 B); solo el fallo
       de **validación de flags** no lo crea;
    4. aplicar `resultados`, luego `fallos*`;
    5. ejecutar la operación;
    6. disparar el `hook`.
    """

    def __init__(
        self,
        drive: FakeDrive | dict[str, bytes],
        *,
        raiz_local: Path,
        fallos: dict[str, int] | None = None,
        fallos_push: dict[str, list[int]] | None = None,
        fallos_sub: dict[str, list[int]] | None = None,
        resultados: dict[tuple[str, int], tuple[int, str, str]] | None = None,
    ) -> None:
        self.drive = drive if isinstance(drive, FakeDrive) else FakeDrive(drive)
        self._raiz = Path(raiz_local).resolve()
        self.fallos = fallos or {}
        self.fallos_push = fallos_push or {}
        self.fallos_sub = fallos_sub or {}
        self.resultados = dict(resultados or {})
        self.registro: list[list[str]] = []
        self.traza_actores: list[tuple[str, str]] = []
        self.n_operaciones = 0
        self._n_push: dict[str, int] = {}
        self._n_sub: dict[str, int] = {}
        self._hook: tuple[int, Callable[[int, list[str], FakeDrive], None]] | None = None
        self._actor = "?"

    @property
    def cmds(self) -> list[list[str]]:
        """Alias **contractual** de `registro`, no un resto histórico.

        Los 16 tests migrados asertan sobre `.cmds` (`guard_pull.py:309`, `:431`, y el
        helper de `:251`) y la migración promete no tocar sus asertos. Renombrarlo a
        secas habría hecho saltar el «para y repórtalo» sin que cambiara nada.
        """
        return self.registro

    # -- hook
    def armar(self, n_objetivo: int, callback: Callable[[int, list[str], FakeDrive], None]) -> None:
        """Arma el hook para la operación `n_objetivo` (1-based, contador global)."""
        assert n_objetivo >= 1, "n_objetivo es 1-based"
        self._hook = (n_objetivo, callback)

    # -- selectores de fallo heredados de #160
    def _push_falla(self, destino_rel: str) -> bool:
        for clave, ocurrencias in self.fallos_push.items():
            if clave in destino_rel:
                self._n_push[clave] = self._n_push.get(clave, 0) + 1
                if self._n_push[clave] in ocurrencias:
                    return True
        return False

    def _sub_falla(self, sub: str) -> bool:
        ocurrencias = self.fallos_sub.get(sub)
        if not ocurrencias:
            return False
        self._n_sub[sub] = self._n_sub.get(sub, 0) + 1
        return self._n_sub[sub] in ocurrencias

    # -- helpers
    @staticmethod
    def _es_remoto(arg: str) -> bool:
        return arg.startswith(REMOTO_SINTETICO)

    @staticmethod
    def _rel(arg: str) -> str:
        return arg[len(REMOTO_SINTETICO):] if arg.startswith(REMOTO_SINTETICO) else arg

    @staticmethod
    def _ok(stdout: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], 0, stdout, "")

    @staticmethod
    def _err(rc: int, stderr: str = "fake", stdout: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], rc, stdout, stderr)

    def _inventario_json(self, prefijo: str = "") -> str:
        """Forma del backend **Drive** (`ID`, 3 algoritmos, `ModTime` UTC `.000Z`)."""
        items: list[dict[str, Any]] = []
        for rel in self.drive.rutas():
            if prefijo and not rel.startswith(prefijo):
                continue
            data = self.drive.leer(rel) or b""
            items.append({
                "Path": rel[len(prefijo):] if prefijo else rel,
                "Name": rel.rsplit("/", 1)[-1],
                "Size": len(data),
                "MimeType": "application/octet-stream",
                "ModTime": "2026-07-29T10:00:00.000Z",
                "IsDir": False,
                "ID": "fake-id",
                "Hashes": {"md5": hashlib.md5(data).hexdigest(),
                           "sha1": "0" * 40, "sha256": "0" * 64},
            })
        return json.dumps(items)

    def _rutas_del_files_from(self, ruta: str) -> list[str]:
        txt = Path(ruta).read_text(encoding="utf-8")
        return [ln.strip() for ln in txt.splitlines() if ln.strip()]

    # -- dispatch
    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess:
        cmd = [str(c) for c in cmd]
        self.registro.append(list(cmd))
        sub = cmd[1] if len(cmd) > 1 else ""
        self.traza_actores.append((self._actor, sub))
        self.n_operaciones += 1
        n = self.n_operaciones

        res = self._despachar(cmd, sub)

        if self._hook is not None and self._hook[0] == n:
            objetivo, callback = self._hook
            self._hook = None                      # one-shot: antes de invocar
            callback(n, cmd, self.drive)
        return res

    def _despachar(self, cmd: list[str], sub: str) -> subprocess.CompletedProcess:
        assert sub in SUBCOMANDOS, (
            f"subcomando no soportado por el doble: {sub!r}. Los soportados son "
            f"{sorted(SUBCOMANDOS)}; añádelo en vez de devolver éxito."
        )
        # 1. operandos sintéticos (el proxy de la barrera no ve nada si nos doblan)
        assert_operandos_sinteticos(cmd, raiz_local=self._raiz)

        flags = _Flags(cmd)

        # 2. combinaciones ilegales: rclone aborta en la validación GLOBAL, antes de
        #    crear el log y sin transferir nada (medido: rc=1, log ausente).
        if flags.files_from and flags.excludes:
            return self._err(1, Path(__file__).parent.parent.joinpath(
                "_fixtures/rclone_v1735/files_from_con_filtros.txt").read_text(
                    encoding="utf-8").strip())

        # 3. el log se crea si el comando es VÁLIDO, falle o no la operación.
        if flags.log_file:
            p = Path(flags.log_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fake log\n", encoding="utf-8")

        # 4. resultados guionizados > fallos heredados.
        clave = (sub, self._n_sub.get(sub, 0) + 1)
        if clave in self.resultados:
            self._n_sub[sub] = clave[1]
            rc_, out, err = self.resultados[clave]
            return subprocess.CompletedProcess([], rc_, out, err)
        if self._sub_falla(sub):
            return self._err(3, "fake", stdout="[" if sub == "lsjson" else "")

        # 5. la operación.
        return getattr(self, f"_op_{sub}")(cmd, flags)

    # -- operaciones
    def _op_lsjson(self, cmd: list[str], flags: _Flags) -> subprocess.CompletedProcess:
        rel = self._rel(cmd[2])
        if rel and not self.drive.existe(rel) and not self.drive.hay_prefijo(rel):
            return self._err(3, "directory not found", stdout="[")   # contrato v1.73.5
        if self.drive.existe(rel):                                   # lsjson de UN fichero
            pre = rel.rsplit("/", 1)[0] + "/" if "/" in rel else ""
            return self._ok(self._inventario_json(prefijo=pre))
        return self._ok(self._inventario_json())

    def _op_copyto(self, cmd: list[str], flags: _Flags) -> subprocess.CompletedProcess:
        origen, destino = cmd[2], cmd[3]
        if self._es_remoto(origen):                                  # PULL remoto→local
            rel = self._rel(origen)
            if rel in self.fallos:
                return self._err(self.fallos[rel])
            if not self.drive.existe(rel):
                return self._err(3, "directory not found")           # medido: 3
            p = Path(destino)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(self.drive.leer(rel) or b"")
            return self._ok()
        src = Path(origen)                                           # PUSH local→remoto
        if not src.exists():
            return self._err(3, "directory not found")
        destino_rel = self._rel(destino)
        if self._push_falla(destino_rel):
            return self._err(1)                                      # el Drive NO se muta
        self.drive.escribir(destino_rel, src.read_bytes())
        return self._ok()

    def _op_copy(self, cmd: list[str], flags: _Flags) -> subprocess.CompletedProcess:
        origen, destino = cmd[2], cmd[3]
        if self._es_remoto(origen):                                  # Drive→local (checkout)
            for rel in self.drive.rutas():
                if flags.excludes and _excluido_por_flags(rel, flags.excludes):
                    continue
                p = Path(destino) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(self.drive.leer(rel) or b"")
            return self._ok()
        raiz = Path(origen)                                          # local→Drive (checkin)
        if flags.files_from:
            candidatas = self._rutas_del_files_from(flags.files_from)
        else:
            candidatas = [str(q.relative_to(raiz)).replace("\\", "/")
                          for q in raiz.rglob("*") if q.is_file()]
            candidatas = [c for c in candidatas
                          if not (flags.excludes and _excluido_por_flags(c, flags.excludes))]
        for rel in candidatas:
            q = raiz / rel
            if not q.exists():                                       # medido: se omite, rc 0
                continue
            if flags.backup_dir and self.drive.existe(rel):
                self.drive.escribir(f"{self._rel(flags.backup_dir)}/{rel}",
                                    self.drive.leer(rel) or b"")
            self.drive.escribir(rel, q.read_bytes())
        return self._ok()

    def _op_moveto(self, cmd: list[str], flags: _Flags) -> subprocess.CompletedProcess:
        origen, destino = cmd[2], cmd[3]
        rel_o, rel_d = self._rel(origen), self._rel(destino)
        if not self.drive.existe(rel_o):
            return self._err(1, "source not found")                  # medido: 1, NO 3
        self.drive.escribir(rel_d, self.drive.leer(rel_o) or b"")
        self.drive.borrar(rel_o)
        return self._ok()

    def _op_check(self, cmd: list[str], flags: _Flags) -> subprocess.CompletedProcess:
        local, destino = Path(cmd[2]), cmd[3]
        if flags.files_from:
            rutas = self._rutas_del_files_from(flags.files_from)
        else:
            rutas = [str(q.relative_to(local)).replace("\\", "/")
                     for q in local.rglob("*") if q.is_file()]
            rutas = [r for r in rutas
                     if not (flags.excludes and _excluido_por_flags(r, flags.excludes))]
        difieren = 0
        for rel in rutas:
            q = local / rel
            md5_local = hashlib.md5(q.read_bytes()).hexdigest() if q.exists() else None
            if md5_local != self.drive.md5(rel):                     # compara por md5
                difieren += 1
        if not flags.one_way:                                        # extras del destino
            difieren += len([r for r in self.drive.rutas() if r not in set(rutas)])
        return self._ok() if difieren == 0 else self._err(1, f"{difieren} differences found")

    def _op_rmdirs(self, cmd: list[str], flags: _Flags) -> subprocess.CompletedProcess:
        return self._ok()                                            # medido: 0, no borra


class EjecutorActor:
    """Envoltorio que etiqueta las llamadas de un actor sobre un `FakeRclone` común.

    Comparte Drive, contador global y `registro`; solo cambia quién consta como emisor.
    Es lo que permite asertar la **secuencia causal** en `traza_actores` y no solo el
    estado final.
    """

    def __init__(self, fake: FakeRclone, actor: str) -> None:
        self._fake = fake
        self._actor = actor

    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess:
        previo = self._fake._actor
        self._fake._actor = self._actor
        try:
            return self._fake(cmd)
        finally:
            self._fake._actor = previo


def entorno_de_prueba(cli, fake, *, work_dir: Path, esperas: list[float] | None = None,
                      ahora: str = "2026-07-29T10:00:00Z",
                      hostname: str = "MAQUINA-TEST", nonce: str = "n0nc3n0nc3n0nc31",
                      usuario: str = "test@sintetico") -> Any:
    """`Entorno` determinista: las ocho piezas fijadas, sin esperas ni disco real.

    `esperas` es una lista que el test aporta y donde se acumulan los segundos que el
    frontal habría dormido — así se asierta `esperar(_SYNC_LAG_S)` sin dormir. Se pasa
    desde fuera y no se cuelga del `Entorno` porque es un dataclass **frozen**:
    asignarle un atributo lanza `FrozenInstanceError`.
    """
    from tests._barrera import BINARIO_SINTETICO

    registro_esperas = esperas if esperas is not None else []
    return cli.ENTORNO_REAL.con(
        ejecutar=fake,
        ahora=lambda: ahora,
        hostname=lambda: hostname,
        work_dir=lambda: work_dir,
        esperar=registro_esperas.append,
        nonce=lambda: nonce,
        usuario=lambda: usuario,
        binario=lambda: BINARIO_SINTETICO,
    )
