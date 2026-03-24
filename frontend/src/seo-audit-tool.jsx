import { useState } from "react";

const API_BASE = "http://localhost:8000";

const TOOLS_CONFIG = [
  { id: "serp", name: "SERP Rank Tracker", icon: "📊", desc: "Find where your URL ranks on Google for specific keywords across multiple pages", color: "#00e5ff" },
  { id: "tech", name: "Technology Detection", icon: "🔧", desc: "Identify all technologies, frameworks, and libraries used on a website", color: "#76ff03" },
  { id: "uiux", name: "UI/UX Analysis", icon: "🎨", desc: "AI-powered page-by-page analysis of user interface and experience issues", color: "#ff6d00" },
  { id: "audit", name: "Full SEO Audit", icon: "🔍", desc: "Comprehensive SEO audit covering on-page, technical, and content factors", color: "#d500f9" },
  { id: "performance", name: "Performance & Lighthouse", icon: "⚡", desc: "Core Web Vitals, page speed, and performance metrics analysis", color: "#ffd600" },
  { id: "crawl", name: "Site Crawler", icon: "🕷️", desc: "Automated crawling to discover pages, broken links, and site structure", color: "#ff1744" },
  { id: "content", name: "Content Analysis", icon: "📝", desc: "Analyze content quality, readability, keyword density and semantic relevance", color: "#00e676" },
  { id: "report", name: "Report Generator", icon: "📋", desc: "Generate comprehensive audit reports with actionable insights and roadmap", color: "#448aff" },
];

async function callBackend(endpoint, body) {
  const res = await fetch(`${API_BASE}/api/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${errText}`);
  }
  const data = await res.json();
  return data.result;
}

function Spinner({ size = 20, color = "#00e5ff" }) {
  return <div style={{ width: size, height: size, border: `2px solid ${color}33`, borderTop: `2px solid ${color}`, borderRadius: "50%", animation: "spin 0.8s linear infinite", display: "inline-block" }} />;
}

function ResultBlock({ title, content, color = "#00e5ff" }) {
  return (
    <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 20, marginBottom: 16, borderLeft: `3px solid ${color}` }}>
      {title && <h4 style={{ margin: "0 0 12px", color, fontSize: 14, fontWeight: 600, letterSpacing: 0.5 }}>{title}</h4>}
      <div style={{ color: "#c8d6e5", fontSize: 13, lineHeight: 1.7, whiteSpace: "pre-wrap", fontFamily: "'IBM Plex Sans', sans-serif" }}>{content}</div>
    </div>
  );
}

