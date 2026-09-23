import type { Length, Voice } from "../api";

const LENGTHS: { value: Length; label: string }[] = [
  { value: 30, label: "30s" },
  { value: 60, label: "1 min" },
  { value: 180, label: "3 min" },
];

type Props = {
  length: Length;
  onLength: (length: Length) => void;
  voices: Voice[];
  voice: string;
  onVoice: (voice: string) => void;
};

export default function OptionsPanel({ length, onLength, voices, voice, onVoice }: Props) {
  return (
    <div className="options">
      <div className="option">
        <span className="option-label" id="length-label">
          Length
        </span>
        <div className="segmented" role="radiogroup" aria-labelledby="length-label">
          {LENGTHS.map((l) => (
            <button
              key={l.value}
              type="button"
              role="radio"
              aria-checked={length === l.value}
              className={length === l.value ? "active" : ""}
              onClick={() => onLength(l.value)}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>
      <label className="option">
        <span className="option-label">Voice</span>
        <select value={voice} onChange={(e) => onVoice(e.target.value)}>
          {voices.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
