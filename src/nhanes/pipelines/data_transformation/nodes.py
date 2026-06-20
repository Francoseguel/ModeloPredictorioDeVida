import logging

import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.preprocessing import (
    LabelEncoder, MinMaxScaler, RobustScaler, StandardScaler,
)

logger = logging.getLogger(__name__)

_SCALERS = {
    "standard": StandardScaler,
    "robust": RobustScaler,
    "minmax": MinMaxScaler,
}


def transform_train_test(X_train: pd.DataFrame, X_test: pd.DataFrame, params: dict) -> tuple:
    # Escalado + imputacion KNN + encoding, TODO ajustado SOLO con train y aplicado
    # a test (evita data leakage: el test no influye en medias/escala/imputacion ni
    # en las categorias del encoding). Mismas etapas que antes hacian
    # data_imputation + data_encoding, pero fit en train / transform en test.
    Xtr, Xte = X_train.copy(), X_test.copy()
    enc = params.get("encoding") or {}

    cat_cols = [c for c in (params.get("categorical_cols_impute") or []) if c in Xtr.columns]
    num_cols = [c for c in Xtr.columns if c not in cat_cols]

    # 1. Escalado (fit train -> transform train y test)
    scaler = _SCALERS.get(params.get("scaler_type", "standard"), StandardScaler)()
    Xtr[num_cols] = scaler.fit_transform(Xtr[num_cols])
    Xte[num_cols] = scaler.transform(Xte[num_cols])

    # 2. Imputacion KNN sobre datos ya escalados (fit train -> transform test)
    k = params.get("knn_neighbors", 5)
    if Xtr[num_cols].isnull().any().any() or Xte[num_cols].isnull().any().any():
        imputer = KNNImputer(n_neighbors=k)
        Xtr[num_cols] = imputer.fit_transform(Xtr[num_cols])
        Xte[num_cols] = pd.DataFrame(
            imputer.transform(Xte[num_cols]), index=Xte.index, columns=num_cols
        )
        logger.info("KNN (k=%d) ajustado en train, aplicado a test", k)

    # 3a. Encoding binario (LabelEncoder fit en train; categorias no vistas -> -1)
    for col in enc.get("binary_cols") or []:
        if col in Xtr.columns:
            le = LabelEncoder().fit(Xtr[col].astype(str))
            mapping = {c: i for i, c in enumerate(le.classes_)}
            Xtr[col] = Xtr[col].astype(str).map(mapping).astype(int)
            Xte[col] = Xte[col].astype(str).map(mapping).fillna(-1).astype(int)

    # 3b. Encoding ordinal (mapa explicito)
    for col, m in (enc.get("ordinal_maps") or {}).items():
        if col in Xtr.columns:
            Xtr[col] = Xtr[col].map(m)
            Xte[col] = Xte[col].map(m)

    # 3c. One-Hot nominal; las columnas de test se alinean a las de train
    nominal = [c for c in (enc.get("nominal_cols") or []) if c in Xtr.columns]
    if nominal:
        Xtr = pd.get_dummies(Xtr, columns=nominal, drop_first=False)
        Xte = pd.get_dummies(Xte, columns=nominal, drop_first=False)
        Xte = Xte.reindex(columns=Xtr.columns, fill_value=0)

    # bool -> int (sklearn no acepta bool)
    for X in (Xtr, Xte):
        bcols = X.select_dtypes(include="bool").columns
        X[bcols] = X[bcols].astype(int)

    logger.info("transform -> X_train %s | X_test %s (0 nulos: %s)",
                Xtr.shape, Xte.shape,
                int(Xtr.isnull().sum().sum()) == 0 and int(Xte.isnull().sum().sum()) == 0)
    return Xtr, Xte
