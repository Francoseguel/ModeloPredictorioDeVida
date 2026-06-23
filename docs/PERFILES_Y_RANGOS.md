# Vista del doctor — rangos clínicos y perfiles de ejemplo

Esta guía documenta los parámetros del formulario del doctor (`/doctor`), su rango
clínico válido y dos perfiles de ejemplo (salud buena / salud mala) que se pueden
cargar con los botones del propio formulario para ver qué valores rellenar.

> El modelo objetivo es la **edad biológica (PhenoAge)** sobre cohorte **40+**.
> Cada parámetro mapea a una columna del modelo `master`. Lo que no se rellena se
> imputa con la mediana poblacional. Unidades = unidades NHANES.

## Cómo usar los ejemplos
En `/doctor`, arriba del formulario:
- **🟢 Salud buena** — rellena un perfil sano (referencia).
- **🔴 Salud mala** — rellena un perfil con comorbilidad y biomarcadores alterados.
- **Vaciar** — limpia todos los campos.

Tras cargar un ejemplo puedes editar cualquier valor y pulsar *Calcular*.

## Rangos válidos y valores de ejemplo

Si introduces un valor fuera del rango, el formulario lo rechaza (evita predicciones
absurdas por errores de unidad/escala).

| Parámetro | Unidad | Rango válido | 🟢 Buena | 🔴 Mala |
|---|---|---|---|---|
| Edad | años | 40–120 | 55 | 60 |
| Sexo | — | — | Hombre | Hombre |
| Nivel educativo | 1–5 | 1–5 | 4 | 2 |
| Ratio ingreso/pobreza (PIR) | 0–5 | 0–5 | 3.5 | 1.2 |
| **Antropometría** | | | | |
| IMC | kg/m² | 12–70 | 23 | 34 |
| Cintura | cm | 40–200 | 88 | 118 |
| Altura | cm | 100–230 | 175 | 172 |
| Circ. brazo | cm | 15–60 | 30 | 38 |
| Pulso | lpm | 30–200 | 64 | 88 |
| **Panel de sangre** | | | | |
| HbA1c | % | 3–20 | 5.2 | 8.2 |
| HDL | mg/dL | 10–150 | 65 | 32 |
| Colesterol total | mg/dL | 50–500 | 170 | 250 |
| Triglicéridos | mg/dL | 20–2000 | 90 | 320 |
| ALT | U/L | 1–2000 | 22 | 55 |
| AST | U/L | 1–2000 | 22 | 60 |
| BUN (urea) | mg/dL | 1–200 | 14 | 28 |
| Ácido úrico | mg/dL | 0.5–20 | 5.0 | 8.5 |
| Calcio | mg/dL | 4–15 | 9.5 | 9.8 |
| Globulina | g/dL | 1–7 | 2.8 | 3.6 |
| Bilirrubina total | mg/dL | 0.1–30 | 0.7 | 1.0 |
| LDH | U/L | 50–3000 | 160 | 280 |
| Hierro | µg/dL | 5–400 | 95 | 70 |
| Vitamina D (25-OH) | nmol/L | 5–250 | 75 | 30 |
| Hemoglobina | g/dL | 3–25 | 14.8 | 13.0 |
| Plaquetas | 1000/µL | 10–1000 | 250 | 200 |
| VPM (MPV) | fL | 5–20 | 9 | 11.5 |
| Neutrófilos | % | 0–100 | 55 | 70 |
| Linfocitos | % | 0–100 | 33 | 18 |
| Monocitos | % | 0–100 | 7 | 9 |
| **Comorbilidades** (sí/no) | | | | |
| Diabetes | — | — | No | Sí |
| Diabetes con insulina | — | — | No | Sí |
| Hipertensión dx | — | — | No | Sí |
| Medicación para presión | — | — | No | Sí |
| Colesterol alto dx | — | — | No | Sí |
| Medicación colesterol | — | — | No | Sí |
| Enf. cardiovascular | — | — | No | Sí |
| Cáncer | — | — | No | No |
| Artritis | — | — | No | Sí |
| Enf. renal | — | — | No | No |
| Nº medicamentos | conteo | 0–40 | 0 | 7 |
| PHQ-9 (depresión) | 0–27 | 0–27 | 1 | 12 |
| Nº discapacidades | conteo | 0–20 | 0 | 2 |
| Cambio de peso 1 año | lb | -200–200 | 0 | -12 |
| **Estilo de vida** | | | | |
| Tabaquismo | — | — | Nunca | Activo |
| Activo (OMS) | sí/no | — | Sí | No |
| Frec. alcohol | 0–7 | 0–7 | 1 | 5 |
| Tragos/día | conteo | 0–50 | 1 | 4 |
| MET-min/semana | min | 0–20000 | 1500 | 100 |
| Sedentarismo | min/día | 0–1440 | 300 | 600 |
| Horas de sueño | horas | 2–14 | 7.5 | 5.5 |

