import math
from pathlib import Path
from typing import Dict, Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Carga del modelo MASTER entrenado (edad biologica / PhenoAge) ------------
# Bundle generado por nhanes/export_inference_bundle.py: trae los transformadores
# (scaler/KNNImputer/encoders) reajustados sobre el train, el prototipo "paciente
# medio", el orden de las 112 columnas finales y el modelo embebido (Ridge tuneado,
# R2=0.634, MAE=7.05 años). Si no se puede cargar (faltan sklearn/joblib/pandas o
# el archivo), el endpoint de paciente cae a una heuristica transparente.
_BUNDLE = None
_BUNDLE_ERROR = None
try:
    import joblib
    import pandas as pd

    _BUNDLE = joblib.load(Path(__file__).parent / "model" / "master_bundle.joblib")
except Exception as exc:  # pragma: no cover - depende del entorno
    _BUNDLE_ERROR = str(exc)


def _transformar(raw_df):
    """Aplica el preprocesamiento del bundle a features RAW (igual que el pipeline)."""
    b = _BUNDLE
    X = raw_df.copy()
    num, cat = b["num_cols"], b["cat_cols"]
    X[num] = b["scaler"].transform(X[num])
    if b["imputer"] is not None:
        X[num] = b["imputer"].transform(X[num])
    for col, m in b["binary_maps"].items():
        if col in X.columns:
            X[col] = X[col].astype(str).map(m).fillna(-1).astype(int)
    for col, m in b["ordinal_maps"].items():
        if col in X.columns:
            X[col] = X[col].map(m)
    if b["nominal_cols"]:
        X = pd.get_dummies(X, columns=b["nominal_cols"], drop_first=False)
    bcols = X.select_dtypes(include="bool").columns
    X[bcols] = X[bcols].astype(int)
    return X.reindex(columns=b["final_columns"], fill_value=0)


def _predecir_edad_biologica(overrides: Dict[str, object]) -> float:
    """Construye la fila raw (prototipo + overrides) y devuelve la prediccion.

    El modelo es lineal: valores de entrada extremos (o en unidades equivocadas)
    generan z-scores enormes y predicciones absurdas. Se acota el resultado a un
    rango de edad biologica plausible como red de seguridad."""
    row = dict(_BUNDLE["prototype"])
    row.update(overrides)
    df = pd.DataFrame([row])[list(_BUNDLE["prototype"].keys())]
    Xf = _transformar(df)
    pred = float(_BUNDLE["model"].predict(Xf)[0])
    return min(max(pred, 18.0), 110.0)


# Edad metabolica del "paciente medio" (todas las features en su mediana/moda) =
# referencia de la poblacion 40+ contra la que se interpreta el resultado. Se
# calcula una vez y se cachea (es deterministica).
_REFERENCIA_POBLACIONAL = None
if _BUNDLE is not None:
    try:
        _REFERENCIA_POBLACIONAL = round(_predecir_edad_biologica({}), 1)
    except Exception as exc:  # pragma: no cover
        _BUNDLE_ERROR = str(exc)

app = FastAPI(
    title="API Predictiva de Longevidad - NHANES",
    description=(
        "Backend para la plataforma medica y de pacientes. "
        "El objetivo del modelo NHANES es la EDAD BIOLOGICA (PhenoAge de Levine) "
        "y el envejecimiento acelerado, NO la esperanza de vida en años."
    ),
)

# --- CONFIGURACIoN DE CORS ---
# Permite que el frontend en Next.js (localhost:3000) consuma esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# PhenoAge (Levine et al. 2018) — edad biologica a partir de 9 biomarcadores + edad
# -----------------------------------------------------------------------------
# Replica EXACTA de nhanes/src/.../data_split/nodes.py (_phenoage). Es una formula
# determinista: con los 9 biomarcadores + la edad cronologica se obtiene la edad
# fenotipica sin necesidad de un modelo entrenado. Por eso el endpoint del doctor
# devuelve un resultado real hoy mismo.
# Unidades de entrada = unidades NHANES (se convierten a las de Levine aqui).
# =============================================================================
_PHENO_INTERCEPT = -19.9067
_PHENO_GOMP = 0.0076927


