import logging

import pandas as pd
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)


def encode_dataset(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    # Encoding categorico, misma logica que prueba2.encode_categorical pero
    # parametrizado por dataset (bloque 'encoding' de params):
    #   - binary_cols  -> LabelEncoder (0/1); solo dos categorias, sin trampa dummy.
    #   - ordinal_maps -> map explicito {categoria: entero} que preserva el orden.
    #   - nominal_cols -> One-Hot (drop_first=False) para no perder categorias en
    #                     modelos de arbol; los lineales con L2 manejan colinealidad.
    # Resultado totalmente numerico, listo para modelar. SEQN sigue en el indice.
    df = df.copy()
    enc = params.get("encoding") or {}

    for col in enc.get("binary_cols") or []:
        if col in df.columns:
            df[col] = LabelEncoder().fit_transform(df[col].astype(str))

    for col, mapping in (enc.get("ordinal_maps") or {}).items():
        if col in df.columns:
            df[col] = df[col].map(mapping)

    nominal = [c for c in (enc.get("nominal_cols") or []) if c in df.columns]
    if nominal:
        df = pd.get_dummies(df, columns=nominal, drop_first=False)

    # sklearn no acepta columnas bool -> a int (0/1)
    bool_cols = df.select_dtypes(include="bool").columns
    df[bool_cols] = df[bool_cols].astype(int)

    logger.info("Encoding aplicado — shape final %s", df.shape)
    return df
