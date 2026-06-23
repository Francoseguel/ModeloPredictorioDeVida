"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { FlaskConical, CheckCircle2, ShieldAlert, User, Activity, HeartPulse, UserCheck, X } from "lucide-react";

// ---------------------------------------------------------------------------
// Formulario clinico del DOCTOR -> modelo MASTER entrenado.
// Cada campo mapea a una columna RAW del modelo (exam_/lab_/quest_/demo_). Lo que
// no se rellene se imputa con el prototipo poblacional 40+. Algunos features
// derivados (no-HDL, NLR, AST/ALT, cintura/talla...) se calculan al enviar a
// partir de campos auxiliares (prefijo h_, no se envian directamente).
// ---------------------------------------------------------------------------

type Field =
  | { key: string; label: string; unit?: string; ref?: string; type: "number" }
  | { key: string; label: string; type: "select"; options: { v: string; t: string }[] }
  | { key: string; label: string; type: "check" };

type Section = { title: string; icon: React.ReactNode; cols: string; fields: Field[] };

const SECCIONES: Section[] = [
  {
    title: "Datos demográficos",
    icon: <User className="text-blue-500" size={20} />,
    cols: "sm:grid-cols-3",
    fields: [
      { key: "edad", label: "Edad", unit: "años", type: "number" },
      {
        key: "demo_sexo", label: "Sexo", type: "select",
        options: [{ v: "", t: "—" }, { v: "masculino", t: "Hombre" }, { v: "femenino", t: "Mujer" }],
      },
      {
        key: "demo_raza", label: "Raza/etnia", type: "select",
        options: [
          { v: "", t: "—" },
          { v: "blanco_no_hispano", t: "Blanco no hispano" },
          { v: "negro_no_hispano", t: "Negro no hispano" },
          { v: "mexicano_americano", t: "Mexicano-americano" },
          { v: "otro_hispano", t: "Otro hispano" },
          { v: "asiatico_no_hispano", t: "Asiático no hispano" },
          { v: "otro_multirracial", t: "Otro/multirracial" },
        ],
      },
      { key: "demo_educacion", label: "Nivel educativo (1-5)", type: "number" },
      { key: "demo_pir", label: "Ratio ingreso/pobreza (0-5)", type: "number" },
    ],
  },
  {
    title: "Antropometría y signos",
    icon: <Activity className="text-blue-500" size={20} />,
    cols: "sm:grid-cols-3",
    fields: [
      { key: "exam_imc", label: "IMC", unit: "kg/m²", ref: "18.5-25", type: "number" },
      { key: "exam_cintura", label: "Cintura", unit: "cm", type: "number" },
      { key: "exam_altura", label: "Altura", unit: "cm", type: "number" },
      { key: "exam_circ_brazo", label: "Circ. brazo", unit: "cm", type: "number" },
      { key: "exam_pulso", label: "Pulso", unit: "lpm", ref: "60-100", type: "number" },
    ],
  },
  {
    title: "Panel de sangre",
    icon: <FlaskConical className="text-blue-500" size={20} />,
    cols: "sm:grid-cols-3",
    fields: [
      { key: "lab_hba1c", label: "HbA1c", unit: "%", ref: "<5.7", type: "number" },
      { key: "lab_hdl", label: "HDL", unit: "mg/dL", ref: ">40", type: "number" },
      { key: "h_col_total", label: "Colesterol total", unit: "mg/dL", ref: "<200", type: "number" },
      { key: "lab_trigliceridos", label: "Triglicéridos", unit: "mg/dL", ref: "<150", type: "number" },
      { key: "lab_alt", label: "ALT", unit: "U/L", ref: "7-56", type: "number" },
      { key: "h_ast", label: "AST", unit: "U/L", ref: "10-40", type: "number" },
      { key: "lab_bun", label: "BUN (urea)", unit: "mg/dL", ref: "7-20", type: "number" },
      { key: "lab_acido_urico", label: "Ácido úrico", unit: "mg/dL", type: "number" },
      { key: "lab_calcio", label: "Calcio", unit: "mg/dL", type: "number" },
      { key: "lab_globulina", label: "Globulina", unit: "g/dL", type: "number" },
      { key: "lab_bilirrubina_total", label: "Bilirrubina total", unit: "mg/dL", type: "number" },
      { key: "lab_ldh", label: "LDH", unit: "U/L", type: "number" },
      { key: "lab_hierro", label: "Hierro", unit: "µg/dL", type: "number" },
      { key: "lab_vitamina_d", label: "Vitamina D (25-OH)", unit: "nmol/L", type: "number" },
      { key: "lab_hemoglobina", label: "Hemoglobina", unit: "g/dL", type: "number" },
      { key: "lab_plaquetas", label: "Plaquetas", unit: "1000/µL", type: "number" },
      { key: "lab_mpv", label: "VPM (MPV)", unit: "fL", type: "number" },
      { key: "lab_neutrofilos_pct", label: "Neutrófilos", unit: "%", type: "number" },
      { key: "h_linfocitos_pct", label: "Linfocitos", unit: "%", type: "number" },
      { key: "lab_monocitos_pct", label: "Monocitos", unit: "%", type: "number" },
    ],
  },
  {
    title: "Comorbilidades e historia clínica",
    icon: <HeartPulse className="text-blue-500" size={20} />,
    cols: "sm:grid-cols-2",
    fields: [
      { key: "quest_diabetes_flag", label: "Diabetes", type: "check" },
      { key: "quest_diabetes_insulina", label: "Diabetes con insulina", type: "check" },
      { key: "quest_hipertension_dx", label: "Hipertensión dx", type: "check" },
      { key: "quest_medicacion_presion", label: "Medicación para presión", type: "check" },
      { key: "quest_colesterol_alto_dx", label: "Colesterol alto dx", type: "check" },
      { key: "quest_medicacion_colesterol", label: "Medicación colesterol", type: "check" },
      { key: "quest_cvd_flag", label: "Enf. cardiovascular", type: "check" },
      { key: "quest_cancer_flag", label: "Cáncer", type: "check" },
      { key: "quest_artritis_flag", label: "Artritis", type: "check" },
      { key: "quest_enf_renal_dx", label: "Enf. renal", type: "check" },
      { key: "quest_n_medicamentos", label: "Nº medicamentos recetados", type: "number" },
      { key: "quest_phq9_score", label: "PHQ-9 (0-27)", type: "number" },
      { key: "quest_discapacidad_count", label: "Nº discapacidades", type: "number" },
      { key: "quest_cambio_peso_1y_lb", label: "Cambio de peso 1 año (lb)", type: "number" },
    ],
  },
  {
    title: "Estilo de vida",
    icon: <Activity className="text-blue-500" size={20} />,
    cols: "sm:grid-cols-3",
    fields: [
      {
        key: "quest_tabaquismo", label: "Tabaquismo", type: "select",
        options: [{ v: "", t: "—" }, { v: "nunca", t: "Nunca" }, { v: "exfumador", t: "Exfumador" }, { v: "activo", t: "Activo" }],
      },
      {
        key: "quest_activo_oms", label: "Activo (OMS)", type: "select",
        options: [{ v: "", t: "—" }, { v: "1", t: "Sí" }, { v: "0", t: "No" }],
      },
      { key: "quest_alcohol_freq_anual", label: "Frec. alcohol (0-7)", type: "number" },
      { key: "quest_tragos_por_dia", label: "Tragos/día", type: "number" },
      { key: "quest_met_min_semana", label: "MET-min/semana", type: "number" },
      { key: "quest_sedentario_min", label: "Sedentarismo (min/día)", type: "number" },
      { key: "quest_horas_sueno", label: "Horas de sueño", type: "number" },
    ],
  },
];

