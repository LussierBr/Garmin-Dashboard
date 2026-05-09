export default function AgentPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto h-full flex flex-col">
      <h1 className="text-2xl font-bold mb-4">AI Data Agent</h1>
      <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-4 overflow-y-auto">
        <p className="text-slate-400 italic text-center mt-20">Ask a question about your Garmin data to generate a custom chart...</p>
      </div>
      <div className="flex gap-2">
        <input 
          className="flex-1 p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="e.g. Compare my stress to my steps over the last month..."
        />
        <button className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700">Ask</button>
      </div>
    </div>
  );
}