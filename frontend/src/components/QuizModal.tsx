"use client";
import { useState, useEffect } from "react";
import { X, Clock, AlertTriangle, CheckCircle, XCircle } from "lucide-react";

export default function QuizModal({ data, onClose }: { data: any, onClose: () => void }) {
  // Safety Check
  if (!data || !data.questions || data.questions.length === 0) {
    return null; // Should be handled by parent, but safe keeping
  }

  const [currentQ, setCurrentQ] = useState(0);
  const [userAnswers, setUserAnswers] = useState<string[]>(new Array(data.questions.length).fill(null));
  const [timeLeft, setTimeLeft] = useState(data.timer_seconds || 60);
  const [finished, setFinished] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  // Timer Logic
  useEffect(() => {
    if (timeLeft > 0 && !finished) {
      const timer = setInterval(() => setTimeLeft((prev: number) => prev - 1), 1000);
      return () => clearInterval(timer);
    } else if (timeLeft === 0 && !finished) {
      finishQuiz();
    }
  }, [timeLeft, finished]);

  const handleNext = () => {
    // Save the answer
    const newAnswers = [...userAnswers];
    newAnswers[currentQ] = selectedOption || "Skipped"; // Mark skipped if time ran out/empty
    setUserAnswers(newAnswers);

    if (currentQ < data.questions.length - 1) {
      setCurrentQ(currentQ + 1);
      setSelectedOption(null);
    } else {
      finishQuiz(newAnswers);
    }
  };

  const finishQuiz = (finalAnswers?: string[]) => {
    if (finalAnswers) setUserAnswers(finalAnswers);
    setFinished(true);
  };

  // Calculate Score
  const calculateScore = () => {
    return userAnswers.filter((ans, index) => ans === data.questions[index].answer).length;
  };

  // Format Time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // --- RESULTS VIEW ---
  if (finished) {
    const score = calculateScore();
    const percentage = Math.round((score / data.questions.length) * 100);

    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
        <div className="bg-white rounded-2xl max-w-2xl w-full flex flex-col max-h-[90vh] my-8 animate-in fade-in zoom-in">
          
          {/* Header */}
          <div className="p-6 border-b border-gray-100 text-center bg-gray-50 rounded-t-2xl">
            <h2 className="text-2xl font-bold mb-2">Quiz Results</h2>
            <div className={`text-5xl font-black mb-2 ${percentage >= 50 ? 'text-green-600' : 'text-red-500'}`}>
              {percentage}%
            </div>
            <p className="text-gray-600">You scored {score} out of {data.questions.length}</p>
          </div>

          {/* Detailed Review List */}
          <div className="p-6 overflow-y-auto flex-1 space-y-8">
            {data.questions.map((q: any, index: number) => {
              const userAnswer = userAnswers[index];
              const isCorrect = userAnswer === q.answer;
              
              return (
                <div key={index} className={`p-4 rounded-xl border-l-4 ${isCorrect ? 'border-green-500 bg-green-50/50' : 'border-red-500 bg-red-50/50'}`}>
                  <h3 className="font-bold text-gray-800 mb-3 flex gap-2">
                    <span className="text-gray-400">#{index + 1}</span> {q.question}
                  </h3>

                  <div className="space-y-2 text-sm">
                    {/* Your Answer */}
                    <div className="flex items-start gap-2">
                      <span className="font-semibold min-w-[80px]">Your Answer:</span>
                      <span className={isCorrect ? "text-green-700 font-medium" : "text-red-600 font-medium line-through"}>
                        {userAnswer || "Skipped"}
                      </span>
                    </div>

                    {/* Correct Answer (if wrong) */}
                    {!isCorrect && (
                      <div className="flex items-start gap-2">
                        <span className="font-semibold min-w-[80px]">Correct:</span>
                        <span className="text-green-700 font-bold">{q.answer}</span>
                      </div>
                    )}
                    
                    {/* Explanation */}
                    <div className="mt-3 text-gray-600 bg-white p-3 rounded-lg border border-gray-200 text-sm">
                      <span className="font-bold text-indigo-600">💡 Explanation:</span> {q.explanation}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end rounded-b-2xl">
            <button onClick={onClose} className="bg-gray-900 text-white px-8 py-3 rounded-xl hover:bg-black font-bold">
              Close & Return to Chat
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- QUIZ VIEW ---
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-white w-full max-w-2xl rounded-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-indigo-600 text-white p-4 flex justify-between items-center">
          <div className="flex items-center gap-2 font-bold">
            <Clock className="w-5 h-5" /> 
            <span className={timeLeft < 30 ? "text-red-300 animate-pulse" : ""}>
              {formatTime(timeLeft)}
            </span>
          </div>
          <div className="text-sm opacity-80">Question {currentQ + 1} / {data.questions.length}</div>
          <button onClick={onClose} className="hover:bg-white/20 p-1 rounded"><X className="w-5 h-5"/></button>
        </div>

        {/* Question Area */}
        <div className="p-8 overflow-y-auto flex-1">
          <h3 className="text-xl font-bold text-gray-800 mb-6 leading-relaxed">
            {data.questions[currentQ].question}
          </h3>

          <div className="space-y-3">
            {data.questions[currentQ].options.map((opt: string, idx: number) => (
              <button
                key={idx}
                onClick={() => !finished && setSelectedOption(opt)}
                className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                  selectedOption === opt
                    ? "border-indigo-600 bg-indigo-50 text-indigo-900 font-medium"
                    : "border-gray-200 hover:border-gray-300 text-gray-700"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
          <button
            onClick={handleNext}
            disabled={!selectedOption}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-bold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {currentQ === data.questions.length - 1 ? "Submit Exam" : "Next Question"}
          </button>
        </div>
      </div>
    </div>
  );
}