// Rangos clinicos plausibles [min, max] por campo numerico. Fuera de estos valores
// el modelo (lineal) extrapola a edades absurdas, asi que se rechazan al enviar.
const RANGOS: Record<string, [number, number]> = {
  edad: [40, 120],
  demo_educacion: [1, 5],
  demo_pir: [0, 5],
  exam_imc: [12, 70],
  exam_cintura: [40, 200],
  exam_altura: [100, 230],
  exam_circ_brazo: [15, 60],
  exam_pulso: [30, 200],
  lab_hba1c: [3, 20],
  lab_hdl: [10, 150],
  h_col_total: [50, 500],
  lab_trigliceridos: [20, 2000],
  lab_alt: [1, 2000],
  h_ast: [1, 2000],
  lab_bun: [1, 200],
  lab_acido_urico: [0.5, 20],
  lab_calcio: [4, 15],
  lab_globulina: [1, 7],
  lab_bilirrubina_total: [0.1, 30],
  lab_ldh: [50, 3000],
  lab_hierro: [5, 400],
  lab_vitamina_d: [5, 250],
  lab_hemoglobina: [3, 25],
  lab_plaquetas: [10, 1000],
  lab_mpv: [5, 20],
  lab_neutrofilos_pct: [0, 100],
  h_linfocitos_pct: [0, 100],
  lab_monocitos_pct: [0, 100],
  quest_n_medicamentos: [0, 40],
  quest_phq9_score: [0, 27],
  quest_discapacidad_count: [0, 20],
  quest_cambio_peso_1y_lb: [-200, 200],
  quest_alcohol_freq_anual: [0, 7],
  quest_tragos_por_dia: [0, 50],
  quest_met_min_semana: [0, 20000],
  quest_sedentario_min: [0, 1440],
  quest_horas_sueno: [2, 14],
};

