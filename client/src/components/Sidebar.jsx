import React, { useMemo } from 'react';
import { Activity, Plus, Search, Settings } from 'lucide-react';

export default function Sidebar({
  meetings,
  searchQuery,
  setSearchQuery,
  selectedMeetingId,
  setSelectedMeetingId,
  isSettingsActive,
  setIsSettingsActive,
  formatDuration,
  formatDate
}) {
  const filteredMeetings = useMemo(() => {
    return meetings.filter(m => 
      m.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.summary && m.summary.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [meetings, searchQuery]);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <Activity className="logo-icon" size={24} />
          <span className="title">Meeting Assistant</span>
        </div>
        <button className="new-btn" onClick={() => { setSelectedMeetingId(null); setIsSettingsActive(false); }}>
          <Plus size={18} /> New Meeting
        </button>
      </div>

      <div className="search-box">
        <Search className="search-icon" size={16} />
        <input 
          type="text" 
          placeholder="Search meetings..." 
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="meetings-list">
        {filteredMeetings.map((m) => (
          <div 
            key={m.id}
            className={`meeting-item ${selectedMeetingId === m.id ? 'active' : ''}`}
            onClick={() => { setSelectedMeetingId(m.id); setIsSettingsActive(false); }}
          >
            <div className="meeting-item-header">
              <span className="meeting-title" title={m.filename}>{m.filename}</span>
              <span className="meeting-duration">{formatDuration(m.duration)}</span>
            </div>
            <p className="meeting-preview">{m.summary || 'No summary generated.'}</p>
            <span className="meeting-date">{formatDate(m.created_at)}</span>
          </div>
        ))}
        {filteredMeetings.length === 0 && (
          <div className="empty-list-notice">No meetings found.</div>
        )}
      </div>
      
      <div className="sidebar-footer">
        <button 
          className={`sidebar-footer-btn ${isSettingsActive ? 'active' : ''}`}
          onClick={() => { setIsSettingsActive(true); setSelectedMeetingId(null); }}
        >
          <Settings size={16} /> AI Model Settings
        </button>
      </div>
    </div>
  );
}
