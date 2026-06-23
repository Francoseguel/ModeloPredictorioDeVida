"""Exporta un bundle de inferencia para el modelo MASTER (edad biologica / PhenoAge).

El pipeline de transformacion (data_transformation.transform_train_test) ajusta el
scaler / KNNImputer / encoders en memoria y solo persiste los parquets transformados.
Para servir el modelo en produccion necesitamos esos transformadores. Aqui los
RE-AJUSTAMOS sobre exactamente los mismos datos de entrenamiento (master_X_train_raw),
reproduciendo paso a paso transform_train_test, y los guardamos junto con:

  - prototipo: fila "paciente medio" (mediana num / moda cat) para rellenar las
    ~80 features que un paciente del front no aporta.
  - final_columns: orden EXACTO de las 112 columnas que vio el modelo.
  - el propio modelo elegido.

Uso (desde nhanes/):  .venv/Scripts/python.exe export_inference_bundle.py
Salida: models/inference/master_bundle.joblib
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.impute import KNNImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler

ROOT = Path(__file__).parent
RAW = ROOT / "data/06_model_input/master_X_train_raw.parquet"
FINAL = ROOT / "data/06_model_input/master_X_train.parquet"
PARAMS = ROOT / "conf/base/parameters.yml"
MODELS = ROOT / "models/trained_models"
OUT = ROOT / "models/inference/master_bundle.joblib"

# Modelo a servir. Ridge tuneado: R2 ~0.634 (a 0.007 del mejor, SVR) pero LINEAL,
# mucho mas estable cuando la mayoria de features van imputadas con la mediana
# (un paciente del front aporta ~14 de 94) e interpretable. Cambia el nombre del
# archivo si prefieres otro (p.ej. master_svr_reg_tuned.joblib).
MODEL_FILE = "master_ridge_reg_tuned.joblib"


def main() -> None:
    Xraw = pd.read_parquet(RAW)
    Xfin = pd.read_parquet(FINAL)
    params = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))["master"]
    enc = params.get("encoding") or {}

    cat_cols = [c for c in (params.get("categorical_cols_impute") or []) if c in Xraw.columns]
    num_cols = [c for c in Xraw.columns if c not in cat_cols]

    # --- Reproduce transform_train_test (FIT en train) -----------------------
    Xtr = Xraw.copy()

    scaler = StandardScaler()
    Xtr[num_cols] = scaler.fit_transform(Xtr[num_cols])

    imputer = None
    if Xtr[num_cols].isnull().any().any():
        imputer = KNNImputer(n_neighbors=params.get("knn_neighbors", 5))
        Xtr[num_cols] = imputer.fit_transform(Xtr[num_cols])

    binary_maps = {}
    for col in enc.get("binary_cols") or []:
        if col in Xtr.columns:
            le = LabelEncoder().fit(Xtr[col].astype(str))
            binary_maps[col] = {c: i for i, c in enumerate(le.classes_)}

    nominal = [c for c in (enc.get("nominal_cols") or []) if c in Xraw.columns]

    # --- Prototipo "paciente medio" (sobre features RAW, antes de transformar) -
    proto = {}
    for c in num_cols:
        proto[c] = float(Xraw[c].median())
    for c in cat_cols:
        proto[c] = str(Xraw[c].mode(dropna=True).iloc[0])

    bundle = {
        "scaler": scaler,
        "imputer": imputer,
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "binary_maps": binary_maps,          # {col: {categoria: int}}
        "ordinal_maps": enc.get("ordinal_maps") or {},
        "nominal_cols": nominal,
        "prototype": proto,                  # fila raw por defecto
        "final_columns": list(Xfin.columns), # 112 cols en orden
        "model_file": MODEL_FILE,
        "model": joblib.load(MODELS / MODEL_FILE),  # modelo embebido (1 solo archivo)
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, OUT)
    print(f"bundle -> {OUT}  ({len(num_cols)} num + {len(cat_cols)} cat -> {len(Xfin.columns)} cols finales)")

    # --- Validacion: transformar X_test crudo con el bundle y comparar R2 -----
    _validate(bundle)


def transformar(bundle: dict, raw_df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el preprocesamiento del bundle a un DataFrame de features RAW."""
    X = raw_df.copy()
    num, cat = bundle["num_cols"], bundle["cat_cols"]
    X[num] = bundle["scaler"].transform(X[num])
    if bundle["imputer"] is not None:
        X[num] = bundle["imputer"].transform(X[num])
    for col, m in bundle["binary_maps"].items():
        if col in X.columns:
            X[col] = X[col].astype(str).map(m).fillna(-1).astype(int)
    for col, m in bundle["ordinal_maps"].items():
        if col in X.columns:
            X[col] = X[col].map(m)
    if bundle["nominal_cols"]:
        X = pd.get_dummies(X, columns=bundle["nominal_cols"], drop_first=False)
    bcols = X.select_dtypes(include="bool").columns
    X[bcols] = X[bcols].astype(int)
    return X.reindex(columns=bundle["final_columns"], fill_value=0)


def _validate(bundle: dict) -> None:
    from sklearn.metrics import r2_score, mean_absolute_error

    Xte_raw = pd.read_parquet(ROOT / "data/06_model_input/master_X_test_raw.parquet")
    yte = pd.read_parquet(ROOT / "data/06_model_input/master_y_test_reg.parquet").iloc[:, 0]
    model = joblib.load(MODELS / bundle["model_file"])

    Xte = transformar(bundle, Xte_raw)
    common = Xte.index.intersection(yte.index)
    pred = model.predict(Xte.loc[common])
    print(f"validacion {bundle['model_file']}: R2={r2_score(yte.loc[common], pred):.4f} "
          f"MAE={mean_absolute_error(yte.loc[common], pred):.4f} (debe coincidir con el reporte)")


if __name__ == "__main__":
    main()