// Etiqueta por clave (para mensajes de validacion).
const LABELS: Record<string, string> = Object.fromEntries(
  SECCIONES.flatMap((s) => s.fields.map((f) => [f.key, f.label]))
);

// Referencia clinica por campo: que valor indica buena vs mala salud. Se muestra
// debajo del campo para que el medico introduzca datos coherentes con el paciente.
// (🟢 = saludable / favorable, 🔴 = alterado / peor salud)
const REFERENCIAS: Record<string, string> = {
  demo_educacion: "1 (menor) – 5 (mayor). Mayor nivel ~ mejor salud",
  demo_pir: "0 (pobreza) – 5 (mayor ingreso). Mayor ~ mejor",
  exam_imc: "🟢 18.5–24.9 · sobrepeso 25–29.9 · 🔴 obesidad ≥30",
  exam_cintura: "🟢 H <94 / M <80 · 🔴 H ≥102 / M ≥88 cm",
  exam_circ_brazo: "🔴 bajo = desnutrición/sarcopenia · normal ~26–35",
  exam_pulso: "🟢 60–80 · normal hasta 100 · 🔴 >100 lpm en reposo",
  lab_hba1c: "🟢 <5.7 · prediabetes 5.7–6.4 · 🔴 diabetes ≥6.5 %",
  lab_hdl: "🔴 <40 (malo) · 🟢 ≥60 mg/dL (protector)",
  h_col_total: "🟢 <200 · límite 200–239 · 🔴 ≥240 mg/dL",
  lab_trigliceridos: "🟢 <150 · límite 150–199 · 🔴 ≥200 mg/dL",
  lab_alt: "🟢 7–56 U/L · 🔴 elevado = daño hepático",
  h_ast: "🟢 10–40 U/L · 🔴 elevado = daño hepático/muscular",
  lab_bun: "🟢 7–20 mg/dL · 🔴 alto = función renal alterada",
  lab_acido_urico: "🟢 3.5–7.2 · 🔴 alto = gota/riesgo metabólico",
  lab_calcio: "🟢 8.5–10.2 mg/dL",
  lab_globulina: "🟢 2.0–3.5 g/dL · 🔴 alto = inflamación crónica",
  lab_bilirrubina_total: "🟢 0.1–1.2 mg/dL",
  lab_ldh: "🟢 140–280 U/L · 🔴 alto = daño tisular",
  lab_hierro: "🟢 60–170 µg/dL · 🔴 bajo = anemia ferropénica",
  lab_vitamina_d: "🔴 deficiencia <30 · 🟢 suficiente ≥50 nmol/L",
  lab_hemoglobina: "🟢 H 13.5–17.5 / M 12–15.5 · 🔴 bajo = anemia",
  lab_plaquetas: "🟢 150–400 (×1000/µL)",
  lab_mpv: "🟢 7.5–11.5 fL",
  lab_neutrofilos_pct: "🟢 40–70 % (junto a linfocitos define el NLR)",
  h_linfocitos_pct: "🟢 20–40 % · 🔴 bajo = peor pronóstico (NLR alto)",
  lab_monocitos_pct: "🟢 2–8 %",
  quest_n_medicamentos: "🟢 0–2 · 🔴 ≥5 = polifarmacia",
  quest_phq9_score: "🟢 0–4 mínimo · 5–9 leve · 🔴 ≥10 depresión",
  quest_discapacidad_count: "🟢 0 · 🔴 más = peor estado funcional",
  quest_cambio_peso_1y_lb: "🔴 pérdida involuntaria marcada = fragilidad",
  quest_alcohol_freq_anual: "🟢 0 nunca … 🔴 7 diario",
  quest_tragos_por_dia: "🟢 ≤1–2 · 🔴 ≥4 = consumo de riesgo",
  quest_met_min_semana: "🔴 <600 sedentario · 🟢 ≥600 (recomendación OMS)",
  quest_sedentario_min: "🟢 bajo · 🔴 >480 min/día = riesgo",
  quest_horas_sueno: "🟢 7–9 h · 🔴 <6 o >9 h",
  quest_tabaquismo: "🟢 nunca · exfumador · 🔴 activo",
  quest_activo_oms: "🟢 Sí (cumple actividad recomendada)",
};

