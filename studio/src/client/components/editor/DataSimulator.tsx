import { useEditor } from "../../lib/store/editor.ts";

function Slider({
  label, value, min, max, onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 text-xs text-zinc-500">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="flex-1 accent-indigo-500"
      />
      <span className="w-10 text-right text-xs text-zinc-400">{value}</span>
    </div>
  );
}

export function DataSimulator() {
  const { sim, setSim } = useEditor();

  return (
    <div className="space-y-1.5 rounded-xl border border-zinc-800 bg-zinc-900/50 p-3">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Data Simulator
      </div>
      <Slider label="Hour" value={sim.hour} min={0} max={23} onChange={(v) => setSim({ hour: v })} />
      <Slider label="Min" value={sim.minute} min={0} max={59} onChange={(v) => setSim({ minute: v })} />
      <Slider label="Sec" value={sim.second} min={0} max={59} onChange={(v) => setSim({ second: v })} />
      <Slider label="Steps" value={sim.steps} min={0} max={50000} onChange={(v) => setSim({ steps: v })} />
      <Slider label="HR" value={sim.heartRate} min={40} max={200} onChange={(v) => setSim({ heartRate: v })} />
      <Slider label="Cal" value={sim.calories} min={0} max={2000} onChange={(v) => setSim({ calories: v })} />
      <Slider label="Temp" value={sim.temperature} min={-20} max={50} onChange={(v) => setSim({ temperature: v })} />
      <Slider label="Batt" value={sim.battery} min={0} max={100} onChange={(v) => setSim({ battery: v })} />
    </div>
  );
}