def calcular_phenoage(
    edad: float,
    albumina: float,       # g/dL  -> g/L (*10)
    creatinina: float,     # mg/dL -> umol/L (*88.4017)
    glucosa_serica: float, # mg/dL -> mmol/L (*0.0555)
    crp: float,            # mg/L  -> mg/dL (/10) -> ln
    linfocitos_pct: float, # %
    mcv: float,            # fL
    rdw: float,            # %
    alp: float,            # U/L
    wbc: float,            # 1000 celulas/uL
) -> float:
    alb = albumina * 10.0
    cre = creatinina * 88.4017
    glu = glucosa_serica * 0.0555
    crp_ln = math.log(max(crp / 10.0, 1e-4))

    xb = (
        _PHENO_INTERCEPT
        + (-0.0336) * alb
        + 0.0095 * cre
        + 0.1953 * glu
        + 0.0954 * crp_ln
        + (-0.0120) * linfocitos_pct
        + 0.0268 * mcv
        + 0.3306 * rdw
        + 0.00188 * alp
        + 0.0554 * wbc
        + 0.0804 * edad
    )

    g = _PHENO_GOMP
    mort = 1.0 - math.exp(-math.exp(xb) * (math.exp(120.0 * g) - 1.0) / g)
    mort = min(max(mort, 1e-8), 1 - 1e-8)
    phenoage = 141.50225 + math.log(-0.00553 * math.log(1.0 - mort)) / 0.090165
    return phenoage


# =============================================================================
# ESQUEMAS
# =============================================================================
class ResultadoEdadBiologica(BaseModel):
    edad_cronologica: float
    edad_biologica: float
    # Paciente (modelo master): aceleracion = desviacion respecto al promedio de la
    #   poblacion 40+ (referencia_poblacional), NO respecto a la edad cronologica
    #   (el modelo no usa la edad como feature -> predice hacia la media de cohorte).
    # Doctor (PhenoAge exacto): aceleracion = edad_biologica - edad_cronologica (Levine).
    aceleracion: float
    referencia_poblacional: Optional[float] = None  # solo en el modo paciente
    clasificacion: Literal["acelerado", "normal"]
    impacto_variables: Dict[str, float]
    recomendacion_principal: str
    metodo: str  # 'modelo_master (...)' | 'phenoage_levine' | 'estimacion_estilo_vida'
    # Estimaciones de longevidad derivadas de la edad biologica (PhenoAge):
    riesgo_mortalidad_10a: Optional[float] = None       # % de fallecer en 10 años
    esperanza_vida_restante: Optional[float] = None      # años estimados restantes
    edad_fallecimiento_estimada: Optional[float] = None  # edad cronologica estimada al fallecer


# --- PACIENTE: subconjunto de features que una persona puede aportar ----------
# Nombres alineados con las features del modelo NHANES (bloques demo/exam/quest).
class DatosPaciente(BaseModel):
    edad: int = Field(ge=40, le=120)  # modelo calibrado en cohorte 40+
    sexo: Literal["masculino", "femenino"]
    imc: float = Field(ge=10, le=60)  # calculado en el front desde peso/altura
    altura: Optional[float] = Field(default=None, ge=100, le=250)  # cm (feature exam)
    cintura: Optional[float] = Field(default=None, ge=40, le=200)  # cm
    tabaquismo: Literal["nunca", "exfumador", "activo"]
    alcohol_freq_anual: float = Field(ge=0, le=7, default=0)  # escala NHANES 0-7
    activo_oms: bool = False                                  # cumple actividad fisica OMS
    horas_sueno: float = Field(ge=2, le=14, default=7)
    salud_autopercibida: int = Field(ge=1, le=5, default=3)   # 1=excelente ... 5=mala
    diabetes_flag: bool = False
    hipertension_dx: bool = False
    cvd_flag: bool = False
    cancer_flag: bool = False
    n_medicamentos: int = Field(ge=0, le=30, default=0)


# --- DOCTOR: los 9 biomarcadores del PhenoAge + edad (+ labs opcionales) -------
class DatosClinicos(BaseModel):
    edad: int = Field(ge=18, le=120)
    albumina: float = Field(gt=0, description="g/dL (ref ~3.5-5.0)")
    creatinina: float = Field(gt=0, description="mg/dL (ref ~0.6-1.3)")
    glucosa_serica: float = Field(gt=0, description="mg/dL (ref ~70-99 ayuno)")
    crp: float = Field(ge=0, description="hs-CRP mg/L (ref < 3)")
    linfocitos_pct: float = Field(gt=0, le=100, description="% (ref ~20-40)")
    mcv: float = Field(gt=0, description="fL (ref ~80-100)")
    rdw: float = Field(gt=0, description="% (ref ~11.5-14.5)")
    alp: float = Field(gt=0, description="U/L (ref ~44-147)")
    wbc: float = Field(gt=0, description="1000 celulas/uL (ref ~4-11)")


