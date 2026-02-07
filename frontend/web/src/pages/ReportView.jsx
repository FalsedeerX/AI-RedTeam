import React from 'react';
export default function ReportView({ targets, reportType, onDownloadPDF, onStartNewScan }) {
  const timestamp = new Date().toLocaleString();
  const targetDisplay = targets.join(', ');
  
  // Determine content based on report type
  const isSQLInjection = reportType === 'sql_injection';
  const isSensitiveData = reportType === 'sensitive_data';

  return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-8">
          <div className="max-w-4xl w-full bg-white rounded-lg shadow-2xl p-8 border-2 border-gray-300">
              {/* Header */}
              <div className="border-b-2 border-gray-300 pb-6 mb-6">
                  <h1 className="text-4xl font-bold text-gray-900 mb-2">
                      Security Assessment Report
                  </h1>
                  <div className="flex justify-between items-center text-gray-600">
                      <div>
                          <p className="text-lg">
                              <span className="font-semibold">Target:</span> {targetDisplay}
                          </p>
                          <p className="text-sm mt-1">
                              <span className="font-semibold">Generated:</span> {timestamp}
                          </p>
                      </div>
                      <div className="text-right">
                          <p className="text-sm">AI RedTeam Platform</p>
                          <p className="text-xs text-gray-500">Purdue University</p>
                      </div>
                  </div>
              </div>

              {/* Security Score Card - Conditional */}
              <div className="mb-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">Security Scorecard</h2>
                  
                  {isSQLInjection && (
                      <div className="flex items-center gap-8 bg-red-50 border-2 border-red-300 rounded-lg p-6">
                          <div className="flex-shrink-0">
                              <div className="w-32 h-32 rounded-full bg-red-600 flex items-center justify-center border-4 border-red-800">
                                  <span className="text-6xl font-bold text-white">F</span>
                              </div>
                              <p className="text-center mt-2 font-bold text-red-800">Security Score</p>
                          </div>
                          <div className="flex-1">
                              <p className="text-lg font-semibold text-gray-900 mb-2">
                                  Critical Vulnerabilities Detected
                              </p>
                              <p className="text-gray-700">
                                  Your application contains high-severity security flaws that require immediate attention. 
                                  Exploitation of these vulnerabilities could lead to complete system compromise.
                              </p>
                          </div>
                      </div>
                  )}
                  
                  {isSensitiveData && (
                      <div className="flex items-center gap-8 bg-orange-50 border-2 border-orange-400 rounded-lg p-6">
                          <div className="flex-shrink-0">
                              <div className="w-32 h-32 rounded-full bg-orange-500 flex items-center justify-center border-4 border-orange-700">
                                  <span className="text-6xl font-bold text-white">C-</span>
                              </div>
                              <p className="text-center mt-2 font-bold text-orange-800">Security Score</p>
                          </div>
                          <div className="flex-1">
                              <p className="text-lg font-semibold text-gray-900 mb-2">
                                  High-Risk Data Exposure Detected
                              </p>
                              <p className="text-gray-700">
                                  Sensitive backup files are publicly accessible, potentially exposing confidential data. 
                                  While less severe than active exploitation, this represents a significant security risk.
                              </p>
                          </div>
                      </div>
                  )}
              </div>

              {/* Findings Section - Conditional */}
              <div className="mb-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">Vulnerability Findings</h2>
                  
                  {isSQLInjection && (
                      <div className="space-y-4">
                          <div className="border-2 border-red-400 rounded-lg p-6 bg-red-50">
                              <div className="flex items-start gap-3">
                                  <span className="text-3xl">🔴</span>
                                  <div className="flex-1">
                                      <h3 className="text-xl font-bold text-red-800 mb-2">
                                          Critical: SQL Injection Vulnerability
                                      </h3>
                                      <p className="text-gray-700 mb-2">
                                          <span className="font-semibold">CWE-89:</span> Improper Neutralization of Special Elements used in an SQL Command
                                      </p>
                                      <p className="text-gray-700 mb-2">
                                          <span className="font-semibold">Location:</span> Login form authentication endpoint
                                      </p>
                                      <p className="text-gray-700">
                                          <span className="font-semibold">Risk:</span> Attackers can bypass authentication, extract sensitive data, 
                                          modify database contents, or execute administrative operations.
                                      </p>
                                  </div>
                              </div>
                          </div>
                          <div className="bg-gray-100 border border-gray-300 rounded-lg p-4">
                              <p className="text-sm text-gray-600">
                                  <span className="font-semibold">CVSS Score:</span> 9.8 (Critical) | 
                                  <span className="font-semibold"> Impact:</span> Confidentiality Loss, Integrity Loss, Availability Loss
                              </p>
                          </div>
                      </div>
                  )}
                  
                  {isSensitiveData && (
                      <div className="space-y-4">
                          <div className="border-2 border-orange-400 rounded-lg p-6 bg-orange-50">
                              <div className="flex items-start gap-3">
                                  <span className="text-3xl">🟠</span>
                                  <div className="flex-1">
                                      <h3 className="text-xl font-bold text-orange-800 mb-2">
                                          High: Sensitive Data Exposure
                                      </h3>
                                      <p className="text-gray-700 mb-2">
                                          <span className="font-semibold">CWE-200:</span> Exposure of Sensitive Information to an Unauthorized Actor
                                      </p>
                                      <p className="text-gray-700 mb-2">
                                          <span className="font-semibold">Location:</span> Publicly accessible backup file (database.bak)
                                      </p>
                                      <p className="text-gray-700">
                                          <span className="font-semibold">Risk:</span> Unprotected backup file found publicly accessible. 
                                          Contains sensitive database information including user credentials and personal data.
                                      </p>
                                  </div>
                              </div>
                          </div>
                          <div className="bg-gray-100 border border-gray-300 rounded-lg p-4">
                              <p className="text-sm text-gray-600">
                                  <span className="font-semibold">CVSS Score:</span> 7.5 (High) | 
                                  <span className="font-semibold"> Impact:</span> Confidentiality Loss
                              </p>
                          </div>
                      </div>
                  )}
              </div>

              {/* Remediation Section - Conditional */}
              <div className="mb-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">AI-Generated Remediation</h2>
                  
                  {isSQLInjection && (
                      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-300 rounded-lg p-6">
                          <div className="flex items-start gap-3 mb-4">
                              <span className="text-2xl">🤖</span>
                              <div>
                                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                                      Recommended Fix
                                  </h3>
                                  <p className="text-gray-700 mb-3">
                                      Replace all dynamic SQL query construction with parameterized prepared statements 
                                      to ensure user input is properly sanitized.
                                  </p>
                              </div>
                          </div>
                          <div className="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded overflow-x-auto">
                              <p className="text-gray-500"># Before (Vulnerable):</p>
                              <p className="text-red-400">query = "SELECT * FROM users WHERE username='" + user_input + "'"</p>
                              <p className="mt-2 text-gray-500"># After (Secure):</p>
                              <p className="text-green-400">query = "SELECT * FROM users WHERE username=?"</p>
                              <p className="text-green-400">cursor.execute(query, (user_input,))</p>
                          </div>
                          <p className="text-sm text-gray-600 mt-4">
                              <span className="font-semibold">Priority:</span> Immediate | 
                              <span className="font-semibold"> Effort:</span> Low | 
                              <span className="font-semibold"> Effectiveness:</span> High
                          </p>
                      </div>
                  )}
                  
                  {isSensitiveData && (
                      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-300 rounded-lg p-6">
                          <div className="flex items-start gap-3 mb-4">
                              <span className="text-2xl">🤖</span>
                              <div>
                                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                                      Recommended Fix
                                  </h3>
                                  <p className="text-gray-700 mb-3">
                                      Restrict access to .bak files in web server configuration to prevent public access to sensitive backup files.
                                  </p>
                              </div>
                          </div>
                          <div className="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded overflow-x-auto">
                              <p className="text-gray-500"># Apache .htaccess:</p>
                              <p className="text-green-400">&lt;FilesMatch "\.(bak|backup|old|sql)$"&gt;</p>
                              <p className="text-green-400">  Require all denied</p>
                              <p className="text-green-400">&lt;/FilesMatch&gt;</p>
                              <p className="mt-2 text-gray-500"># Nginx configuration:</p>
                              <p className="text-green-400">location ~* \.(bak|backup|old|sql)$ &#123;</p>
                              <p className="text-green-400">  deny all;</p>
                              <p className="text-green-400">&#125;</p>
                          </div>
                          <p className="text-sm text-gray-600 mt-4">
                              <span className="font-semibold">Priority:</span> High | 
                              <span className="font-semibold"> Effort:</span> Low | 
                              <span className="font-semibold"> Effectiveness:</span> High
                          </p>
                      </div>
                  )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 pt-6 border-t-2 border-gray-300">
                  <button
                      onClick={onDownloadPDF}
                      className="flex-1 bg-blue-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg flex items-center justify-center gap-2"
                  >
                      <span>📥</span>
                      <span>Download PDF Report</span>
                  </button>
                  <button
                      onClick={onStartNewScan}
                      className="flex-1 bg-purple-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-purple-700 transition-colors text-lg flex items-center justify-center gap-2"
                  >
                      <span>🔄</span>
                      <span>Exit & Start New Scan</span>
                  </button>
              </div>

              {/* Footer */}
              <div className="mt-6 pt-4 border-t border-gray-200 text-center text-xs text-gray-500">
                  <p>This report was generated by AI RedTeam autonomous security assessment platform.</p>
                  <p className="mt-1">For questions or support, contact the development team at Purdue University.</p>
              </div>
          </div>
      </div>
  );
}
