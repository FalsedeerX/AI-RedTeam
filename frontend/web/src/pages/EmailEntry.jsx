import React from 'react';
import { apiPost } from '../lib/api';

export default function EmailEntry({ onVerify }) {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  const handleSubmit = async (e) => {
      e.preventDefault();
      if (!email.trim() || !password.trim()) {
          setError('Please enter your email and password.');
          return;
      }

      setIsLoading(true);
      setError('');

      try {
          let userId;

          // Attempt to register; if email already exists (409), fall back to login.
          try {
              const registered = await apiPost('/users/register', { email, password });
              userId = registered.id;
          } catch (registerErr) {
              if (registerErr.message && registerErr.message.includes('409')) {
                  const authed = await apiPost('/users/auth', { email, password });
                  userId = authed.user_id;
              } else {
                  throw registerErr;
              }
          }

          // Derive a display name from the email prefix for example -  "paul" from "paul@example.com"
          const username = email.split('@')[0];
          onVerify(username, email, userId);
      } catch (err) {
          console.error('Auth error:', err);
          setError(err.message || 'Could not connect to the server. Is it running?');
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
                  <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter your password"
                      className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 text-black"
                      required
                      disabled={isLoading}
                      minLength={8}
                  />
                  <p className="text-gray-500 text-xs -mt-3 text-left">
                      New users are registered automatically. Returning users are logged in.
                  </p>
                  {error && <p className="text-red-500 text-sm">{error}</p>}
                  <button
                      type="submit"
                      className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                      disabled={isLoading}
                  >
                      {isLoading ? 'Signing in...' : 'Continue'}
                  </button>
              </form>
          </div>
      </div>
  );
}
