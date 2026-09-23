import type { Job } from "../api";

// Progress thresholds match the backend pipeline in app/pipeline/run.py.
const STEPS = [
  { label: "Reading the PDF", from: 0 },
  { label: "Writing the script", from: 15 },
  { label: "Recording the voiceover", from: 45 },
  { label: "Rendering the video", from: 60 },
];

export default function JobProgress({ job }: { job: Job }) {
  const active = STEPS.findLastIndex((s) => job.progress >= s.from);

  return (
    <div className="progress-card" aria-live="polite">
      <h2>Cooking your brainrot…</h2>
      <p className="progress-stage">{job.status === "queued" ? "Waiting in line" : job.stage}</p>
      <div className="bar" role="progressbar" aria-valuenow={job.progress} aria-valuemin={0} aria-valuemax={100}>
        <div className="bar-fill" style={{ width: `${Math.max(3, job.progress)}%` }} />
      </div>
      <ol className="steps">
        {STEPS.map((step, i) => (
          <li
            key={step.label}
            className={i < active ? "done" : i === active && job.status === "running" ? "active" : ""}
          >
            <span className="step-dot" aria-hidden>
              {i < active ? "✓" : i + 1}
            </span>
            {step.label}
          </li>
        ))}
      </ol>
      <p className="progress-note">
        The first run downloads the voice model and takes longer.
      </p>
    </div>
  );
}
