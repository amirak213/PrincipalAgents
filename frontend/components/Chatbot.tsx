'use client';

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Message } from './Message';
import { ChatHeader } from './ChatHeader';
import { ChatInput } from './ChatInput';
import { WelcomeBanner } from './WelcomeBanner';

interface MessageData {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

export function Chatbot() {
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        const response = await axios.post('http://localhost:5000/api/sessions');
        setSessionId(response.data.session_id);
      } catch (error) {
        console.error('Error initializing session:', error);
      }
    };

    initSession();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (userMessage: string) => {
    if (!sessionId) return;

    // Add user message
    const newUserMessage: MessageData = {
      text: userMessage,
      isUser: true,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newUserMessage]);
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:5000/api/chat', {
        message: userMessage,
        session_id: sessionId,
      });

      const botMessage: MessageData = {
        text: response.data.response,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: MessageData = {
        text: 'Sorry, there was an error processing your request. Please try again.',
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      <ChatHeader onClear={handleClear} />

      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <WelcomeBanner />
        ) : (
          <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
            {messages.map((msg, index) => (
              <Message
                key={index}
                text={msg.text}
                isUser={msg.isUser}
                timestamp={msg.timestamp}
              />
            ))}
            {loading && (
              <div className="flex justify-start mb-4">
                <div className="bg-surface border border-primary-dark rounded-lg px-4 py-3">
                  <div className="flex gap-2">
                    <div className="w-2 h-2 rounded-full bg-primary-light animate-bounce" style={{ animationDelay: '0s' }}></div>
                    <div className="w-2 h-2 rounded-full bg-primary-light animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 rounded-full bg-primary-light animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <ChatInput onSend={handleSendMessage} loading={loading} />
    </div>
  );
}