function SERPTracker() {
  const [url, setUrl] = useState("");
  const [keywords, setKeywords] = useState([""]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");

  const addKeyword = () => setKeywords([...keywords, ""]);
  const removeKeyword = (i) => setKeywords(keywords.filter((_, idx) => idx !== i));
  const updateKeyword = (i, v) => { const nk = [...keywords]; nk[i] = v; setKeywords(nk); };

  const runSearch = async () => {
    const validKw = keywords.filter((k) => k.trim());
    if (!url.trim() || validKw.length === 0) return;
    setLoading(true); setResults(null);
    setProgress("Analyzing keyword rankings...");
    try {
      const resp = await callBackend("serp", { url: url.trim(), keywords: validKw });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false); setProgress("");
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Target URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Keywords to Track</label>
        {keywords.map((kw, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
            <input style={{ ...styles.input, marginBottom: 0, flex: 1 }} placeholder={`Keyword ${i + 1}`} value={kw} onChange={(e) => updateKeyword(i, e.target.value)} onKeyDown={(e) => e.key === "Enter" && addKeyword()} />
            {keywords.length > 1 && <button onClick={() => removeKeyword(i)} style={styles.removeBtn}>✕</button>}
          </div>
        ))}
        <button onClick={addKeyword} style={styles.addBtn}>+ Add Keyword</button>
      </div>
      <button onClick={runSearch} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #00e5ff, #0091ea)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> {progress}</span> : "🔎 Track Rankings"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="SERP Ranking Results" content={results} color="#00e5ff" /></div>}
    </div>
  );
}

function TechDetector() {
  const [url, setUrl] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const detect = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    try {
      const resp = await callBackend("tech", { url: url.trim() });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <button onClick={detect} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #76ff03, #00c853)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> Scanning technologies...</span> : "🔧 Detect Technologies"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="Technology Stack Detected" content={results} color="#76ff03" /></div>}
    </div>
  );
}

function UIUXAnalysis() {
  const [url, setUrl] = useState("");
  const [pages, setPages] = useState([""]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const addPage = () => setPages([...pages, ""]);
  const updatePage = (i, v) => { const np = [...pages]; np[i] = v; setPages(np); };

  const analyze = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    try {
      const pageList = pages.filter((p) => p.trim());
      const resp = await callBackend("uiux", { url: url.trim(), pages: pageList });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Specific Pages (optional)</label>
        {pages.map((p, i) => (
          <input key={i} style={{ ...styles.input, marginBottom: 8 }} placeholder="/about, /pricing, /contact..." value={p} onChange={(e) => updatePage(i, e.target.value)} />
        ))}
        <button onClick={addPage} style={styles.addBtn}>+ Add Page</button>
      </div>
      <button onClick={analyze} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #ff6d00, #ff9100)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> Analyzing UI/UX...</span> : "🎨 Analyze UI/UX"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="UI/UX Audit Results" content={results} color="#ff6d00" /></div>}
    </div>
  );
}

function FullAudit() {
  const [url, setUrl] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("");

  const runAudit = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    const stages = ["Crawling site structure...", "Checking meta tags & headings...", "Analyzing content quality...", "Evaluating backlink profile...", "Checking technical SEO...", "Generating recommendations..."];
    let si = 0;
    const iv = setInterval(() => { si = (si + 1) % stages.length; setStage(stages[si]); }, 3000);
    try {
      setStage(stages[0]);
      const resp = await callBackend("audit", { url: url.trim() });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    clearInterval(iv); setLoading(false); setStage("");
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL for Full Audit</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <button onClick={runAudit} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #d500f9, #aa00ff)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> {stage}</span> : "🔍 Run Full SEO Audit"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="Complete SEO Audit Report" content={results} color="#d500f9" /></div>}
    </div>
  );
}

function PerformanceCheck() {
  const [url, setUrl] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const check = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    try {
      const resp = await callBackend("performance", { url: url.trim() });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <button onClick={check} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #ffd600, #ffab00)", color: "#0a1628" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8, color: "#fff" }}><Spinner size={16} color="#fff" /> Analyzing performance...</span> : "⚡ Check Performance"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="Performance Analysis" content={results} color="#ffd600" /></div>}
    </div>
  );
}

function SiteCrawler() {
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState("3");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const crawl = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    try {
      const resp = await callBackend("crawl", { url: url.trim(), depth: parseInt(depth) });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Crawl Depth</label>
        <select style={styles.input} value={depth} onChange={(e) => setDepth(e.target.value)}>
          <option value="1">1 Level (Homepage only)</option>
          <option value="2">2 Levels</option>
          <option value="3">3 Levels (Recommended)</option>
          <option value="5">5 Levels (Deep)</option>
        </select>
      </div>
      <button onClick={crawl} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #ff1744, #d50000)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> Crawling site...</span> : "🕷️ Start Crawling"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="Crawl Results" content={results} color="#ff1744" /></div>}
    </div>
  );
}

function ContentAnalysis() {
  const [url, setUrl] = useState("");
  const [targetKw, setTargetKw] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    try {
      const resp = await callBackend("content", { url: url.trim(), target_keywords: targetKw.trim() });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Target Keywords (optional, comma-separated)</label>
        <input style={styles.input} placeholder="seo tools, website audit, keyword research..." value={targetKw} onChange={(e) => setTargetKw(e.target.value)} />
      </div>
      <button onClick={analyze} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #00e676, #00c853)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> Analyzing content...</span> : "📝 Analyze Content"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="Content Analysis Report" content={results} color="#00e676" /></div>}
    </div>
  );
}

function ReportGenerator() {
  const [url, setUrl] = useState("");
  const [sections, setSections] = useState({ technical: true, onpage: true, content: true, performance: true, uiux: true, competitive: true });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggle = (key) => setSections({ ...sections, [key]: !sections[key] });

  const generate = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null);
    try {
      const resp = await callBackend("report", { url: url.trim(), sections });
      setResults(resp);
    } catch (e) { setResults("Error: " + e.message); }
    setLoading(false);
  };

  const checkboxes = [["technical", "Technical SEO"], ["onpage", "On-Page SEO"], ["content", "Content Analysis"], ["performance", "Performance"], ["uiux", "UX Analysis"], ["competitive", "Competitive Analysis"]];

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Report Sections</label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {checkboxes.map(([key, label]) => (
            <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: sections[key] ? "#0d2847" : "#0d1b2a", border: `1px solid ${sections[key] ? "#448aff" : "#1a2d42"}`, borderRadius: 8, cursor: "pointer", fontSize: 13, color: sections[key] ? "#c8d6e5" : "#5a7a95", transition: "all 0.2s" }}>
              <input type="checkbox" checked={sections[key]} onChange={() => toggle(key)} style={{ accentColor: "#448aff" }} />{label}
            </label>
          ))}
        </div>
      </div>
      <button onClick={generate} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #448aff, #2962ff)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> Generating report...</span> : "📋 Generate Report"}
      </button>
      {results && <div style={{ marginTop: 24 }}><ResultBlock title="SEO Audit Report" content={results} color="#448aff" /></div>}
    </div>
  );
}

