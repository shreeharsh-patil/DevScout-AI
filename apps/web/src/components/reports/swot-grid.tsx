"use client";

interface SwotGridProps {
  markdown: string;
}

interface SwotData {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

function parseSwot(markdown: string): SwotData {
  const extract = (keyword: string): string[] => {
    const regex = new RegExp(
      `\\*\\*${keyword}:?\\*\\*([\\s\\S]*?)(?=\\*\\*(?:Strengths|Weaknesses|Opportunities|Threats):?\\*\\*|$)`,
      "i"
    );
    const match = markdown.match(regex);
    if (!match) return [];
    return match[1]
      .split("\n")
      .map((l) => l.replace(/^[-*•]\s*/, "").trim())
      .filter((l) => l.length > 0);
  };
  return {
    strengths: extract("Strengths"),
    weaknesses: extract("Weaknesses"),
    opportunities: extract("Opportunities"),
    threats: extract("Threats"),
  };
}

function Quadrant({
  title,
  items,
  bg,
  textColor,
  borderColor,
}: {
  title: string;
  items: string[];
  bg: string;
  textColor: string;
  borderColor: string;
}) {
  return (
    <div className={`rounded-xl p-4 border ${bg} ${borderColor}`}>
      <p className={`text-xs font-bold uppercase tracking-widest mb-3 ${textColor}`}>{title}</p>
      <ul className="space-y-1">
        {items.slice(0, 6).map((item, i) => (
          <li key={i} className="flex gap-2 text-sm text-neutral-300">
            <span className={`mt-0.5 shrink-0 ${textColor}`}>•</span>
            <span>{item}</span>
          </li>
        ))}
        {items.length === 0 && <li className="text-xs text-neutral-600 italic">None detected</li>}
      </ul>
    </div>
  );
}

export default function SwotGrid({ markdown }: SwotGridProps) {
  const { strengths, weaknesses, opportunities, threats } = parseSwot(markdown);
  if (!strengths.length && !weaknesses.length && !opportunities.length && !threats.length) {
    return null;
  }

  return (
    <div className="mb-8">
      <p className="text-xs uppercase tracking-widest text-neutral-500 mb-4">SWOT Analysis</p>
      <div className="grid grid-cols-2 gap-3">
        <Quadrant title="Strengths" items={strengths} bg="bg-emerald-950/40" textColor="text-emerald-400" borderColor="border-emerald-800/40" />
        <Quadrant title="Weaknesses" items={weaknesses} bg="bg-red-950/40" textColor="text-red-400" borderColor="border-red-800/40" />
        <Quadrant title="Opportunities" items={opportunities} bg="bg-blue-950/40" textColor="text-blue-400" borderColor="border-blue-800/40" />
        <Quadrant title="Threats" items={threats} bg="bg-amber-950/40" textColor="text-amber-400" borderColor="border-amber-800/40" />
      </div>
    </div>
  );
}
