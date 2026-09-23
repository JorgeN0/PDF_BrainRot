import type { Job } from "../api";

type Props = { job: Job; onReset: () => void };

function slug(text: string) {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60) || "brainrot"
  );
}

export default function VideoResult({ job, onReset }: Props) {
  if (!job.video_url) return null;
  return (
    <div className="result">
      <video className="result-video" src={job.video_url} controls autoPlay playsInline />
      <div className="result-side">
        <h2>{job.title}</h2>
        <div className="result-actions">
          <a className="btn primary" href={job.video_url} download={`${slug(job.title ?? "")}.mp4`}>
            Download MP4
          </a>
          <button type="button" className="btn" onClick={onReset}>
            Make another
          </button>
        </div>
        {job.script && (
          <details className="script" open>
            <summary>Script</summary>
            <p>{job.script}</p>
          </details>
        )}
      </div>
    </div>
  );
}
