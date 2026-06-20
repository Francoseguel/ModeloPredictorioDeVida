import logging

import pandas as pd

logger = logging.getLogger(__name__)


def clean_dataset(df: pd.DataFrame, params: dict) -> tuple:
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
