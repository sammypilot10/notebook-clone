import axios from 'axios';

// Ensure this matches your backend URL (usually port 8000)
const API_URL = 'http://127.0.0.1:8000';

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await axios.post(`${API_URL}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// UPDATED: Now correctly accepts 3 arguments: question, history, and docId
export const chatWithBot = async (question: string, history: any[] = [], docId?: string | null) => {
  const response = await axios.post(`${API_URL}/chat`, { 
    question: question,
    history: history, // Send the conversation memory
    doc_id: docId     // Send the specific document ID
  });
  return response.data;
};