import logging

import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

logger = logging.getLogger(__name__)

_SCALERS = {
    "standard": StandardScaler,  # media=0, std=1 — distribuciones aprox. normales
    "robust": RobustScaler,      # mediana+IQR — cuando hay outliers (>5%)
    "minmax": MinMaxScaler,      # rango [0,1]
}


def impute_dataset(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    # Escalado + imputacion KNN, mismo orden que prueba2.data_transformation:
    # se escala ANTES de imputar para que las distancias euclideas del KNN sean
    # comparables entre variables de distinto rango. Los escaladores de sklearn
    # ignoran los NaN en fit y los conservan en transform, asi que el orden
    # escalar->imputar es valido. Las categoricas (texto) se dejan intactas para
    # el pipeline de encoding posterior.
    df = df.copy()

    cat_cols = [c for c in (params.get("categorical_cols_impute") or []) if c in df.columns]
    num_cols = [c for c in df.columns if c not in cat_cols]

    scaler_type = params.get("scaler_type", "standard")
    scaler = _SCALERS.get(scaler_type, StandardScaler)()
    df[num_cols] = scaler.fit_transform(df[num_cols])
    logger.info("Escalado '%s' aplicado a %d numericas", scaler_type, len(num_cols))

    k = params.get("knn_neighbors", 5)
    cols_with_nulls = [c for c in num_cols if df[c].isnull().any()]
    if cols_with_nulls:
        imputer = KNNImputer(n_neighbors=k)
        df[num_cols] = imputer.fit_transform(df[num_cols])
        logger.info("KNN (k=%d) imputo nulos en: %s", k, cols_with_nulls)
    else:
        logger.info("Sin nulos numericos — imputacion omitida")

    return df
