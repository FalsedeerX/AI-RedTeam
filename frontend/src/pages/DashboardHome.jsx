import React from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost, apiDelete } from '../lib/api';

// Infer a relative time label from an ISO date string.
function relativeTime(isoStr) {
  if (!isoStr) return null;
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(isoStr).toLocaleDateString();
}

export default function DashboardHome() {
  const navigate = useNavigate();
  const [projects, setProjects] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');

  // New project modal state
  const [showModal, setShowModal] = React.useState(false);
  const [newName, setNewName] = React.useState('');
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState('');

  // Delete confirmation
  const [confirmDelete, setConfirmDelete] = React.useState(null);

  const modalRef = React.useRef(null);
  const inputRef = React.useRef(null);

  React.useEffect(() => {
    loadProjects();
  }, []);

  // Focus input when modal opens
  React.useEffect(() => {
    if (showModal) inputRef.current?.focus();
  }, [showModal]);

  async function loadProjects() {
    setLoading(true);
    setError('');
    try {
      const data = await apiGet('/projects');
      setProjects(data);
    } catch (err) {
      setError(`Could not load projects: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateProject() {
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    setCreateError('');
    try {
      const created = await apiPost('/projects', { name });
      setProjects(prev => [...prev, created]);
      setShowModal(false);
      setNewName('');
      navigate(`/projects/${created.id}`);
    } catch (err) {
      setCreateError(`Failed to create project: ${err.message}`);
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteProject(project) {
    try {
      await apiDelete(`/projects/${project.id}`);
      setProjects(prev => prev.filter(p => p.id !== project.id));
      setConfirmDelete(null);
    } catch (err) {
      setError(`Failed to delete project: ${err.message}`);
      setConfirmDelete(null);
    }
  }

  const totalProjects = projects.length;

  return (
    <div className="min-h-screen" style={{ background: 'var(--rt-bg)' }}>
      <div className="max-w-6xl mx-auto px-8 py-8">

        {/* Page header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--rt-text)', letterSpacing: '-0.5px' }}>
              Dashboard
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--rt-muted)' }}>
              Overview of your security assessments
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-85"
            style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
          >
            <span className="text-base leading-none">+</span>
            New Project
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div
            className="mb-6 flex items-start justify-between gap-3 px-4 py-3 rounded-lg text-sm"
            style={{ background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.3)', color: 'var(--rt-ember)' }}
          >
            <span>{error}</span>
            <button onClick={() => setError('')} className="text-xs underline flex-shrink-0">Dismiss</button>
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Total Projects"
            value={loading ? '—' : String(totalProjects)}
            sub={loading ? 'Loading…' : totalProjects === 1 ? '1 project' : `${totalProjects} projects`}
          />
          <StatCard label="Critical Findings" value="—" sub="TBD" accent="var(--rt-ember)" />
          <StatCard label="Scans Run" value="—" sub="TBD" accent="var(--rt-amber)" />
          <StatCard label="Reports Exported" value="—" sub="TBD" accent="var(--rt-leaf)" />
        </div>

        {/* Projects section */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>Your Projects</h2>
        </div>

        {loading ? (
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[1, 2, 3].map(i => (
              <div
                key={i}
                className="rounded-lg animate-pulse"
                style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)', height: '140px' }}
              />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div
            className="rounded-lg mb-8 py-16 text-center"
            style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
          >
            <p className="text-3xl mb-3 opacity-30">📁</p>
            <p className="text-sm font-semibold mb-1" style={{ color: 'var(--rt-muted)' }}>No projects yet</p>
            <p className="text-xs mb-5" style={{ color: 'var(--rt-dim)' }}>Create a project to start your first security assessment.</p>
            <button
              onClick={() => setShowModal(true)}
              className="px-5 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-85"
              style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
            >
              + Create your first project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {projects.map(project => (
              <ProjectCard
                key={project.id}
                project={project}
                onOpen={() => navigate(`/projects/${project.id}`)}
                onDelete={() => setConfirmDelete(project)}
              />
            ))}
            {/* New project card */}
            <button
              onClick={() => setShowModal(true)}
              className="rounded-lg flex flex-col items-center justify-center gap-2 min-h-[130px] transition-colors"
              style={{
                background: 'transparent',
                border: '1px dashed var(--rt-border)',
                color: 'var(--rt-muted)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--rt-border-bright)'; e.currentTarget.style.color = 'var(--rt-text)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--rt-border)'; e.currentTarget.style.color = 'var(--rt-muted)'; }}
            >
              <span className="text-2xl opacity-40">＋</span>
              <span className="text-sm font-medium">Create new project</span>
            </button>
          </div>
        )}

        {/* Activity feed */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>Recent Activity</h2>
        </div>
        <div
          className="rounded-lg overflow-hidden"
          style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
        >
          <div className="py-12 text-center">
            <p className="text-2xl mb-3 opacity-20">📋</p>
            <p className="text-sm font-medium mb-1" style={{ color: 'var(--rt-muted)' }}>Activity log coming soon</p>
            <p className="text-xs" style={{ color: 'var(--rt-dim)' }}>Scan events, HITL approvals, and report exports will appear here.</p>
          </div>
        </div>

      </div>

      {/* New Project Modal */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={e => { if (e.target === e.currentTarget) { setShowModal(false); setNewName(''); setCreateError(''); } }}
        >
          <div
            ref={modalRef}
            className="w-full max-w-sm rounded-xl p-6 shadow-2xl"
            style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border-bright)' }}
          >
            <h2 className="text-base font-bold mb-1" style={{ color: 'var(--rt-text)' }}>New Project</h2>
            <p className="text-xs mb-5" style={{ color: 'var(--rt-muted)' }}>
              Give your engagement a clear, descriptive name.
            </p>

            {createError && (
              <p className="text-xs mb-3 px-3 py-2 rounded" style={{ background: 'rgba(248,81,73,0.1)', color: 'var(--rt-ember)' }}>
                {createError}
              </p>
            )}

            <input
              ref={inputRef}
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateProject()}
              placeholder="e.g. Juice Shop Assessment"
              className="w-full px-3 py-2 rounded-lg text-sm mb-4 outline-none focus:ring-1 font-mono"
              style={{
                background: 'var(--rt-surface2)',
                border: '1px solid var(--rt-border)',
                color: 'var(--rt-text)',
              }}
              onFocus={e => { e.target.style.borderColor = 'var(--rt-sky)'; }}
              onBlur={e => { e.target.style.borderColor = 'var(--rt-border)'; }}
            />

            <div className="flex gap-3">
              <button
                onClick={() => { setShowModal(false); setNewName(''); setCreateError(''); }}
                className="flex-1 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: 'var(--rt-surface2)', border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newName.trim() || creating}
                className="flex-1 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
              >
                {creating ? 'Creating…' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
        >
          <div
            className="w-full max-w-sm rounded-xl p-6 shadow-2xl"
            style={{ background: 'var(--rt-surface)', border: '1px solid rgba(248,81,73,0.4)' }}
          >
            <h2 className="text-base font-bold mb-2" style={{ color: 'var(--rt-text)' }}>Delete Project?</h2>
            <p className="text-sm mb-5" style={{ color: 'var(--rt-muted)' }}>
              This will permanently delete{' '}
              <strong style={{ color: 'var(--rt-text)' }}>{confirmDelete.name}</strong> and all its
              targets. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 py-2 rounded-lg text-sm font-medium"
                style={{ background: 'var(--rt-surface2)', border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteProject(confirmDelete)}
                className="flex-1 py-2 rounded-lg text-sm font-semibold"
                style={{ background: 'var(--rt-ember)', color: 'white' }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }) {
  return (
    <div
      className="rounded-lg px-5 py-4"
      style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
    >
      <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--rt-muted)' }}>
        {label}
      </p>
      <p className="font-mono text-3xl font-bold leading-none mb-1" style={{ color: accent || 'var(--rt-text)' }}>
        {value}
      </p>
      <p className="text-xs" style={{ color: 'var(--rt-dim)' }}>{sub}</p>
    </div>
  );
}

function ProjectCard({ project, onOpen, onDelete }) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      className="rounded-lg relative overflow-hidden cursor-pointer transition-colors"
      style={{
        background: hovered ? 'var(--rt-surface2)' : 'var(--rt-surface)',
        border: `1px solid ${hovered ? 'var(--rt-border-bright)' : 'var(--rt-border)'}`,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onOpen}
    >
      {/* Top accent bar on hover */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 transition-opacity"
        style={{
          background: 'linear-gradient(90deg, var(--rt-sky), var(--rt-orchid))',
          opacity: hovered ? 1 : 0,
        }}
      />

      <div className="p-5">
        <p className="text-sm font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>
          {project.name}
        </p>
        <p className="font-mono text-xs mb-4" style={{ color: 'var(--rt-muted)' }}>
          {project.created_at ? `Created ${relativeTime(project.created_at)}` : 'New project'}
        </p>

        <div
          className="flex items-center justify-between pt-3"
          style={{ borderTop: '1px solid var(--rt-border)' }}
        >
          <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--rt-muted)' }}>
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: 'var(--rt-leaf)', boxShadow: '0 0 5px var(--rt-leaf)' }}
            />
            Active
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={e => { e.stopPropagation(); onDelete(); }}
              className="text-xs px-2 py-1 rounded transition-colors"
              style={{ color: 'var(--rt-dim)', border: '1px solid var(--rt-border)' }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--rt-ember)'; e.currentTarget.style.borderColor = 'rgba(248,81,73,0.4)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--rt-dim)'; e.currentTarget.style.borderColor = 'var(--rt-border)'; }}
              title="Delete project"
            >
              ✕
            </button>
            <button
              onClick={e => { e.stopPropagation(); onOpen(); }}
              className="text-xs font-medium transition-colors"
              style={{ color: 'var(--rt-sky)' }}
            >
              Open →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
