import { useEffect, useState } from "react";
import {
  createJob,
  getBackgrounds,
  getHealth,
  getJob,
  getVoices,
  type Background,
  type Health,
  type Job,
  type Length,
  type Voice,
} from "./api";
import BackgroundPicker from "./components/BackgroundPicker";
import JobProgress from "./components/JobProgress";
import OptionsPanel from "./components/OptionsPanel";
import PdfDropzone from "./components/PdfDropzone";
import VideoResult from "./components/VideoResult";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [backgrounds, setBackgrounds] = useState<Background[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [backgroundId, setBackgroundId] = useState("random");
  const [length, setLength] = useState<Length>(60);
  const [voice, setVoice] = useState("");

  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getHealth(), getBackgrounds(), getVoices()])
      .then(([h, bgs, v]) => {
        setHealth(h);
        setBackgrounds(bgs);
        setVoices(v.voices);
        setVoice(v.default);
      })
      .catch(() => setLoadError("Can't reach the backend. Is it running on port 8000?"));
  }, []);

  // Poll the job until it finishes.
  const jobId = job?.id;
  const jobActive = job?.status === "queued" || job?.status === "running";
  useEffect(() => {
    if (!jobId || !jobActive) return;
    const timer = setInterval(() => {
      getJob(jobId)
        .then(setJob)
        .catch((err: Error) =>
          setJob((prev) => prev && { ...prev, status: "error", error: err.message }),
        );
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId, jobActive]);

  async function generate() {
    if (!file) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { job_id } = await createJob({ pdf: file, backgroundId, length, voice });
      setJob({
        id: job_id,
        status: "queued",
        stage: "Queued",
        progress: 0,
        error: null,
        title: null,
        script: null,
        video_url: null,
      });
    } catch (err) {
      setSubmitError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const problems = health
    ? Object.values(health).filter((check) => !check.ok && check !== health.backgrounds)
    : [];
  const canGenerate = !!file && backgrounds.length > 0 && !!voice && !submitting;

  return (
    <div className="page">
      <header className="hero">
        <h1>
          PDF <span className="arrow">→</span> <span className="accent">BrainRot</span>
        </h1>
        <p>Turn that 40-page reading into 60 seconds of Subway Surfers. Runs on your machine, costs $0.</p>
      </header>

      {loadError && <div className="banner error">{loadError}</div>}
      {problems.map((p) => (
        <div key={p.message} className="banner warn">
          {p.message}
        </div>
      ))}

      {job && job.status === "done" ? (
        <VideoResult job={job} onReset={() => setJob(null)} />
      ) : job && job.status !== "error" ? (
        <JobProgress job={job} />
      ) : (
        <main className="form">
          {job?.status === "error" && (
            <div className="banner error">
              <strong>That didn't work.</strong> {job.error}
            </div>
          )}

          <section>
            <h2>
              <span className="step-num">1</span> Upload a PDF
            </h2>
            <PdfDropzone file={file} onFile={setFile} />
          </section>

          <section>
            <h2>
              <span className="step-num">2</span> Pick the background
            </h2>
            <BackgroundPicker
              backgrounds={backgrounds}
              selected={backgroundId}
              onSelect={setBackgroundId}
            />
          </section>

          <section>
            <h2>
              <span className="step-num">3</span> Tune it
            </h2>
            <OptionsPanel
              length={length}
              onLength={setLength}
              voices={voices}
              voice={voice}
              onVoice={setVoice}
            />
          </section>

          {submitError && <div className="banner error">{submitError}</div>}
          <button type="button" className="btn primary big" disabled={!canGenerate} onClick={generate}>
            {submitting ? "Uploading…" : "Generate video"}
          </button>
        </main>
      )}
    </div>
  );
}
