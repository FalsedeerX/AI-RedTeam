export default function EmailEntry({ onVerify }) {
  const [email, setEmail] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  // fucntion handles api call
  const handleSubmit = async (e) => {
      e.preventDefault();
      if (!email.trim()) {
          setError('Please enter an email.');
          return;
      }
      
      setIsLoading(true);
      setError('');

      try {
          const response = await fetch('http://127.0.0.1:5000/verify', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ email: email }),
          });

          const data = await response.json();

          if (response.ok && data.success) {
              
              onVerify(data.username, data.email);
          } else {
          
              setError(data.message || 'Verification failed.');
          }

      } catch (err) {
      
          console.error('Fetch error:', err);
          setError('Could not connect to the server. Is it running?');
      } finally {
          setIsLoading(false);
      }
  };

  return (
      <div className="min-h-screen bg-white flex items-center justify-center">
          <div className="max-w-md w-full mx-4 text-center">
              <h1 className="text-4xl font-bold text-black mb-8">
                  Protect your business with AI - enter your email to get started
              </h1>
              <form onSubmit={handleSubmit} className="space-y-6">
                  <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter your email"
                      className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 text-black"
                      required
                      disabled={isLoading}
                  />
                  {error && <p className="text-red-500 text-sm">{error}</p>}
                  <button
                      type="submit"
                      className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                      disabled={isLoading}
                  >
                      {isLoading ? 'Verifying...' : 'Verify'}
                  </button>
              </form>
          </div>
      </div>
  );
}
