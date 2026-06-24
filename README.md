# 🧬 ModeloPredictorioDeVida

## 📌 Descripción General
ModeloPredictorioDeVida es una plataforma web médica de doble interfaz diseñada para calcular, visualizar y gestionar predicciones de esperanza de vida. Impulsada por un modelo de Machine Learning entrenado con el dataset **NHANES** (National Health and Nutrition Examination Survey), la aplicación traduce datos biométricos y de estilo de vida en información clínica accionable.

El proyecto está construido con un enfoque en **Alta Conversión (CRO)** para la captura de datos de pacientes y **Explicabilidad de IA (XAI)** para el análisis médico.

## ✨ Características Principales

* **🖥️ Vista de Paciente (Orientada a Conversión):**
  * Flujo de *onboarding* paso a paso, diseñado para reducir la fricción en la entrada de datos sensibles.
  * Dashboard de resultados empático que presenta la esperanza de vida junto con recomendaciones de salud personalizadas y accionables.
* **🩺 Vista Médica (Clinical Dashboard):**
  * Panel de control seguro para la gestión de la cartera de pacientes y evaluación de riesgos.
  * Transparencia del modelo predictivo: visualización del impacto de cada variable clínica (ej. presión arterial, colesterol, tabaquismo) en el pronóstico final del paciente para facilitar la comunicación médico-paciente.
* **🧠 Motor Predictivo NHANES:**
  * Algoritmo de Machine Learning (ej. modelo de supervivencia o regresión) que evalúa el riesgo y la longevidad basándose en una de las bases de datos de salud pública más completas de EE. UU.

## 🛠️ Stack Tecnológico Sugerido

* **Frontend:** Next.js (React), Tailwind CSS.
* **Backend:** Python, FastAPI (para inferencia del modelo y API REST).
* **Machine Learning:** Scikit-learn / XGBoost, Pandas.

## ⚠️ Aviso Legal y Médico
**IMPORTANTE:** Este software y su modelo predictivo asociado están desarrollados con fines experimentales, educativos y de investigación. Las predicciones generadas **no constituyen consejo médico, diagnóstico ni pronóstico profesional**. La herramienta está diseñada como un soporte analítico y las decisiones clínicas siempre deben ser tomadas por un profesional de la salud cualificado.