function ToolView({ toolId }) {
  const map = { serp: SERPTracker, tech: TechDetector, uiux: UIUXAnalysis, audit: FullAudit, performance: PerformanceCheck, crawl: SiteCrawler, content: ContentAnalysis, report: ReportGenerator };
  const Comp = map[toolId];
  return Comp ? <Comp /> : null;
}

function Dashboard({ onSelectTool }) {
  return (
    <div style={{ animation: "fadeUp 0.4s ease" }}>
      <div style={{ position: "relative", marginBottom: 36, padding: "32px 0" }}>
        <div style={{ position: "absolute", top: -40, left: -40, width: 200, height: 200, background: "radial-gradient(circle, #00e5ff10 0%, transparent 70%)", borderRadius: "50%", pointerEvents: "none" }} />
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: 32, fontWeight: 800, color: "#e8f0fe", margin: 0, position: "relative" }}>
          SEO Audit <span style={{ background: "linear-gradient(135deg, #00e5ff, #d500f9)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Command Center</span>
        </h1>
        <p style={{ fontFamily: "'IBM Plex Sans', sans-serif", color: "#5a7a95", fontSize: 15, marginTop: 8, maxWidth: 550, lineHeight: 1.6, position: "relative" }}>
          AI-powered website analysis toolkit. Select a tool below to begin auditing your site's SEO, performance, content, and user experience.
        </p>
      </div>

      <div style={{ marginBottom: 32 }}>
        <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: 14, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 2, marginBottom: 20 }}>Audit Roadmap</h3>
        <div style={{ display: "flex", alignItems: "flex-start", overflowX: "auto", padding: "12px 0 32px" }}>
          {TOOLS_CONFIG.map((tool, i) => (
            <div key={tool.id} style={{ display: "flex", alignItems: "center", position: "relative", animation: "fadeUp 0.5s ease both", animationDelay: `${i * 80}ms` }}>
              <div style={{ width: 14, height: 14, borderRadius: "50%", flexShrink: 0, zIndex: 1, background: tool.color, boxShadow: `0 0 12px ${tool.color}60` }} />
              {i < TOOLS_CONFIG.length - 1 && <div style={{ width: 48, height: 2, background: "linear-gradient(90deg, #1a2d42, #2a4a6b, #1a2d42)", flexShrink: 0 }} />}
              <div style={{ position: "absolute", top: 22, left: -20, display: "flex", flexDirection: "column", gap: 2, width: 80, textAlign: "center" }}>
                <span style={{ fontSize: 10, color: tool.color, fontWeight: 600 }}>STEP {i + 1}</span>
                <span style={{ fontSize: 11, color: "#c8d6e5" }}>{tool.name}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16, marginBottom: 36 }}>
        {TOOLS_CONFIG.map((tool, i) => (
          <button key={tool.id} onClick={() => onSelectTool(tool.id)}
            style={{ background: "#0d1b2a", border: `1px solid ${tool.color}15`, borderRadius: 14, padding: 20, cursor: "pointer", textAlign: "left", transition: "all 0.3s ease", animation: "fadeUp 0.5s ease both", animationDelay: `${i * 60}ms`, fontFamily: "'IBM Plex Sans', sans-serif" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = `${tool.color}50`; e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = `0 8px 32px ${tool.color}15`; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = `${tool.color}15`; e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>{tool.icon}</div>
            <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: 14, fontWeight: 600, color: "#e8f0fe", margin: "0 0 6px" }}>{tool.name}</h3>
            <p style={{ fontSize: 12, color: "#5a7a95", margin: 0, lineHeight: 1.5 }}>{tool.desc}</p>
            <div style={{ marginTop: 14, fontSize: 11, color: tool.color, fontWeight: 600 }}>Launch Tool →</div>
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, padding: "24px 0", borderTop: "1px solid #1a2d42" }}>
        {[
          { icon: "🤖", title: "AI-Powered Analysis", desc: "Uses Azure OpenAI to provide intelligent insights, not just raw data" },
          { icon: "🔧", title: "Programmatic Scanning", desc: "Real HTML scraping, PageSpeed Insights, and BFS crawling for accurate data" },
          { icon: "📊", title: "Comprehensive Reports", desc: "Detailed, actionable reports covering every aspect of your site" },
        ].map((f) => (
          <div key={f.title} style={{ textAlign: "center", padding: 16 }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>{f.icon}</div>
            <h4 style={{ fontFamily: "'Sora', sans-serif", fontSize: 13, fontWeight: 600, color: "#e8f0fe", margin: "0 0 4px" }}>{f.title}</h4>
            <p style={{ fontSize: 12, color: "#5a7a95", margin: 0, lineHeight: 1.5 }}>{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SEOAuditTool() {
  const [activeTool, setActiveTool] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const currentTool = TOOLS_CONFIG.find((t) => t.id === activeTool);

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0a1628", fontFamily: "'IBM Plex Sans', sans-serif", color: "#c8d6e5" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&family=Sora:wght@300;400;500;600;700;800&display=swap');
        @keyframes spin { to { transform: rotate(360deg) } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(16px) } to { opacity:1; transform:translateY(0) } }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width:6px }
        ::-webkit-scrollbar-track { background:#0a1628 }
        ::-webkit-scrollbar-thumb { background:#1a2d42; border-radius:3px }
      `}</style>

      <div style={{ background: "#0d1b2a", borderRight: "1px solid #1a2d42", display: "flex", flexDirection: "column", transition: "all 0.3s ease", flexShrink: 0, position: "sticky", top: 0, height: "100vh", overflowY: "auto", width: sidebarOpen ? 260 : 56, minWidth: sidebarOpen ? 260 : 56 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 12px", borderBottom: "1px solid #1a2d42" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, overflow: "hidden" }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #00e5ff, #d500f9)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 }}>🔍</div>
            {sidebarOpen && <span style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: 15, color: "#e8f0fe", whiteSpace: "nowrap" }}>SEO Audit Suite</span>}
          </div>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} style={{ background: "none", border: "none", color: "#5a7a95", cursor: "pointer", fontSize: 18, padding: 4, flexShrink: 0 }}>
            {sidebarOpen ? "◀" : "▶"}
          </button>
        </div>

        <div style={{ padding: 8, flex: 1, overflowY: "auto" }}>
          <button onClick={() => setActiveTool(null)} style={{ ...styles.navItem, background: activeTool === null ? "#0d2847" : "transparent", borderColor: activeTool === null ? "#00e5ff33" : "transparent" }}>
            <span style={{ fontSize: 18, flexShrink: 0 }}>🏠</span>
            {sidebarOpen && <span>Dashboard</span>}
          </button>
          {sidebarOpen && <div style={{ fontSize: 10, color: "#3a5a7a", textTransform: "uppercase", letterSpacing: 1.5, padding: "16px 12px 8px", fontWeight: 600 }}>Tools</div>}
          {TOOLS_CONFIG.map((tool) => (
            <button key={tool.id} onClick={() => setActiveTool(tool.id)} style={{ ...styles.navItem, background: activeTool === tool.id ? "#0d2847" : "transparent", borderColor: activeTool === tool.id ? `${tool.color}33` : "transparent" }}>
              <span style={{ fontSize: 18, flexShrink: 0 }}>{tool.icon}</span>
              {sidebarOpen && <span style={{ color: activeTool === tool.id ? tool.color : "#8899aa" }}>{tool.name}</span>}
            </button>
          ))}
        </div>

        {sidebarOpen && <div style={{ padding: "12px 16px", borderTop: "1px solid #1a2d42", textAlign: "center" }}><span style={{ fontSize: 10, color: "#3a5a7a" }}>Powered by Azure OpenAI</span></div>}
      </div>

      <div style={{ flex: 1, padding: "24px 32px", overflowY: "auto", maxWidth: 960 }}>
        {activeTool === null ? (
          <Dashboard onSelectTool={setActiveTool} />
        ) : (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ marginBottom: 24, paddingBottom: 20, borderBottom: "1px solid #1a2d42" }}>
              <button onClick={() => setActiveTool(null)} style={{ background: "none", border: "none", color: "#5a7a95", cursor: "pointer", fontSize: 13, padding: "4px 0", marginBottom: 12, fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 500 }}>← Back</button>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 28 }}>{currentTool?.icon}</span>
                <h2 style={{ margin: 0, fontFamily: "'Sora', sans-serif", fontSize: 22, fontWeight: 700, color: "#e8f0fe" }}>{currentTool?.name}</h2>
              </div>
              <p style={{ margin: "6px 0 0", color: "#5a7a95", fontSize: 13 }}>{currentTool?.desc}</p>
            </div>
            <div style={{ maxWidth: 700 }}>
              <ToolView toolId={activeTool} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  label: { display: "block", fontSize: 12, fontWeight: 600, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, fontFamily: "'Sora', sans-serif" },
  input: { width: "100%", padding: "12px 16px", background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 10, color: "#e8f0fe", fontSize: 14, fontFamily: "'IBM Plex Sans', sans-serif", outline: "none", marginBottom: 4 },
  primaryBtn: { width: "100%", padding: "14px 24px", border: "none", borderRadius: 10, color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "'Sora', sans-serif", letterSpacing: 0.3, display: "flex", alignItems: "center", justifyContent: "center" },
  addBtn: { background: "none", border: "1px dashed #1a2d42", borderRadius: 8, color: "#5a7a95", padding: "8px 16px", fontSize: 12, cursor: "pointer", fontFamily: "'IBM Plex Sans', sans-serif" },
  removeBtn: { background: "#1a0a0a", border: "1px solid #3a1a1a", borderRadius: 8, color: "#ff4444", width: 32, height: 40, cursor: "pointer", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center" },
  navItem: { display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "10px 12px", border: "1px solid transparent", borderRadius: 8, background: "transparent", color: "#8899aa", fontSize: 13, fontWeight: 500, cursor: "pointer", textAlign: "left", fontFamily: "'IBM Plex Sans', sans-serif", marginBottom: 2 },
};
