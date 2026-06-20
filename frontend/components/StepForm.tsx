"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Activity, User, HeartPulse, ArrowRight, ArrowLeft, CheckCircle2 } from "lucide-react";

// 1. Definimos las validaciones con Zod (Asegura calidad de datos para NHANES)
const formSchema = z.object({
  edad: z.coerce.number().min(18, "Debe ser mayor de 18").max(120, "Edad no válida"),
  sexo: z.enum(["M", "F"], { required_error: "Seleccione su sexo" }),
  imc: z.coerce.number().min(10, "IMC muy bajo").max(60, "IMC muy alto"),
  es_fumador: z.enum(["true", "false"], { required_error: "¿Fuma actualmente?" }),
  presion_sistolica: z.coerce.number().min(70).max(250),
  colesterol_total: z.coerce.number().min(100).max(400),
});

type FormData = z.infer<typeof formSchema>;

export default function StepForm() {
  const [paso, setPaso] = useState(1);
  const totalPasos = 3;

  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  });

  // Función para avanzar de paso validando solo los campos actuales
  const avanzarPaso = async (camposAValidar: (keyof FormData)[]) => {
    const esValido = await trigger(camposAValidar);
    if (esValido) setPaso((prev) => prev + 1);
  };

  // Función final (Aquí es donde enviaremos los datos a tu FastAPI)
  const onSubmit = async (data: FormData) => {
    // Transformamos el string "true"/"false" a booleano real
    const payloadFinal = { ...data, es_fumador: data.es_fumador === "true" };
    
    try {
      const response = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payloadFinal),
      });

      if (!response.ok) {
        throw new Error('Error en la predicción');
      }

      const resultado = await response.json();
      
      // En una app real, aquí guardaríamos el resultado en el estado global o la base de datos
      // y redirigiríamos al dashboard del paciente. Por ahora, mostramos una alerta con la respuesta real:
      alert(`¡Predicción recibida de FastAPI!\n\nEsperanza de vida estimada: ${resultado.esperanza_vida_estimada} años\nRecomendación: ${resultado.recomendacion_principal}`);
      
      console.log("Respuesta completa de la API:", resultado);

    } catch (error) {
      console.error("Error al conectar con la API:", error);
      alert("Hubo un error al conectar con el servidor. Asegúrate de que FastAPI esté corriendo en el puerto 8000.");
    }
  };
  
  return (
    <div className="max-w-xl mx-auto bg-white p-8 rounded-2xl shadow-lg border border-slate-100">
      {/* Barra de Progreso (CRO: Mantiene al usuario motivado) */}
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
        
        {/* PASO 1: Datos Demográficos */}
        {paso === 1 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <User className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Datos Personales</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Edad</label>
                <input
                  {...register("edad")}
                  type="number"
                  placeholder="Ej: 45"
                  className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                />
                {errors.edad && <p className="text-red-500 text-sm mt-1">{errors.edad.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sexo Biológico</label>
                <div className="flex gap-4">
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="M" {...register("sexo")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-blue-50 peer-checked:border-blue-500 peer-checked:text-blue-700 font-medium transition-all text-slate-900">Hombre</div>
                  </label>
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="F" {...register("sexo")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-blue-50 peer-checked:border-blue-500 peer-checked:text-blue-700 font-medium transition-all text-slate-900">Mujer</div>
                  </label>
                </div>
                {errors.sexo && <p className="text-red-500 text-sm mt-1">{errors.sexo.message}</p>}
              </div>
            </div>

            <button
              type="button"
              onClick={() => avanzarPaso(["edad", "sexo"])}
              className="mt-8 w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              Continuar <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* PASO 2: Hábitos y Físico */}
        {paso === 2 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Estilo de Vida</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Índice de Masa Corporal (IMC)</label>
                <input
                  {...register("imc")}
                  type="number"
                  step="0.1"
                  placeholder="Ej: 24.5"
                  className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                />
                {errors.imc && <p className="text-red-500 text-sm mt-1">{errors.imc.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">¿Fuma actualmente?</label>
                <div className="flex gap-4">
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="true" {...register("es_fumador")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-red-50 peer-checked:border-red-500 peer-checked:text-red-700 font-medium transition-all text-slate-900">Sí</div>
                  </label>
                  <label className="flex-1 cursor-pointer">
                    <input type="radio" value="false" {...register("es_fumador")} className="peer sr-only" />
                    <div className="p-3 text-center border border-slate-300 rounded-lg peer-checked:bg-emerald-50 peer-checked:border-emerald-500 peer-checked:text-emerald-700 font-medium transition-all text-slate-900">No</div>
                  </label>
                </div>
                {errors.es_fumador && <p className="text-red-500 text-sm mt-1">{errors.es_fumador.message}</p>}
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button type="button" onClick={() => setPaso(1)} className="px-4 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors">
                <ArrowLeft size={18} />
              </button>
              <button
                type="button"
                onClick={() => avanzarPaso(["imc", "es_fumador"])}
                className="flex-1 bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                Continuar <ArrowRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* PASO 3: Variables Clínicas (Métricas de Laboratorio) */}
        {paso === 3 && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <HeartPulse className="text-blue-500" size={28} />
              <h2 className="text-2xl font-bold text-slate-800">Métricas Clínicas</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Presión Arterial Sistólica (mmHg)</label>
                <input
                  {...register("presion_sistolica")}
                  type="number"
                  placeholder="Ej: 120"
                  className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                />
                {errors.presion_sistolica && <p className="text-red-500 text-sm mt-1">{errors.presion_sistolica.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Colesterol Total (mg/dL)</label>
                <input
                  {...register("colesterol_total")}
                  type="number"
                  placeholder="Ej: 190"
                  className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                />
                {errors.colesterol_total && <p className="text-red-500 text-sm mt-1">{errors.colesterol_total.message}</p>}
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button type="button" onClick={() => setPaso(2)} className="px-4 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors">
                <ArrowLeft size={18} />
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-70"
              >
                {isSubmitting ? "Procesando..." : <>Calcular Longevidad <CheckCircle2 size={18} /></>}
              </button>
            </div>
          </div>
        )}

      </form>
    </div>
  );
}