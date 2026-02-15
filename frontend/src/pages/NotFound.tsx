import { useLocation } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname
    );
  }, [location.pathname]);

  return (
    <div className="app-bg min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background Watermark */}
      <div className="absolute inset-0 flex items-center justify-center select-none pointer-events-none">
        <h1 className="text-[20vw] font-black text-white/[0.02] tracking-tighter">404</h1>
      </div>

      {/* Foreground Content */}
      <div className="glass-card p-12 text-center backdrop-blur-md border-white/10 relative z-10 max-w-md mx-6">
        <h2 className="text-3xl font-extralight text-white mb-2">
          Path <span className="text-prismatic font-normal">Uncharted</span>
        </h2>
        <p className="text-white/40 font-light text-sm tracking-wide mb-8">
          The requested strata could not be located.
        </p>
        <a href="/" className="dawn-button inline-flex no-underline items-center justify-center hover:text-white">
          Return to Origin
        </a>
      </div>
    </div>
  );
};

export default NotFound;
