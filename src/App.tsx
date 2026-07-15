import React, { useState, useEffect, useRef } from "react";
import { 
  Tv, 
  Youtube, 
  Instagram, 
  Calendar, 
  Download, 
  Play, 
  X, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  FolderOpen,
  Search,
  Eye,
  User,
  Settings,
  HelpCircle,
  Terminal,
  Moon,
  ToggleLeft
} from "lucide-react";
import "./App.css";

const API_BASE = "http://127.0.0.1:49152";

interface VideoItem {
  id: string;
  title: string;
  views: number;
  url: string;
  thumbnail: string;
  uploader: string;
  duration?: number;
}

interface ScheduledTask {
  id: string;
  video_path: string;
  platform: 'youtube' | 'instagram';
  caption: string;
  scheduled_time: string;
  status: 'scheduled' | 'uploading' | 'published' | 'failed';
  error_msg?: string;
  created_at: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "youtube" | "instagram" | "scheduler">("dashboard");
  const [downloadDir, setDownloadDir] = useState("C:\\Users\\MHVRG\\Downloads");
  
  // YouTube State
  const [ytTab, setYtTab] = useState<"channel" | "video">("channel");
  const [ytUrl, setYtUrl] = useState("");
  const [ytItems, setYtItems] = useState<VideoItem[]>([]);
  const [ytSelected, setYtSelected] = useState<Record<string, boolean>>({});
  const [ytLoading, setYtLoading] = useState(false);
  const [ytStatusText, setYtStatusText] = useState("");

  // Instagram State
  const [instaTab, setInstaTab] = useState<"reel" | "profile">("reel");
  const [instaUrl, setInstaUrl] = useState("");
  const [instaItems, setInstaItems] = useState<VideoItem[]>([]);
  const [instaSelected, setInstaSelected] = useState<Record<string, boolean>>({});
  const [instaLoading, setInstaLoading] = useState(false);
  const [instaStatusText, setInstaStatusText] = useState("");

  // Active Downloads State
  const [activeDownloads, setActiveDownloads] = useState<Record<string, any>>({});

  // Scheduler State
  const [schedulerList, setSchedulerList] = useState<ScheduledTask[]>([]);
  const [selectedScheduleFile, setSelectedScheduleFile] = useState("");
  const [schedulerCaption, setSchedulerCaption] = useState("");
  const [schedulerDate, setSchedulerDate] = useState("");
  const [schedulerHour, setSchedulerHour] = useState("12");
  const [schedulerMinute, setSchedulerMinute] = useState("00");
  const [schedulerAmpm, setSchedulerAmpm] = useState("PM");
  const [schedulerPlatform, setSchedulerPlatform] = useState<"youtube" | "instagram">("youtube");
  const [unqMirror, setUnqMirror] = useState(false);
  const [unqSpeed, setUnqSpeed] = useState(false);
  const [unqContrast, setUnqContrast] = useState(false);
  const [unqScrub, setUnqScrub] = useState(true);
  const [schedulerLogs, setSchedulerLogs] = useState<string[]>([]);

  // Clipboard monitor state
  const [monitorClipboard, setMonitorClipboard] = useState(false);

  // References
  const logsConsoleRef = useRef<HTMLDivElement>(null);

  // Initialize
  useEffect(() => {
    // Get default download dir
    fetch(`${API_BASE}/api/config/dir`)
      .then(res => res.json())
      .then(data => {
        if (data.download_dir) setDownloadDir(data.download_dir);
      })
      .catch(() => {});
      
    // Set default date to today
    const today = new Date().toISOString().split("T")[0];
    setSchedulerDate(today);
  }, []);

  // Polling loops
  useEffect(() => {
    const progressInterval = setInterval(() => {
      fetch(`${API_BASE}/api/downloads/progress`)
        .then(res => res.json())
        .then(data => setActiveDownloads(data))
        .catch(() => {});
    }, 1000);

    const schedulerInterval = setInterval(() => {
      if (activeTab === "scheduler") {
        fetchSchedulerTasks();
        fetchSchedulerLogs();
      }
    }, 2000);

    return () => {
      clearInterval(progressInterval);
      clearInterval(schedulerInterval);
    };
  }, [activeTab]);

  // Scroll logs to bottom when updated
  useEffect(() => {
    if (logsConsoleRef.current) {
      logsConsoleRef.current.scrollTop = logsConsoleRef.current.scrollHeight;
    }
  }, [schedulerLogs]);

  const fetchSchedulerTasks = () => {
    fetch(`${API_BASE}/api/scheduler/list`)
      .then(res => res.json())
      .then(data => setSchedulerList(data))
      .catch(() => {});
  };

