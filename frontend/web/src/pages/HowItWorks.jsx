import React from 'react';
import { useNavigate } from 'react-router-dom';

const STEPS = [
  {
    num: '01',
    title: 'Create a Project',
    color: 'var(--rt-sky)',
    bg: 'rgba(121,192,255,0.1)',
    border: 'rgba(121,192,255,0.2)',
    body: (
      <>
        A <strong style={{ color: 'var(--rt-text)' }}>Project</strong> is the container for one
        engagement — think of it as a named folder for a specific system or client you&apos;re
        assessing. Give it a clear name (e.g. &quot;Juice Shop QA&quot; or &quot;Internal API
        Audit&quot;) so you can track multiple engagements separately. Click{' '}
        <strong style={{ color: 'var(--rt-sky)' }}>+ New Project</strong> from the dashboard to get
        started.
      </>
    ),
  },
  {
    num: '02',
    title: 'Define Your Targets',
    color: 'var(--rt-orchid)',
    bg: 'rgba(188,140,255,0.08)',
    border: 'rgba(188,140,255,0.2)',
    body: (
      <>
        Inside your project, add one or more{' '}
        <strong style={{ color: 'var(--rt-text)' }}>Targets</strong> — these are the URLs, IP
        addresses, or CIDR ranges you have authorization to test. The system auto-detects the target
        type. You can add multiple targets and scan them independently.{' '}
        <strong style={{ color: 'var(--rt-ember)' }}>
          Only add targets you own or have written permission to test.
        </strong>
      </>
    ),
  },
  {
    num: '03',
    title: 'Configure & Launch a Scan',
    color: 'var(--rt-amber)',
    bg: 'rgba(210,153,34,0.08)',
    border: 'rgba(210,153,34,0.2)',
    body: (
      <>
        Go to the <strong style={{ color: 'var(--rt-text)' }}>Scan</strong> tab, choose a target,
        and pick a scan mode.{' '}
        <strong style={{ color: 'var(--rt-text)' }}>Passive mode</strong> (default) is
        non-intrusive — it observes and fingerprints without sending attack payloads, safe for
        production. <strong style={{ color: 'var(--rt-text)' }}>Active mode</strong> sends test
        payloads and may trigger security alerts — use it only on isolated test environments. Type{' '}
        <strong style={{ color: 'var(--rt-ember)' }}>I AUTHORIZE</strong> to confirm you have
        permission, then hit Start Scan.
      </>
    ),
  },
  {
    num: '04',
    title: 'Approve or Deny High-Impact Actions (HITL Gate)',
    color: 'var(--rt-ember)',
    bg: 'rgba(248,81,73,0.07)',
    border: 'rgba(248,81,73,0.2)',
    body: (
      <>
        During a scan, the AI agent may propose{' '}
        <strong style={{ color: 'var(--rt-text)' }}>high-impact actions</strong> — commands that
        could modify state, disrupt services, or trigger alerts. The system will{' '}
        <strong style={{ color: 'var(--rt-text)' }}>pause and prompt you</strong> to approve or
        deny each one before it executes. This is the Human-in-the-Loop (HITL) gate — you are
        always the final decision-maker. You can kill the entire scan at any time using the emergency
        stop in the live terminal.
      </>
    ),
  },
  {
    num: '05',
    title: 'Review Findings & Export a Report',
    color: 'var(--rt-leaf)',
    bg: 'rgba(63,185,80,0.07)',
    border: 'rgba(63,185,80,0.2)',
    body: (
      <>
        After the scan completes, navigate to the{' '}
        <strong style={{ color: 'var(--rt-text)' }}>Findings</strong> tab to review all discovered
        vulnerabilities ranked by severity (Critical → Low). Each finding includes a description,
        affected target, CVE reference where available, and AI-generated remediation guidance. When
        ready, go to <strong style={{ color: 'var(--rt-text)' }}>Reports</strong> to export a
        structured report as <strong style={{ color: 'var(--rt-sky)' }}>JSON</strong> or{' '}
        <strong style={{ color: 'var(--rt-sky)' }}>PDF</strong>.
      </>
    ),
  },
];

