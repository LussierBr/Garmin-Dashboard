import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { LayoutDashboard, Sparkles, Lock } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Brody's Garmin Analytics",
  description: "AI-powered health insights and forecasting",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} flex h-screen bg-slate-50`}>
        {/* Sidebar / Drawer */}
        <nav className="w-64 bg-white border-r border-slate-200 flex flex-col p-4">
          <div className="mb-8 px-2 font-bold text-xl text-indigo-600">Garmin Dashboard</div>
          
          <div className="space-y-2 flex-1">
            <Link href="/dashboard" className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-100 text-slate-700 transition-all font-medium">
              <LayoutDashboard size={20} /> 7-Day Snapshot
            </Link>
            <Link href="/agent" className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-100 text-slate-700 transition-all font-medium">
              <Sparkles size={20} /> AI Data Agent
            </Link>
          </div>

          <Link href="/admin" className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-900 transition-all text-sm font-medium border-t border-slate-100 pt-4">
            <Lock size={16} /> Admin / Brody Only
          </Link>
        </nav>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </body>
    </html>
  );
}