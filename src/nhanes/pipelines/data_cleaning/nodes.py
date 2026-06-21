import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_cohort(demo_intermediate: pd.DataFrame, params: dict) -> pd.Index:
    # Construye el indice de SEQN elegibles segun el filtro de cohorte por edad
    # (params['cohort_min_age']). Se calcula desde demo_intermediate (tiene 'edad')
    # y se aplica a TODOS los datasets en clean_dataset (union por SEQN). Si
    # cohort_min_age es null, devuelve todos los SEQN (sin filtro).
    min_age = params.get("cohort_min_age")
    if min_age is None:
        logger.info("Sin filtro de cohorte (cohort_min_age=null): %d personas", len(demo_intermediate))
        return pd.Index(demo_intermediate.index)
    elig = demo_intermediate.index[demo_intermediate["edad"] >= min_age]
    logger.info("Cohorte edad >= %s: %d de %d personas", min_age, len(elig), len(demo_intermediate))
    return pd.Index(elig)


def clean_dataset(df: pd.DataFrame, params: dict, cohort: pd.Index) -> tuple:
    # Limpieza de un componente NHANES (mismo patron que prueba2.data_cleaning,
    # generalizado a un bloque de parametros por dataset).
    #
    # Pasos:
    #   1. Elimina columnas indicadas a mano (cols_to_drop).
    #   2. Reserva las columnas target en escala original y las separa de las
    #      features (evita circularidad: el target nunca se escala ni se encodea).
    #   3. Elimina features con missingness > missing_threshold: KNN no puede
    #      imputar de forma fiable cuando casi todo es nulo (p.ej. en quest
    #      'cigarrillos_dia' es 89% nulo por ser condicional a fumadores).
    #   4. Rellena categoricas faltantes con 'Unknown' (MCAR -> categoria propia,
    #      preserva la informacion de ausencia sin sesgar hacia la moda).
    #
    # SEQN viaja en el indice, no se toca. Devuelve (features_limpias, target_raw).
    df = df.copy()

    # 0. Filtro de cohorte (edad): se aplica ANTES de todo para que missingness,
    #    target y split se calculen solo sobre la poblacion de estudio.
    n0 = len(df)
    df = df.loc[df.index.intersection(cohort)]
    logger.info("Cohorte aplicada: %d -> %d filas", n0, len(df))

    cols_to_drop = [c for c in (params.get("cols_to_drop") or []) if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        logger.info("Columnas eliminadas (manual): %s", cols_to_drop)

    # 2. Reservar target ANTES de cualquier poda por missingness
    target_cols = [c for c in (params.get("target_cols") or []) if c in df.columns]
    target_raw = df[target_cols].copy()
    feat = df.drop(columns=target_cols)
    logger.info("Target reservado (escala original): %s", target_cols)

    # 3. Poda por missingness (solo sobre features)
    thr = params.get("missing_threshold", 1.0)
    frac = feat.isnull().mean()
    high_missing = frac[frac > thr].index.tolist()
    if high_missing:
        feat = feat.drop(columns=high_missing)
        logger.info("Eliminadas por missing > %.0f%%: %s", thr * 100, high_missing)

    # 4. Imputacion categorica -> 'Unknown'
    cat_cols = [c for c in (params.get("categorical_cols_impute") or []) if c in feat.columns]
    for c in cat_cols:
        feat[c] = feat[c].astype("object").fillna("Unknown")
    if cat_cols:
        logger.info("Categoricas rellenadas con 'Unknown': %s", cat_cols)

    logger.info("clean -> features %s | target_raw %s", feat.shape, target_raw.shape)
    return feat, target_raw
