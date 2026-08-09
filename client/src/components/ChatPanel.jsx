import React, { useState, useRef, useEffect } from 'react';
import { Sparkles } from 'lucide-react';

export default function ChatPanel({
  chatMessages,
  setChatMessages,
  isChatSending,
  handleSendChat,
}) {
  const [chatInput, setChatInput] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isChatSending]);

  const onSubmit = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const msg = chatInput.trim();
    setChatInput('');
    handleSendChat(msg);
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {chatMessages.map((msg, idx) => (
          <div key={idx} className={`chat-bubble ${msg.sender}`}>
            {msg.sender === 'ai' && (
              <Sparkles size={16} className="logo-icon" style={{ marginTop: '3px', flexShrink: 0 }} />
            )}
            <div className="chat-bubble-content">{msg.text}</div>
          </div>
        ))}
        {isChatSending && (
          <div className="chat-bubble ai">
            <Sparkles size={16} className="logo-icon" style={{ marginTop: '3px', flexShrink: 0 }} />
            <div className="typing-dots">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
      <div className="chat-input-area">
        <form onSubmit={onSubmit} className="chat-form">
          <input 
            type="text" 
            placeholder="Ask a question about this meeting..."
            className="chat-input"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            disabled={isChatSending}
          />
          <button 
            type="submit" 
            className="chat-send-btn"
            disabled={isChatSending || !chatInput.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
