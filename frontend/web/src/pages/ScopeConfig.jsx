import React from 'react';
export default function ScopeConfig({ username, email, onStartScan }) {
  const [scanType, setScanType] = React.useState('web');
  const [targets, setTargets] = React.useState('');
  const [confirmation, setConfirmation] = React.useState('');
  
  const isAuthorized = confirmation === 'I AUTHORIZE';
  
  // Dynamic placeholder based on scan type
  const placeholder = scanType === 'web' 
      ? 'https://site1.com, https://site2.com'
      : '192.168.1.0/24, 10.0.0.5';
  
  const handleStartScan = () => {
      if (isAuthorized) {
          // Parse comma-separated targets
          const targetList = targets.split(',').map(t => t.trim()).filter(t => t);
          onStartScan(scanType, targetList);
      }
  };

  return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
          <div className="max-w-2xl w-full mx-4 p-8 bg-gray-800 rounded-lg shadow-xl">
              <h1 className="text-3xl font-bold text-white mb-2">
                  Scope Configuration
              </h1>
              <p className="text-gray-400 mb-8">
                  Welcome, {username}
              </p>
              
              <div className="space-y-6">
                  {/* Scan Type Radio Group */}
                  <div>
                      <label className="block text-sm font-medium text-gray-300 mb-3">
                          Scan Type
                      </label>
                      <div className="space-y-3">
                          <label className="flex items-center space-x-3 cursor-pointer">
                              <input
                                  type="radio"
                                  name="scanType"
                                  value="web"
                                  checked={scanType === 'web'}
                                  onChange={(e) => setScanType(e.target.value)}
                                  className="w-4 h-4 text-blue-600 border-gray-600 focus:ring-blue-500 bg-gray-700"
                              />
                              <span className="text-gray-300">Web Target (URL)</span>
                          </label>
                          <label className="flex items-center space-x-3 cursor-pointer">
                              <input
                                  type="radio"
                                  name="scanType"
                                  value="network"
                                  checked={scanType === 'network'}
                                  onChange={(e) => setScanType(e.target.value)}
                                  className="w-4 h-4 text-blue-600 border-gray-600 focus:ring-blue-500 bg-gray-700"
                              />
                              <span className="text-gray-300">Network Target (IP Range)</span>
                          </label>
                      </div>
                  </div>

                  {/* Targets Textarea */}
                  <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                          Target(s) <span className="text-gray-500">(comma-separated for multiple)</span>
                      </label>
                      <textarea
                          value={targets}
                          onChange={(e) => setTargets(e.target.value)}
                          placeholder={placeholder}
                          rows="4"
                          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 text-white placeholder-gray-500 resize-none"
                      />
                  </div>

                  {/* Warning Label */}
                  <div className="bg-red-900 bg-opacity-30 border border-red-500 rounded-lg p-4">
                      <p className="text-red-400 font-semibold text-center">
                          ⚠️ Unauthorized testing is a violation of the CFAA.
                      </p>
                  </div>

                  {/* Confirmation Input */}
                  <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                          Type "I AUTHORIZE" to confirm permission
                      </label>
                      <input
                          type="text"
                          value={confirmation}
                          onChange={(e) => setConfirmation(e.target.value)}
                          placeholder="I AUTHORIZE"
                          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 text-white placeholder-gray-500"
                      />
                  </div>

                  {/* Start Scan Button */}
                  <button
                      onClick={handleStartScan}
                      disabled={!isAuthorized}
                      className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
                  >
                      Start Scan
                  </button>
              </div>
          </div>
      </div>
  );
}
