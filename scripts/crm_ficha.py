"""CLI local: rellenar la ficha CRM completa de un expediente extrajudicial (B1).

Orquestador fino sobre core: resuelve el caso por --case-id, carga el
``_ficha_crm.yaml`` y ejecuta (idempotente) cliente propio EV + contrario +
colaboradores + Notas, con GET de verificación tras cada escritura.

Uso:
  python -m scripts.crm_ficha --case-id W-XXXXXX [--dry-run] [--yes]

Requiere SUDESPACHO_API_KEY (.env). El _ficha_crm.yaml (PII) vive en
data/CASOS/<caso>/00_Input/ y nunca se commitea.
"""
from __future__ import annotations

import html

import typer

from core import case_manager
from core import config
from core.casos import case_locator
from core.crm_ficha import (
    auditar_datos, auditar_relaciones, cargar_ficha_yaml, contradicciones_previas,
)
from core.sudespacho_create import get_expediente, update_expediente
from core.sudespacho_relations import (
    ensure_colaborador_vinculado, ensure_contrario_vinculado, get_cliente_contrario,
    get_colaborador, get_relaciones, link_ev_mmc, resolver_colaborador_existente,
    resolver_contrario_existente,
)

app = typer.Typer(add_completion=False, help="Rellenar la ficha CRM completa de un expediente")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"
_FICHA_YAML = "_ficha_crm.yaml"

#: El literal de éxito, UNA vez: los tests lo importan —los positivos y los negativos—, así que
#: cambiar el texto no puede vaciar un negativo en silencio (§9 del plan, frontera 3). Dice
#: exactamente lo que certifica (spec rev. 3 §2.5): los tres bloques de vínculos son los del
#: YAML, cada parte tiene en el CRM los datos declarados, y las Notas coinciden.
EXITO_VERIFICADA = "VERIFICADA: vínculos y datos de la ficha"
SIN_VERIFICAR = "SIN VERIFICAR"


def _mismas_notas(guardado: str | None, escrito: str) -> bool:
    """True si el CRM guardó lo que se escribió, salvo normalización de entidades HTML.

    **El CRM DESESCAPA las entidades al guardar** (`&amp;` → `&`), así que la igualdad
    byte a byte declaraba `[FALTA]` sobre una escritura que sí había entrado. Medido el
    2026-09-04 sobre el expediente 637: de 5158 caracteres escritos y 5142 guardados, las
    16 diferencias eran cuatro `&amp;` (`MEJORAS #150`). Y como el campo es HTML, escribir
    `&` suelto no es la solución —sería HTML inválido—: el problema estaba en la igualdad.

    Se **desescapan las dos partes** y se comparan por igualdad, no por inclusión: unas
    notas realmente truncadas por el servidor tienen que seguir dando distinto, que es la
    razón de ser de esta verificación. Los dos mutantes están en
    `tests/test_crm_ficha_cli.py::TestElCRMDesescapaLasEntidadesHTML`.
    """
    return html.unescape(guardado or "").strip() == html.unescape(escrito).strip()


def _exp_id_de(case_id: str) -> str | None:
    for e in case_manager.get_case_status(case_id)["expedientes"]:
        if isinstance(e, dict) and e.get("element") == _ELEMENT_EXTRAJUDICIAL:
            return str(e.get("id"))
    return None


def _identifica(dto) -> str:
    return f"id_crm {dto.id_crm}" if dto.id_crm else "dedup NIF/email"