# --- DOCTOR (modelo master): features clinicas con sus nombres RAW del modelo --
# 'features' es un dict {columna_raw_master: valor}. El front envia solo lo que el
# medico rellena (p.ej. {"lab_hdl": 45, "exam_imc": 31, "quest_diabetes_flag": 1,
# "demo_sexo": "masculino"}); el resto se imputa con el prototipo poblacional.
class DatosMaster(BaseModel):
    edad: int = Field(ge=40, le=120)  # modelo calibrado en cohorte 40+
    features: Dict[str, object] = Field(default_factory=dict)


# =============================================================================
# ENDPOINTS
# =============================================================================
def _overrides_paciente(datos: "DatosPaciente") -> Dict[str, Dict[str, object]]:
    """Mapea los campos del formulario a las features RAW del modelo master,
    agrupadas por concepto (para la atribucion de impacto). salud_autopercibida
    NO se incluye: en el modelo es target, no feature."""
    grupos: Dict[str, Dict[str, object]] = {
        "sexo": {"demo_sexo": datos.sexo},
        "imc": {"exam_imc": datos.imc},
        "tabaquismo": {"quest_tabaquismo": datos.tabaquismo},
        "actividad_fisica": {"quest_activo_oms": int(datos.activo_oms)},
        "alcohol": {"quest_alcohol_freq_anual": float(datos.alcohol_freq_anual)},
        "diabetes": {"quest_diabetes_flag": int(datos.diabetes_flag)},
        "hipertension": {"quest_hipertension_dx": int(datos.hipertension_dx)},
        "enf_cardiovascular": {"quest_cvd_flag": int(datos.cvd_flag)},
        "cancer": {"quest_cancer_flag": int(datos.cancer_flag)},
        "medicamentos": {
            "quest_n_medicamentos": int(datos.n_medicamentos),
            "quest_polifarmacia_flag": int(datos.n_medicamentos >= 5),
        },
    }
    cat = "corto" if datos.horas_sueno < 6 else ("largo" if datos.horas_sueno > 9 else "normal")
    grupos["sueno"] = {"quest_horas_sueno": float(datos.horas_sueno), "quest_sueno_categoria": cat}
    if datos.altura is not None:
        grupos["altura"] = {"exam_altura": float(datos.altura)}
    if datos.cintura is not None:
        cintura_talla = datos.cintura / datos.altura if datos.altura else None
        grupos["cintura"] = {"exam_cintura": float(datos.cintura)}
        if cintura_talla is not None:
            grupos["cintura"]["exam_cintura_talla"] = float(cintura_talla)
    return grupos


# --- Estimaciones de longevidad a partir de la edad biologica -----------------
# Tabla de vida: esperanza de vida RESTANTE (años) por edad exacta, aprox. SSA 2021
# EEUU. Tupla (hombre, mujer). Se interpola linealmente entre puntos.
_LIFE_TABLE = {
    40: (38.0, 42.3), 45: (33.6, 37.7), 50: (29.3, 33.2), 55: (25.2, 28.9),
    60: (21.3, 24.7), 65: (17.6, 20.6), 70: (14.2, 16.8), 75: (11.1, 13.2),
    80: (8.3, 9.9), 85: (6.0, 7.0), 90: (4.2, 4.8), 95: (3.0, 3.3), 100: (2.2, 2.3),
}


def _esperanza_vida_restante(edad_biologica: float, sexo: Optional[str] = None) -> float:
    """Esperanza de vida restante de una persona cuya edad cronologica fuera igual
    a la edad biologica dada (interpola la tabla de vida; promedia sexos si no se da)."""
    edades = sorted(_LIFE_TABLE)
    e = min(max(edad_biologica, edades[0]), edades[-1])
    mh, mf = _LIFE_TABLE[edades[-1]]
    for i in range(len(edades) - 1):
        a, b = edades[i], edades[i + 1]
        if a <= e <= b:
            t = (e - a) / (b - a)
            mh = _LIFE_TABLE[a][0] + t * (_LIFE_TABLE[b][0] - _LIFE_TABLE[a][0])
            mf = _LIFE_TABLE[a][1] + t * (_LIFE_TABLE[b][1] - _LIFE_TABLE[a][1])
            break
    if sexo == "masculino":
        return mh
    if sexo == "femenino":
        return mf
    return (mh + mf) / 2.0


def _riesgo_mortalidad_10a(edad_biologica: float) -> float:
    """Riesgo de mortalidad a 10 años implicito en el PhenoAge (inverso exacto de
    la conversion mortalidad->edad de Levine usada en calcular_phenoage)."""
    x = math.exp(0.090165 * (edad_biologica - 141.50225)) / 0.00553
    return min(max(1.0 - math.exp(-x), 0.0), 1.0)


