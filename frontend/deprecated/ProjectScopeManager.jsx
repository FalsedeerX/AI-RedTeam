import React from 'react';
import { apiGet, apiPost, apiDelete } from '../lib/api';

// ---------------------------------------------------------------------------
// API contract assumptions (update TODOs when backend routes are confirmed):
//
//   GET  /projects                           → Project[]
//   POST /projects                body: { name: string }    → Project
//   GET  /projects/:id/targets               → Target[]
//   POST /projects/:id/targets    body: { value: string }   → Target
//      TODO: if backend expects bulk { targets: string[] }, change handleAddTarget
//   DELETE /projects/:id/targets/:targetId                  → 204 | { success }
//
// Project shape: { id: string, name: string, created_at?: string }
// Target shape:  { id: string, value: string }
// ---------------------------------------------------------------------------

export default function ProjectScopeManager({ username, onStartScan }) {
  const [projects, setProjects] = React.useState([]);
  const [selectedProject, setSelectedProject] = React.useState(null);
  const [targets, setTargets] = React.useState([]);

  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState('');
  const [newTargetValue, setNewTargetValue] = React.useState('');

  const [scanType, setScanType] = React.useState('web');
  const [confirmation, setConfirmation] = React.useState('');

  const [loadingProjects, setLoadingProjects] = React.useState(false);
  const [loadingTargets, setLoadingTargets] = React.useState(false);
  const [error, setError] = React.useState('');

  const isAuthorized = confirmation === 'I AUTHORIZE';
  const canStart = isAuthorized && selectedProject !== null && targets.length > 0;

  // ---- Load projects on mount ----
  React.useEffect(() => {
    loadProjects();
  }, []);

  // ---- Load targets whenever selected project changes ----
  React.useEffect(() => {
    if (selectedProject) {
      loadTargets(selectedProject.id);
    } else {
      setTargets([]);
    }
  }, [selectedProject]);

  async function loadProjects() {
    setLoadingProjects(true);
    setError('');
    try {
      // TODO: Confirm the response is a bare array, not { data: [] } or similar
      const data = await apiGet('/projects');
      setProjects(data);
    } catch (err) {
      // Backend may not be wired yet — degrade gracefully to empty list
      setError(`Could not load projects: ${err.message}`);
    } finally {
      setLoadingProjects(false);
    }
  }

  async function loadTargets(projectId) {
    setLoadingTargets(true);
    try {
      // TODO: Confirm the response is a bare array, not { data: [] } or similar
      const data = await apiGet(`/projects/${projectId}/targets`);
      setTargets(data);
    } catch (err) {
      setError(`Could not load targets: ${err.message}`);
      setTargets([]);
    } finally {
      setLoadingTargets(false);
    }
  }

  // ---- Project CRUD ----

  async function handleCreateProject() {
    const name = newProjectName.trim();
    if (!name) return;

    // Optimistic: insert with a temp id immediately so UI feels instant
    const tempProject = { id: `temp-${Date.now()}`, name };
    setProjects(prev => [...prev, tempProject]);
    setSelectedProject(tempProject);
    setNewProjectName('');
    setShowCreateModal(false);

    try {
      // TODO: Confirm POST /projects returns the full project object { id, name, ... }
      const created = await apiPost('/projects', { name });
      setProjects(prev => prev.map(p => (p.id === tempProject.id ? created : p)));
      setSelectedProject(created);
    } catch (err) {
      // Rollback optimistic insert
      setProjects(prev => prev.filter(p => p.id !== tempProject.id));
      setSelectedProject(null);
      setError(`Failed to create project: ${err.message}`);
    }
  }

  // ---- Target CRUD ----

  async function handleAddTarget() {
    const value = newTargetValue.trim();
    if (!value || !selectedProject) return;

    // Optimistic add
    const tempTarget = { id: `temp-${Date.now()}`, value };
    setTargets(prev => [...prev, tempTarget]);
    setNewTargetValue('');

    try {
      // TODO: If backend expects bulk format { targets: string[] }, change body below
      const created = await apiPost(`/projects/${selectedProject.id}/targets`, { value });
      setTargets(prev => prev.map(t => (t.id === tempTarget.id ? created : t)));
    } catch (err) {
      // Rollback optimistic add
      setTargets(prev => prev.filter(t => t.id !== tempTarget.id));
      setError(`Failed to add target: ${err.message}`);
    }
  }

  async function handleRemoveTarget(target) {
    // Optimistic remove
    setTargets(prev => prev.filter(t => t.id !== target.id));

    // Targets that were never persisted (still have a temp id) need no API call
    if (String(target.id).startsWith('temp-')) return;

    try {
      // TODO: Confirm DELETE /projects/:id/targets/:targetId returns 204 or { success }
      await apiDelete(`/projects/${selectedProject.id}/targets/${target.id}`);
    } catch (err) {
      // Rollback optimistic remove
      setTargets(prev => [...prev, target]);
      setError(`Failed to remove target: ${err.message}`);
    }
  }

  // ---- Start scan ----

  function handleStartScan() {
    if (!canStart) return;
    const targetValues = targets.map(t => t.value);
    // projectId is forwarded to App so Dashboard can pass it to the run-start endpoint later
    onStartScan(scanType, targetValues, selectedProject.id);
  }

  const targetPlaceholder = scanType === 'web' ? 'https://example.com' : '192.168.1.0/24';

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full mx-4 p-8 bg-gray-800 rounded-lg shadow-xl">

        {/* Header */}
        <h1 className="text-3xl font-bold text-white mb-1">Project & Scope Configuration</h1>
        <p className="text-gray-400 mb-6">Welcome, {username}</p>

        {/* Error banner */}
        {error && (
          <div className="mb-5 bg-red-900 bg-opacity-30 border border-red-500 rounded-lg p-3 flex items-start justify-between gap-3">
            <p className="text-red-400 text-sm">{error}</p>
            <button
              onClick={() => setError('')}
              className="text-red-300 text-xs underline shrink-0"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* ── Two-panel layout ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">

          {/* Left panel: Project list */}
          <div className="bg-gray-700 rounded-lg p-4 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-white font-semibold">Projects</h2>
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-blue-600 text-white text-sm px-3 py-1 rounded hover:bg-blue-700 transition-colors"
              >
                + New
              </button>
            </div>

            {loadingProjects ? (
              <p className="text-gray-400 text-sm animate-pulse">Loading…</p>
            ) : projects.length === 0 ? (
              <p className="text-gray-500 text-sm">No projects yet. Create one to get started.</p>
            ) : (
              <ul className="space-y-1 overflow-y-auto max-h-52">
                {projects.map(project => (
                  <li key={project.id}>
                    <button
                      onClick={() => setSelectedProject(project)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                        selectedProject?.id === project.id
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {project.name}
                      {String(project.id).startsWith('temp-') && (
                        <span className="ml-2 text-xs text-blue-300 opacity-70">saving…</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Right panel: Target manager */}
          <div className="bg-gray-700 rounded-lg p-4 flex flex-col">
            <h2 className="text-white font-semibold mb-3">
              {selectedProject ? `Targets — ${selectedProject.name}` : 'Targets'}
            </h2>

            {!selectedProject ? (
              <p className="text-gray-500 text-sm">Select or create a project to manage targets.</p>
            ) : loadingTargets ? (
              <p className="text-gray-400 text-sm animate-pulse">Loading targets…</p>
            ) : (
              <div className="flex flex-col flex-1">
                {/* Target list */}
                {targets.length === 0 ? (
                  <p className="text-gray-500 text-sm mb-3">No targets yet. Add one below.</p>
                ) : (
                  <ul className="space-y-1.5 mb-3 overflow-y-auto max-h-40">
                    {targets.map(target => (
                      <li
                        key={target.id}
                        className="flex items-center justify-between bg-gray-600 rounded px-3 py-2"
                      >
                        <span className="text-gray-200 text-sm font-mono truncate flex-1 mr-2">
                          {target.value}
                        </span>
                        {String(target.id).startsWith('temp-') && (
                          <span className="text-xs text-blue-300 opacity-70 mr-2">saving…</span>
                        )}
                        <button
                          onClick={() => handleRemoveTarget(target)}
                          className="text-red-400 hover:text-red-300 text-sm shrink-0 transition-colors"
                          title="Remove target"
                        >
                          ✕
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {/* Add target row */}
                <div className="flex gap-2 mt-auto">
                  <input
                    type="text"
                    value={newTargetValue}
                    onChange={e => setNewTargetValue(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAddTarget()}
                    placeholder={targetPlaceholder}
                    className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={handleAddTarget}
                    disabled={!newTargetValue.trim()}
                    className="bg-green-600 text-white text-sm px-4 py-2 rounded hover:bg-green-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Bottom: scan type + legal + start ── */}
        <div className="space-y-4">

          {/* Scan type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Scan Type</label>
            <div className="flex gap-6">
              {[
                { value: 'web', label: 'Web Target (URL)' },
                { value: 'network', label: 'Network Target (IP Range)' },
              ].map(({ value, label }) => (
                <label key={value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="scanType"
                    value={value}
                    checked={scanType === value}
                    onChange={e => setScanType(e.target.value)}
                    className="w-4 h-4 text-blue-600 border-gray-600 bg-gray-700"
                  />
                  <span className="text-gray-300 text-sm">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* CFAA warning */}
          <div className="bg-red-900 bg-opacity-30 border border-red-500 rounded-lg p-3">
            <p className="text-red-400 font-semibold text-center text-sm">
              ⚠️ Unauthorized testing is a violation of the CFAA.
            </p>
          </div>

          {/* Authorization confirmation */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Type "I AUTHORIZE" to confirm permission
            </label>
            <input
              type="text"
              value={confirmation}
              onChange={e => setConfirmation(e.target.value)}
              placeholder="I AUTHORIZE"
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 text-white placeholder-gray-500"
            />
          </div>

          {/* Contextual hint below the auth field */}
          {!canStart && (
            <p className="text-gray-500 text-xs text-center -mt-1">
              {!selectedProject
                ? 'Select or create a project above to continue.'
                : targets.length === 0
                ? 'Add at least one target to continue.'
                : !isAuthorized
                ? 'Type "I AUTHORIZE" above to unlock the scan.'
                : ''}
            </p>
          )}

          {/* Start scan */}
          <button
            onClick={handleStartScan}
            disabled={!canStart}
            className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
          >
            Start Scan
          </button>
        </div>
      </div>

      {/* ── Create Project modal ── */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 border border-gray-600 shadow-2xl">
            <h2 className="text-white font-bold text-xl mb-4">New Project</h2>
            <input
              type="text"
              value={newProjectName}
              onChange={e => setNewProjectName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateProject()}
              placeholder="Project name"
              autoFocus
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setShowCreateModal(false); setNewProjectName(''); }}
                className="flex-1 bg-gray-600 text-white py-2 rounded-lg hover:bg-gray-500 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim()}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