// Flags de enfermedad que suman al conteo de comorbilidad.
const FLAGS_COMORBILIDAD = [
  "quest_diabetes_flag", "quest_hipertension_dx", "quest_cvd_flag",
  "quest_cancer_flag", "quest_artritis_flag", "quest_enf_renal_dx",
];

// Perfiles de ejemplo (valores clinicos plausibles) para ver el rango a rellenar
// y comparar salud buena vs mala. Documentados en docs/PERFILES_Y_RANGOS.md.
const PERFIL_BUENA: Record<string, string> = {
  edad: "55", demo_sexo: "masculino", demo_educacion: "4", demo_pir: "3.5",
  exam_imc: "23", exam_cintura: "88", exam_altura: "175", exam_circ_brazo: "30", exam_pulso: "64",
  lab_hba1c: "5.2", lab_hdl: "65", h_col_total: "170", lab_trigliceridos: "90",
  lab_alt: "22", h_ast: "22", lab_bun: "14", lab_acido_urico: "5.0", lab_calcio: "9.5",
  lab_globulina: "2.8", lab_bilirrubina_total: "0.7", lab_ldh: "160", lab_hierro: "95",
  lab_vitamina_d: "75", lab_hemoglobina: "14.8", lab_plaquetas: "250", lab_mpv: "9",
  lab_neutrofilos_pct: "55", h_linfocitos_pct: "33", lab_monocitos_pct: "7",
  quest_n_medicamentos: "0", quest_phq9_score: "1", quest_discapacidad_count: "0", quest_cambio_peso_1y_lb: "0",
  quest_tabaquismo: "nunca", quest_activo_oms: "1", quest_alcohol_freq_anual: "1",
  quest_tragos_por_dia: "1", quest_met_min_semana: "1500", quest_sedentario_min: "300", quest_horas_sueno: "7.5",
};
const PERFIL_MALA: Record<string, string> = {
  edad: "60", demo_sexo: "masculino", demo_educacion: "2", demo_pir: "1.2",
  exam_imc: "34", exam_cintura: "118", exam_altura: "172", exam_circ_brazo: "38", exam_pulso: "88",
  lab_hba1c: "8.2", lab_hdl: "32", h_col_total: "250", lab_trigliceridos: "320",
  lab_alt: "55", h_ast: "60", lab_bun: "28", lab_acido_urico: "8.5", lab_calcio: "9.8",
  lab_globulina: "3.6", lab_bilirrubina_total: "1.0", lab_ldh: "280", lab_hierro: "70",
  lab_vitamina_d: "30", lab_hemoglobina: "13.0", lab_plaquetas: "200", lab_mpv: "11.5",
  lab_neutrofilos_pct: "70", h_linfocitos_pct: "18", lab_monocitos_pct: "9",
  quest_diabetes_flag: "1", quest_diabetes_insulina: "1", quest_hipertension_dx: "1",
  quest_medicacion_presion: "1", quest_colesterol_alto_dx: "1", quest_medicacion_colesterol: "1",
  quest_cvd_flag: "1", quest_artritis_flag: "1",
  quest_n_medicamentos: "7", quest_phq9_score: "12", quest_discapacidad_count: "2", quest_cambio_peso_1y_lb: "-12",
  quest_tabaquismo: "activo", quest_activo_oms: "0", quest_alcohol_freq_anual: "5",
  quest_tragos_por_dia: "4", quest_met_min_semana: "100", quest_sedentario_min: "600", quest_horas_sueno: "5.5",
};