def _fase_previa(ficha) -> list[str]:
    """SOLO LECTURA (spec rev. 3 §3 A.4): cada parte que ya existe, contra lo que el YAML declara.

    Corre después del corte de `--dry-run` y de la confirmación, y **antes del primer writer**.
    Devuelve TODOS los problemas: un dato distinto en una ficha existente, una ficha que no se
    puede leer, un `id_crm` que no existe, un conflicto o una ambigüedad de la resolución. Si hay
    alguno, no se escribe nada: escribir antes dejaría un vínculo y unos completados sobre una
    ficha que el propio YAML desmiente, y `crm_ficha` no desvincula (R2/H-01).
    """
    problemas: list[str] = []
    for elemento, partes, declarados, resolver, leer in (
        ("clientes_contrarios", ficha.contrarios, ficha.declarados_contrarios,
         resolver_contrario_existente, get_cliente_contrario),
        ("colaboradores", ficha.colaboradores, ficha.declarados_colaboradores,
         resolver_colaborador_existente, get_colaborador),
    ):
        for dto, declarado in zip(partes, declarados, strict=True):
            try:
                existente = resolver(dto)
            except Exception as exc:  # noqa: BLE001 — conflicto, ambigüedad o consulta caída
                problemas.append(f"{elemento} {dto.nombre!r}: {exc}")
                continue
            if not existente:
                continue                    # se creará: la audita la lectura final
            try:
                actual = leer(existente)
            except Exception as exc:  # noqa: BLE001
                problemas.append(f"{elemento} id={existente}: no se pudo leer la ficha "
                                 f"({exc!r}); no se escribe sobre lo que no se ha podido "
                                 "comparar")
                continue
            problemas += contradicciones_previas(elemento, existente, declarado, actual,
                                                 por_id=bool(dto.id_crm))
    return problemas


