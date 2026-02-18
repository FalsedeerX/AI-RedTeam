import React from 'react';
export default function TermsModal({ username, email, onAccept, onDecline }) {
  return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
          <div className="max-w-3xl w-full mx-4 bg-gray-800 rounded-lg shadow-2xl border-2 border-yellow-500">
              {/* Header */}
              <div className="bg-gray-900 p-6 border-b-2 border-yellow-500">
                  <h1 className="text-3xl font-bold text-yellow-400 text-center mb-2">
                      ⚖️ LEGAL AGREEMENT REQUIRED
                  </h1>
                  <p className="text-gray-300 text-center">
                      Please review and accept the terms before proceeding
                  </p>
              </div>

              {/* Scrollable Legal Text */}
              <div className="p-6">
                  <div className="bg-gray-900 rounded-lg p-6 h-96 overflow-y-auto border border-gray-700">
                      <div className="text-white font-mono text-sm leading-relaxed space-y-4">
                          <h2 className="text-xl font-bold text-center mb-4 text-yellow-400">
                              AI REDTEAM – END USER LICENSE & LIABILITY AGREEMENT
                          </h2>
                          
                          <div className="space-y-4">
                              <div>
                                  <h3 className="font-bold text-yellow-300 mb-2">1. AUTHORIZED USE ONLY:</h3>
                                  <p className="text-gray-300">
                                      You acknowledge that this software is a dual-use security tool. You agree to use AI RedTeam SOLELY for defensive auditing of systems you own or have explicit written permission to test. Unauthorized scanning of third-party networks is a violation of the Computer Fraud and Abuse Act (CFAA) (18 U.S.C. § 1030).
                                  </p>
                              </div>

                              <div>
                                  <h3 className="font-bold text-yellow-300 mb-2">2. NO WARRANTY & DATA LOSS:</h3>
                                  <p className="text-gray-300">
                                      This software utilizes autonomous AI agents to execute active exploits. While safeguards are in place, you acknowledge that use of this tool carries inherent risks of service disruption, data corruption, or system instability. The developers provide this software "AS IS" without warranty of any kind.
                                  </p>
                              </div>

                              <div>
                                  <h3 className="font-bold text-yellow-300 mb-2">3. INDEMNIFICATION:</h3>
                                  <p className="text-gray-300">
                                      You agree to assume full legal and operational liability for all actions taken by the AI agent under your command. You hereby indemnify and hold harmless the AI RedTeam developers and Purdue University from any legal claims, damages, or liabilities arising from your use of this tool.
                                  </p>
                              </div>

                              <div>
                                  <h3 className="font-bold text-yellow-300 mb-2">4. AUDIT LOGGING:</h3>
                                  <p className="text-gray-300">
                                      You acknowledge that all engagement activities, including target scopes and executed commands, are cryptographically logged to a local immutable ledger for forensic purposes.
                                  </p>
                              </div>
                          </div>

                          <div className="mt-6 pt-4 border-t border-gray-700">
                              <p className="text-center text-gray-400 text-xs">
                                  By clicking "I Accept" below, you acknowledge that you have read, understood, and agree to be bound by this agreement.
                              </p>
                          </div>
                      </div>
                  </div>

                  {/* User Info */}
                  <div className="mt-4 text-center text-gray-400 text-sm">
                      <p>Agreement for: <span className="text-white font-semibold">{username}</span> ({email})</p>
                  </div>
              </div>

              {/* Action Buttons */}
              <div className="p-6 bg-gray-900 border-t-2 border-gray-700 flex gap-4">
                  <button
                      onClick={onDecline}
                      className="flex-1 bg-red-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-red-700 transition-colors text-lg"
                  >
                      ❌ Decline
                  </button>
                  <button
                      onClick={onAccept}
                      className="flex-1 bg-green-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-green-700 transition-colors text-lg"
                  >
                      ✓ I Accept
                  </button>
              </div>
          </div>
      </div>
  );
}