type Resultado = {
  edad_cronologica: number;
  edad_biologica: number;
  aceleracion: number;
  referencia_poblacional: number | null;
  clasificacion: "acelerado" | "normal";
  impacto_variables: Record<string, number>;
  recomendacion_principal: string;
  riesgo_mortalidad_10a: number | null;
  esperanza_vida_restante: number | null;
  edad_fallecimiento_estimada: number | null;
};

const prettify = (k: string) =>
  k.replace(/^(exam|lab|quest|demo)_/, "").replace(/_/g, " ").replace(/\bpct\b/, "%");

export default function ClinicalForm() {
  const [vals, setVals] = useState<Record<string, string>>({});
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nPaciente, setNPaciente] = useState(0); // nº de campos precargados del paciente

  // Al montar: cargar los datos que el paciente dejó (puente vía localStorage).
  useEffect(() => {
    try {
      const raw = localStorage.getItem("nhanes_datos_paciente");
      if (raw) {
        const datos = JSON.parse(raw) as Record<string, string>;
        setVals(datos);
        setNPaciente(Object.keys(datos).length);
      }
    } catch { /* localStorage no disponible */ }
  }, []);

  const limpiarPaciente = () => {
    try { localStorage.removeItem("nhanes_datos_paciente"); } catch { /* noop */ }
    setVals({});
    setNPaciente(0);
    setResultado(null);
  };

  const set = (k: string, v: string) => setVals((p) => ({ ...p, [k]: v }));
  const num = (k: string): number | null => {
    const v = vals[k];
    if (v === undefined || v === "") return null;
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const edad = num("edad");
    if (edad === null) {
      setError("La edad es obligatoria.");
      return;
    }

    // Validacion de rangos clinicos: evita que valores fuera de escala (o en
    // unidades equivocadas) disparen la prediccion a edades imposibles.
    const fuera: string[] = [];
    for (const [k, v] of Object.entries(vals)) {
      const rango = RANGOS[k];
      if (!rango || v === "") continue;
      const n = parseFloat(v);
      if (!Number.isFinite(n) || n < rango[0] || n > rango[1]) {
        fuera.push(`${LABELS[k] ?? k} (rango ${rango[0]}–${rango[1]})`);
      }
    }
    if (fuera.length) {
      setError("Revise estos valores fuera de rango clínico: " + fuera.join(", ") + ".");
      return;
    }

    // 1. Features directas (todo lo que no sea auxiliar 'h_' ni 'edad').
    const features: Record<string, number | string> = {};
    for (const sec of SECCIONES) {
      for (const f of sec.fields) {
        if (f.key === "edad" || f.key.startsWith("h_")) continue;
        const raw = vals[f.key];
        if (raw === undefined || raw === "") continue;
        if (f.type === "number") {
          const n = parseFloat(raw);
          if (Number.isFinite(n)) features[f.key] = n;
        } else if (f.type === "check") {
          features[f.key] = 1;
        } else {
          features[f.key] = raw; // select (string o "1"/"0")
        }
      }
    }
    // quest_activo_oms viene como "1"/"0" string -> a number
    if (features.quest_activo_oms !== undefined) features.quest_activo_oms = parseFloat(String(features.quest_activo_oms));

    // 2. Features derivadas.
    const colTotal = num("h_col_total"), hdl = num("lab_hdl");
    if (colTotal !== null && hdl !== null) features["lab_no_hdl"] = colTotal - hdl;
    const ast = num("h_ast"), alt = num("lab_alt");
    if (ast !== null && alt !== null && alt !== 0) features["lab_ast_alt_ratio"] = ast / alt;
    const neutro = num("lab_neutrofilos_pct"), linfo = num("h_linfocitos_pct");
    if (neutro !== null && linfo !== null && linfo !== 0) features["lab_nlr"] = neutro / linfo;
    const cintura = num("exam_cintura"), altura = num("exam_altura");
    if (cintura !== null && altura !== null && altura !== 0) features["exam_cintura_talla"] = cintura / altura;
    const nmed = num("quest_n_medicamentos");
    if (nmed !== null) features["quest_polifarmacia_flag"] = nmed >= 5 ? 1 : 0;
    const phq = num("quest_phq9_score");
    if (phq !== null) features["quest_depresion_flag"] = phq >= 10 ? 1 : 0;
    const sueno = num("quest_horas_sueno");
    if (sueno !== null) features["quest_sueno_categoria"] = sueno < 6 ? "corto" : sueno > 9 ? "largo" : "normal";
    const ncomorb = FLAGS_COMORBILIDAD.reduce((acc, k) => acc + (vals[k] ? 1 : 0), 0);
    if (ncomorb > 0) features["quest_comorbilidad_count"] = ncomorb;

    // 3. Llamada al modelo master.
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/predict/master", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edad, features }),
      });
      if (!res.ok) throw new Error("Error en la predicción");
      setResultado(await res.json());
    } catch (err) {
      console.error(err);
      setError("Error al conectar con la API (FastAPI en el puerto 8000).");
    } finally {
      setLoading(false);
    }
  };

  const acelerado = resultado?.clasificacion === "acelerado";
  const shapData = resultado
    ? Object.entries(resultado.impacto_variables)
        .map(([k, v]) => ({ name: prettify(k), impacto: v }))
        .sort((a, b) => Math.abs(b.impacto) - Math.abs(a.impacto))
    : [];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
      {/* Formulario (2/3) */}
      <form onSubmit={onSubmit} className="xl:col-span-2 space-y-6">
        {/* Perfiles de ejemplo: rellenan valores plausibles para ver el rango */}
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-slate-600">Cargar ejemplo:</span>
          <button
            type="button"
            onClick={() => { setVals(PERFIL_BUENA); setNPaciente(0); setResultado(null); setError(null); }}
            className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-semibold hover:bg-emerald-100 transition-colors"
          >
            🟢 Salud buena
          </button>
          <button
            type="button"
            onClick={() => { setVals(PERFIL_MALA); setNPaciente(0); setResultado(null); setError(null); }}
            className="px-3 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-semibold hover:bg-red-100 transition-colors"
          >
            🔴 Salud mala
          </button>
          <button
            type="button"
            onClick={limpiarPaciente}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 text-sm font-semibold hover:bg-slate-50 transition-colors"
          >
            Vaciar
          </button>
          <span className="text-xs text-slate-400 basis-full">
            Los ejemplos rellenan valores clínicos plausibles. Puede editarlos antes de calcular.
          </span>
        </div>

        {nPaciente > 0 && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3">
            <UserCheck className="text-emerald-600 shrink-0" size={20} />
            <p className="text-sm text-emerald-800 flex-grow">
              <strong>Datos del paciente cargados</strong> ({nPaciente} campos del cuestionario). Añada los datos
              clínicos y de laboratorio; la predicción combinará ambos.
            </p>
            <button
              type="button"
              onClick={limpiarPaciente}
              className="flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-900 shrink-0"
            >
              <X size={14} /> Limpiar
            </button>
          </div>
        )}
        {SECCIONES.map((sec) => (
          <div key={sec.title} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <div className="flex items-center gap-2 mb-4">
              {sec.icon}
              <h2 className="text-lg font-semibold text-slate-800">{sec.title}</h2>
            </div>
            <div className={`grid grid-cols-1 ${sec.cols} gap-3`}>
              {sec.fields.map((f) =>
                f.type === "check" ? (
                  <label key={f.key} className="flex items-center gap-2 p-2.5 border border-slate-300 rounded-lg cursor-pointer hover:bg-slate-50 text-slate-900">
                    <input
                      type="checkbox"
                      checked={vals[f.key] === "1"}
                      onChange={(e) => set(f.key, e.target.checked ? "1" : "")}
                      className="w-4 h-4 accent-blue-600"
                    />
                    <span className="text-sm">{f.label}</span>
                  </label>
                ) : (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      {f.label}
                      {"unit" in f && f.unit ? <span className="text-slate-400"> ({f.unit}{f.ref ? `, ref ${f.ref}` : ""})</span> : null}
                    </label>
                    {f.type === "select" ? (
                      <select
                        value={vals[f.key] ?? ""}
                        onChange={(e) => set(f.key, e.target.value)}
                        className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900 text-sm"
                      >
                        {f.options.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
                      </select>
                    ) : (
                      <input
                        type="number"
                        step="any"
                        min={RANGOS[f.key]?.[0]}
                        max={RANGOS[f.key]?.[1]}
                        value={vals[f.key] ?? ""}
                        onChange={(e) => set(f.key, e.target.value)}
                        className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900 text-sm"
                      />
                    )}
                    {REFERENCIAS[f.key] && (
                      <p className="text-[11px] text-slate-500 mt-1 leading-tight">{REFERENCIAS[f.key]}</p>
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        ))}

        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-70"
        >
          {loading ? "Calculando..." : <>Calcular Edad Biológica (modelo master) <CheckCircle2 size={18} /></>}
        </button>
        <p className="text-xs text-slate-400">
          Solo la edad es obligatoria. Cuantos más parámetros introduzca, más precisa será la estimación;
          lo no introducido se imputa con la mediana de la población 40+.
        </p>
      </form>

      {/* Resultado (1/3) */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col h-fit xl:sticky xl:top-8">
        <h2 className="text-xl font-semibold text-slate-800 mb-4">Resultado (modelo master)</h2>

        {!resultado ? (
          <div className="flex-grow flex items-center justify-center text-slate-400 text-sm text-center px-6 py-12">
            Rellene los parámetros disponibles y pulse calcular para estimar la edad biológica con el modelo entrenado.
          </div>
        ) : (
          <>
            <div className="text-center mb-4">
              <p className="text-sm font-semibold text-slate-500">Edad biológica estimada</p>
              <p className={`text-5xl font-extrabold ${acelerado ? "text-red-500" : "text-emerald-500"}`}>
                {resultado.edad_biologica}
              </p>
              <p className="text-slate-500 text-sm">
                años · cronológica {resultado.edad_cronologica}
                {resultado.referencia_poblacional != null ? ` · promedio 40+: ${resultado.referencia_poblacional}` : ""}
              </p>
              <p className={`mt-1 text-sm font-semibold ${acelerado ? "text-red-600" : "text-emerald-600"}`}>
                {resultado.aceleracion > 0 ? "+" : ""}{resultado.aceleracion} años vs promedio poblacional
              </p>
            </div>

            {resultado.edad_fallecimiento_estimada != null && (
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
                  <p className="text-xl font-bold text-slate-800">{resultado.riesgo_mortalidad_10a}%</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Mortalidad a 10 años</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
                  <p className="text-xl font-bold text-slate-800">~{resultado.edad_fallecimiento_estimada}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Esperanza de vida (≈{resultado.esperanza_vida_restante}a más)</p>
                </div>
              </div>
            )}

            <p className="text-xs text-slate-500 mb-2">Factores con mayor impacto (rojo = eleva la edad)</p>
            <div className="flex-grow min-h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={shapData} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "#f8fafc" }} formatter={(v) => [v as number, "Impacto (años)"]} />
                  <Bar dataKey="impacto" radius={[0, 4, 4, 0]} barSize={16}>
                    {shapData.map((entry, i) => (
                      <Cell key={i} fill={entry.impacto > 0 ? "#ef4444" : "#10b981"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className={`mt-4 p-4 rounded-lg flex items-start gap-3 ${acelerado ? "bg-red-50 border border-red-100" : "bg-emerald-50 border border-emerald-100"}`}>
              <ShieldAlert className={`shrink-0 ${acelerado ? "text-red-500" : "text-emerald-500"}`} size={20} />
              <p className={`text-xs ${acelerado ? "text-red-800" : "text-emerald-800"}`}>{resultado.recomendacion_principal}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
