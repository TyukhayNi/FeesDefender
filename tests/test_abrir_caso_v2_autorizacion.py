"""La autorizacion de escritura del modo secuenciado (V2).

R1/H-01 lo midio: nombrar las etapas NO acredita autorizacion. El default de
`--crm` es `api`, asi que omitir el flag escribiria en el CRM sin que nadie lo
hubiera pedido. La puerta vieja («exige --crm skip») protegia esa propiedad
prohibiendo escribir; la nueva la protege exigiendo que se DECLARE.
"""

import scripts.abrir_caso as ac


class _Ident:
    case_id = "W-TEST1"


def test_las_etapas_de_v2_amplian_v1_por_la_derecha():
    # Un `--hasta sala_maquina` de antes tiene que seguir parando donde paraba. Por
    # `len(...)` y no por un `4` literal: un indice fijo vuelve a romperse en cuanto
    # entre otra etapa —como entrara `viabilidad`—, y lo que el aserto quiere decir es
    # «V2 empieza por V1 entera», no «V2 empieza por N».
    assert ac.ETAPAS_V2[:len(ac.ETAPAS_V1)] == ac.ETAPAS_V1


def test_las_tres_etapas_nuevas_estan_y_en_orden():
    # `crm_ficha` NO esta: ejecuta los efectos materiales de la §8.1, que el spec
    # situa despues de sala de lectura y viabilidad (R1/H-05). `viabilidad` TAMPOCO
    # esta todavia en este PR: entra en una tarea posterior.
    assert ac.ETAPAS_V2[len(ac.ETAPAS_V1):] == ("crm_alta", "actuacion", "verificar")


def test_omitir_crm_en_modo_secuenciado_es_ERROR():
    errores = ac.validar_modo("v1", crm=None, fuente="drive_ev",
                              folder_id="X", hasta=None)

    assert [e for e in errores if "--crm" in e], (
        "omitir el flag no puede valer como autorizacion de escritura")


def test_declarar_crm_api_autoriza():
    errores = ac.validar_modo("v1", crm="api", fuente="drive_ev",
                              folder_id="X", hasta=None)

    assert not [e for e in errores if "--crm" in e]


def test_declarar_crm_skip_sigue_siendo_valido():
    errores = ac.validar_modo("v1", crm="skip", fuente="drive_ev",
                              folder_id="X", hasta=None)

    assert not [e for e in errores if "--crm" in e]


def test_hasta_admite_una_etapa_NUEVA():
    errores = ac.validar_modo("v1", crm="skip", fuente="drive_ev",
                              folder_id="X", hasta="actuacion")

    assert not [e for e in errores if "--hasta" in e]


def test_hasta_sigue_rechazando_lo_que_no_es_etapa():
    errores = ac.validar_modo("v1", crm="skip", fuente="drive_ev",
                              folder_id="X", hasta="inventada")

    assert [e for e in errores if "--hasta" in e], (
        "un --hasta mal escrito no puede convertirse en «no pares»")


def test_crm_fuera_del_vocabulario_es_error():
    errores = ac.validar_modo("v1", crm="lo_que_sea",
                              fuente="drive_ev", folder_id="X", hasta=None)

    assert [e for e in errores if "--crm" in e]


def test_el_modo_libre_no_se_mueve():
    # La puerta nueva es del modo secuenciado. `libre` retorna antes de leerla, y
    # su default `api` se conserva: cambiarlo seria una regresion (R1/H-01).
    assert ac.validar_modo("libre", crm="api", fuente="drive_ev") == []