const CONCEPTS = [
  {
    icon: '🧠',
    title: 'Local LLM — No Cloud',
    body: 'All AI inference runs locally via Ollama (qwen3:8b). Your targets, scan data, and findings never leave your machine.',
  },
  {
    icon: '📚',
    title: 'RAG Pipeline',
    body: 'The AI retrieves context from a local vector database (ChromaDB) seeded with security playbooks, OWASP docs, and prior scan outputs.',
  },
  {
    icon: '🔒',
    title: 'Severity Grades (A–F)',
    body: 'Each project receives a letter grade based on the distribution of findings. A = clean, F = critical unresolved issues.',
  },
  {
    icon: '⚖️',
    title: 'Legal Responsibility',
    body: 'Unauthorized security testing is a federal crime under the CFAA. The "I AUTHORIZE" confirmation is a legal acknowledgment — not a formality.',
  },
];

const FAQS = [
  {
    q: "What's the difference between Passive and Active mode?",
    a: "Passive mode observes and fingerprints without sending attack payloads — it's safe for production. Active mode sends real test payloads (e.g. SQL injection strings, fuzzing inputs) that may cause errors or trigger security alerts. Always use Active mode only on isolated test environments like DVWA or Juice Shop.",
  },
  {
    q: 'Can I run multiple scans at the same time?',
    a: 'Not currently. AI RedTeam is designed for single, controlled scan sessions. Running concurrent scans on the same machine would degrade LLM performance and make HITL gate management difficult. Parallel scan support is a planned future feature.',
  },
  {
    q: 'Does the AI ever take action without my approval?',
    a: 'No. Any action the AI agent classifies as "high-impact" — meaning it could modify remote state, disrupt a service, or trigger an alert — is gated behind the HITL modal. You must explicitly approve it before it executes. You can also kill the scan at any time.',
  },
  {
    q: 'What scanning tools does it use under the hood?',
    a: 'Currently: nmap for network/port scanning and Nikto for web server vulnerability scanning. SQLMap support is planned. All tools run as subprocesses and their output is parsed and fed back to the AI reasoning layer.',
  },
  {
    q: 'Where is my data stored?',
    a: 'All data — projects, targets, findings, reports, and scan logs — is stored in a local PostgreSQL database on your machine. LLM inference runs via Ollama locally. No data is transmitted to external servers.',
  },
];

