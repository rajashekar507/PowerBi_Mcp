import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = '/api';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [activeJobs, setActiveJobs] = useState({});
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingConversation, setLoadingConversation] = useState(false);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const pollInterval = useRef(null);

  // Initialize app
  useEffect(() => {
    loadConversations();
    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current);
      }
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Poll for job status updates
  useEffect(() => {
    if (Object.keys(activeJobs).length > 0) {
      pollInterval.current = setInterval(checkJobStatuses, 2000);
    } else if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
    
    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current);
      }
    };
  }, [activeJobs]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Load conversations list
  const loadConversations = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/conversations`);
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
      setConversations([]);
    }
  };

  // Load specific conversation
  const loadConversation = async (conversationId) => {
    if (loadingConversation) return;
    
    try {
      setLoadingConversation(true);
      const response = await axios.get(`${API_BASE_URL}/conversations/${conversationId}`);
      
      if (response.data && response.data.messages) {
        setMessages(response.data.messages);
        setCurrentConversationId(conversationId);
        
        // Load files for this conversation
        try {
          const filesResponse = await axios.get(`${API_BASE_URL}/conversations/${conversationId}/files`);
          if (filesResponse.data && filesResponse.data.files) {
            setUploadedFiles(filesResponse.data.files);
          }
        } catch (filesError) {
          console.error('Error loading conversation files:', filesError);
          setUploadedFiles([]);
        }
      }
    } catch (error) {
      console.error('Error loading conversation:', error);
      setMessages([]);
      setUploadedFiles([]);
    } finally {
      setLoadingConversation(false);
    }
  };

  // Start new conversation
  const startNewConversation = () => {
    setMessages([]);
    setUploadedFiles([]);
    setCurrentConversationId('');
    setActiveJobs({});
  };

  // Delete conversation
  const deleteConversation = async (conversationId) => {
    try {
      await axios.delete(`${API_BASE_URL}/conversations/${conversationId}`);
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      
      // If we're deleting the current conversation, start a new one
      if (currentConversationId === conversationId) {
        startNewConversation();
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  // Duplicates removed - using functions defined earlier

  const sendMessage = async () => {
    if (!inputMessage.trim() && uploadedFiles.length === 0) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

    // Add user message to UI immediately
    if (userMessage) {
      const newMessage = {
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, newMessage]);
    }

    try {
      // Send chat message
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: userMessage || 'I have uploaded files for dashboard creation',
        conversation_id: currentConversationId
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        dashboard_url: response.data.dashboard_url,
        download_link: response.data.download_link
      };

      setMessages(prev => [...prev, assistantMessage]);
      setCurrentConversationId(response.data.conversation_id);

      // If there are uploaded files and this looks like a dashboard request, create dashboard
      if (uploadedFiles.length > 0 && (userMessage.toLowerCase().includes('dashboard') || 
          userMessage.toLowerCase().includes('chart') || userMessage.toLowerCase().includes('visualization'))) {
        
        const dashboardResponse = await axios.post(`${API_BASE_URL}/create-dashboard`, {
          message: userMessage,
          conversation_id: response.data.conversation_id,
          file_paths: uploadedFiles.map(f => f.path)
        });

        if (dashboardResponse.data.job_id) {
          setActiveJobs(prev => ({
            ...prev,
            [dashboardResponse.data.job_id]: {
              conversation_id: response.data.conversation_id,
              status: 'processing',
              progress: 0
            }
          }));
        }
      }

      // Refresh conversations list
      loadConversations();

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        error: true
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

  const handleFileUpload = async (files) => {
    const formData = new FormData();
    
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });
    
    if (currentConversationId) {
      formData.append('conversation_id', currentConversationId);
    }

    try {
      // Don't disable chat during file upload
      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // Update uploaded files list with more details
      const newFiles = response.data.file_names.map(name => ({ 
        name, 
        path: name,
        type: name.split('.').pop().toLowerCase(),
        uploadTime: new Date().toISOString()
      }));
      
      setUploadedFiles(prev => [...prev, ...newFiles]);
      setCurrentConversationId(response.data.conversation_id);

      // Just log success - no auto-message like modern chat interfaces
      console.log('Files uploaded successfully:', response.data.file_names);

    } catch (error) {
      console.error('Error uploading files:', error);
      let errorText = 'Error uploading files. Please try again.';
      
      if (error.response?.data?.detail) {
        errorText = `Upload failed: ${error.response.data.detail}`;
      } else if (error.response?.status === 413) {
        errorText = 'File too large. Please upload files smaller than 100MB.';
      } else if (error.response?.status === 400) {
        errorText = 'Invalid file format. Please upload CSV, Excel, JSON, TXT, or image files.';
      }
      
      const errorMessage = {
        role: 'assistant', 
        content: errorText,
        timestamp: new Date().toISOString(),
        error: true
      };
      setMessages(prev => [...prev, errorMessage]);
    }
    // Don't disable chat after upload
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const checkJobStatuses = async () => {
    for (const jobId of Object.keys(activeJobs)) {
      try {
        const response = await axios.get(`${API_BASE_URL}/job-status/${jobId}`);
        const jobStatus = response.data;

        setActiveJobs(prev => ({
          ...prev,
          [jobId]: jobStatus
        }));

        // If job completed, add result message and refresh conversation
        if (jobStatus.status === 'completed' && jobStatus.response) {
          const resultMessage = {
            role: 'assistant',
            content: jobStatus.response,
            timestamp: new Date().toISOString(),
            dashboard_url: jobStatus.dashboard_url,
            download_link: jobStatus.download_link,
            completed: true
          };

          setMessages(prev => {
            // Check if we already added this completion message
            const hasCompletionMessage = prev.some(msg => 
              msg.completed && msg.content === jobStatus.response
            );
            
            if (!hasCompletionMessage) {
              return [...prev, resultMessage];
            }
            return prev;
          });

          // Remove from active jobs
          setActiveJobs(prev => {
            const newJobs = { ...prev };
            delete newJobs[jobId];
            return newJobs;
          });
        }
        
        // If job failed, show error
        if (jobStatus.status === 'error') {
          const errorMessage = {
            role: 'assistant',
            content: jobStatus.response || `Error: ${jobStatus.error}`,
            timestamp: new Date().toISOString(),
            error: true
          };
          setMessages(prev => [...prev, errorMessage]);

          // Remove from active jobs
          setActiveJobs(prev => {
            const newJobs = { ...prev };
            delete newJobs[jobId];
            return newJobs;
          });
        }

      } catch (error) {
        console.error(`Error checking job ${jobId}:`, error);
      }
    }
  };

  // Duplicate deleteConversation removed

  const formatMessage = (content) => {
    // Simple markdown-like formatting
    let formatted = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br/>');
    
    return { __html: formatted };
  };

  const renderProgressBar = (progress) => (
    <div className="progress-bar">
      <div className="progress-fill" style={{ width: `${progress}%` }}></div>
    </div>
  );

  return (
    <div className="app">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>🤖 AI Power BI</h2>
          <button 
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? '‹' : '›'}
          </button>
        </div>
        
        <button className="new-chat-btn" onClick={startNewConversation}>
          + New Dashboard
        </button>

        <div className="conversations-list">
          {conversations.map(conv => (
            <div key={conv.id} className={`conversation-item ${currentConversationId === conv.id ? 'active' : ''}`}>
              <div 
                className="conversation-content"
                onClick={() => loadConversation(conv.id)}
              >
                <div className="conversation-title">{conv.title}</div>
                <div className="conversation-meta">
                  {conv.message_count} messages • {new Date(conv.updated_at).toLocaleDateString()}
                </div>
              </div>
              <button 
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="main-content">
        <div className="chat-header">
          <h1>AI Power BI Dashboard Generator</h1>
          <p>Upload your data and create professional Power BI dashboards just by chatting!</p>
        </div>

        <div 
          className={`chat-messages ${isDragging ? 'dragging' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          {messages.length === 0 && (
            <div className="welcome-message">
              <h3>👋 Welcome! I'm your AI Power BI Assistant</h3>
              <p>I can help you create professional dashboards in minutes. Here's how:</p>
              <div className="feature-grid">
                <div className="feature">
                  <div className="feature-icon">📁</div>
                  <h4>1. Upload Your Data</h4>
                  <p>Drop Excel, CSV, or JSON files here</p>
                </div>
                <div className="feature">
                  <div className="feature-icon">💬</div>
                  <h4>2. Describe Your Dashboard</h4>
                  <p>"Create a sales dashboard with monthly trends"</p>
                </div>
                <div className="feature">
                  <div className="feature-icon">🎨</div>
                  <h4>3. Get Your Dashboard</h4>
                  <p>Receive a real, working Power BI dashboard</p>
                </div>
              </div>
              <div className="example-prompts">
                <h4>Try saying:</h4>
                <div className="prompt-examples">
                  <span className="prompt">"Create a sales dashboard with monthly trends"</span>
                  <span className="prompt">"Build an executive summary with KPIs"</span>
                  <span className="prompt">"Make a financial report with charts"</span>
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role} ${message.error ? 'error' : ''}`}>
              <div className="message-wrapper">
                <div className="message-avatar">
                  {message.role === 'user' ? 'U' : message.role === 'assistant' ? 'AI' : '!'}
                </div>
                <div className="message-content">
                  <div 
                    dangerouslySetInnerHTML={formatMessage(message.content)}
                  />
                  
                  {message.dashboard_url && (
                    <div className="dashboard-links">
                      <a href={message.dashboard_url} target="_blank" rel="noopener noreferrer" className="dashboard-link">
                        View Dashboard
                      </a>
                      {message.download_link && (
                        <a href={message.download_link} target="_blank" rel="noopener noreferrer" className="dashboard-link">
                          Download .pbix
                        </a>
                      )}
                    </div>
                  )}
                  
                  {uploadedFiles.length > 0 && message.role === 'user' && index === messages.length - 1 && (
                    <div className="uploaded-files">
                      <div className="file-list">
                        {uploadedFiles.map((file, fileIndex) => (
                          <div key={fileIndex} className="file-item">
                            📎 {file.name}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="message-timestamp">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Active Jobs Progress */}
          {Object.entries(activeJobs).map(([jobId, job]) => (
            <div key={jobId} className="message assistant processing">
              <div className="message-content">
                <div className="processing-status">
                  <div className="status-text">
                    🔄 Creating your dashboard... ({job.progress || 0}%)
                  </div>
                  {renderProgressBar(job.progress || 0)}
                  <div className="status-detail">
                    Status: {job.status}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="message assistant loading">
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



        {/* Chat Input Container */}
        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            {/* File Upload Area */}
            <div className="file-upload-area">
              {uploadedFiles.length > 0 && (
                <div className="uploaded-files-display">
                  {uploadedFiles.map((file, index) => (
                    <div key={index} className="uploaded-file-tag">
                      📎 {file.name}
                      <button 
                        onClick={() => setUploadedFiles(prev => prev.filter((_, i) => i !== index))}
                        style={{ background: 'none', border: 'none', color: '#999', marginLeft: '8px', cursor: 'pointer' }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => handleFileUpload(e.target.files)}
                multiple
                accept=".xlsx,.xls,.csv,.json,.txt,.png,.jpg,.jpeg,.gif,.bmp"
                style={{ display: 'none' }}
              />
              
              <button 
                className="file-upload-button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
              >
                📎 Attach files (Excel, CSV, JSON, Images)
              </button>
            </div>
            
            {/* Input Container */}
            <div className="input-container">
              <textarea
                className="chat-input"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Message AI Power BI Assistant..."
                disabled={isLoading}
                rows={1}
              />
              
              <button 
                className="send-button"
                onClick={sendMessage}
                disabled={isLoading || (!inputMessage.trim() && uploadedFiles.length === 0)}
              >
                {isLoading ? (
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                ) : (
                  '↑'
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;