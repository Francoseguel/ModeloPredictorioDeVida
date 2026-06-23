import StepForm from "@/components/StepForm";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 flex flex-col justify-center items-center relative">
      
      {/* Botón de Acceso Médico */}
      <div className="absolute top-6 right-6">
        <Link 
          href="/doctor" 
          className="flex items-center gap-2 bg-white px-4 py-2 rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 hover:text-blue-600 hover:border-blue-300 transition-all shadow-sm"
        >
          👨‍⚕️ Acceso Médico
        </Link>
      </div>

      <div className="max-w-3xl w-full space-y-8 text-center mb-10 mt-10">
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">
          Calcule su <span className="text-blue-600">Edad Biológica</span>
        </h1>
        <p className="text-lg text-slate-600">
          Complete este breve cuestionario de estilo de vida. Estimaremos su edad biológica
          y si presenta envejecimiento acelerado, con el modelo NHANES (PhenoAge).
        </p>
        <p className="text-sm text-slate-400">Dirigido a personas de 40 años o más.</p>
      </div>

      <div className="w-full">
        <StepForm />
      </div>
    </main>
  );
}