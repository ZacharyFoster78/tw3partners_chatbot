import React, { useState, useRef, useEffect } from 'react';
import './Chat.css';

// Utiliser une icône pour le feedback
const ThumbsUp = () => '👍';
const ThumbsDown = () => '👎';

function App() {
  const [messages, setMessages] = useState([
    { text: "Bonjour! Comment puis-je vous aider aujourd'hui?", sender: 'bot' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (input.trim() === '' || isLoading) return;

    const userMessage = { text: input, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          conversation_history: messages
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const botMessage = { text: data.answer, sender: 'bot', id: Date.now() };
      setMessages(prev => [...prev, botMessage]);

    } catch (error) {
      console.error("Failed to fetch chat response:", error);
      const errorMessage = { text: "Sorry, I'm having trouble connecting to my brain. Please try again later.", sender: 'bot' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleFeedback = async (messageId, rating) => {
    const conversation = messages.map(({id, ...rest}) => rest); // remove id before sending
    try {
      await fetch('http://localhost:8000/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation, rating })
      });
      alert('Thank you for your feedback!');
    } catch (error) {
      console.error("Failed to send feedback:", error);
    }
  };


  return (
    <div className="chat-container">
      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            <p dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br />') }} />
            {msg.sender === 'bot' && msg.id && (
              <div className="feedback-buttons">
                <button onClick={() => handleFeedback(msg.id, true)}><ThumbsUp /></button>
                <button onClick={() => handleFeedback(msg.id, false)}><ThumbsDown /></button>
              </div>
            )}
          </div>
        ))}
        {isLoading && <div className="message bot"><p><i>Typing...</i></p></div>}
        <div ref={messagesEndRef} />
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask me anything..."
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;