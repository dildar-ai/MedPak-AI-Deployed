import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, ArrowLeft, ShieldCheck, ShieldAlert, Pill } from 'lucide-react';
import { chatApi } from '../lib/api';
import ReactMarkdown from 'react-markdown';
import logoIcon from '../assets/logo-icon.png';

const SUGGESTED_QUESTIONS = [
  'What is Panadol used for?',
  'What are the side effects of Brufen?',
  'Can I take Panadol with Augmentin?',
  'What is Amoxil used to treat?',
];

const WELCOME_MESSAGE =
  'Salam! 👋 I am **MedPak AI**, your medicine information assistant.\n\n' +
  'Ask me about any medicine — its uses, side effects, interactions, brands, or prices — in English, Urdu, or Roman Urdu.\n\n' +
  '*Note: I provide medicine information only. I cannot diagnose conditions or recommend which medicine you should take.*\n\n' +
  '*میں صرف ادویات کی معلومات فراہم کرتا ہوں۔ میں تشخیص نہیں کر سکتا اور نہ ہی دوا کی سفارش کر سکتا ہوں۔*';

const Chatbot = ({ onBack }) => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: WELCOME_MESSAGE }
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

  const sendMessage = async (text) => {
    if (!text.trim() || isLoading) return;

    const userMessage = text.trim();
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
        content: data.answer,
        guarded: !!data.guarded,
        drugs: data.rag_context?.drugs?.length ? data.rag_context.drugs.slice(0, 4) : [],
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

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleDrugChipClick = (drug) => {
    const name = drug.brand_name || drug.NAME || 'this medicine';
    sendMessage(`Tell me about ${name}`);
  };

  const isWelcomeOnly = messages.length === 1 && !isLoading;

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full bg-white md:rounded-3xl md:shadow-xl md:border border-slate-200 overflow-hidden animate-fade-in">

      {/* Header */}
      <div className="bg-gradient-to-r from-medical-600 to-primary-600 p-4 text-white flex justify-between items-center z-10 shadow-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2.5">
            <img src={logoIcon} alt="" className="w-9 h-9" />
            <div>
              <h3 className="font-bold text-sm">MedPak AI Chat</h3>
              <p className="text-[10px] text-white/80 leading-none">Bilingual Medicine Information Assistant</p>
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
                msg.role === 'user'
                  ? 'bg-slate-200'
                  : msg.guarded
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-primary-100 text-primary-700'
              }`}>
                {msg.role === 'user'
                  ? <User className="w-4 h-4 text-slate-600" />
                  : msg.guarded
                    ? <ShieldAlert className="w-4 h-4" />
                    : <Bot className="w-4 h-4" />}
              </div>

              <div className={`flex flex-col min-w-0 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`p-4 rounded-2xl text-sm md:text-[15px] leading-relaxed shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-tr-sm'
                    : msg.guarded
                      ? 'bg-amber-50 border border-amber-200 text-slate-800 rounded-tl-sm'
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

                {/* Medicine context chips from the RAG retrieval */}
                {msg.drugs?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {msg.drugs.map((drug, i) => (
                      <button
                        key={`${drug.drug_id}-${i}`}
                        onClick={() => handleDrugChipClick(drug)}
                        disabled={isLoading}
                        title={`Ask about ${drug.salt_name || drug.brand_name}`}
                        className="inline-flex items-center gap-1.5 bg-white border border-primary-200 text-primary-700 text-xs font-medium px-2.5 py-1.5 rounded-full hover:bg-primary-50 hover:border-primary-300 disabled:opacity-50 transition-colors"
                      >
                        <Pill className="w-3 h-3" />
                        {drug.brand_name || drug.NAME || `Drug ${drug.drug_id}`}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Suggested questions on the welcome screen */}
        {isWelcomeOnly && (
          <div className="max-w-[80%] animate-fade-in">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">Try asking</p>
            <div className="flex flex-col gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="text-left bg-white border border-slate-200 text-slate-700 text-sm px-4 py-2.5 rounded-xl hover:border-primary-300 hover:bg-primary-50/50 hover:text-primary-800 transition-all shadow-sm"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

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
            placeholder="Ask about a medicine..."
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
        <p className="mt-2.5 text-[11px] text-slate-400 flex items-center justify-center gap-1.5 text-center">
          <ShieldCheck className="w-3 h-3 flex-shrink-0" />
          MedPak AI provides medicine information only — it does not prescribe or diagnose.
        </p>
      </div>
    </div>
  );
};

export default Chatbot;