def _longevidad(edad_cronologica: float, edad_biologica: float, sexo: Optional[str]) -> dict:
    restante = _esperanza_vida_restante(edad_biologica, sexo)
    return {
        "riesgo_mortalidad_10a": round(_riesgo_mortalidad_10a(edad_biologica) * 100, 1),
        "esperanza_vida_restante": round(restante, 1),
        "edad_fallecimiento_estimada": round(edad_cronologica + restante, 1),
    }


def _resultado_master(edad: int, grupos: Dict[str, Dict[str, object]], max_factores: int = 12) -> ResultadoEdadBiologica:
    """Motor comun (paciente y doctor): corre el modelo master sobre el prototipo
    + overrides, calcula la desviacion respecto al promedio 40+ y la atribucion
    leave-one-out por grupo. Solo se invoca cuando _BUNDLE esta cargado."""
    overrides: Dict[str, object] = {}
    for ov in grupos.values():
        overrides.update(ov)

    pred = _predecir_edad_biologica(overrides)
    impacto = {}
    for label, ov in grupos.items():
        sin = {k: v for k, v in overrides.items() if k not in ov}
        impacto[label] = round(pred - _predecir_edad_biologica(sin), 1)

    referencia = _REFERENCIA_POBLACIONAL
    desviacion = round(pred - referencia, 1)
    impacto = {k: v for k, v in impacto.items() if abs(v) >= 0.05}
    # Solo los factores de mayor magnitud (para el grafico de explicabilidad).
    impacto = dict(sorted(impacto.items(), key=lambda kv: abs(kv[1]), reverse=True)[:max_factores])
    factor_top = max(impacto, key=impacto.get) if impacto else None

    if desviacion > 0 and factor_top and impacto[factor_top] > 0:
        reco = f"Edad metabolica por encima del promedio; el factor que mas la eleva es '{factor_top}'."
    elif desviacion <= 0:
        reco = "Edad metabolica por debajo del promedio de la poblacion 40+: perfil favorable."
    else:
        reco = "Edad metabolica por encima del promedio de la poblacion 40+."

    edad_biologica = round(pred, 1)
    sexo = overrides.get("demo_sexo")
    longevidad = _longevidad(edad, edad_biologica, sexo if isinstance(sexo, str) else None)

    return ResultadoEdadBiologica(
        edad_cronologica=edad,
        edad_biologica=edad_biologica,
        aceleracion=desviacion,
        referencia_poblacional=referencia,
        clasificacion="acelerado" if desviacion > 0 else "normal",
        impacto_variables=impacto,
        recomendacion_principal=reco,
        metodo=f"modelo_master ({_BUNDLE['model_file']})",
        **longevidad,
    )


@app.post("/api/predict", response_model=ResultadoEdadBiologica)
def predecir_paciente(datos: DatosPaciente):
    """Edad biologica para PACIENTE usando el modelo MASTER entrenado.

    El formulario aporta ~14 de las 94 features; el resto se rellenan con el
    'paciente medio' (mediana/moda del train) del bundle. Si el bundle no carga,
    usa la heuristica de abajo.
    """
    if _BUNDLE is not None:
        return _resultado_master(datos.edad, _overrides_paciente(datos))

    # ----- FALLBACK heuristico (solo si el bundle del modelo no carga) --------
    impacto: Dict[str, float] = {}
    aceleracion = 0.0

    if datos.tabaquismo == "activo":
        impacto["tabaquismo"] = 4.0
    elif datos.tabaquismo == "exfumador":
        impacto["tabaquismo"] = 1.5
    else:
        impacto["tabaquismo"] = -0.5

    impacto["imc"] = 2.0 if datos.imc >= 30 else (1.0 if datos.imc >= 25 else (-0.5 if datos.imc >= 18.5 else 1.5))

    if datos.cintura is not None:
        umbral = 102 if datos.sexo == "masculino" else 88
        impacto["cintura"] = 1.5 if datos.cintura >= umbral else -0.3

    impacto["actividad_fisica"] = -1.5 if datos.activo_oms else 1.0
    impacto["sueno"] = -0.3 if 7 <= datos.horas_sueno <= 9 else 1.0
    impacto["alcohol"] = 1.0 if datos.alcohol_freq_anual >= 5 else 0.0
    impacto["salud_autopercibida"] = (datos.salud_autopercibida - 3) * 1.2
    impacto["diabetes"] = 2.5 if datos.diabetes_flag else 0.0
    impacto["hipertension"] = 1.5 if datos.hipertension_dx else 0.0
    impacto["enf_cardiovascular"] = 3.0 if datos.cvd_flag else 0.0
    impacto["cancer"] = 2.5 if datos.cancer_flag else 0.0
    impacto["polifarmacia"] = 1.5 if datos.n_medicamentos >= 5 else 0.0

    aceleracion = sum(impacto.values())
    edad_biologica = round(datos.edad + aceleracion, 1)

    factor_top = max(impacto, key=impacto.get)
    if impacto[factor_top] > 0:
        reco = f"El factor de mayor impacto negativo es '{factor_top}'. Trabajar en el reduciria su edad biologica."
    else:
        reco = "Sus habitos juegan a favor: mantengalos para conservar una edad biologica menor a la cronologica."

    return ResultadoEdadBiologica(
        edad_cronologica=datos.edad,
        edad_biologica=edad_biologica,
        aceleracion=round(aceleracion, 1),
        clasificacion="acelerado" if aceleracion > 0 else "normal",
        impacto_variables={k: round(v, 1) for k, v in impacto.items()},
        recomendacion_principal=reco,
        metodo="estimacion_estilo_vida",
    )


