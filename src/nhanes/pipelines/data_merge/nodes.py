import logging

import pandas as pd

logger = logging.getLogger(__name__)


def merge_master(
    exam: pd.DataFrame,
    lab: pd.DataFrame,
    quest: pd.DataFrame,
    diet: pd.DataFrame,
    demo: pd.DataFrame,
    lab_target_raw: pd.DataFrame,
) -> tuple:
    # Une los 5 bloques limpios (post-cleaning, pre-transform: con NaN en numericas
    # y 'Unknown' en categoricas) en UNA tabla maestra por SEQN. Cada columna se
    # prefija con su bloque (exam_/lab_/quest_/diet_/demo_) para evitar colisiones.
    #
    # La edad cronologica (demo['edad']) se EXCLUYE de las features: PhenoAge ~ edad
    # + residuo, asi que darla al modelo haria trivial el target. La edad se usa solo
    # para construir el target (en create_target, desde demo_intermediate).
    #
    # El target_raw maestro = los 9 biomarcadores del PhenoAge (de lab_target_raw),
    # alineados al indice de la tabla maestra.
    demo_feat = demo.drop(columns=["edad"], errors="ignore")
    blocks = {"exam": exam, "lab": lab, "quest": quest, "diet": diet, "demo": demo_feat}

    parts = [df.add_prefix(f"{name}_") for name, df in blocks.items()]
    master_clean = pd.concat(parts, axis=1, join="outer")
    master_clean.index.name = "SEQN"

    master_target_raw = lab_target_raw.reindex(master_clean.index)

    for name, df in blocks.items():
        logger.info("bloque %-6s -> %d cols", name, df.shape[1])
    logger.info("master_clean: %s (union por SEQN) | target_raw: %s",
                master_clean.shape, master_target_raw.shape)
    return master_clean, master_target_raw
