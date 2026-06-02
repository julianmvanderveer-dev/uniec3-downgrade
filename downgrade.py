"""
Uniec3 downgrade logica: versie 3.4 → versie 3.3.
"""

import json
import os
import shutil
import tempfile
import zipfile
from collections import defaultdict

# --- Configuratie: wat is nieuw in v3.4 ---

NEW_ENTITY_TYPES_V34 = {"OVERIG", "UNIT-VENT", "VARIANTEN"}
NEW_ENTITY_VERSION_IDS_V34 = {7165, 7171, 7172}

NEW_PROPERTIES_V34 = {
    "AFMOBJ_LABEL_HUIDIG", "AFMOBJ_LABEL_HUIDIG_EWEPTOT", "AFMOBJ_LABEL_HUIDIG_STATUS",
    "AFM_WLC_GWP",
    "BELEMM_DAKRAND", "BELEMM_DAKRAND_AFSTAND", "BELEMM_DAKRAND_HOOGTE",
    "EP_A0LABEL", "EP_BENG1_A0_EIS", "EP_BENG2_A0_EIS", "EP_BENG3_A0_EIS",
    "GEB_EXT_TOOL", "GEB_GEVEL_ISO",
    "OVERIG_GACS", "OVERIG_INST_CO2_EM", "OVERIG_INST_GT290", "OVERIG_INST_GT290_NON",
    "OVERIG_OPEN", "OVERIG_OPM",
    "PV-VELD_BATT", "PV-VELD_BATT_VERM", "PV_BATT", "PV_BATT_VERM",
    "RESULT-EEL_PV_OUT",
    "RESULT-EEP_BM", "RESULT-EEP_DC", "RESULT-EEP_DH", "RESULT-EEP_DW",
    "RESULT-EEP_EL", "RESULT-EEP_GAS", "RESULT-EEP_OIL", "RESULT-EEP_PR",
    "RESULT-ENERGIEFUNCTIE_RES_ENER_PRIM_EMGFORF",
    "RESULT-ENERGIEFUNCTIE_RES_HULPENER_PRIM_EMGFORF",
    "RESULT-EPEXP_EL", "RESULT-EPPRN_EP_US_EL",
    "RESULT-EP_KOUDEBEHOEFTE", "RESULT-EP_WARMKOUDBEHOEFTE",
    "RESULT-EP_ZEB_DEL_BM_MI", "RESULT-EP_ZEB_DEL_DC_MI", "RESULT-EP_ZEB_DEL_DH_MI",
    "RESULT-EP_ZEB_DEL_DW_MI", "RESULT-EP_ZEB_DEL_EL_MI", "RESULT-EP_ZEB_DEL_GAS_MI",
    "RESULT-EP_ZEB_DEL_OIL_MI",
    "RESULT-EP_ZEB_EXP_EL_NREN_TOT", "RESULT-EP_ZEB_EXP_EL_REN_TOT",
    "RESULT-EP_ZEB_EXP_T_GI", "RESULT-EP_ZEB_TOT_AN", "RESULT-EP_ZEB_TOT_MI",
    "RESULT-EWE_FINAL", "RESULT-EWE_FINAL_EED", "RESULT-EWE_P_ZEB",
    "RESULT-EXP_EL_NREN_TOT", "RESULT-EXP_EL_REN_TOT",
    "RESULT-E_BAT_TOT_IN", "RESULT-E_BAT_TOT_OUT",
    "RESULT-E_FINAL_BM", "RESULT-E_FINAL_DC", "RESULT-E_FINAL_DH", "RESULT-E_FINAL_DW",
    "RESULT-E_FINAL_E", "RESULT-E_FINAL_GAS", "RESULT-E_FINAL_OIL",
    "RESULT-E_FINAL_PR", "RESULT-E_FINAL_TOT",
    "RESULT-FP_ZEB_WEEG_H", "RESULT-FP_ZEB_WEEG_W",
    "RESULT-HERNIEUW_BM", "RESULT-HERNIEUW_EK", "RESULT-HERNIEUW_EK_EMGFORF",
    "RESULT-HERNIEUW_EL", "RESULT-HERNIEUW_EW", "RESULT-HERNIEUW_EW_EMGFORF",
    "RESULT-HERNIEUW_K", "RESULT-HERNIEUW_W",
    "RESULT-PR_EL_NREN_DIRECTUSE", "RESULT-PR_EL_REN_DIRECTUSE",
    "RESULT_W_BATT_SYS",
    "RZ_BOUWW_PL", "RZ_DM",
    "SETTINGS_RENOPASP",
    "TAPW-OPWEK_BRON_POMP_COL", "TAPW-OPWEK_TEMP_EXTERN", "TAPW-OPWEK_TEMP_EXTERN_NON",
    "TAPW-OPWEK_TYPE_BOOSTER",
    "UNIT-RZ_DM", "UNIT-VENT_QV_ODA_REQ",
    "VAR_RENOPASP_STAP1", "VAR_RENOPASP_STAP2", "VAR_RENOPASP_STAP3",
    "VENTAAN_ZRR", "VENTAAN_ZRR_TYPE",
    "VENT_QV_ODA_REQ", "VENT_ZRR", "VENT_ZRR_TYPE",
    "VERW-OPWEK_POMP_COL", "VERW-OPWEK_TEMP_EXTERN", "VERW-OPWEK_TEMP_EXTERN_NON",
}