@app.command()
def main(
    case_id: str = typer.Option(..., "--case-id", help="case_id canónico o W-code"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma la escritura al CRM"),
) -> None:
    resolved = case_locator.resolve_ref(case_id)
    # `buscar` y no `path_for`: el error legible es el contrato de un CLI.
    case_dir = case_locator.buscar(resolved)
    if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r} (resuelto: {resolved!r})", err=True)
        raise typer.Exit(code=1)

    exp_id = _exp_id_de(resolved)
    if not exp_id:
        typer.echo(f"[ERROR] El caso {resolved!r} no tiene expediente extrajudicial "
                   "registrado; da de alta primero con abrir_caso --crm api", err=True)
        raise typer.Exit(code=1)

    ficha_path = case_dir / "00_Input" / _FICHA_YAML
    try:
        ficha = cargar_ficha_yaml(ficha_path)
    except FileNotFoundError:
        typer.echo(f"[ERROR] Falta {_FICHA_YAML} en {case_dir / '00_Input'}", err=True)
        raise typer.Exit(code=1)
    except ValueError as exc:
        typer.echo(f"[ERROR] {_FICHA_YAML} inválido: {exc}", err=True)
        raise typer.Exit(code=1)

    try:
        cliente_propio_id = config.cliente_propio_id(ficha.cliente_propio)
    except ValueError:
        typer.echo(
            f"[ERROR] cliente_propio desconocido: {ficha.cliente_propio!r}"
            " (ver core.config.CLIENTES_PROPIOS_EV)", err=True,
        )
        raise typer.Exit(code=1)

    plan = [f"cliente propio {ficha.cliente_propio} (id {cliente_propio_id}) → exp {exp_id}"]
    # TODOS los contrarios, no solo el primero ([APER-63]): una reclamación formulada por
    # dos firmantes —un matrimonio— exigía una segunda llamada a mano.
    plan += [f"contrario: {c.apellido1 or c.nombre} ({_identifica(c)})" for c in ficha.contrarios]
    plan += [f"colaborador: {c.email or c.nombre} ({_identifica(c)})" for c in ficha.colaboradores]
    if ficha.notas_html:
        plan.append("Notas (update_expediente)")
    typer.echo("Plan ficha CRM:\n  - " + "\n  - ".join(plan))

    if dry_run:
        typer.echo("[dry-run] no se escribe nada.")
        raise typer.Exit(code=0)
    if not (yes or typer.confirm("¿Escribir la ficha en el CRM?")):
        typer.echo("Cancelado.")
        raise typer.Exit(code=0)

    # La fase previa, de solo lectura: aquí y no antes (`--dry-run` no lee el CRM, R2/H-08), y
    # antes del primer writer, para que un «distinto» no deje nada escrito (R2/H-01).
    previas = _fase_previa(ficha)
    if previas:
        typer.echo("[ERROR] El CRM contradice el _ficha_crm.yaml, o no se ha podido comparar, así "
                   "que no se escribe NADA:\n  - " + "\n  - ".join(previas) + "\n"
                   "crm_ficha no pisa datos: corrige el YAML o la ficha del CRM y relanza.",
                   err=True)
        raise typer.Exit(code=1)

    #: Todo lo que la corrida AFIRMA haber escrito, para contrastarlo por lectura. La
    #: frontera es «TODO», no «las relaciones»: R1/H-01 encontró que verificar solo los
    #: vínculos dejaba las Notas fuera y aun así imprimía VERIFICADA — el mismo falso OK
    #: que esta verificación existe para eliminar.
    esperado: dict[str, list[str]] = {
        "clientes_propios": [str(cliente_propio_id)],
        "clientes_contrarios": [],
        "colaboradores": [],
    }
    #: (elemento, id, declaración, creado) de cada parte ya resuelta, en el orden en que se
    #: escribió: es lo que relee la lectura de datos (spec rev. 3 §4 B.2), creada o existente.
    resueltas: list[tuple[str, str, dict, bool]] = []
    notas_escritas: str | None = None

    def _vinculos(rel: dict, *, parcial: bool = False) -> tuple[list[str], list[str]]:
        """`esperado` contra lo leído, por IGUALDAD (spec §4 B.1). Devuelve `(faltan, sobran)`.

        En la **parcial** —tras una escritura fallida— solo informa de lo que falta (B.4): las
        partes que no llegaron a resolverse no tienen id, y sus vínculos de una corrida anterior
        saldrían como sobrantes sin serlo.
        """
        a = auditar_relaciones(esperado, rel)
        for linea in a.ok:
            typer.echo(f"  [ok] {linea}")
        for linea in a.faltan:
            typer.echo(f"  [FALTA] {linea}")
        if parcial:
            typer.echo("  sobrantes: sin comprobar — las partes que no llegaron a resolverse no "
                       "tienen id, y sus vínculos de otra corrida saldrían como sobrantes sin "
                       "serlo")
            return a.faltan, []
        for linea in a.sobran:
            typer.echo(f"  [SOBRA] {linea}")
        return a.faltan, a.sobran

    def _leer() -> dict | None:
        """Las relaciones, o `None` si no se pudieron leer. `None` NO es «vacío»."""
        try:
            return get_relaciones(_ELEMENT_EXTRAJUDICIAL, exp_id)
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"[AVISO] No se pudieron LEER las relaciones ({exc!r}); "
                       f"los vínculos quedan {SIN_VERIFICAR}, que no es lo mismo que mal.")
            return None

    try:
        link_ev_mmc(exp_id, cliente_propio_id=cliente_propio_id)
        typer.echo(f"OK cliente propio {ficha.cliente_propio} (id {cliente_propio_id}) vinculado (exp {exp_id})")

        declarados_c = iter(ficha.declarados_contrarios)
        for contrario in ficha.contrarios:
            cid, creado = ensure_contrario_vinculado(exp_id, contrario)
            esperado["clientes_contrarios"].append(str(cid))
            resueltas.append(("clientes_contrarios", str(cid), next(declarados_c), creado))
            typer.echo(f"OK contrario id={cid} ({'creado' if creado else 'existente'}) vinculado")
        declarados_col = iter(ficha.declarados_colaboradores)
        for col in ficha.colaboradores:
            colid, creado = ensure_colaborador_vinculado(exp_id, col)
            esperado["colaboradores"].append(str(colid))
            resueltas.append(("colaboradores", str(colid), next(declarados_col), creado))
            typer.echo(f"OK colaborador id={colid} ({'creado' if creado else 'existente'}) vinculado")
        if ficha.notas_html:
            update_expediente(exp_id, {"Notas": ficha.notas_html})
            notas_escritas = ficha.notas_html
            typer.echo("OK Notas actualizadas")
    except Exception as exc:  # noqa: BLE001 — tolerancia a caída (spec §7.4), como _alta_crm
        typer.echo(
            f"[ERROR] Falló una escritura al CRM ({exc!r}). "
            "Re-ejecutar es seguro: contrario/colaboradores deduplican por NIF/email.",
            err=True,
        )
        # Auditar lo YA escrito antes de rendirse: es justo cuando más importa saber en
        # qué estado quedó la ficha, y los `OK` de arriba se apoyaban en un status
        # (R1/H-03). No cambia el código de salida: la corrida falló igual.
        parcial = _leer()
        if parcial is not None:
            typer.echo("Estado de lo que sí se llegó a escribir:")
            _vinculos(parcial, parcial=True)
        raise typer.Exit(code=1)

    # Verificación POR RESULTADO. El 201 de `relation_element` no prueba el vínculo, y
    # hasta el 2026-09-04 aquí se remataba con «verificar partes visualmente en el CRM»
    # porque se creía que la API no sabía leer relaciones. Sí sabe: `related_register`.
    faltan: list[str] = []
    sobran: list[str] = []
    datos_mal: list[str] = []
    sin_verificar: list[str] = []

    try:
        rec = get_expediente(exp_id)
        typer.echo(f"Verificación: expediente {exp_id} "
                   f"Numero_Expediente={rec.get('Numero_Expediente')}")
        if notas_escritas is not None:
            if _mismas_notas(rec.get("Notas"), notas_escritas):
                typer.echo("  [ok] Notas coinciden con lo escrito")
            else:
                typer.echo("  [FALTA] Notas: el CRM devuelve un contenido distinto del escrito")
                faltan.append("Notas")
    except Exception as exc:  # noqa: BLE001 — la verificación no debe tumbar el éxito
        typer.echo(f"[AVISO] GET de verificación falló ({exc!r}); revisa manualmente el CRM")
        if notas_escritas is not None:
            sin_verificar.append("Notas")

    rel = _leer()
    if rel is None:
        sin_verificar.extend(esperado)
    else:
        f_vinc, sobran = _vinculos(rel)
        faltan += f_vinc

    # Los DATOS de cada parte, releídos por id (spec §4 B.2, R1/H-03): una igualdad de ids
    # exacta certificaba una ficha cuyos datos no se habían escrito —el apellido de W-030A13—.
    # Se compara la DECLARACIÓN, no el DTO (R2/H-02).
    for elemento, id_, declarado, _creado in resueltas:
        leer = get_cliente_contrario if elemento == "clientes_contrarios" else get_colaborador
        try:
            ficha_crm = leer(id_)
        except Exception as exc:  # noqa: BLE001 — «no pude leer» no es «está mal»
            typer.echo(f"[AVISO] No se pudo LEER la ficha de {elemento} id={id_} ({exc!r}); sus "
                       f"datos quedan {SIN_VERIFICAR}, que no es lo mismo que mal.")
            sin_verificar.append(f"datos de {elemento} id={id_}")
            continue
        for d in auditar_datos(elemento, id_, declarado, ficha_crm):
            typer.echo(f"  [DATO] {d}")
            datos_mal.append(str(d))

    # El veredicto (spec §4 B.3): qué hacer con cada tipo, sin hacerlo. Un fallo conocido GANA
    # a un «sin verificar» simultáneo, y ningún mensaje de fallo dice la palabra del éxito.
    if faltan or sobran or datos_mal:
        if faltan:
            typer.echo(
                "[ERROR] La lectura DESMIENTE la escritura: no consta -> "
                + ", ".join(faltan)
                + ". Los 'OK ...' de arriba se apoyaban en el status, no en el resultado.",
                err=True,
            )
        if sobran:
            typer.echo(
                "[ERROR] Hay partes vinculadas que el _ficha_crm.yaml no declara: "
                + ", ".join(sobran)
                + ". El YAML es la lista COMPLETA de partes: si alguna es legítima, añádela al "
                "YAML (con id_crm si no tiene NIF ni email) y relanza; si no, desvincúlala a "
                "mano en el CRM. crm_ficha no desvincula.",
                err=True,
            )
        if datos_mal:
            typer.echo(
                "[ERROR] La ficha del CRM no tiene los datos que el YAML declara: "
                + "; ".join(datos_mal)
                + ". Revísalos y corrígelos en la ficha del CRM: crm_ficha no pisa datos.",
                err=True,
            )
        if sin_verificar:
            typer.echo(f"  Además, {SIN_VERIFICAR}: {', '.join(sin_verificar)}.")
        raise typer.Exit(code=1)

    if sin_verificar:
        typer.echo(f"OK ficha CRM completada: {resolved} "
                   f"— {SIN_VERIFICAR}: {', '.join(sin_verificar)}")
        return

    typer.echo(f"OK ficha CRM completada y {EXITO_VERIFICADA}: {resolved}")


if __name__ == "__main__":
    app()
