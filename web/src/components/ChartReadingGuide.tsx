import { Lightbulb, Target } from 'lucide-react';

interface ChartReadingGuideProps {
  howToRead: string;
  actionSignal: string;
}

export function ChartReadingGuide({ howToRead, actionSignal }: ChartReadingGuideProps) {
  return (
    <div className="rounded-xl bg-slate-50 border border-slate-200/90 border-l-4 border-l-[#1D4ED8] px-3.5 py-2.5 text-xs space-y-1">
      <div className="flex items-start gap-1.5 text-slate-700 leading-relaxed">
        <Lightbulb className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" aria-hidden="true" />
        <span>
          <strong className="text-slate-900">怎么看：</strong>
          {howToRead}
        </span>
      </div>
      <div className="flex items-start gap-1.5 text-slate-700 leading-relaxed">
        <Target className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" aria-hidden="true" />
        <span>
          <strong className="text-slate-900">行动信号：</strong>
          {actionSignal}
        </span>
      </div>
    </div>
  );
}
