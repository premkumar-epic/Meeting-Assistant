import React from 'react';
import { Settings, Cpu, Activity, FileText, Sparkles, DownloadCloud } from 'lucide-react';

export default function SettingsModal({
  modelsStatus,
  downloadProgress,
  handleActivateModel,
  handleDownloadModel
}) {
  return (
    <div className="settings-panel glass-panel">
      <h1 className="settings-title title">
        <Settings size={28} style={{ verticalAlign: 'middle', marginRight: '10px' }} />
        AI Model Manager
      </h1>
      <p className="settings-subtitle">
        Configure and cache local AI models for speech recognition, summarization, and interactive Q&A.
      </p>

      {modelsStatus ? (
        <>
          {/* System Specs Section */}
          <div className="settings-section">
            <h2 className="settings-section-title"><Cpu size={18} /> System Hardware Profile</h2>
            <div className="specs-grid">
              <div className="spec-card">
                <span className="spec-label">System Memory (RAM)</span>
                <span className="spec-value">{modelsStatus.specs.ram_gb} GB</span>
                <span className={`spec-badge ${modelsStatus.specs.recommendation_tier}`}>
                  Tier: {modelsStatus.specs.recommendation_tier.toUpperCase()}
                </span>
              </div>
              <div className="spec-card">
                <span className="spec-label">CPU Cores</span>
                <span className="spec-value">{modelsStatus.specs.cpu_count} Cores</span>
              </div>
              <div className="spec-card">
                <span className="spec-label">GPU Acceleration</span>
                <span className="spec-value">
                  {modelsStatus.specs.gpu_available ? 'Active (CUDA)' : 'CPU Only'}
                </span>
                {modelsStatus.specs.gpu_name && (
                  <span className="spec-sublabel">{modelsStatus.specs.gpu_name}</span>
                )}
              </div>
            </div>
          </div>

          {/* Model categories rendering */}
          {['asr', 'summarizer', 'llm'].map((category) => {
            const title = category === 'asr' ? 'Transcription Model (ASR)' :
                          category === 'summarizer' ? 'Summarization Model' : 'Q&A Chat Assistant (LLM)';
            const icon = category === 'asr' ? <Activity size={18} /> :
                         category === 'summarizer' ? <FileText size={18} /> : <Sparkles size={18} />;
            const models = modelsStatus[category];

            return (
              <div key={category} className="settings-section">
                <h3 className="settings-section-title">{icon} {title}</h3>
                <div className="models-list-group">
                  {models.map((m) => {
                    const isDownloading = downloadProgress[m.id] && downloadProgress[m.id].status !== 'completed' && downloadProgress[m.id].status !== 'failed';
                    const pct = downloadProgress[m.id] ? downloadProgress[m.id].progress : 0;
                    const dlStatus = downloadProgress[m.id] ? downloadProgress[m.id].status : '';

                    return (
                      <div key={m.id} className={`model-settings-row ${m.active ? 'active' : ''}`}>
                        <div className="model-row-info">
                          <div className="model-row-name-row">
                            <span className="model-row-name">{m.name}</span>
                            <span className="model-row-size">{m.size}</span>
                            {m.recommended && (
                              <span className="recommended-badge">Recommended</span>
                            )}
                            {m.active && (
                              <span className="active-badge">Active</span>
                            )}
                          </div>
                          <p className="model-row-desc">{m.description}</p>
                        </div>
                        
                        <div className="model-row-actions">
                          {isDownloading ? (
                            <div className="download-progress-container">
                              <span className="download-progress-status">{dlStatus} ({pct}%)</span>
                              <div className="progress-bar-container mini">
                                <div className="progress-bar" style={{ width: `${pct}%` }}></div>
                              </div>
                            </div>
                          ) : m.active ? (
                            <button className="model-btn active" disabled>
                              Active
                            </button>
                          ) : m.cached ? (
                            <button 
                              className="model-btn activate"
                              onClick={() => handleActivateModel(category, m.id)}
                            >
                              Activate
                            </button>
                          ) : (
                            <button 
                              className="model-btn download"
                              onClick={() => handleDownloadModel(category, m.id)}
                            >
                              <DownloadCloud size={14} /> Download & Cache
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </>
      ) : (
        <div className="settings-loading">
          <div className="spinner mini"></div>
          <span>Loading system profile and AI models...</span>
        </div>
      )}
    </div>
  );
}
