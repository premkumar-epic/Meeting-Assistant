import React, { useState, useEffect, useRef, useMemo } from 'react';
import './App.css';
import { 
  fetchMeetingsList, fetchMeetingDetail, deleteMeeting, 
  fetchModelsStatus, activateModel, startModelDownload, 
  pollModelDownload, uploadMeetingFile, getChatStreamResponse 
} from './services/api';
import { useJobPoller } from './hooks/useJobPoller';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

// Components
import Sidebar from './components/Sidebar';
import SettingsModal from './components/SettingsModal';
import MeetingDetail from './components/MeetingDetail';
import UploadDropzone from './components/UploadDropzone';

function App() {
  const [meetings, setMeetings] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMeetingId, setSelectedMeetingId] = useState(null);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [isSettingsActive, setIsSettingsActive] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [chatMessages, setChatMessages] = useState([]);
  const [isChatSending, setIsChatSending] = useState(false);
  
  const [modelsStatus, setModelsStatus] = useState(null);
  const [downloadProgress, setDownloadProgress] = useState({});
  
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Job Polling hook for Uploads
  const { 
    isPolling: isUploading, 
    status: uploadStatus, 
    progress: uploadProgress, 
    startPolling 
  } = useJobPoller(API_URL);

  // Load meetings on mount
  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    try {
      const data = await fetchMeetingsList();
      setMeetings(data.meetings || []);
    } catch (err) {
      console.error('Failed to load meetings:', err);
    }
  };

  // Load selected meeting details
  useEffect(() => {
    if (selectedMeetingId) {
      loadMeetingDetail(selectedMeetingId);
      setActiveTab('summary');
      setChatMessages([{ sender: 'ai', text: 'Hello! I am your AI Meeting Assistant. Ask me anything about this meeting.' }]);
    } else {
      setSelectedMeeting(null);
    }
  }, [selectedMeetingId]);

  const loadMeetingDetail = async (id) => {
    try {
      const data = await fetchMeetingDetail(id);
      setSelectedMeeting(data);
    } catch (err) {
      console.error('Failed to fetch meeting detail:', err);
      setSelectedMeetingId(null);
    }
  };

  // Delete Meeting
  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this meeting?")) return;
    try {
      await deleteMeeting(id);
      if (selectedMeetingId === id) setSelectedMeetingId(null);
      await loadMeetings();
    } catch (err) {
      console.error('Failed to delete meeting:', err);
    }
  };

  // Settings & Models
  useEffect(() => {
    if (isSettingsActive) {
      loadModelsStatus();
    }
  }, [isSettingsActive]);

  const loadModelsStatus = async () => {
    try {
      const data = await fetchModelsStatus();
      setModelsStatus(data);
    } catch (err) {
      console.error('Failed to fetch models status:', err);
    }
  };

  const handleActivateModel = async (category, modelId) => {
    if (!modelsStatus) return;
    try {
      await activateModel(category, modelId, modelsStatus.active_config);
      alert('Active model configuration updated successfully.');
      loadModelsStatus();
    } catch (err) {
      alert(`Failed to activate model: ${err.message}`);
    }
  };

  const handleDownloadModel = async (category, modelId) => {
    try {
      setDownloadProgress(prev => ({
        ...prev,
        [modelId]: { progress: 5, status: 'Queuing download...' }
      }));
      await startModelDownload(category, modelId);
      
      const intervalId = setInterval(async () => {
        try {
          const data = await pollModelDownload(modelId);
          setDownloadProgress(prev => ({ ...prev, [modelId]: data }));
          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(intervalId);
            loadModelsStatus();
          }
        } catch (pollErr) {
          console.error(`Polling failed for ${modelId}:`, pollErr);
          clearInterval(intervalId);
        }
      }, 2000);
    } catch (err) {
      alert(`Download failed to start: ${err.message}`);
      setDownloadProgress(prev => {
        const copy = { ...prev };
        delete copy[modelId];
        return copy;
      });
    }
  };

  // Streaming Chat
  const handleSendChat = async (userMessage) => {
    setChatMessages(prev => [...prev, { sender: 'user', text: userMessage }]);
    setIsChatSending(true);
    
    try {
      const history = chatMessages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.text
      }));

      const res = await getChatStreamResponse(selectedMeetingId, userMessage, history);
      
      setChatMessages(prev => [...prev, { sender: 'ai', text: '' }]);
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let textBuffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunkString = decoder.decode(value, { stream: true });
          const lines = chunkString.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              try {
                const data = JSON.parse(dataStr);
                if (data.error) throw new Error(data.error);
                if (data.chunk) {
                  textBuffer += data.chunk;
                  setChatMessages(prev => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { sender: 'ai', text: textBuffer };
                    return newMessages;
                  });
                }
              } catch (e) {
                // ignore parse errors
              }
            }
          }
        }
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { sender: 'ai', text: `Error: ${err.message}. Please verify the model is loaded.` }]);
    } finally {
      setIsChatSending(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const data = await uploadMeetingFile(formData);
      startPolling(data.job_id, {
        onSuccess: (result) => {
          loadMeetings();
          setSelectedMeetingId(result.meeting_id);
        },
        onError: (err) => {
          alert(`Error processing meeting: ${err.message}`);
        }
      });
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const formatDuration = (secs) => {
    const minutes = Math.floor(secs / 60);
    const remainingSeconds = Math.round(secs % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}m`;
  };

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  };

  return (
    <div className="app-container">
      <Sidebar 
        meetings={meetings}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        selectedMeetingId={selectedMeetingId}
        setSelectedMeetingId={setSelectedMeetingId}
        isSettingsActive={isSettingsActive}
        setIsSettingsActive={setIsSettingsActive}
        formatDuration={formatDuration}
        formatDate={formatDate}
      />

      <div className="main-content">
        {isUploading ? (
          <div className="empty-state">
            <div className="processing-card glass-panel">
              <div className="spinner"></div>
              <div className="status-indicator">{uploadStatus}</div>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${uploadProgress}%` }}></div>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '-8px' }}>
                {uploadProgress}% Complete
              </div>
              <p className="processing-sub">
                Our local AI pipeline is processing your audio file.<br />
                This executes entirely on your device for absolute data privacy.
              </p>
            </div>
          </div>
        ) : isSettingsActive ? (
          <SettingsModal 
            modelsStatus={modelsStatus}
            downloadProgress={downloadProgress}
            handleActivateModel={handleActivateModel}
            handleDownloadModel={handleDownloadModel}
          />
        ) : selectedMeeting ? (
          <MeetingDetail 
            selectedMeeting={selectedMeeting}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            handleDelete={handleDelete}
            formatDuration={formatDuration}
            formatDate={formatDate}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            isChatSending={isChatSending}
            handleSendChat={handleSendChat}
          />
        ) : (
          <UploadDropzone 
            dragActive={dragActive}
            handleDrag={handleDrag}
            handleDrop={handleDrop}
            fileInputRef={fileInputRef}
            handleFileSelect={handleFileSelect}
          />
        )}
      </div>
    </div>
  );
}

export default App;
