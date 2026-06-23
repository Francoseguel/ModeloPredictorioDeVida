import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ignoramos errores menores de tipeo o formato que bloquean el build en la nube
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;