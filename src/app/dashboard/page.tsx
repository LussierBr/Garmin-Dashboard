"use client";

import { useState } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { Activity, Battery, Footprints } from 'lucide-react';

// This is the data shape the Garmin API will eventually provide
const dummyData = [
  { date: 'May 3', stress: 42, bodyBattery: 85, steps: 6500 },
  { date: 'May 4', stress: 58, bodyBattery: 60, steps: 12000 },
  { date: 'May 5', stress: 65, bodyBattery: 45, steps: 4000 },
  { date: 'May 6', stress: 35, bodyBattery: 90, steps: 8500 },
  { date: 'May 7', stress: 50, bodyBattery: 70, steps: 10500 },
  { date: 'May 8', stress: 70, bodyBattery: 30, steps: 2000 },
  { date: 'May 9', stress: 40, bodyBattery: 80, steps: 7500 },
];

export default function DashboardPage() {
  // Logic to toggle metrics on/off
  const [showStress, setShowStress] = useState(true);
  const [showBattery, setShowBattery] = useState(true);
  const [showSteps, setShowSteps] = useState(true);

  return (
    <div className="p-8 space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-slate-900">7-Day Snapshot</h1>
        <p className="text-slate-500 mt-1">Interactive overview of your recent health metrics.</p>
      </header>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <h2 className="text-lg font-semibold text-slate-800">Metric Correlation Explorer</h2>
          
          {/* Legend / Toggle Buttons */}
          <div className="flex flex-wrap gap-2">
            <button 
              onClick={() => setShowStress(!showStress)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${showStress ? 'bg-orange-100 text-orange-700 ring-1 ring-orange-200' : 'bg-slate-50 text-slate-400'}`}
            >
              <Activity size={16} /> Stress
            </button>
            <button 
              onClick={() => setShowBattery(!showBattery)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${showBattery ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-200' : 'bg-slate-50 text-slate-400'}`}
            >
              <Battery size={16} /> Body Battery
            </button>
            <button 
              onClick={() => setShowSteps(!showSteps)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${showSteps ? 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200' : 'bg-slate-50 text-slate-400'}`}
            >
              <Footprints size={16} /> Steps
            </button>
          </div>
        </div>

        {/* The Chart Interface */}
        <div className="h-[450px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dummyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="date" 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94a3b8', fontSize: 12}} 
                dy={10}
              />
              
              {/* Left axis for 0-100 metrics */}
              <YAxis 
                yAxisId="left" 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94a3b8', fontSize: 12}} 
                domain={[0, 100]}
              />
              
              {/* Right axis specifically for high-volume Step counts */}
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                axisLine={false} 
                tickLine={false} 
                tick={{fill: '#94a3b8', fontSize: 12}} 
              />
              
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
              />
              
              {showStress && (
                <Line 
                  yAxisId="left" 
                  type="monotone" 
                  dataKey="stress" 
                  stroke="#ea580c" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: '#ea580c' }} 
                  activeDot={{ r: 7 }} 
                />
              )}
              {showBattery && (
                <Line 
                  yAxisId="left" 
                  type="monotone" 
                  dataKey="bodyBattery" 
                  stroke="#2563eb" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: '#2563eb' }} 
                  activeDot={{ r: 7 }} 
                />
              )}
              {showSteps && (
                <Line 
                  yAxisId="right" 
                  type="monotone" 
                  dataKey="steps" 
                  stroke="#10b981" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: '#10b981' }} 
                  activeDot={{ r: 7 }} 
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}