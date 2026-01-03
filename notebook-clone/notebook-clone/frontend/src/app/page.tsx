'use client';
import { useState, useRef, useEffect } from 'react'; 
import { Upload, Send, FileText, Bot, User, Loader2 } from 'lucide-react';
import { uploadDocument, chatWithBot } from '@/lib/api';

export default function Home() {
  const [messages, setMessages] = useState<{role: 'user' | 'bot', content: string, sources?: any[]}[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [docId, setDocId] = useState<string | null>(null);

  // 1. Handle File Upload
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setIsUploading(true);
    try {
      const result = await uploadDocument(e.target.files[0]);
      setDocId(result.doc_id);
      alert("✅ Document uploaded successfully!");
    } catch (error) {
      alert("❌ Upload failed. Make sure Backend is running!");
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  // 2. Handle Chat Message
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Pass the current docId state to the API
      const response = await chatWithBot(userMessage, docId);
      setMessages(prev => [...prev, { 
        role: 'bot', 
        content: response.answer,
        sources: response.sources 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'bot', content: "⚠️ Error connecting to server." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans">
      
      {/* LEFT SIDEBAR - Upload Area */}
      <div className="w-64 bg-white border-r border-gray-200 p-6 flex flex-col">
        <h1 className="text-xl font-bold mb-6 flex items-center gap-2">
          <FileText className="w-6 h-6 text-blue-600" />
          Notebook
        </h1>

        <div className="mb-8">
          <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 transition">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              {isUploading ? (
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              ) : (
                <>
                  <Upload className="w-8 h-8 text-gray-400 mb-2" />
                  <p className="text-sm text-gray-500">Click to upload PDF</p>
                </>
              )}
            </div>
            <input type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
          </label>
        </div>

        {docId && (
          <div className="p-3 bg-green-50 text-green-700 rounded-md text-sm border border-green-200">
             Active Source: <br/> <span className="font-semibold">Document Ready</span>
          </div>
        )}
      </div>

      {/* RIGHT SIDE - Chat Interface */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full h-full shadow-xl bg-white">
        
        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 mt-20">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Upload a PDF and ask a question to start!</p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-600' : 'bg-green-600'}`}>
                  {msg.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
                </div>
                
                <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  
                  {/* Citations / Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-gray-200/50">
                      <p className="text-xs font-bold opacity-70 mb-2">Sources:</p>
                      <div className="flex flex-wrap gap-2">
                        {msg.sources.map((src: any, i: number) => (
                          <span key={i} className="text-xs bg-white/50 px-2 py-1 rounded border border-gray-300/30">
                            Page {src.metadata.page}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="p-4 bg-gray-100 rounded-2xl flex items-center">
                <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question about your documents..."
              className="flex-1 p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              disabled={isLoading}
            />
            <button 
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 text-white p-3 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}