@app.post("/api/predict/clinico", response_model=ResultadoEdadBiologica)
def predecir_clinico(datos: DatosClinicos):
    """Edad biologica EXACTA para el DOCTOR via PhenoAge de Levine (determinista)."""
    edad_biologica = round(
        calcular_phenoage(
            edad=datos.edad,
            albumina=datos.albumina,
            creatinina=datos.creatinina,
            glucosa_serica=datos.glucosa_serica,
            crp=datos.crp,
            linfocitos_pct=datos.linfocitos_pct,
            mcv=datos.mcv,
            rdw=datos.rdw,
            alp=datos.alp,
            wbc=datos.wbc,
        ),
        1,
    )
    aceleracion = round(edad_biologica - datos.edad, 1)

    # Contribucion aproximada de cada biomarcador (coef * valor convertido), util
    # como explicabilidad clinica de que empuja la edad fenotipica arriba/abajo.
    impacto = {
        "albumina": round(-0.0336 * datos.albumina * 10.0, 2),
        "creatinina": round(0.0095 * datos.creatinina * 88.4017, 2),
        "glucosa_serica": round(0.1953 * datos.glucosa_serica * 0.0555, 2),
        "crp": round(0.0954 * math.log(max(datos.crp / 10.0, 1e-4)), 2),
        "linfocitos_pct": round(-0.0120 * datos.linfocitos_pct, 2),
        "mcv": round(0.0268 * datos.mcv, 2),
        "rdw": round(0.3306 * datos.rdw, 2),
        "alp": round(0.00188 * datos.alp, 2),
        "wbc": round(0.0554 * datos.wbc, 2),
    }

    if aceleracion > 0:
        reco = (
            f"Envejecimiento acelerado (+{aceleracion} años sobre la edad cronologica). "
            "Revisar los biomarcadores con mayor contribucion al alza."
        )
    else:
        reco = f"Edad biologica por debajo de la cronologica ({aceleracion} años). Perfil favorable."

    return ResultadoEdadBiologica(
        edad_cronologica=datos.edad,
        edad_biologica=edad_biologica,
        aceleracion=aceleracion,
        clasificacion="acelerado" if aceleracion > 0 else "normal",
        impacto_variables=impacto,
        recomendacion_principal=reco,
        metodo="phenoage_levine",
        **_longevidad(datos.edad, edad_biologica, None),
    )


@app.post("/api/predict/master", response_model=ResultadoEdadBiologica)
def predecir_master(datos: DatosMaster):
    """Edad biologica (modelo MASTER) para el DOCTOR con MUCHAS features clinicas.

    Recibe 'features' con nombres de columna RAW del modelo (exam_/lab_/quest_/
    demo_). Cada feature valida se trata como su propio grupo para la atribucion
    leave-one-out. Lo no enviado se imputa con el prototipo poblacional 40+.
    """
    if _BUNDLE is None:
        raise HTTPException(status_code=503, detail=f"Modelo no disponible: {_BUNDLE_ERROR}")

    proto = _BUNDLE["prototype"]
    grupos: Dict[str, Dict[str, object]] = {}
    ignoradas = []
    for col, val in (datos.features or {}).items():
        if val is None or val == "":
            continue
        if col not in proto:
            ignoradas.append(col)
            continue
        # Numericas -> float; categoricas (str en el prototipo) -> str
        grupos[col] = {col: (str(val) if isinstance(proto[col], str) else float(val))}

    if ignoradas:
        import logging
        logging.getLogger("uvicorn.error").warning("features ignoradas (no son del modelo): %s", ignoradas)

    return _resultado_master(datos.edad, grupos, max_factores=15)
