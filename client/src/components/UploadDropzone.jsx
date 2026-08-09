import React from 'react';
import { UploadCloud } from 'lucide-react';

export default function UploadDropzone({
  dragActive,
  handleDrag,
  handleDrop,
  fileInputRef,
  handleFileSelect
}) {
  return (
    <div className="empty-state" onDragEnter={handleDrag}>
      <div 
        className={`upload-card glass-panel ${dragActive ? 'drag-active' : ''}`}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
      >
        <div className="upload-icon-container">
          <UploadCloud size={48} className="upload-icon gradient-text" />
        </div>
        <h2 className="upload-title">Drop your meeting audio here</h2>
        <p className="upload-subtitle">
          Supports MP3, WAV, M4A, FLAC, OGG.<br/>
          Processed 100% locally on your device.
        </p>
        
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept="audio/*,video/mp4" 
          onChange={handleFileSelect}
        />
        <button className="upload-btn" onClick={() => fileInputRef.current.click()}>
          Select File
        </button>
      </div>
    </div>
  );
}
