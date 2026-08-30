import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../../store/useStore';
import { uploadRepository } from '../../services/apiService';
import './UploadModal.css';

const MAX_MB = 50;

export default function UploadModal({ onClose }) {
  const navigate = useNavigate();
  const { setActiveRepo, addNotification } = useStore();
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | uploading | success | error
  const [errorMsg, setErrorMsg] = useState('');
  const fileRef = useRef(null);

  const validate = (f) => {
    if (!f.name.endsWith('.zip')) {
      setErrorMsg('Only .zip files are supported.');
      return false;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setErrorMsg(`File exceeds ${MAX_MB}MB limit.`);
      return false;
    }
    return true;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && validate(f)) { setFile(f); setErrorMsg(''); }
  };

  const handleChange = (e) => {
    const f = e.target.files[0];
    if (f && validate(f)) { setFile(f); setErrorMsg(''); }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    setProgress(0);

    const { data, error } = await uploadRepository(file, setProgress);

    if (error) {
      setStatus('error');
      setErrorMsg(error);
      return;
    }

    setStatus('success');
    setActiveRepo(data.repository);
    addNotification(`Repository "${data.repository.name}" analyzed successfully.`, 'success');
    setTimeout(() => {
      onClose();
      navigate('/repository');
    }, 1200);
  };

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Upload Repository">
      <div className="modal-panel" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Import Repository</h2>
          <button className="btn-icon" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="modal-body">
          {/* Dropzone */}
          <div
            className={`upload-dropzone ${dragging ? 'upload-dropzone--drag' : ''} ${file ? 'upload-dropzone--ready' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Drop ZIP file here or click to browse"
            onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".zip"
              style={{ display: 'none' }}
              onChange={handleChange}
            />
            {file ? (
              <>
                <div className="upload-file-icon">📦</div>
                <div className="upload-file-name">{file.name}</div>
                <div className="text-sm muted">{(file.size / 1024 / 1024).toFixed(1)} MB</div>
              </>
            ) : (
              <>
                <div className="upload-drop-icon">⬆</div>
                <div className="upload-drop-title">Drop your repository ZIP here</div>
                <div className="text-sm muted">or click to browse — max {MAX_MB}MB</div>
              </>
            )}
          </div>

          {/* Security note */}
          <div className="upload-security-note text-xs muted">
            🔒 Files are analyzed statically. No code is executed. 
            node_modules, .git, build artifacts excluded automatically.
          </div>

          {/* Progress */}
          {status === 'uploading' && (
            <div className="upload-progress">
              <div className="upload-progress-label text-sm muted">
                Uploading and analyzing… {progress}%
              </div>
              <div className="upload-progress-bar">
                <div className="upload-progress-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {status === 'success' && (
            <div className="upload-success">
              <span className="text-green">✓</span> Repository analyzed successfully!
            </div>
          )}

          {errorMsg && (
            <div className="upload-error">{errorMsg}</div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose} disabled={status === 'uploading'}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!file || status === 'uploading' || status === 'success'}
          >
            {status === 'uploading' ? 'Analyzing…' : 'Analyze Repository'}
          </button>
        </div>
      </div>
    </div>
  );
}
