"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Activity, User, HeartPulse, ArrowRight, ArrowLeft, CheckCircle2 } from "lucide-react";

// Esquema alineado con las features REALES del modelo NHANES (bloques demo/exam/quest).
// El target del modelo es la EDAD BIOLOGICA (PhenoAge), no la esperanza de vida.
const formSchema = z.object({
  // demo
  edad: z.coerce.number().min(40, "Esta evaluación está calibrada para personas de 40 años o más").max(120, "Edad no valida"),
  sexo: z.enum(["masculino", "femenino"], { message: "Seleccione su sexo" }),
  // exam (antropometria) — el IMC se calcula desde peso y altura
  peso: z.coerce.number().min(30, "Peso muy bajo").max(300, "Peso muy alto"),
  altura: z.coerce.number().min(100, "Altura muy baja").max(250, "Altura muy alta"),
  cintura: z.coerce.number().min(40).max(200).optional(),
  // quest (estilo de vida)
  tabaquismo: z.enum(["nunca", "exfumador", "activo"], { message: "Indique su habito tabaquico" }),
  alcohol_freq_anual: z.coerce.number().min(0).max(7),
  activo_oms: z.enum(["true", "false"], { message: "Indique su nivel de actividad" }),
  horas_sueno: z.coerce.number().min(2).max(14),
  salud_autopercibida: z.coerce.number().min(1).max(5),
  // comorbilidad
  diabetes_flag: z.boolean().optional(),
  hipertension_dx: z.boolean().optional(),
  cvd_flag: z.boolean().optional(),
  cancer_flag: z.boolean().optional(),
  n_medicamentos: z.coerce.number().min(0).max(30),
});

type FormInput = z.input<typeof formSchema>;
type FormData = z.output<typeof formSchema>;

type Resultado = {
  edad_cronologica: number;
  edad_biologica: number;
  aceleracion: number; // desviacion respecto al promedio poblacional (40+)
  referencia_poblacional: number | null;
  clasificacion: "acelerado" | "normal";
  recomendacion_principal: string;
  metodo: string;
  riesgo_mortalidad_10a: number | null;
  esperanza_vida_restante: number | null;
  edad_fallecimiento_estimada: number | null;
};

const inputCls =
  "w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900";