NTA_VERSION_ID_V34 = 404
NTA_VERSION_ID_V33 = 312


def _find_v34_only_installatie_ids(entities, relations):
    parent_child_types = defaultdict(set)
    for rel in relations:
        parent_child_types[rel.get("ParentId", "")].add(rel.get("NTAEntityIdChild", ""))

    result = set()
    for entity in entities:
        if entity.get("NTAEntityId") != "INSTALLATIE":
            continue
        eid = entity.get("NTAEntityDataId", "")
        children = parent_child_types.get(eid, set())
        if children and children.issubset(NEW_ENTITY_TYPES_V34 | {""}):
            result.add(eid)
    return result


def _is_v34_entity(entity, extra_ids):
    return (
        entity.get("NTAEntityId") in NEW_ENTITY_TYPES_V34
        or entity.get("NTAEntityVersionId") in NEW_ENTITY_VERSION_IDS_V34
        or entity.get("NTAEntityDataId") in extra_ids
    )


def _downgrade_entities(entities, relations):
    extra_install_ids = _find_v34_only_installatie_ids(entities, relations)
    result = []
    removed_ids = set()
    for entity in entities:
        if _is_v34_entity(entity, extra_install_ids):
            removed_ids.add(entity.get("NTAEntityDataId"))
            continue
        props = entity.get("NTAPropertyDatas") or []
        entity["NTAPropertyDatas"] = [
            p for p in props if p.get("NTAPropertyId") not in NEW_PROPERTIES_V34
        ]
        result.append(entity)
    return result, removed_ids


def _downgrade_relations(relations, removed_ids):
    return [
        r for r in relations
        if r.get("ParentId") not in removed_ids
        and r.get("ChildId") not in removed_ids
        and r.get("NTAEntityIdParent") not in NEW_ENTITY_TYPES_V34
        and r.get("NTAEntityIdChild") not in NEW_ENTITY_TYPES_V34
    ]


def _downgrade_deltas(deltas, removed_ids):
    result = []
    for delta in deltas:
        delta_id = delta.get("Id", "")
        base_id = delta_id.split(":")[0] if ":" in delta_id else delta_id
        if base_id in removed_ids or delta.get("NTAEntityId") in NEW_ENTITY_TYPES_V34:
            continue
        result.append(delta)
    return result


def downgrade_bytes(input_bytes: bytes) -> bytes:
    """Verwerkt een v3.4 .uniec3 bestand (bytes) en geeft de v3.3 versie terug (bytes)."""
    tmp_dir = tempfile.mkdtemp()
    try:
        tmp_zip = os.path.join(tmp_dir, "input.zip")
        with open(tmp_zip, "wb") as f:
            f.write(input_bytes)

        extract_dir = os.path.join(tmp_dir, "extracted")
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(extract_dir)

        # buildings.json
        buildings_path = os.path.join(extract_dir, "buildings.json")
        with open(buildings_path, encoding="utf-8") as f:
            buildings = json.load(f)
        for b in buildings:
            if b.get("NTAVersionId") == NTA_VERSION_ID_V34:
                b["NTAVersionId"] = NTA_VERSION_ID_V33
            b.pop("ChangeDate", None)
        with open(buildings_path, "w", encoding="utf-8") as f:
            json.dump(buildings, f, ensure_ascii=False, separators=(",", ":"))

        buildings_dir = os.path.join(extract_dir, "buildings")
        for building in buildings:
            bld_id = str(building["BuildingId"])
            bld_dir = os.path.join(buildings_dir, bld_id)
            if not os.path.isdir(bld_dir):
                continue

            # Laad relations alvast (nodig voor entity-analyse)
            relations_path = os.path.join(bld_dir, "relations.json")
            with open(relations_path, encoding="utf-8") as f:
                relations = json.load(f)

            # entities.json
            entities_path = os.path.join(bld_dir, "entities.json")
            with open(entities_path, encoding="utf-8") as f:
                entities = json.load(f)
            entities, removed_ids = _downgrade_entities(entities, relations)
            with open(entities_path, "w", encoding="utf-8") as f:
                json.dump(entities, f, ensure_ascii=False, separators=(",", ":"))

            # relations.json
            relations = _downgrade_relations(relations, removed_ids)
            with open(relations_path, "w", encoding="utf-8") as f:
                json.dump(relations, f, ensure_ascii=False, separators=(",", ":"))

            # deltas.json
            deltas_path = os.path.join(bld_dir, "deltas.json")
            if os.path.exists(deltas_path):
                with open(deltas_path, encoding="utf-8") as f:
                    deltas = json.load(f)
                deltas = _downgrade_deltas(deltas, removed_ids)
                with open(deltas_path, "w", encoding="utf-8") as f:
                    json.dump(deltas, f, ensure_ascii=False, separators=(",", ":"))

        # Inpakken
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(extract_dir):
                for fname in files:
                    full = os.path.join(root, fname)
                    arcname = os.path.relpath(full, extract_dir).replace("\\", "/")
                    zf.write(full, arcname)
        return buf.getvalue()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
