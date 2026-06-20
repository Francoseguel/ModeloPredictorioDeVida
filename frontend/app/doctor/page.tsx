"use client";

import Link from "next/link";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { ArrowLeft, Users, Activity, ShieldAlert } from "lucide-react";

// Datos MOCK para el gráfico XAI (Valores SHAP simulados)
// Positivo = Suma años de vida (Verde) | Negativo = Resta años de vida (Rojo)
const shapData = [
  { name: "Actividad Física", impacto: 2.3 },
  { name: "IMC Saludable", impacto: 1.5 },
  { name: "Colesterol", impacto: -0.8 },
  { name: "Presión Sistólica", impacto: -2.1 },
  { name: "Tabaquismo", impacto: -4.2 },
];

// Datos MOCK para la tabla de pacientes
const pacientes = [
  { id: 1, nombre: "Carlos Martínez", edad: 58, riesgo: "Alto", longevidad: 72.4, fecha: "Hoy" },
  { id: 2, nombre: "Elena Rodríguez", edad: 42, riesgo: "Bajo", longevidad: 86.1, fecha: "Ayer" },
  { id: 3, nombre: "Jorge Luis Pena", edad: 65, riesgo: "Medio", longevidad: 78.8, fecha: "12/06/2026" },
];

export default function DoctorDashboard() {
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      {/* Cabecera */}
      <div className="max-w-7xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Panel Clínico</h1>
          <p className="text-slate-500 mt-1">Gestión de riesgos predictivos - NHANES</p>
        </div>
        <Link href="/" className="flex items-center gap-2 text-slate-600 hover:text-blue-600 transition-colors">
          <ArrowLeft size={20} /> Volver a Inicio
        </Link>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Columna Izquierda: Tabla de Pacientes */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center gap-3 mb-6">
            <Users className="text-blue-500" />
            <h2 className="text-xl font-semibold text-slate-800">Pacientes Recientes</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 text-sm">
                  <th className="pb-3 font-medium">Paciente</th>
                  <th className="pb-3 font-medium">Edad</th>
                  <th className="pb-3 font-medium">Est. Longevidad</th>
                  <th className="pb-3 font-medium">Nivel de Riesgo</th>
                  <th className="pb-3 font-medium">Última Eval.</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {pacientes.map((p) => (
                  <tr key={p.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="py-4 font-medium text-slate-800">{p.nombre}</td>
                    <td className="py-4 text-slate-600">{p.edad}</td>
                    <td className="py-4 font-semibold text-blue-600">{p.longevidad} años</td>
                    <td className="py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        p.riesgo === 'Alto' ? 'bg-red-100 text-red-700' : 
                        p.riesgo === 'Medio' ? 'bg-amber-100 text-amber-700' : 
                        'bg-emerald-100 text-emerald-700'
                      }`}>
                        {p.riesgo}
                      </span>
                    </td>
                    <td className="py-4 text-slate-500">{p.fecha}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Columna Derecha: Explicabilidad IA (XAI) */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="text-emerald-500" />
            <h2 className="text-xl font-semibold text-slate-800">Análisis XAI</h2>
          </div>
          <p className="text-sm text-slate-500 mb-6">Impacto de variables en el último paciente (Carlos M.)</p>
          
          {/* Gráfico SHAP (Recharts) */}
          <div className="flex-grow min-h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={shapData} layout="vertical" margin={{ top: 0, right: 30, left: 20, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{fill: '#f8fafc'}} formatter={(value: number) => [`${value > 0 ? '+' : ''}${value} años`, "Impacto"]} />
                <Bar dataKey="impacto" radius={[0, 4, 4, 0]} barSize={24}>
                  {shapData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.impacto > 0 ? '#10b981' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          
          <div className="mt-4 p-4 bg-red-50 border border-red-100 rounded-lg flex items-start gap-3">
            <ShieldAlert className="text-red-500 shrink-0" size={20} />
            <p className="text-xs text-red-800">
              <strong>Alerta Clínica:</strong> El tabaquismo es el factor de mayor riesgo, reduciendo la esperanza de vida en 4.2 años frente a la media basal.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}