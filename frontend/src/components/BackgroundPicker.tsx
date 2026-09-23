import type { Background } from "../api";

type Props = {
  backgrounds: Background[];
  selected: string;
  onSelect: (id: string) => void;
};

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function BackgroundPicker({ backgrounds, selected, onSelect }: Props) {
  if (backgrounds.length === 0) {
    return (
      <div className="empty">
        <p>
          <strong>No background clips yet.</strong>
        </p>
        <p>
          Drop some gameplay videos (Minecraft parkour, Subway Surfers, whatever) into the{" "}
          <code>backgrounds/</code> folder, then refresh this page.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-grid" role="radiogroup" aria-label="Background video">
      <button
        type="button"
        role="radio"
        aria-checked={selected === "random"}
        className={`bg-card random${selected === "random" ? " selected" : ""}`}
        onClick={() => onSelect("random")}
      >
        <span className="random-icon" aria-hidden>
          🎲
        </span>
        <span className="bg-name">Random</span>
      </button>
      {backgrounds.map((bg) => (
        <button
          key={bg.id}
          type="button"
          role="radio"
          aria-checked={selected === bg.id}
          className={`bg-card${selected === bg.id ? " selected" : ""}`}
          onClick={() => onSelect(bg.id)}
          onMouseEnter={(e) => e.currentTarget.querySelector("video")?.play().catch(() => {})}
          onMouseLeave={(e) => {
            const video = e.currentTarget.querySelector("video");
            if (video) {
              video.pause();
              video.currentTime = 0;
            }
          }}
        >
          <img src={bg.thumbnail_url} alt="" loading="lazy" />
          <video src={bg.video_url} muted loop playsInline preload="none" />
          <span className="bg-meta">
            <span className="bg-name">{bg.name}</span>
            <span className="bg-duration">{formatDuration(bg.duration)}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
