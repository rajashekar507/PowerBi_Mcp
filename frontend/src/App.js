import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = '/api';

const themes = {
  default: {
    name: 'Default',
    description: 'Clean and professional',
    colors: ['#000000', '#ffffff', '#f0f0f0', '#e0e0e0']
  },
  deepOcean: {
    name: 'Deep Ocean',
    description: 'Calm and sophisticated',
    colors: ['#1e3a8a', '#3b82f6', '#60a5fa', '#93c5fd']
  },
  sunsetGlow: {
    name: 'Sunset Glow',
    description: 'Warm and inviting',
    colors: ['#dc2626', '#f97316', '#fbbf24', '#fde047']
  },
  forestRetreat: {
    name: 'Forest Retreat',
    description: 'Natural and serene',
    colors: ['#166534', '#16a34a', '#4ade80', '#bbf7d0']
  },
  monochromeElegance: {
    name: 'Monochrome Elegance',
    description: 'Classic and minimalist',
    colors: ['#000000', '#374151', '#6b7280', '#d1d5db']
  },
  purpleDream: {
    name: 'Purple Dream',
    description: 'Creative and modern',
    colors: ['#7c3aed', '#a855f7', '#c084fc', '#e9d5ff']
  }
};

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [currentTheme, setCurrentTheme] = useState('default');
  const [showThemeModal, setShowThemeModal] = useState(false);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadConversations();
    const savedTheme = localStorage.getItem('chat-theme') || 'default';
    setCurrentTheme(savedTheme);
    applyTheme(savedTheme);
  }, []);

  const applyTheme = (themeName) => {
    document.body.className = `theme-${themeName}`;
  };

  const handleThemeChange = (themeName) => {
    setCurrentTheme(themeName);
    applyTheme(themeName);
    localStorage.setItem('chat-theme', themeName);
    setShowThemeModal(false);
  };

  const loadConversations = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/conversations`);
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const startNewConversation = () => {
    setCurrentConversationId('');
    setMessages([]);
    setUploadedFiles([]);
  };

  const loadConversation = async (conversationId) => {
    if (loadingConversation) return;
    
    setLoadingConversation(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/conversations/${conversationId}`);
      setMessages(response.data.messages || []);
      setCurrentConversationId(conversationId);
      
      const filesResponse = await axios.get(`${API_BASE_URL}/conversations/${conversationId}/files`);
      setUploadedFiles(filesResponse.data.files || []);
    } catch (error) {
      console.error('Error loading conversation:', error);
    } finally {
      setLoadingConversation(false);
    }
  };

  const deleteConversation = async (conversationId) => {
    try {
      await axios.delete(`${API_BASE_URL}/conversations/${conversationId}`);
      setConversations(conversations.filter(conv => conv.id !== conversationId));
      if (currentConversationId === conversationId) {
        startNewConversation();
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: inputMessage,
        conversation_id: currentConversationId
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (!currentConversationId && response.data.conversation_id) {
        setCurrentConversationId(response.data.conversation_id);
        loadConversations();
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'I encountered an issue processing your request. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('conversation_id', currentConversationId);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const fileNames = response.data.file_names || [];
      const fileObjects = fileNames.map(name => ({
        filename: name,
        uploadTime: new Date().toISOString()
      }));
      setUploadedFiles(prev => [...prev, ...fileObjects]);
      
      if (!currentConversationId && response.data.conversation_id) {
        setCurrentConversationId(response.data.conversation_id);
        loadConversations();
      }
    } catch (error) {
      console.error('Error uploading files:', error);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit'
    });
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">✨ Premium Chat</div>
        </div>
        
        <button className="new-chat-btn" onClick={startNewConversation}>
          + New Chat
        </button>

        <div className="conversations-list">
          {conversations.map(conv => (
            <div 
              key={conv.id} 
              className={`conversation-item ${currentConversationId === conv.id ? 'active' : ''}`}
              onClick={() => loadConversation(conv.id)}
            >
              <div className="conversation-title">{conv.title}</div>
              <div className="conversation-meta">
                {conv.message_count} messages • {new Date(conv.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
        
        <div className="sidebar-footer">
          <div className="sidebar-item">
            <span>🌙</span> Dark Mode
          </div>
          <div className="sidebar-item" onClick={() => setShowThemeModal(true)}>
            <span>🎨</span> Color Themes
          </div>
          <div className="sidebar-item">
            <span>⚙️</span> Settings
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="chat-header">
          <h1>✨ Premium Chat Interface</h1>
          <p>Experience AI conversation with premium styling and color themes</p>
          <div className="premium-badge">Premium</div>
        </div>

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-message">
                <div className="assistant-avatar">
                  <div className="avatar-icon">🤖</div>
                </div>
                <div className="welcome-text">
                  Hello! I'm your AI assistant with premium styling. How can I help you today?
                </div>
                <div className="welcome-timestamp">
                  {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} AM
                </div>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className={`message-wrapper ${message.role}`}>
                <div className="message-avatar">
                  {message.role === 'user' ? (
                    <div className="user-avatar">
                      <div className="avatar-icon">👤</div>
                    </div>
                  ) : (
                    <div className="assistant-avatar">
                      <div className="avatar-icon">🤖</div>
                    </div>
                  )}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-timestamp">
                    {formatTimestamp(message.timestamp)}
                  </div>
                </div>
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="message-wrapper assistant">
              <div className="message-avatar">
                <div className="assistant-avatar">
                  <div className="avatar-icon">🤖</div>
                </div>
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="file-upload-section">
            <input
              type="file"
              id="file-upload"
              multiple
              accept=".xlsx,.xls,.csv,.json,.png,.jpg,.jpeg"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-upload" className="attach-btn">
              📎 Attach files (Excel, CSV, JSON, Images)
            </label>
            {uploadedFiles.length > 0 && (
              <div className="uploaded-files">
                {uploadedFiles.map((file, index) => (
                  <span key={index} className="file-tag">
                    {file.filename}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          <div className="input-container">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              className="message-input"
              rows="1"
              disabled={isLoading}
            />
            <button 
              onClick={sendMessage} 
              className="send-btn"
              disabled={isLoading || !inputMessage.trim()}
            >
              ↑
            </button>
          </div>
        </div>
      </div>
      
      {/* Theme Modal */}
      {showThemeModal && (
        <div className="modal-overlay" onClick={() => setShowThemeModal(false)}>
          <div className="theme-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>🎨 Premium Color Themes</h3>
              <button className="close-btn" onClick={() => setShowThemeModal(false)}>×</button>
            </div>
            <div className="themes-grid">
              {Object.entries(themes).map(([key, theme]) => (
                <div 
                  key={key} 
                  className={`theme-card ${currentTheme === key ? 'active' : ''}`}
                  onClick={() => handleThemeChange(key)}
                >
                  <div className="theme-header">
                    <div className="theme-name">{theme.name}</div>
                    {currentTheme === key && <div className="active-badge">✓ Active</div>}
                  </div>
                  <div className="theme-colors">
                    {theme.colors.map((color, index) => (
                      <div key={index} className="color-dot" style={{ backgroundColor: color }}></div>
                    ))}
                  </div>
                  <div className="theme-description">{theme.description}</div>
                </div>
              ))}
            </div>
            <div className="premium-features">
              <h4>Premium Features</h4>
              <ul>
                <li>• 6 carefully crafted color palettes</li>
                <li>• Automatic dark mode adaptation</li>
                <li>• Persistent theme preferences</li>
                <li>• Optimized for accessibility</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
