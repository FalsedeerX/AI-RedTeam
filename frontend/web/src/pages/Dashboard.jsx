// TODO: Migrate from demo.html lines 533-899
export default function Dashboard({ username, email, targets, scanType }) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full mx-4 p-8 bg-gray-800 text-white rounded-lg shadow-xl">
        <h1 className="text-3xl font-bold mb-4">
          Dashboard Page
        </h1>
        <p className="text-gray-400">Placeholder - will be migrated from demo.html</p>
        <div className="mt-4 text-gray-500">
          <p>Welcome, {username}</p>
          <p>Targets: {targets?.join(', ')}</p>
          <p>Scan Type: {scanType}</p>
        </div>
      </div>
    </div>
  );
}
