from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict

app = FastAPI(
    title="API Predictiva de Longevidad - NHANES",
    description="Backend para la plataforma médica y de pacientes."
)

# --- CONFIGURACIÓN DE CORS ---
# Esto permite que tu frontend en Next.js (localhost:3000) se comunique con esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Origen de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DatosPaciente(BaseModel):
    edad: int
    sexo: str
    imc: float
    es_fumador: bool
    presion_sistolica: int
    colesterol_total: float

class ResultadoPrediccion(BaseModel):
    esperanza_vida_estimada: float
    impacto_variables: Dict[str, float]
    recomendacion_principal: str

@app.post("/api/predict", response_model=ResultadoPrediccion)
def predecir_longevidad(datos: DatosPaciente):
    # MOCK: Simulamos la respuesta
    return ResultadoPrediccion(
        esperanza_vida_estimada=82.5,
        impacto_variables={
            "es_fumador": -4.2 if datos.es_fumador else 0.0,
            "presion_sistolica": -1.5 if datos.presion_sistolica > 120 else 0.5,
            "colesterol_total": -0.8 if datos.colesterol_total > 200 else 0.2,
            "imc": -1.0 if datos.imc > 25 else 1.5
        },
        recomendacion_principal="Mantener estos niveles es clave para su longevidad." if not datos.es_fumador else "Dejar de fumar tendría el mayor impacto positivo en su expectativa de vida."
    )