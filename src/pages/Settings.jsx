import { useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { uploadVideo, analyzeVideo } from '../services/api';
import PageHeader from '../components/shared/PageHeader';

function Section({ icon, title, description, children }) {
  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center gap-3">
        <span className="material-symbols-outlined text-[18px] text-primary flex-shrink-0">{icon}</span>
        <div className="min-w-0">
          <span className="font-label-sm text-on-surface text-[11px] tracking-wider">{title}</span>
          {description && (
            <span className="font-body-sm text-outline text-[10px] block mt-0.5">{description}</span>
          )}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors flex-shrink-0 ${
        checked ? 'bg-primary' : 'bg-outline-variant/40'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-surface transition-transform shadow ${
          checked ? 'translate-x-5' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

function SettingRow({ label, description, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 border-b border-outline-variant/10 last:border-0">
      <div className="min-w-0">
        <span className="font-body-sm text-on-surface text-[12px] block">{label}</span>
        {description && (
          <span className="font-label-xs text-outline text-[9px] mt-0.5 block">{description}</span>
        )}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

function TextField({ label, defaultValue }) {
  const [value, setValue] = useState(defaultValue);
  return (
    <div>
      <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block mb-1">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="w-full bg-surface-container-low border border-outline-variant/30 rounded-lg px-3 py-2 font-label-xs text-on-surface text-[11px] outline-none focus:border-primary/40 placeholder:text-outline/50"
      />
    </div>
  );
}

function SelectField({ label, options }) {
  const [value, setValue] = useState(options[0]);
  return (
    <div>
      <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block mb-1">{label}</span>
      <div className="flex items-center gap-2 bg-surface-container-low border border-outline-variant/30 rounded-lg px-3 py-2">
        <select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="bg-transparent font-label-xs text-on-surface text-[11px] outline-none w-full appearance-none cursor-pointer"
        >
          {options.map((opt) => (
            <option key={opt} value={opt} className="bg-surface-container text-on-surface">
              {opt}
            </option>
          ))}
        </select>
        <span className="material-symbols-outlined text-[14px] text-outline">expand_more</span>
      </div>
    </div>
  );
}

export default function Settings() {
  const { demoMode, setDemoMode, cameras, videoProgress, addNotification } = useApp();
  const [saved, setSaved] = useState(false);
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [selectedCamera, setSelectedCamera] = useState('');

  const camOptions = cameras.map((c) => c.id);

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setActiveJob(null);
    try {
      const res = await uploadVideo(file, selectedCamera || null);
      addNotification({
        type: 'video',
        severity: 'info',
        title: 'Video uploaded',
        message: `${file.name} queued for analysis (${res.videoId}).`,
      });
      const analysis = await analyzeVideo(res.videoId, selectedCamera || null);
      setActiveJob(analysis.videoId || res.videoId);
      addNotification({
        type: 'video',
        severity: 'info',
        title: 'Analysis started',
        message: `${analysis.videoId || res.videoId} is now processing on the AI backend.`,
      });
    } catch (err) {
      setUploadError(err.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const activeProgress = activeJob ? (videoProgress[activeJob] || {}) : null;
  const progressValue = activeProgress?.progress ?? (activeJob ? 0 : null);

  const [notifications, setNotifications] = useState({ desktop: true, email: true, sound: false, incidents: true });
  const [privacy, setPrivacy] = useState({ blurFaces: true, retention: true, auditLogging: true });

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-5">
      <PageHeader icon="tune" title="SETTINGS" subtitle="SYSTEM CONFIGURATION & PREFERENCES">
        <span className="inline-flex items-center gap-1.5 bg-surface-container-high border border-outline-variant/30 text-on-surface-variant font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
          <span className="material-symbols-outlined text-[12px]">lock</span>
          ADMIN CONTEXT
        </span>
      </PageHeader>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="space-y-4">
          <Section icon="settings" title="GENERAL" description="Workspace-wide system identity">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <TextField label="SYSTEM NAME" defaultValue="SENTINEL AI" />
              <SelectField label="TIME ZONE" options={['UTC', 'GMT+5:30', 'GMT+8', 'GMT-5']} />
            </div>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <SelectField label="LANGUAGE" options={['ENGLISH', 'ESPANOL', 'FRANCAIS', 'DEUTSCH']} />
              <SelectField label="THEME" options={['SENTINEL DARK', 'SENTINEL LIGHT']} />
            </div>
          </Section>

          <Section icon="science" title="DEMO MODE" description="Simulated live telemetry via local WebSocket">
            <SettingRow
              label="Enable demo data stream"
              description="Streams simulated camera, detection and incident events. Disable to connect to production services."
            >
              <Toggle checked={demoMode} onChange={setDemoMode} />
            </SettingRow>
            <div className="flex items-center gap-2 mt-3 rounded-lg bg-surface-container-low border border-outline-variant/20 px-3 py-2">
              <span className={`h-1.5 w-1.5 rounded-full ${demoMode ? 'bg-secondary animate-pulse' : 'bg-outline/40'}`} />
              <span className="font-label-xs text-on-surface-variant text-[9px] tracking-wider">
                {demoMode ? 'DEMO TELEMETRY ACTIVE' : 'SIMULATION DISABLED'}
              </span>
              <span className="font-label-xs text-outline text-[8px] ml-auto">
                ws://cv.sentinel.internal:8443
              </span>
            </div>
          </Section>

          <Section icon="notifications" title="NOTIFICATIONS" description="Alert routing preferences">
            <SettingRow label="Desktop alerts" description="Push critical incident banners to this workstation.">
              <Toggle checked={notifications.desktop} onChange={(v) => setNotifications((s) => ({ ...s, desktop: v }))} />
            </SettingRow>
            <SettingRow label="Email digest" description="Quarterly report of detections and resolved incidents.">
              <Toggle checked={notifications.email} onChange={(v) => setNotifications((s) => ({ ...s, email: v }))} />
            </SettingRow>
            <SettingRow label="Audible alerts" description="Play an audible tone on new critical incidents.">
              <Toggle checked={notifications.sound} onChange={(v) => setNotifications((s) => ({ ...s, sound: v }))} />
            </SettingRow>
            <SettingRow label="Incident creation" description="Notify the duty officer when an incident is opened.">
              <Toggle checked={notifications.incidents} onChange={(v) => setNotifications((s) => ({ ...s, incidents: v }))} />
            </SettingRow>
          </Section>
        </div>

        <div className="space-y-4">
          <Section icon="movie_filter" title="VIDEO ANALYSIS UPLOAD" description="Send footage to the AI backend for event detection">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block mb-1">FOOTAGE FILE</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/mov,video/x-msvideo,video/webm,video/mpeg,video/x-matroska"
                  className="w-full text-[10px] text-on-surface-variant bg-surface-container-low rounded-lg border border-outline-variant/30 px-3 py-2 file:mr-3 file:font-label-xs file:text-[9px] file:tracking-wider file:text-on-primary file:bg-primary file:border-0 file:rounded file:px-2 file:py-1"
                />
              </div>
              <div>
                <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase block mb-1">SOURCE CAMERA</span>
                <select
                  value={selectedCamera}
                  onChange={(e) => setSelectedCamera(e.target.value)}
                  className="w-full text-[10px] text-on-surface bg-surface-container-low rounded-lg border border-outline-variant/30 px-3 py-2 focus:outline-none focus:border-primary/50"
                >
                  <option value="">UNASSIGNED</option>
                  {camOptions.map((c) => (
                    <option key={c} value={c} className="bg-surface-container text-on-surface">{c}</option>
                  ))}
                </select>
              </div>
            </div>
            {uploadError && <p className="font-body-sm text-error text-[10px] mt-2">{uploadError}</p>}
            {activeJob && (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-label-xs text-outline text-[9px] tracking-wider">{activeJob}</span>
                  <span className="font-label-xs text-on-surface-variant text-[9px]">
                    {activeProgress?.status === 'failed' ? 'FAILED' : `${Math.round(progressValue || 0)}%`}
                  </span>
                </div>
                <div className="h-2 bg-surface-container-lowest rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${activeProgress?.status === 'failed' ? 'bg-error' : 'bg-primary'}`}
                    style={{ width: `${Math.min(progressValue || 0, 100)}%` }}
                  />
                </div>
                {activeProgress?.status === 'failed' && (
                  <p className="font-body-sm text-error text-[10px] mt-1">Processing failed. Check backend AI queue logs.</p>
                )}
              </div>
            )}
            <div className="flex items-center gap-3 mt-4">
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="inline-flex items-center gap-1.5 bg-primary text-on-primary font-label-xs text-[9px] tracking-wider px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-40"
              >
                <span className="material-symbols-outlined text-[13px]">upload</span>
                {uploading ? 'UPLOADING…' : 'UPLOAD & ANALYZE'}
              </button>
              {activeJob && activeProgress?.status === 'completed' && (
                <span className="font-label-xs text-secondary text-[9px] tracking-wider">ANALYSIS COMPLETE</span>
              )}
            </div>
          </Section>

          <Section icon="videocam" title="CAMERA DEFAULTS" description="Defaults applied to newly registered nodes">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <SelectField label="DEFAULT RESOLUTION" options={['1080p', '720p', '4K UHD']} />
              <SelectField label="DEFAULT FRAME RATE" options={['30 FPS', '60 FPS', '25 FPS']} />
            </div>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <SelectField label="RECORDING RETENTION" options={['30 DAYS', '60 DAYS', '90 DAYS', '1 YEAR']} />
              <SelectField label="STREAM CODEC" options={['H.265 / HEVC', 'H.264 / AVC', 'H.266 / VVC']} />
            </div>
            <SettingRow label="Auto-calibrate on registration" description="Run PTZ and white-balance calibration when a camera joins the network.">
              <Toggle checked={true} onChange={() => {}} />
            </SettingRow>
          </Section>

          <Section icon="neurology" title="AI CONFIGURATION" description="Detection model pipeline settings">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <SelectField label="DETECTION MODEL" options={['YOLOv9b', 'YOLOv9x', 'YOLOv10n']} />
              <SelectField label="TRACKING ENGINE" options={['BYTETrack', 'StrongSORT']} />
            </div>
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase">CONFIDENCE THRESHOLD</span>
                <span className="font-label-xs text-primary text-[10px]">85%</span>
              </div>
              <div className="h-1.5 bg-surface-container-lowest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: '85%' }} />
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="font-label-xs text-outline text-[8px]">LOW</span>
                <span className="font-label-xs text-outline text-[8px]">HIGH</span>
              </div>
            </div>
            <SettingRow label="Batch inference offload" description="Offload non-critical inference jobs to secondary GPU core.">
              <Toggle checked={true} onChange={() => {}} />
            </SettingRow>
          </Section>

          <Section icon="gavel" title="PRIVACY & COMPLIANCE" description="ISO-27701 aligned governance controls">
            <SettingRow label="Automated face blurring" description="Privacy-mask identifiable faces in stored evidence review copies.">
              <Toggle checked={privacy.blurFaces} onChange={(v) => setPrivacy((s) => ({ ...s, blurFaces: v }))} />
            </SettingRow>
            <SettingRow label="Retention enforcement" description="Auto-purge non-evidence footage after the retention window.">
              <Toggle checked={privacy.retention} onChange={(v) => setPrivacy((s) => ({ ...s, retention: v }))} />
            </SettingRow>
            <SettingRow label="Audit logging" description="Log all operator queries, exports and configuration changes.">
              <Toggle checked={privacy.auditLogging} onChange={(v) => setPrivacy((s) => ({ ...s, auditLogging: v }))} />
            </SettingRow>
            <div className="flex items-center gap-2 mt-3 rounded-lg bg-surface-container-low border border-outline-variant/20 px-3 py-2">
              <span className="material-symbols-outlined text-[14px] text-secondary">verified_user</span>
              <span className="font-label-xs text-on-surface-variant text-[9px] tracking-wider">
                ISO-27701 · GDPR · CCPA COMPLIANT
              </span>
              <span className="font-label-xs text-secondary text-[8px] ml-auto">CERTIFIED</span>
            </div>
          </Section>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3">
        <span
          className={`font-label-xs text-secondary text-[9px] tracking-wider transition-opacity ${
            saved ? 'opacity-100' : 'opacity-0'
          }`}
        >
          <span className="material-symbols-outlined text-[12px] align-middle mr-1">check_circle</span>
          SETTINGS SAVED
        </span>
        <button
          onClick={handleSave}
          className="inline-flex items-center gap-1.5 bg-primary text-on-primary font-label-xs text-[9px] tracking-wider px-5 py-2.5 rounded-lg hover:bg-primary/90 transition-colors"
        >
          <span className="material-symbols-outlined text-[15px]">save</span>
          SAVE CHANGES
        </button>
      </div>
    </div>
  );
}