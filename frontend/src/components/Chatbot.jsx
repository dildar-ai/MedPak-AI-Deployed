import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Sparkles, ArrowLeft } from 'lucide-react';
import { chatApi } from '../lib/api';
import ReactMarkdown from 'react-markdown';

const Chatbot = ({ onBack }) => {
  const [messages, setMessages] = useState([
    { 
      role: 'assistant', 
      content: 'Salam! 👋 I am **MedPak AI**, your dedicated medical assistant. How can I help you today?\n\nYou can ask me in English, Urdu, or Roman Urdu.\n\n*میں میڈپاک اے آئی ہوں، آپ کا طبی مشیر۔ میں آپ کی کیا مدد کر سکتا ہوں؟*',
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const detectUrdu = (text) => /[\u0600-\u06FF]/.test(text);

  // Strip any leftover <think>...</think> blocks from Qwen3 responses
  const cleanResponse = (text) => {
    return text.replace(/<think>[\s\S]*?<\/think>\s*/g, '').trim();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const data = await chatApi.sendMessage(userMessage, sessionId);
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: cleanResponse(data.answer),
      }]);
    } catch (error) {
      console.error("Chat error", error);
      const errMsg = error.response?.data?.detail || 'Sorry, I am having trouble connecting to the server. Please try again.';
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ ${errMsg}` }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full bg-white md:rounded-3xl md:shadow-xl md:border border-slate-200 overflow-hidden animate-fade-in">
      
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 p-4 text-white flex justify-between items-center z-10 shadow-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary-200" />
            <div>
              <h3 className="font-bold text-sm">MedPak AI Chat</h3>
              <p className="text-[10px] text-primary-200 leading-none">Bilingual Medical Assistant</p>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5 bg-slate-50">
        {messages.map((msg, idx) => {
          const isUrdu = msg.role === 'assistant' && detectUrdu(msg.content);
          return (
            <div key={idx} className={`flex gap-3 max-w-[92%] md:max-w-[80%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${
                msg.role === 'user' ? 'bg-slate-200' : 'bg-primary-100 text-primary-700'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-slate-600" /> : <Bot className="w-4 h-4" />}
              </div>
              
              <div className={`p-4 rounded-2xl text-sm md:text-[15px] leading-relaxed shadow-sm ${
                msg.role === 'user' 
                  ? 'bg-primary-600 text-white rounded-tr-sm' 
                  : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'
              }`}>
                {msg.role === 'user' ? (
                  msg.content
                ) : (
                  <div className="prose prose-sm md:prose-base prose-slate max-w-none prose-headings:text-slate-800 prose-strong:text-slate-700 prose-li:text-slate-600">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {isLoading && (
          <div className="flex gap-3 max-w-[80%] animate-fade-in">
            <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white border border-slate-200 p-3.5 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-2.5 text-sm text-slate-500">
              <Loader2 className="w-4 h-4 animate-spin text-primary-500" /> 
              <span>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} className="h-2" />
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-slate-200 flex-shrink-0">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a medical question..."
            className="w-full bg-slate-100 text-slate-900 rounded-2xl px-5 py-3.5 pr-14 focus:outline-none focus:ring-2 focus:ring-primary-500/30 transition-all text-[15px] border border-transparent focus:border-primary-300"
            disabled={isLoading}
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-500 disabled:opacity-40 disabled:bg-slate-300 transition-all shadow-sm"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chatbot;
