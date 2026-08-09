import React from 'react';
import { Clock, Calendar, Trash2, Sparkles, CheckSquare, Users, User } from 'lucide-react';
import ChatPanel from './ChatPanel';

export default function MeetingDetail({
  selectedMeeting,
  activeTab,
  setActiveTab,
  handleDelete,
  formatDuration,
  formatDate,
  chatMessages,
  setChatMessages,
  isChatSending,
  handleSendChat
}) {
  return (
    <>
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1 className="meeting-header-title">{selectedMeeting.filename}</h1>
          <div className="meeting-header-meta">
            <div className="meta-item">
              <Clock size={14} /> {formatDuration(selectedMeeting.duration)}
            </div>
            <div className="meta-item">
              <Calendar size={14} /> {formatDate(selectedMeeting.created_at)}
            </div>
          </div>
        </div>
        <button className="delete-btn" onClick={(e) => handleDelete(selectedMeeting.id, e)}>
          <Trash2 size={15} /> Delete Meeting
        </button>
      </div>

      <div className="tabs-bar">
        <button 
          className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          Summary & Insights
        </button>
        <button 
          className={`tab-btn ${activeTab === 'transcript' ? 'active' : ''}`}
          onClick={() => setActiveTab('transcript')}
        >
          Transcript
        </button>
        <button 
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          Q&A Chat
        </button>
      </div>

      <div className="dashboard-body">
        {activeTab === 'summary' && (
          <>
            {/* Summary Section */}
            <div className="summary-card glass-panel">
              <div className="summary-title title">
                <Sparkles size={18} /> Meeting Summary
              </div>
              <p className="summary-text">{selectedMeeting.summary}</p>
            </div>

            <div className="detail-grid">
              {/* Action Items List */}
              <div className="section-card glass-panel">
                <div className="section-title">
                  <CheckSquare size={18} className="logo-icon" /> Action Items
                </div>
                <div className="actions-list">
                  {selectedMeeting.action_items && selectedMeeting.action_items.map((item) => {
                    const assigneeClass = item.assignee.toLowerCase() === 'speaker' ? 'speaker' :
                                          item.assignee.toLowerCase() === 'team' ? 'team' :
                                          item.assignee.toLowerCase() === 'unassigned' ? 'unassigned' : 'user';
                    return (
                      <div key={item.id} className="action-card-item">
                        <CheckSquare size={16} className="action-checkbox" />
                        <div className="action-content">
                          <p className="action-text">{item.text}</p>
                          <span className={`assignee-badge ${assigneeClass}`}>{item.assignee}</span>
                        </div>
                      </div>
                    );
                  })}
                  {(!selectedMeeting.action_items || selectedMeeting.action_items.length === 0) && (
                    <div className="empty-list-notice">No action items detected.</div>
                  )}
                </div>
              </div>

              {/* Named Entities Section */}
              <div className="section-card glass-panel">
                <div className="section-title">
                  <Users size={18} className="logo-icon" /> Named Entities
                </div>
                <div className="entities-container">
                  {selectedMeeting.entities && ['PERSON', 'ORG', 'DATE'].map((label) => {
                    const groupEntities = selectedMeeting.entities.filter(e => e.label === label);
                    if (groupEntities.length === 0) return null;
                    return (
                      <div key={label} className="entity-group">
                        <span className="entity-group-title">
                          {label === 'PERSON' ? 'People' : label === 'ORG' ? 'Organizations' : 'Dates'}
                        </span>
                        <div className="entity-chips">
                          {groupEntities.map((ent, idx) => (
                            <span key={idx} className={`entity-chip ${label}`}>
                              {label === 'PERSON' && <User size={12} />}
                              {ent.text}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                  {(!selectedMeeting.entities || selectedMeeting.entities.length === 0) && (
                    <div className="empty-list-notice">No key entities extracted.</div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'transcript' && (
          <div className="transcript-panel">
            {selectedMeeting.transcript ? (
              selectedMeeting.transcript.split('. ').map((sentence, idx) => {
                const cleanText = sentence ? sentence.trim() : '';
                if (!cleanText) return null;
                return (
                  <div key={idx} className="transcript-segment">
                    <span className="segment-time">Sentence {idx + 1}</span>
                    <div className="segment-content">
                      <p className="segment-text">{cleanText}.</p>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-list-notice">No transcript available.</div>
            )}
          </div>
        )}

        {activeTab === 'chat' && (
          <ChatPanel 
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            isChatSending={isChatSending}
            handleSendChat={handleSendChat}
          />
        )}
      </div>
    </>
  );
}
