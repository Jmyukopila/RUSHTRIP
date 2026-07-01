import { useState, useCallback } from 'react';
import PlanForm from '../components/PlanForm';
import PlanResult from '../components/PlanResult';
import LoadingPlane from '../components/LoadingPlane';
import { IconPlane } from '../components/icons';

export default function Plan() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formKey, setFormKey] = useState(0);

  function handlePlanCreated(result) {
    setData(result);
    setError(null);
  }

  function handlePlanError(err) {
    setError(err);
    setData(null);
    setLoading(false);
  }

  function handlePlanLoading(isLoading) {
    setLoading(isLoading);
  }

  async function handleRetry() {
    setError(null);
    setData(null);
    setFormKey((k) => k + 1);
  }

  const handleModify = useCallback(() => {
    setFormKey((k) => k + 1);
    setData(null);
    setError(null);
    setTimeout(() => {
      document.querySelector('.plan-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }, []);

  return (
    <div className="py-12 sm:py-16 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-96 bg-warm-glow pointer-events-none" />
      <div className="absolute top-8 -left-20 w-72 h-72 bg-accent/3 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-24 -right-16 w-64 h-64 bg-accent2/5 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 relative">
        <div className="text-center mb-10">
          <svg viewBox="0 0 320 40" className="w-64 sm:w-80 mx-auto mb-4 text-accent2" fill="none" aria-hidden="true">
            <path d="M10 32 Q110 4 250 14 Q290 17 312 28" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" opacity="0.5" />
            <circle cx="10" cy="32" r="3" fill="#E8611A" opacity="0.5" />
            <circle cx="312" cy="28" r="3" fill="#E8611A" opacity="0.5" />
            <g transform="translate(150 9) rotate(8)">
              <path d="M14 0 L8.5 4.5 L2 3 L0.5 4.5 L6 7 L3 10.5 L0 10 L-1 11 L2.5 13 L4.5 16.5 L5.5 15.5 L5 12.5 L8.5 9.5 L11 15 L12.5 13.5 L11 7 L15.5 1.5 Z" fill="#E8611A" opacity="0.85" />
            </g>
          </svg>
          <h1 className="font-display text-3xl sm:text-4xl text-text">
            Arma tu viaje
          </h1>
          <p className="mt-2 text-muted">
            Completa los datos y te mostraremos el mejor plan para tu presupuesto.
          </p>
          <div className="separator mt-5 max-w-xs mx-auto">
            <IconPlane className="w-3.5 h-3.5 text-accent" />
          </div>
        </div>

        <PlanForm
          key={formKey}
          onPlanCreated={handlePlanCreated}
          onPlanError={handlePlanError}
          onPlanLoading={handlePlanLoading}
        />

        <div className="mt-10 max-w-3xl mx-auto">
          {loading && <LoadingPlane />}
          {!loading && (data || error) && (
            <PlanResult
              data={data}
              error={error}
              loading={false}
              onRetry={handleRetry}
              onModify={handleModify}
            />
          )}
        </div>
      </div>
    </div>
  );
}