  const fetchSchedulerLogs = () => {
    fetch(`${API_BASE}/api/scheduler/logs`)
      .then(res => res.json())
      .then(data => {
        if (data.logs) setSchedulerLogs(data.logs);
      })
      .catch(() => {});
  };

  const handleYtFetch = async () => {
    if (!ytUrl.trim()) return;
    setYtLoading(true);
    setYtStatusText("Fetching YouTube content metadata...");
    setYtItems([]);
    setYtSelected({});

    try {
      const res = await fetch(`${API_BASE}/api/yt/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: ytUrl })
      });
      const data = await res.json();
      if (data.error) {
        setYtStatusText(`Error: ${data.error}`);
      } else {
        setYtItems(data.items || []);
        setYtStatusText(`Successfully loaded ${data.items?.length || 0} items.`);
        // Auto-select all
        const sel: Record<string, boolean> = {};
        data.items?.forEach((item: any) => {
          sel[item.id] = true;
        });
        setYtSelected(sel);
      }
    } catch (err) {
      setYtStatusText(`Network Error: ${err}`);
    } finally {
      setYtLoading(false);
    }
  };

  const handleYtDownload = async () => {
    const selected = ytItems.filter(item => ytSelected[item.id]);
    if (selected.length === 0) return;

    for (const item of selected) {
      const task_id = `yt_${item.id}_${Date.now()}`;
      try {
        await fetch(`${API_BASE}/api/yt/download`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: item.url,
            download_dir: downloadDir,
            task_id
          })
        });
      } catch (err) {
        console.error(err);
      }
    }
  };

  const handleInstaFetch = async () => {
    if (!instaUrl.trim()) return;
    setInstaLoading(true);
    setInstaStatusText("Fetching Instagram Reels metadata...");
    setInstaItems([]);
    setInstaSelected({});

    try {
      const res = await fetch(`${API_BASE}/api/insta/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: instaUrl })
      });
      const data = await res.json();
      if (data.error) {
        setInstaStatusText(`Error: ${data.error}`);
      } else {
        setInstaItems(data.items || []);
        setInstaStatusText(`Successfully loaded ${data.items?.length || 0} Reels.`);
        // Auto-select all
        const sel: Record<string, boolean> = {};
        data.items?.forEach((item: any) => {
          sel[item.id] = true;
        });
        setInstaSelected(sel);
      }
    } catch (err) {
      setInstaStatusText(`Network Error: ${err}`);
    } finally {
      setInstaLoading(false);
    }
  };

  const handleInstaDownload = async () => {
    const selected = instaItems.filter(item => instaSelected[item.id]);
    if (selected.length === 0) return;

    for (const item of selected) {
      const task_id = `insta_${item.id}_${Date.now()}`;
      try {
        await fetch(`${API_BASE}/api/insta/download`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: item.url,
            download_dir: downloadDir,
            task_id
          })
        });
      } catch (err) {
        console.error(err);
      }
    }
  };

  // Scheduler handlers
  const handleAddSchedule = async () => {
    if (!selectedScheduleFile) return;

    // Build scheduled_time string
    let hourInt = parseInt(schedulerHour);
    if (schedulerAmpm === "PM" && hourInt < 12) hourInt += 12;
    else if (schedulerAmpm === "AM" && hourInt === 12) hourInt = 0;
    const time_str = `${hourInt.toString().padStart(2, '0')}:${schedulerMinute}`;
    const scheduled_time = `${schedulerDate} ${time_str}`;

    // Preventative YouTube PublishAt scheduling ISO conversion
    let publish_at = null;
    if (schedulerPlatform === "youtube") {
      const dt = new Date(`${schedulerDate}T${time_str}:00`);
      const now = new Date();
      // If greater than 5 minutes, schedule natively
      if (dt.getTime() > now.getTime() + 5 * 60 * 1000) {
        // Build timezone offset string
        const offset = -dt.getTimezoneOffset();
        const diff = offset >= 0 ? "+" : "-";
        const pad = (num: number) => num.toString().padStart(2, '0');
        const offset_str = `${diff}${pad(Math.floor(Math.abs(offset) / 60))}:${pad(Math.abs(offset) % 60)}`;
        // Local ISO
        publish_at = `${schedulerDate}T${time_str}:00${offset_str}`;
      }
    }

    const payload = {
      video_path: selectedScheduleFile,
      platform: schedulerPlatform,
      caption: schedulerCaption,
      scheduled_time,
      publish_at,
      uniquifier_opts: {
        mirror: unqMirror,
        speed: unqSpeed,
        contrast: unqContrast,
        scrub: unqScrub
      }
    };

    try {
      const res = await fetch(`${API_BASE}/api/scheduler/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setSelectedScheduleFile("");
        setSchedulerCaption("");
        fetchSchedulerTasks();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCancelTask = async (task_id: string) => {
    try {
      await fetch(`${API_BASE}/api/scheduler/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id })
      });
      fetchSchedulerTasks();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePublishNow = async (task_id: string) => {
    try {
      await fetch(`${API_BASE}/api/scheduler/publish_now`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id })
      });
      fetchSchedulerTasks();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-container">
      <div className="bg-glow"></div>
      <div className="bg-glow-bottom"></div>

      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div className="brand">
          <Tv size={24} color="#cba6f7" />
          <span className="brand-text">YT SYNC</span>
        </div>

        <div className="nav-menu">
          <div 
            className={`nav-item ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            <Moon size={16} />
            Dashboard
          </div>
          <div 
            className={`nav-item ${activeTab === "youtube" ? "active" : ""}`}
            onClick={() => setActiveTab("youtube")}
          >
            <Youtube size={16} />
            YouTube
          </div>
          <div 
            className={`nav-item ${activeTab === "instagram" ? "active" : ""}`}
            onClick={() => setActiveTab("instagram")}
          >
            <Instagram size={16} />
            Instagram
          </div>
          <div 
            className={`nav-item ${activeTab === "scheduler" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("scheduler");
              fetchSchedulerTasks();
              fetchSchedulerLogs();
            }}
          >
            <Calendar size={16} />
            Scheduler
          </div>
        </div>
      </div>

      {/* Content View */}
      <div className="content-area">
        
        {/* DASHBOARD TAB */}
        {activeTab === "dashboard" && (
          <div className="glass-panel" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 className="panel-header">Dashboard</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
              Welcome back to YT Sync Desktop. Fetch creator clips, download high quality assets, and schedule uploads to YouTube Studio or Instagram Reels.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginTop: "10px" }}>
              <div className="glass-panel" style={{ cursor: "pointer" }} onClick={() => setActiveTab("youtube")}>
                <Youtube size={32} color="var(--red)" style={{ marginBottom: "12px" }} />
                <h3 style={{ fontSize: "15px", fontWeight: "700" }}>YouTube Shorts</h3>
                <p style={{ color: "var(--text-dim)", fontSize: "11px", marginTop: "4px" }}>Scrape channel feeds and download MP4 clips.</p>
              </div>
              <div className="glass-panel" style={{ cursor: "pointer" }} onClick={() => setActiveTab("instagram")}>
                <Instagram size={32} color="var(--accent-color)" style={{ marginBottom: "12px" }} />
                <h3 style={{ fontSize: "15px", fontWeight: "700" }}>Instagram Reels</h3>
                <p style={{ color: "var(--text-dim)", fontSize: "11px", marginTop: "4px" }}>Scrape user feeds and download HD reels.</p>
              </div>
              <div className="glass-panel" style={{ cursor: "pointer" }} onClick={() => setActiveTab("scheduler")}>
                <Calendar size={32} color="var(--green)" style={{ marginBottom: "12px" }} />
                <h3 style={{ fontSize: "15px", fontWeight: "700" }}>Auto Scheduler</h3>
                <p style={{ color: "var(--text-dim)", fontSize: "11px", marginTop: "4px" }}>Schedule, mirror, mirror speed, and post.</p>
              </div>
            </div>

            {/* Active Downloads Queue */}
            <div className="glass-panel" style={{ marginTop: "10px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "12px" }}>Active Downloads Queue</h3>
              {Object.keys(activeDownloads).length === 0 ? (
                <p style={{ color: "var(--text-dim)", fontSize: "12px" }}>No active downloads in progress.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {Object.entries(activeDownloads).map(([id, info]: [string, any]) => (
                    <div key={id} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                        <span style={{ fontWeight: "700" }}>{id.split('_')[1] || "Video Download"}</span>
                        <span>{info.percent}% ({info.speed})</span>
                      </div>
                      <div style={{ background: "rgba(255,255,255,0.05)", height: "6px", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ background: "var(--accent-color)", width: `${info.percent}%`, height: "100%" }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* YOUTUBE DOWNLOADER TAB */}
        {activeTab === "youtube" && (
          <div className="glass-panel" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <h2 className="panel-header">YouTube Shorts Downloader</h2>

            <div className="tabs-header">
              <button 
                className={`tab-btn ${ytTab === "channel" ? "active" : ""}`}
                onClick={() => setYtTab("channel")}
              >
                Channel Scraper
              </button>
              <button 
                className={`tab-btn ${ytTab === "video" ? "active" : ""}`}
                onClick={() => setYtTab("video")}
              >
                Single Short / Video
              </button>
            </div>

            <div className="input-row">
              <input 
                type="text" 
                className="text-input" 
                placeholder={ytTab === "channel" ? "Enter YouTube Channel URL (e.g. @CreatorName)" : "Enter Video URL"}
                value={ytUrl}
                onChange={(e) => setYtUrl(e.target.value)}
              />
              <button className="btn" onClick={handleYtFetch} disabled={ytLoading}>
                <Search size={16} />
                {ytLoading ? "Loading..." : "Fetch"}
              </button>
            </div>

            {ytStatusText && (
              <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{ytStatusText}</p>
            )}

            {ytItems.length > 0 && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: "700" }}>Clips Ready</h3>
                  <button className="btn" onClick={handleYtDownload}>
                    <Download size={16} />
                    Download Selected
                  </button>
                </div>

                <div className="cards-grid">
                  {ytItems.map(item => (
                    <div 
                      key={item.id} 
                      className="media-card"
                      onClick={() => setYtSelected(prev => ({ ...prev, [item.id]: !prev[item.id] }))}
                    >
                      <input 
                        type="checkbox" 
                        checked={!!ytSelected[item.id]} 
                        onChange={() => {}} 
                        style={{ accentColor: "var(--accent-color)" }}
                      />
                      <img src={item.thumbnail} className="media-thumb" alt="thumbnail" />
                      <div className="media-details">
                        <span className="media-title">{item.title}</span>
                        <span className="media-meta">Views: {item.views.toLocaleString()}</span>
                        <span className="media-meta" style={{ color: "var(--accent-color)" }}>{item.uploader}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* INSTAGRAM DOWNLOADER TAB */}
        {activeTab === "instagram" && (
          <div className="glass-panel" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <h2 className="panel-header">Instagram Reels Downloader</h2>

            <div className="tabs-header">
              <button 
                className={`tab-btn ${instaTab === "reel" ? "active" : ""}`}
                onClick={() => setInstaTab("reel")}
              >
                Single Reel
              </button>
              <button 
                className={`tab-btn ${instaTab === "profile" ? "active" : ""}`}
                onClick={() => setInstaTab("profile")}
              >
                Profile Scraper
              </button>
            </div>

            <div className="input-row">
              <input 
                type="text" 
                className="text-input" 
                placeholder={instaTab === "reel" ? "Enter Instagram Reel Link" : "Enter Creator Username"}
                value={instaUrl}
                onChange={(e) => setInstaUrl(e.target.value)}
              />
              <button className="btn" onClick={handleInstaFetch} disabled={instaLoading}>
                <Search size={16} />
                {instaLoading ? "Loading..." : "Fetch"}
              </button>
            </div>

            {instaStatusText && (
              <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{instaStatusText}</p>
            )}

            {instaItems.length > 0 && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: "700" }}>Clips Ready</h3>
                  <button className="btn" onClick={handleInstaDownload}>
                    <Download size={16} />
                    Download Selected
                  </button>
                </div>

                <div className="cards-grid">
                  {instaItems.map(item => (
                    <div 
                      key={item.id} 
                      className="media-card"
                      onClick={() => setInstaSelected(prev => ({ ...prev, [item.id]: !prev[item.id] }))}
                    >
                      <input 
                        type="checkbox" 
                        checked={!!instaSelected[item.id]} 
                        onChange={() => {}} 
                        style={{ accentColor: "var(--accent-color)" }}
                      />
                      <img src={item.thumbnail} className="media-thumb" alt="thumbnail" />
                      <div className="media-details">
                        <span className="media-title">{item.title}</span>
                        <span className="media-meta">Likes/Views: {item.views.toLocaleString()}</span>
                        <span className="media-meta" style={{ color: "var(--accent-color)" }}>{item.uploader}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* SCHEDULER TAB */}
        {activeTab === "scheduler" && (
          <div className="scheduler-grid">
            
            {/* Scheduler Form Panel */}
            <div className="glass-panel" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "6px" }}>Schedule Upload</h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-dim)" }}>Video File Path</span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input 
                    type="text" 
                    className="text-input" 
                    placeholder="C:\path\to\video.mp4" 
                    value={selectedScheduleFile}
                    onChange={(e) => setSelectedScheduleFile(e.target.value)}
                    style={{ fontSize: "11px" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-dim)" }}>Caption / Description</span>
                <textarea 
                  className="text-input" 
                  rows={3} 
                  placeholder="Enter caption..."
                  value={schedulerCaption}
                  onChange={(e) => setSchedulerCaption(e.target.value)}
                  style={{ resize: "none", fontSize: "11px" }}
                />
              </div>

              {/* Timepicker dropdowns */}
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-dim)" }}>Post Date / Time</span>
                <div className="timepicker-row">
                  <input 
                    type="date" 
                    className="dropdown-select" 
                    value={schedulerDate}
                    onChange={(e) => setSchedulerDate(e.target.value)}
                    style={{ padding: "8px", fontSize: "11px" }}
                  />
                  <select 
                    className="dropdown-select"
                    value={schedulerHour}
                    onChange={(e) => setSchedulerHour(e.target.value)}
                  >
                    {Array.from({ length: 12 }, (_, i) => (i + 1).toString().padStart(2, '0')).map(h => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                  <select 
                    className="dropdown-select"
                    value={schedulerMinute}
                    onChange={(e) => setSchedulerMinute(e.target.value)}
                  >
                    {Array.from({ length: 12 }, (_, i) => (i * 5).toString().padStart(2, '0')).map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                  <select 
                    className="dropdown-select"
                    value={schedulerAmpm}
                    onChange={(e) => setSchedulerAmpm(e.target.value)}
                  >
                    <option value="AM">AM</option>
                    <option value="PM">PM</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-dim)" }}>Platform Target</span>
                <select 
                  className="dropdown-select"
                  value={schedulerPlatform}
                  onChange={(e) => setSchedulerPlatform(e.target.value as any)}
                  style={{ width: "100%" }}
                >
                  <option value="youtube">YouTube Shorts</option>
                  <option value="instagram">Instagram Reels</option>
                </select>
              </div>

              {/* Uniquifier Options */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "4px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-dim)", fontWeight: "700" }}>Uniquifier Filters</span>
                <div className="checkbox-group">
                  <label className="checkbox-item">
                    <input type="checkbox" checked={unqMirror} onChange={(e) => setUnqMirror(e.target.checked)} />
                    Mirror video horizontally
                  </label>
                  <label className="checkbox-item">
                    <input type="checkbox" checked={unqSpeed} onChange={(e) => setUnqSpeed(e.target.checked)} />
                    Speed adjustment (+1%)
                  </label>
                  <label className="checkbox-item">
                    <input type="checkbox" checked={unqContrast} onChange={(e) => setUnqContrast(e.target.checked)} />
                    Shift contrast and grading
                  </label>
                  <label className="checkbox-item">
                    <input type="checkbox" checked={unqScrub} onChange={(e) => setUnqScrub(e.target.checked)} />
                    Scrub metadata tags
                  </label>
                </div>
              </div>

              <button className="btn" onClick={handleAddSchedule} style={{ width: "100%", marginTop: "6px" }}>
                <Calendar size={16} />
                Schedule Upload
              </button>
            </div>

            {/* Scheduler Queue and Console Panel */}
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div className="glass-panel">
                <h3 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "12px" }}>Active Schedule</h3>

                <div className="tasks-scroll">
                  {schedulerList.length === 0 ? (
                    <p style={{ color: "var(--text-dim)", fontSize: "12px", padding: "40px 0", textAlign: "center" }}>
                      No uploads scheduled yet.
                    </p>
                  ) : (
                    schedulerList.map(task => (
                      <div key={task.id} className="task-card">
                        <div className="task-info">
                          <span className="task-title">{task.video_path.split('\\').pop() || "Video"}</span>
                          <span className="task-subtitle">
                            {task.platform === "youtube" ? "YouTube Shorts" : "Instagram Reels"} | {task.scheduled_time}
                          </span>
                        </div>
                        <div className="task-actions">
                          <span className={`status-badge status-${task.status}`}>
                            {task.status.toUpperCase()}
                          </span>
                          {(task.status === "scheduled" || task.status === "failed") && (
                            <button 
                              className="task-btn" 
                              title="Publish Now"
                              onClick={() => handlePublishNow(task.id)}
                            >
                              🚀
                            </button>
                          )}
                          <button 
                            className="task-btn" 
                            title="Cancel/Delete"
                            onClick={() => handleCancelTask(task.id)}
                          >
                            ❌
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Console Logs Terminal */}
              <div className="glass-panel" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Terminal size={16} color="var(--accent-color)" />
                  <h3 style={{ fontSize: "14px", fontWeight: "700" }}>Live Logs Terminal</h3>
                </div>
                <div className="console-panel" ref={logsConsoleRef}>
                  {schedulerLogs.map((log, index) => (
                    <div key={index} className="log-entry">
                      {log}
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  );
}