export default function HowItWorks({ onComplete }) {
  const navigate = useNavigate();
  const [openFaq, setOpenFaq] = React.useState(null);

  const isOnboarding = typeof onComplete === 'function';

  function handleCta() {
    if (isOnboarding) {
      onComplete();
    } else {
      navigate('/dashboard');
    }
  }

  return (
    <div
      className="min-h-screen py-10 px-6"
      style={{ background: isOnboarding ? 'var(--rt-bg)' : 'transparent' }}
    >
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          {isOnboarding && (
            <div className="mb-4 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-semibold" style={{ background: 'rgba(121,192,255,0.1)', border: '1px solid rgba(121,192,255,0.25)', color: 'var(--rt-sky)' }}>
              Step 3 of 3 — Operational Briefing
            </div>
          )}
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--rt-text)', letterSpacing: '-0.5px' }}>
            {isOnboarding ? 'Before You Begin — How AI RedTeam Works' : 'How It Works'}
          </h1>
          <p className="text-sm" style={{ color: 'var(--rt-muted)' }}>
            {isOnboarding
              ? 'Review this guide carefully. You must acknowledge it before accessing the platform.'
              : 'A guided walkthrough of the AI RedTeam workflow.'}
          </p>
        </div>

        {/* Intro banner */}
        <div
          className="rounded-xl p-5 mb-8 flex gap-4 items-start"
          style={{ background: 'linear-gradient(135deg,rgba(121,192,255,0.08) 0%,rgba(188,140,255,0.06) 100%)', border: '1px solid rgba(121,192,255,0.2)' }}
        >
          <span className="text-3xl flex-shrink-0">⬡</span>
          <div>
            <p className="text-sm font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>
              AI RedTeam — Intelligent Penetration Testing Assistant
            </p>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--rt-muted)' }}>
              AI RedTeam lets you run professional-grade security assessments against{' '}
              <strong style={{ color: 'var(--rt-text)' }}>systems you own or have explicit permission to test</strong>.
              It combines a locally-hosted AI model (no data leaves your machine) with open-source
              scanning tools and a human-in-the-loop approval system to keep you in control at every step.
            </p>
          </div>
        </div>

        {/* Step-by-step workflow */}
        <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--rt-muted)' }}>
          Workflow — Step by Step
        </p>
        <div className="flex flex-col gap-3 mb-10">
          {STEPS.map(step => (
            <div
              key={step.num}
              className="rounded-lg overflow-hidden flex"
              style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
            >
              <div
                className="flex items-center justify-center px-5 flex-shrink-0"
                style={{ background: step.bg, borderRight: `1px solid ${step.border}`, minWidth: '64px' }}
              >
                <span className="font-mono text-lg font-bold" style={{ color: step.color }}>{step.num}</span>
              </div>
              <div className="p-4">
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>{step.title}</p>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--rt-muted)' }}>{step.body}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Key concepts */}
        <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--rt-muted)' }}>
          Key Concepts
        </p>
        <div className="grid grid-cols-2 gap-3 mb-10">
          {CONCEPTS.map(c => (
            <div
              key={c.title}
              className="rounded-lg p-4"
              style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
            >
              <div className="text-xl mb-2">{c.icon}</div>
              <p className="text-sm font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>{c.title}</p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--rt-muted)' }}>{c.body}</p>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--rt-muted)' }}>
          FAQ
        </p>
        <div
          className="rounded-lg overflow-hidden mb-10"
          style={{ border: '1px solid var(--rt-border)' }}
        >
          {FAQS.map((faq, i) => (
            <div
              key={i}
              style={{ borderBottom: i < FAQS.length - 1 ? '1px solid var(--rt-border)' : 'none' }}
            >
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full text-left px-5 py-4 flex items-center justify-between gap-3 transition-colors"
                style={{ background: openFaq === i ? 'var(--rt-surface2)' : 'var(--rt-surface)', color: 'var(--rt-text)' }}
              >
                <span className="text-sm font-medium">{faq.q}</span>
                <span
                  className="text-xs flex-shrink-0 transition-transform"
                  style={{ color: 'var(--rt-dim)', transform: openFaq === i ? 'rotate(180deg)' : 'none' }}
                >
                  ▾
                </span>
              </button>
              {openFaq === i && (
                <div
                  className="px-5 py-4 text-xs leading-relaxed"
                  style={{ color: 'var(--rt-muted)', borderTop: '1px solid var(--rt-border)', background: 'var(--rt-surface)' }}
                >
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* CTA */}
        <div
          className="rounded-xl p-6 text-center"
          style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
        >
          {isOnboarding ? (
            <>
              <p className="text-sm mb-1 font-semibold" style={{ color: 'var(--rt-text)' }}>
                Ready to proceed?
              </p>
              <p className="text-xs mb-5" style={{ color: 'var(--rt-muted)' }}>
                By continuing, you confirm that you understand the above and will only test systems
                you own or have explicit written permission to test.
              </p>
            </>
          ) : (
            <p className="text-sm mb-5" style={{ color: 'var(--rt-muted)' }}>
              Need a refresher? This guide is always available from the navigation bar.
            </p>
          )}
          <button
            onClick={handleCta}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-sm transition-opacity hover:opacity-85"
            style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
          >
            {isOnboarding ? "I understand — take me to the dashboard →" : "← Back to Dashboard"}
          </button>
        </div>

      </div>
    </div>
  );
}
