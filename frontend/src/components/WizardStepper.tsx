import React from 'react';
import { Check, X } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

interface WizardStepperProps {
  currentStep: number;
  onStepClick?: (step: number) => void;
  onClose: () => void;
}

export const WizardStepper: React.FC<WizardStepperProps> = ({ currentStep, onStepClick, onClose }) => {
  const { t } = useLanguage();

  const steps = [
    { number: 1, label: t.stepper.step1 },
    { number: 2, label: t.stepper.step2 },
    { number: 3, label: t.stepper.step3 },
    { number: 4, label: t.stepper.step4 },
    { number: 5, label: t.stepper.step5 },
  ];

  return (
    <div className="relative mb-6">
      {/* Close button in top-right corner */}
      <button
        onClick={onClose}
        className="absolute -top-1 -right-1 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors z-10"
        title={t.stepper.close || 'Close'}
      >
        <X className="w-5 h-5" />
      </button>

      {/* Stepper pills row */}
      <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2 scrollbar-none pr-8">
        {steps.map((step) => {
          const isCompleted = step.number < currentStep;
          const isCurrent = step.number === currentStep;

          return (
            <div
              key={step.number}
              onClick={() => {
                if (isCompleted && onStepClick) {
                  onStepClick(step.number);
                }
              }}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all select-none ${
                isCompleted ? 'cursor-pointer hover:border-slate-600' : ''
              } ${
                isCurrent
                  ? 'border border-indigo-500 bg-indigo-950/40 text-indigo-300 ring-1 ring-indigo-500/50 shadow-md shadow-indigo-950/50'
                  : isCompleted
                  ? 'border border-slate-700 bg-slate-900/60 text-slate-300'
                  : 'border border-slate-800/80 bg-slate-900/20 text-slate-500'
              }`}
            >
              {/* Pill badge: circle with check or step number */}
              <div
                className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  isCurrent
                    ? 'bg-indigo-600 text-white'
                    : isCompleted
                    ? 'border border-slate-600 text-emerald-400'
                    : 'border border-slate-700 text-slate-500'
                }`}
              >
                {isCompleted ? <Check className="w-2.5 h-2.5" /> : step.number}
              </div>
              <span className={isCurrent ? 'font-semibold' : ''}>{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
