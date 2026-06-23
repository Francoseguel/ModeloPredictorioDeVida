import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ClinicalForm from "@/components/ClinicalForm";

export default function DoctorDashboard() {
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      {/* Cabecera */}
      <div className="max-w-7xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Panel Clinico</h1>
          <p className="text-slate-500 mt-1">Estimación de edad biológica con el modelo NHANES (master)</p>
        </div>
        <Link href="/" className="flex items-center gap-2 text-slate-600 hover:text-blue-600 transition-colors">
          <ArrowLeft size={20} /> Volver a Inicio
        </Link>
      </div>

      <div className="max-w-7xl mx-auto">
        <ClinicalForm />
      </div>
    </div>
  );
}