export default function StepForm() {
  const [paso, setPaso] = useState(1);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const totalPasos = 4;

  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { alcohol_freq_anual: 0, horas_sueno: 7, salud_autopercibida: 3, n_medicamentos: 0 },
  });

  const avanzarPaso = async (campos: (keyof FormInput)[]) => {
    if (await trigger(campos)) setPaso((p) => p + 1);
  };

  const onSubmit = async (data: FormData) => {
    // IMC = peso (kg) / altura (m)^2. El modelo usa 'imc' como feature.
    const imc = +(data.peso / Math.pow(data.altura / 100, 2)).toFixed(1);
    const { peso: _peso, altura: _altura, ...resto } = data;
    const payload = {
      ...resto,
      imc,
      altura: data.altura, // 'altura' tambien es feature del modelo (bloque exam)
      activo_oms: data.activo_oms === "true",
      diabetes_flag: !!data.diabetes_flag,
      hipertension_dx: !!data.hipertension_dx,
      cvd_flag: !!data.cvd_flag,
      cancer_flag: !!data.cancer_flag,
      cintura: data.cintura ?? null,
    };

    // Puente paciente -> doctor: guardamos los datos mapeados a las columnas RAW
    // del modelo (mismas claves que usa el formulario del doctor) para que su
    // panel se prerrellene y la prediccion combine paciente + datos clinicos.
    const datosParaDoctor: Record<string, string> = {
      edad: String(data.edad),
      demo_sexo: data.sexo,
      exam_imc: String(imc),
      exam_altura: String(data.altura),
      quest_tabaquismo: data.tabaquismo,
      quest_alcohol_freq_anual: String(data.alcohol_freq_anual),
      quest_activo_oms: data.activo_oms === "true" ? "1" : "0",
      quest_horas_sueno: String(data.horas_sueno),
      quest_n_medicamentos: String(data.n_medicamentos),
    };
    if (data.cintura != null) datosParaDoctor.exam_cintura = String(data.cintura);
    if (data.diabetes_flag) datosParaDoctor.quest_diabetes_flag = "1";
    if (data.hipertension_dx) datosParaDoctor.quest_hipertension_dx = "1";
    if (data.cvd_flag) datosParaDoctor.quest_cvd_flag = "1";
    if (data.cancer_flag) datosParaDoctor.quest_cancer_flag = "1";
    try {
      localStorage.setItem("nhanes_datos_paciente", JSON.stringify(datosParaDoctor));
    } catch { /* localStorage no disponible */ }

    try {
      // --- CAMBIO CLAVE PARA USAR LA IP DE AWS ---
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE_URL}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      // -------------------------------------------
      
      if (!response.ok) throw new Error("Error en la prediccion");
      setResultado(await response.json());
    } catch (error) {
      console.error("Error al conectar con la API:", error);
      alert("Hubo un error al conectar con el servidor. Verifica que el modelo en la nube esté respondiendo.");
    } catch (error) {
      console.error("Error al conectar con la API:", error);
      alert("Hubo un error al conectar con el servidor. Asegurate de que FastAPI este corriendo en el puerto 8000.");
    }
  };

  // --- Pantalla de resultado ---
  if (resultado) {
    const acelerado = resultado.clasificacion === "acelerado";
    const ref = resultado.referencia_poblacional;
    return (
      <div className="max-w-xl mx-auto bg-white p-8 rounded-2xl shadow-lg border border-slate-100 text-center">
        <p className="text-sm font-semibold text-slate-500 mb-2">Su edad metabolica estimada</p>
        <p className={`text-6xl font-extrabold ${acelerado ? "text-red-500" : "text-emerald-500"}`}>
          {resultado.edad_biologica}
        </p>
        <p className="text-slate-500 mt-1">
          años{ref != null ? ` · promedio poblacion 40+: ${ref} años` : ""}
        </p>

        <div
          className={`mt-6 p-4 rounded-lg text-sm ${
            acelerado ? "bg-red-50 text-red-800 border border-red-100" : "bg-emerald-50 text-emerald-800 border border-emerald-100"
          }`}
        >
          {acelerado
            ? `Su edad metabolica esta +${resultado.aceleracion} años por encima del promedio de la poblacion 40+.`
            : `Su edad metabolica esta ${Math.abs(resultado.aceleracion)} años por debajo del promedio de la poblacion 40+.`}
        </div>

        <p className="text-sm text-slate-600 mt-4">{resultado.recomendacion_principal}</p>

        {resultado.edad_fallecimiento_estimada != null && (
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-2xl font-bold text-slate-800">{resultado.riesgo_mortalidad_10a}%</p>
              <p className="text-xs text-slate-500 mt-1">Riesgo de mortalidad a 10 años</p>
            </div>
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-2xl font-bold text-slate-800">~{resultado.edad_fallecimiento_estimada}</p>
              <p className="text-xs text-slate-500 mt-1">
                Esperanza de vida estimada (≈{resultado.esperanza_vida_restante} años más)
              </p>
            </div>
          </div>
        )}

        <p className="text-xs text-slate-400 mt-6">
          Estimacion del modelo NHANES (PhenoAge) entrenado en poblacion de 40+ años. La esperanza de vida es una
          aproximacion <strong>estadistica poblacional</strong> (tabla de vida segun su edad biologica), no una
          prediccion individual. Para un calculo exacto se requiere analitica de sangre (acceso medico).
        </p>

        <a
          href="/doctor"
          className="mt-6 block w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
        >
          Continuar con el médico (añadir analítica) →
        </a>
        <button
          onClick={() => {
            setResultado(null);
            setPaso(1);
          }}
          className="mt-3 text-sm font-semibold text-blue-600 hover:text-blue-700"
        >
          Realizar otra evaluacion
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto bg-white p-8 rounded-2xl shadow-lg border border-slate-100">
      {/* Barra de Progreso */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-slate-500">Paso {paso} de {totalPasos}</span>
          <span className="text-sm font-semibold text-emerald-500">{Math.round((paso / totalPasos) * 100)}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2.5">
          <div
            className="bg-emerald-500 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${(paso / totalPasos) * 100}%` }}
          ></div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* PASO 1: Datos Demograficos */}
        {paso === 1 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <User className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Datos Personales</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Edad</label>
                <input {...register("edad")} type="number" min={40} max={120} placeholder="Ej: 55" className={inputCls} />
                <p className="text-xs text-slate-400 mt-1">Válido para 40 años o más (modelo calibrado en población 40+).</p>
                {errors.edad && <p className="text-red-500 text-sm mt-1">{errors.edad.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sexo Biologico</label>
                <div className="flex gap-4">
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="masculino" {...register("sexo")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-blue-50 peer-checked:border-blue-500 peer-checked:text-blue-700 font-medium transition-all text-slate-900">Hombre</div>
                  </label>
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="femenino" {...register("sexo")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-blue-50 peer-checked:border-blue-500 peer-checked:text-blue-700 font-medium transition-all text-slate-900">Mujer</div>
                  </label>
                </div>
                {errors.sexo && <p className="text-red-500 text-sm mt-1">{errors.sexo.message}</p>}
              </div>
            </div>

            <button type="button" onClick={() => avanzarPaso(["edad", "sexo"])} className="mt-8 w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors">
              Continuar <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* PASO 2: Antropometria */}
        {paso === 2 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Medidas Corporales</h2>
            </div>

            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Peso (kg)</label>
                  <input {...register("peso")} type="number" step="0.1" placeholder="Ej: 72" className={inputCls} />
                  {errors.peso && <p className="text-red-500 text-sm mt-1">{errors.peso.message}</p>}
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Altura (cm)</label>
                  <input {...register("altura")} type="number" step="0.1" placeholder="Ej: 172" className={inputCls} />
                  {errors.altura && <p className="text-red-500 text-sm mt-1">{errors.altura.message}</p>}
                </div>
              </div>
              <p className="text-xs text-slate-400">Calcularemos su IMC automaticamente a partir del peso y la altura.</p>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Circunferencia de cintura (cm) <span className="text-slate-400">— opcional</span></label>
                <input {...register("cintura")} type="number" step="0.1" placeholder="Ej: 92" className={inputCls} />
                {errors.cintura && <p className="text-red-500 text-sm mt-1">{errors.cintura.message}</p>}
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button type="button" onClick={() => setPaso(1)} className="px-4 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"><ArrowLeft size={18} /></button>
              <button type="button" onClick={() => avanzarPaso(["peso", "altura", "cintura"])} className="flex-1 bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors">Continuar <ArrowRight size={18} /></button>
            </div>
          </div>
        )}

        {/* PASO 3: Estilo de vida */}
        {paso === 3 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Estilo de Vida</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Habito tabaquico</label>
                <select {...register("tabaquismo")} className={inputCls}>
                  <option value="">Seleccione...</option>
                  <option value="nunca">Nunca he fumado</option>
                  <option value="exfumador">Exfumador</option>
                  <option value="activo">Fumador actual</option>
                </select>
                {errors.tabaquismo && <p className="text-red-500 text-sm mt-1">{errors.tabaquismo.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">¿Cumple la actividad fisica recomendada (OMS)?</label>
                <div className="flex gap-4">
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="true" {...register("activo_oms")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-emerald-50 peer-checked:border-emerald-500 peer-checked:text-emerald-700 font-medium transition-all text-slate-900">Si</div>
                  </label>
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="false" {...register("activo_oms")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-red-50 peer-checked:border-red-500 peer-checked:text-red-700 font-medium transition-all text-slate-900">No</div>
                  </label>
                </div>
                {errors.activo_oms && <p className="text-red-500 text-sm mt-1">{errors.activo_oms.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Horas de sueño por noche</label>
                <input {...register("horas_sueno")} type="number" step="0.5" placeholder="Ej: 7" className={inputCls} />
                {errors.horas_sueno && <p className="text-red-500 text-sm mt-1">{errors.horas_sueno.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Frecuencia de consumo de alcohol (0 = nunca, 7 = diario)</label>
                <input {...register("alcohol_freq_anual")} type="number" step="1" placeholder="0-7" className={inputCls} />
                {errors.alcohol_freq_anual && <p className="text-red-500 text-sm mt-1">{errors.alcohol_freq_anual.message}</p>}
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button type="button" onClick={() => setPaso(2)} className="px-4 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"><ArrowLeft size={18} /></button>
              <button type="button" onClick={() => avanzarPaso(["tabaquismo", "activo_oms", "horas_sueno", "alcohol_freq_anual"])} className="flex-1 bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors">Continuar <ArrowRight size={18} /></button>
            </div>
          </div>
        )}

        {/* PASO 4: Salud / Comorbilidad */}
        {paso === 4 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <HeartPulse className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Estado de Salud</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Salud autopercibida (1 = excelente, 5 = mala)</label>
                <input {...register("salud_autopercibida")} type="number" min={1} max={5} placeholder="1-5" className={inputCls} />
                {errors.salud_autopercibida && <p className="text-red-500 text-sm mt-1">{errors.salud_autopercibida.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">¿Le han diagnosticado alguna de estas condiciones?</label>
                <div className="grid grid-cols-2 gap-3">
                  {([
                    ["diabetes_flag", "Diabetes"],
                    ["hipertension_dx", "Hipertension"],
                    ["cvd_flag", "Enf. cardiovascular"],
                    ["cancer_flag", "Cancer"],
                  ] as const).map(([name, label]) => (
                    <label key={name} className="flex items-center gap-2 p-3 border border-slate-300 rounded-lg cursor-pointer hover:bg-slate-50 text-slate-900">
                      <input type="checkbox" {...register(name)} className="w-4 h-4 accent-blue-600" />
                      <span className="text-sm">{label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Numero de medicamentos recetados que toma</label>
                <input {...register("n_medicamentos")} type="number" min={0} placeholder="Ej: 2" className={inputCls} />
                {errors.n_medicamentos && <p className="text-red-500 text-sm mt-1">{errors.n_medicamentos.message}</p>}
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button type="button" onClick={() => setPaso(3)} className="px-4 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"><ArrowLeft size={18} /></button>
              <button type="submit" disabled={isSubmitting} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-70">
                {isSubmitting ? "Procesando..." : <>Calcular Edad Biologica <CheckCircle2 size={18} /></>}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
