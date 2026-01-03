"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Upload, Send, Bot, User, Loader2, BrainCircuit, History } from "lucide-react";
import { supabase } from "@/lib/supabaseClient";
import { uploadDocument, sendChatMessage } from "@/lib/api";
import axios from "axios";
import QuizModal from "@/components/QuizModal";

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  
  // Chat State
  const [messages, setMessages] = useState<any[]>([
    { role: "bot", content: "Hello! Upload a PDF to start studying." }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [docId, setDocId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Quiz State
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [quizData, setQuizData] = useState<any>(null);
  const [showQuiz, setShowQuiz] = useState(false);

  // 1. Check Auth on Load
  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
      } else {
        setUser(session.user);
      }
    };
    checkUser();
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 2. Handle Document Upload
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    
    try {
      setIsLoading(true);
      setMessages(prev => [...prev, { role: "bot", content: `Uploading ${file.name}...` }]);
      
      const data = await uploadDocument(file);
      setDocId(data.doc_id);
      
      setMessages(prev => [...prev, { 
        role: "bot", 
        content: `✅ Ready! Ask questions or click "Start Quiz" to test yourself.` 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: "bot", content: "❌ Upload failed." }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 3. Handle Chat
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      // Pass history for context memory
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const response = await sendChatMessage(userMsg, history, docId || undefined);
      
      setMessages(prev => [...prev, { 
        role: "bot", 
        content: response.answer,
        sources: response.sources
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: "bot", content: "⚠️ Error getting response." }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Handle Quiz Generation (FIXED & SAFER)
  const handleStartQuiz = async () => {
    if (!docId) {
      alert("Please upload a document first!");
      return;
    }
    const numQ = prompt("How many questions? (Max 20)", "5");
    if (!numQ) return;

    setIsQuizLoading(true);
    try {
        // Call the backend endpoint
        const response = await axios.post('http://localhost:8000/generate_quiz', {
            doc_id: docId,
            num_questions: parseInt(numQ),
            difficulty: "Hard"
        });
        
        // --- SAFETY CHECKS START ---
        // 1. Check if backend returned an error message
        if (response.data.error) {
            alert("Quiz Error: " + response.data.error);
            return;
        }

        // 2. Check if questions array exists and is valid
        if (!response.data.questions || !Array.isArray(response.data.questions) || response.data.questions.length === 0) {
            alert("The AI couldn't generate a valid quiz from this text. Please try again or use a different PDF.");
            return;
        }
        // --- SAFETY CHECKS END ---

        setQuizData(response.data);
        setShowQuiz(true);
    } catch (error) {
        console.error("Quiz Error:", error);
        alert("Failed to connect to the quiz server.");
    } finally {
        setIsQuizLoading(false);
    }
  };

  if (!user) return null; // Prevent flash before redirect

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Quiz Modal */}
      {showQuiz && quizData && (
        <QuizModal data={quizData} onClose={() => setShowQuiz(false)} />
      )}

      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col hidden md:flex">
        <h1 className="text-xl font-bold mb-6 text-indigo-600 flex items-center gap-2">
          <Bot className="w-6 h-6" /> CampusStudy
        </h1>
        
        {/* Upload Button */}
        <label className="flex items-center gap-2 w-full p-3 rounded-lg border-2 border-dashed border-gray-300 hover:border-indigo-500 cursor-pointer bg-gray-50 text-sm font-medium text-gray-600 transition-all mb-4">
            <Upload className="w-4 h-4" />
            <span>Upload PDF</span>
            <input type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
        </label>

        {/* Action Buttons */}
        <button 
            onClick={handleStartQuiz}
            disabled={!docId || isQuizLoading}
            className="flex items-center gap-2 w-full p-3 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors font-semibold"
        >
            {isQuizLoading ? <Loader2 className="w-4 h-4 animate-spin"/> : <BrainCircuit className="w-4 h-4" />}
            <span>{isQuizLoading ? "Generating..." : "Take Hard Quiz"}</span>
        </button>

        <div className="mt-8">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">History</h3>
            <div className="space-y-1">
                <button className="flex items-center gap-2 w-full p-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md text-left">
                    <History className="w-3 h-3" /> Previous Chat 1
                </button>
                {/* We will populate this from DB later */}
            </div>
        </div>

        <div className="mt-auto pt-4 border-t border-gray-100 flex items-center gap-2 text-sm text-gray-600">
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                <User className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="truncate flex-1">{user.email}</div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full h-full relative">
        <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-24">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "bot" && (
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 text-indigo-600" />
                </div>
              )}
              
              <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${
                msg.role === "user" 
                  ? "bg-indigo-600 text-white" 
                  : "bg-white border border-gray-100 text-gray-800"
              }`}>
                <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200/20 text-xs opacity-70">
                    📚 Sources available
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400 text-sm ml-12">
              <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="absolute bottom-4 left-4 right-4 max-w-3xl mx-auto">
          <div className="bg-white p-2 rounded-2xl shadow-xl border border-gray-200 flex items-center gap-2 pl-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask anything about your document..."
              className="flex-1 py-3 outline-none text-gray-700 bg-transparent"
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="p-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}