// src/lib/api.ts
import axios from 'axios';

// Change this to your Render URL when deploying (e.g., https://your-app.onrender.com)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"; 

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data; // Returns { doc_id: "...", ... }
};

export const sendChatMessage = async (
  question: string, 
  history: any[], 
  docId?: string
) => {
  const response = await api.post('/chat', {
    question,
    history,
    doc_id: docId,
  });
  return response.data; // Returns { answer: "...", sources: [...] }
};