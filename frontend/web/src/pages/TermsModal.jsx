// TODO: Migrate from demo.html lines 93-179
export default function TermsModal({ username, email, onAccept, onDecline }) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-3xl w-full mx-4 bg-gray-800 rounded-lg shadow-2xl border-2 border-yellow-500 p-8">
        <h1 className="text-3xl font-bold text-yellow-400 text-center mb-4">
          TermsModal Page
        </h1>
        <p className="text-white text-center">Placeholder - will be migrated from demo.html</p>
        <p className="text-gray-400 text-center mt-4">User: {username} ({email})</p>
      </div>
    </div>
  );
}
