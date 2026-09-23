import { useRef, useState } from "react";

type Props = {
  file: File | null;
  onFile: (file: File | null) => void;
};

function formatSize(bytes: number) {
  return bytes > 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export default function PdfDropzone({ file, onFile }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function accept(candidate: File | undefined) {
    if (!candidate) return;
    const isPdf =
      candidate.type === "application/pdf" || candidate.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError("That's not a PDF.");
      return;
    }
    setError(null);
    onFile(candidate);
  }

  return (
    <div>
      <button
        type="button"
        className={`dropzone${dragging ? " dragging" : ""}${file ? " has-file" : ""}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          accept(e.dataTransfer.files[0]);
        }}
      >
        {file ? (
          <>
            <span className="dropzone-icon" aria-hidden>
              📄
            </span>
            <span className="dropzone-title">{file.name}</span>
            <span className="dropzone-hint">{formatSize(file.size)} · click to swap</span>
          </>
        ) : (
          <>
            <span className="dropzone-icon" aria-hidden>
              ⬆
            </span>
            <span className="dropzone-title">Drop your PDF here</span>
            <span className="dropzone-hint">or click to browse. Needs selectable text, not a scan.</span>
          </>
        )}
      </button>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(e) => {
          accept(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}
