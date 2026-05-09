import { Lock } from 'lucide-react';

export default function AdminPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-slate-900">Admin Forecasting</h1>
      <div className="mt-6 p-12 border-2 border-dashed border-slate-200 rounded-2xl text-center">
        <Lock className="mx-auto text-slate-300 mb-4" size={48} />
        <p className="text-slate-500">Long-term predictive models (6 months+) are currently restricted to authorized users.</p>
      </div>
    </div>
  );
}