## Features derivadas (calculadas automáticamente al enviar)
No se introducen a mano; se computan a partir de los campos anteriores:

- **no-HDL** = Colesterol total − HDL
- **AST/ALT** = AST ÷ ALT
- **NLR** (neutrófilos/linfocitos) = Neutrófilos % ÷ Linfocitos %
- **cintura/talla** = Cintura ÷ Altura
- **polifarmacia** = sí, si Nº medicamentos ≥ 5
- **depresión (flag)** = sí, si PHQ-9 ≥ 10
- **categoría de sueño** = corto (<6 h) / normal (6–9 h) / largo (>9 h)
- **conteo de comorbilidad** = nº de enfermedades marcadas (diabetes, hipertensión,
  ECV, cáncer, artritis, enf. renal)

## Referencia clínica: ¿qué valor indica buena o mala salud?

Esta guía es la que aparece **debajo de cada campo en el formulario** del doctor.
🟢 = saludable/favorable · 🔴 = alterado/peor salud.

| Parámetro | 🟢 Buena salud | 🔴 Mala salud |
|---|---|---|
| IMC | 18.5–24.9 | ≥30 (obesidad); <18.5 bajo peso |
| Cintura | H <94 / M <80 cm | H ≥102 / M ≥88 cm |
| Circ. brazo | ~26–35 cm | muy bajo = desnutrición/sarcopenia |
| Pulso reposo | 60–80 lpm | >100 lpm |
| HbA1c | <5.7 % | ≥6.5 % (diabetes); 5.7–6.4 prediabetes |
| HDL | ≥60 mg/dL | <40 mg/dL |
| Colesterol total | <200 mg/dL | ≥240 mg/dL |
| Triglicéridos | <150 mg/dL | ≥200 mg/dL |
| ALT | 7–56 U/L | elevado = daño hepático |
| AST | 10–40 U/L | elevado = daño hepático/muscular |
| BUN (urea) | 7–20 mg/dL | alto = función renal alterada |
| Ácido úrico | 3.5–7.2 mg/dL | alto = gota/riesgo metabólico |
| Calcio | 8.5–10.2 mg/dL | fuera de rango |
| Globulina | 2.0–3.5 g/dL | alto = inflamación crónica |
| Bilirrubina total | 0.1–1.2 mg/dL | elevada |
| LDH | 140–280 U/L | alto = daño tisular |
| Hierro | 60–170 µg/dL | bajo = anemia ferropénica |
| Vitamina D | ≥50 nmol/L | <30 nmol/L (deficiencia) |
| Hemoglobina | H 13.5–17.5 / M 12–15.5 g/dL | bajo = anemia |
| Plaquetas | 150–400 ×1000/µL | fuera de rango |
| VPM (MPV) | 7.5–11.5 fL | elevado |
| Neutrófilos | 40–70 % | muy alto (con linfocitos bajos = NLR alto) |
| Linfocitos | 20–40 % | bajo = peor pronóstico |
| Monocitos | 2–8 % | elevado |
| Nº medicamentos | 0–2 | ≥5 (polifarmacia) |
| PHQ-9 | 0–4 (mínimo) | ≥10 (depresión) |
| Cambio de peso 1 año | estable | pérdida involuntaria marcada (fragilidad) |
| Frec. alcohol (0–7) | 0–1 | ≥5 |
| Tragos/día | ≤1–2 | ≥4 |
| MET-min/semana | ≥600 (OMS) | <600 (sedentario) |
| Sedentarismo | bajo | >480 min/día |
| Horas de sueño | 7–9 h | <6 o >9 h |
| Tabaquismo | nunca | activo |
| Comorbilidades (diabetes, HTA, ECV…) | ninguna | presencia de varias |

> **Coherencia paciente↔médico:** si el paciente reportó mala salud (fumador,
> obeso, comorbilidades), rellena los biomarcadores hacia la columna 🔴; si reportó
> buena salud, hacia la 🟢. Así la analítica es congruente con el cuestionario.

## Resultado esperado (orientativo)
- 🟢 **Salud buena** → edad biológica ≈ por debajo o cerca del promedio (53.6),
  riesgo de mortalidad a 10 años bajo, mayor esperanza de vida.
- 🔴 **Salud mala** → edad biológica claramente por encima, mayor riesgo a 10 años,
  menor esperanza de vida.

> Las estimaciones de mortalidad/esperanza de vida son **estadísticas
> poblacionales** (tabla de vida según la edad biológica), no predicciones
> individuales.
