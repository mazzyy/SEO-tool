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
  const [maxPages, setMaxPages] = useState(10);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [expandedKeyword, setExpandedKeyword] = useState(null);
  const [expandedCompetitor, setExpandedCompetitor] = useState(null);

  const addKeyword = () => setKeywords([...keywords, ""]);
  const removeKeyword = (i) => setKeywords(keywords.filter((_, idx) => idx !== i));
  const updateKeyword = (i, v) => { const nk = [...keywords]; nk[i] = v; setKeywords(nk); };

  const runSearch = async () => {
    const validKw = keywords.filter((k) => k.trim());
    if (!url.trim() || validKw.length === 0) return;
    setLoading(true); setResults(null);
    setExpandedKeyword(null); setExpandedCompetitor(null);
    setProgress("Searching Google results...");
    try {
      const resp = await callBackend("serp", { url: url.trim(), keywords: validKw, max_pages: maxPages });
      setResults(typeof resp === "string" ? { keywords: [], visibility_score: 0, quick_wins: [], summary: resp, competitor_analysis: [] } : resp);
    } catch (e) { setResults({ keywords: [], visibility_score: 0, quick_wins: [], summary: "Error: " + e.message, competitor_analysis: [] }); }
    setLoading(false); setProgress("");
  };

  const getRankColor = (rank, found) => {
    if (!found || rank < 0) return "#5a7a95";
    if (rank <= 3) return "#00e676";
    if (rank <= 10) return "#76ff03";
    if (rank <= 20) return "#ffd600";
    if (rank <= 30) return "#ff9100";
    return "#ff1744";
  };

  const getRankLabel = (rank, found) => {
    if (!found || rank < 0) return "Not Found";
    return `#${rank}`;
  };

  const getBarWidth = (rank, found) => {
    if (!found || rank < 0) return 0;
    const max = maxPages * 10;
    return Math.max(5, 100 - (rank / max) * 100);
  };

  // SVG Circular Gauge
  const VisibilityGauge = ({ score }) => {
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    const gaugeColor = score >= 70 ? "#00e676" : score >= 40 ? "#ffd600" : "#ff1744";
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r={radius} fill="none" stroke="#1a2d42" strokeWidth="10" />
          <circle cx="70" cy="70" r={radius} fill="none" stroke={gaugeColor} strokeWidth="10"
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" transform="rotate(-90 70 70)"
            style={{ transition: "stroke-dashoffset 1s ease, stroke 0.5s ease" }} />
          <text x="70" y="64" textAnchor="middle" fill="#e8f0fe" fontSize="28" fontWeight="700" fontFamily="'Sora', sans-serif">{score}</text>
          <text x="70" y="84" textAnchor="middle" fill="#5a7a95" fontSize="11" fontFamily="'IBM Plex Sans', sans-serif">/ 100</text>
        </svg>
        <span style={{ fontSize: 11, color: "#5a7a95", marginTop: 4, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}>Visibility Score</span>
      </div>
    );
  };

  // Competitor Deep Analysis Card
  const CompetitorAnalysisCard = ({ analysis }) => {
    if (!analysis || !analysis.analyzed) return null;
    const scoreColor = analysis.word_count >= 2000 ? "#00e676" : analysis.word_count >= 800 ? "#ffd600" : "#ff9100";
    return (
      <div style={{ background: "#0a1628", border: "1px solid #1a2d42", borderRadius: 10, padding: 16, marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#e8f0fe" }}>{analysis.domain}</span>
            <a href={analysis.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "#00e5ff", marginLeft: 8, textDecoration: "none" }}>Visit</a>
          </div>
          <span style={{ fontSize: 11, padding: "3px 10px", borderRadius: 6, background: `${scoreColor}18`, color: scoreColor, fontWeight: 600 }}>
            {analysis.word_count.toLocaleString()} words
          </span>
        </div>

        {/* Meta Info */}
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 600, marginBottom: 4 }}>Meta Title ({analysis.page_title_length} chars)</div>
          <div style={{ fontSize: 12, color: "#c8d6e5", background: "#0d1b2a", padding: 8, borderRadius: 6, lineHeight: 1.4 }}>{analysis.meta_title || "Not set"}</div>
        </div>
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 600, marginBottom: 4 }}>Meta Description ({analysis.meta_desc_length} chars)</div>
          <div style={{ fontSize: 12, color: "#c8d6e5", background: "#0d1b2a", padding: 8, borderRadius: 6, lineHeight: 1.4 }}>{analysis.meta_description || "Not set"}</div>
        </div>

        {/* Content Metrics Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 10 }}>
          {[
            { label: "Content Type", value: analysis.content_type, color: "#00e5ff" },
            { label: "Internal Links", value: analysis.internal_links, color: "#76ff03" },
            { label: "External Links", value: analysis.external_links, color: "#ffd600" },
            { label: "Images", value: `${analysis.images} (${analysis.images_without_alt} no alt)`, color: analysis.images_without_alt > 0 ? "#ff9100" : "#00e676" },
            { label: "Schema", value: analysis.has_schema_markup ? analysis.schema_types.join(", ") || "Yes" : "None", color: analysis.has_schema_markup ? "#00e676" : "#ff9100" },
            { label: "OG / Twitter", value: `${analysis.has_og_tags ? "OG" : "—"} / ${analysis.has_twitter_cards ? "TC" : "—"}`, color: analysis.has_og_tags ? "#00e676" : "#ff9100" },
          ].map((metric) => (
            <div key={metric.label} style={{ background: "#0d1b2a", borderRadius: 6, padding: 8, textAlign: "center" }}>
              <div style={{ fontSize: 9, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 3 }}>{metric.label}</div>
              <div style={{ fontSize: 11, color: metric.color, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{metric.value}</div>
            </div>
          ))}
        </div>

        {/* Headings Structure */}
        {(analysis.headings.h1.length > 0 || analysis.headings.h2.length > 0) && (
          <div>
            <div style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 600, marginBottom: 4 }}>Heading Structure</div>
            <div style={{ background: "#0d1b2a", borderRadius: 6, padding: 8, maxHeight: 140, overflowY: "auto" }}>
              {analysis.headings.h1.map((h, j) => (
                <div key={`h1-${j}`} style={{ fontSize: 12, color: "#00e5ff", fontWeight: 600, marginBottom: 3 }}>H1: {h}</div>
              ))}
              {analysis.headings.h2.map((h, j) => (
                <div key={`h2-${j}`} style={{ fontSize: 11, color: "#c8d6e5", marginBottom: 2, paddingLeft: 12 }}>H2: {h}</div>
              ))}
              {analysis.headings.h3.map((h, j) => (
                <div key={`h3-${j}`} style={{ fontSize: 10, color: "#8899aa", marginBottom: 2, paddingLeft: 24 }}>H3: {h}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      {/* Inputs */}
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Target URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Keywords to Track</label>
        {keywords.map((kw, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
            <input style={{ ...styles.input, marginBottom: 0, flex: 1 }} placeholder={`Keyword ${i + 1}`} value={kw} onChange={(e) => updateKeyword(i, e.target.value)} onKeyDown={(e) => e.key === "Enter" && addKeyword()} />
            {keywords.length > 1 && <button onClick={() => removeKeyword(i)} style={styles.removeBtn}>x</button>}
          </div>
        ))}
        <button onClick={addKeyword} style={styles.addBtn}>+ Add Keyword</button>
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Google Pages to Search</label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {[1, 3, 5, 10, 15, 20].map((n) => (
            <button key={n} onClick={() => setMaxPages(n)}
              style={{
                padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer",
                fontFamily: "'IBM Plex Sans', sans-serif", transition: "all 0.2s",
                background: maxPages === n ? "#0d2847" : "#0d1b2a",
                border: `1px solid ${maxPages === n ? "#00e5ff" : "#1a2d42"}`,
                color: maxPages === n ? "#00e5ff" : "#5a7a95",
              }}>
              {n} {n === 1 ? "page" : "pages"} ({n * 10} results)
            </button>
          ))}
        </div>
      </div>

      <button onClick={runSearch} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #00e5ff, #0091ea)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> {progress}</span> : "Track Rankings"}
      </button>

      {/* Results Dashboard */}
      {results && (
        <div style={{ marginTop: 28, animation: "fadeUp 0.5s ease" }}>

          {/* Stats Bar */}
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            {[
              { label: "Pages Searched", value: results.pages_searched || maxPages, color: "#00e5ff" },
              { label: "Results Scanned", value: results.total_results_scanned || 0, color: "#76ff03" },
              { label: "Data Source", value: results.data_source || "—", color: "#ffd600" },
              { label: "Keywords Ranking", value: `${(results.keywords || []).filter(k => k.found).length}/${(results.keywords || []).length}`, color: "#d500f9" },
            ].map((stat) => (
              <div key={stat.label} style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 8, padding: "10px 16px", flex: "1 1 120px", textAlign: "center" }}>
                <div style={{ fontSize: 9, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 4 }}>{stat.label}</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: stat.color, fontFamily: "'Sora', sans-serif" }}>{stat.value}</div>
              </div>
            ))}
          </div>

          {/* Top Row: Gauge + Summary */}
          <div style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 24, marginBottom: 24, alignItems: "start" }}>
            <VisibilityGauge score={results.visibility_score || 0} />
            <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 20 }}>
              <h4 style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 600, color: "#00e5ff", letterSpacing: 0.5, textTransform: "uppercase" }}>AI Analysis Summary</h4>
              <p style={{ color: "#c8d6e5", fontSize: 13, lineHeight: 1.7, margin: 0, whiteSpace: "pre-wrap" }}>{results.summary || "No summary available."}</p>
            </div>
          </div>

          {/* Ranking Bar Chart */}
          {results.keywords && results.keywords.length > 0 && (
            <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 20, marginBottom: 24 }}>
              <h4 style={{ margin: "0 0 16px", fontSize: 13, fontWeight: 600, color: "#00e5ff", letterSpacing: 0.5, textTransform: "uppercase" }}>Keyword Rank Overview</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {results.keywords.map((kw, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "140px 50px 1fr", gap: 12, alignItems: "center" }}>
                    <span style={{ fontSize: 12, color: "#c8d6e5", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{kw.keyword}</span>
                    <span style={{
                      fontSize: 13, fontWeight: 700, textAlign: "center", padding: "3px 8px", borderRadius: 6,
                      background: `${getRankColor(kw.rank, kw.found)}18`,
                      color: getRankColor(kw.rank, kw.found),
                    }}>{getRankLabel(kw.rank, kw.found)}</span>
                    <div style={{ position: "relative", height: 22, background: "#0a1628", borderRadius: 6, overflow: "hidden" }}>
                      <div style={{
                        height: "100%", borderRadius: 6,
                        background: `linear-gradient(90deg, ${getRankColor(kw.rank, kw.found)}, ${getRankColor(kw.rank, kw.found)}88)`,
                        width: `${getBarWidth(kw.rank, kw.found)}%`,
                        transition: "width 1s ease",
                        boxShadow: `0 0 8px ${getRankColor(kw.rank, kw.found)}40`,
                      }} />
                      {kw.found && kw.rank > 0 && (
                        <span style={{ position: "absolute", right: 8, top: 3, fontSize: 10, color: "#5a7a95", fontWeight: 500 }}>Page {kw.page}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {/* Legend */}
              <div style={{ display: "flex", gap: 16, marginTop: 14, flexWrap: "wrap" }}>
                {[
                  { color: "#00e676", label: "Top 3" },
                  { color: "#76ff03", label: "4-10" },
                  { color: "#ffd600", label: "11-20" },
                  { color: "#ff9100", label: "21-30" },
                  { color: "#ff1744", label: "30+" },
                  { color: "#5a7a95", label: "Not Found" },
                ].map((l) => (
                  <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 3, background: l.color }} />
                    <span style={{ fontSize: 10, color: "#5a7a95" }}>{l.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full SERP Results Table per Keyword */}
          {results.keywords && results.keywords.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ margin: "0 0 14px", fontSize: 13, fontWeight: 600, color: "#00e5ff", letterSpacing: 0.5, textTransform: "uppercase" }}>
                Full SERP Results ({results.total_results_scanned || 0} results scanned)
              </h4>
              {results.keywords.map((kw, kwIdx) => (
                <div key={kwIdx} style={{ marginBottom: 16 }}>
                  <button
                    onClick={() => setExpandedKeyword(expandedKeyword === kwIdx ? null : kwIdx)}
                    style={{
                      width: "100%", textAlign: "left", padding: "14px 18px",
                      background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: expandedKeyword === kwIdx ? "12px 12px 0 0" : 12,
                      cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center",
                      borderLeft: `3px solid ${getRankColor(kw.rank, kw.found)}`,
                    }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "#e8f0fe" }}>{kw.keyword}</span>
                      <span style={{
                        fontSize: 12, fontWeight: 700, padding: "2px 10px", borderRadius: 6,
                        background: `${getRankColor(kw.rank, kw.found)}18`,
                        color: getRankColor(kw.rank, kw.found),
                      }}>{getRankLabel(kw.rank, kw.found)}</span>
                      <span style={{ fontSize: 11, color: "#5a7a95" }}>
                        {kw.total_scanned} results scanned  {kw.all_competitors ? `| ${kw.all_competitors.length} competitors` : ""}
                      </span>
                    </div>
                    <span style={{ color: "#5a7a95", fontSize: 16, transform: expandedKeyword === kwIdx ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                      ▼
                    </span>
                  </button>

                  {expandedKeyword === kwIdx && kw.all_competitors && (
                    <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderTop: "none", borderRadius: "0 0 12px 12px", padding: 0, maxHeight: 500, overflowY: "auto" }}>
                      {/* Table Header */}
                      <div style={{ display: "grid", gridTemplateColumns: "50px 1fr 200px 60px", gap: 0, padding: "10px 16px", background: "#0a1628", borderBottom: "1px solid #1a2d42", position: "sticky", top: 0, zIndex: 1 }}>
                        <span style={{ fontSize: 10, color: "#5a7a95", fontWeight: 700, textTransform: "uppercase" }}>Rank</span>
                        <span style={{ fontSize: 10, color: "#5a7a95", fontWeight: 700, textTransform: "uppercase" }}>URL & Title</span>
                        <span style={{ fontSize: 10, color: "#5a7a95", fontWeight: 700, textTransform: "uppercase" }}>Snippet</span>
                        <span style={{ fontSize: 10, color: "#5a7a95", fontWeight: 700, textTransform: "uppercase" }}>Page</span>
                      </div>
                      {/* Rows */}
                      {kw.all_competitors.map((comp, j) => (
                        <div key={j} style={{
                          display: "grid", gridTemplateColumns: "50px 1fr 200px 60px", gap: 0,
                          padding: "10px 16px", borderBottom: "1px solid #1a2d4230",
                          background: j % 2 === 0 ? "#0d1b2a" : "#0c1926",
                          transition: "background 0.15s",
                        }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#0d2847"}
                          onMouseLeave={(e) => e.currentTarget.style.background = j % 2 === 0 ? "#0d1b2a" : "#0c1926"}>
                          <span style={{ fontSize: 13, fontWeight: 700, color: comp.position <= 3 ? "#00e676" : comp.position <= 10 ? "#76ff03" : comp.position <= 20 ? "#ffd600" : "#8899aa" }}>
                            #{comp.position}
                          </span>
                          <div style={{ overflow: "hidden" }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: "#e8f0fe", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {comp.title || "Untitled"}
                            </div>
                            <a href={comp.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 10, color: "#00e5ff", textDecoration: "none", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }}>
                              {comp.domain}
                            </a>
                          </div>
                          <div style={{ fontSize: 10, color: "#8899aa", lineHeight: 1.4, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                            {comp.snippet || "—"}
                          </div>
                          <span style={{ fontSize: 11, color: "#5a7a95", textAlign: "center" }}>P{comp.page}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Deep Competitor Analysis */}
          {results.competitor_analysis && results.competitor_analysis.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 600, color: "#d500f9", letterSpacing: 0.5, textTransform: "uppercase" }}>
                Deep Competitor Page Analysis
              </h4>
              <p style={{ fontSize: 11, color: "#5a7a95", margin: "0 0 14px" }}>In-depth analysis of top {results.competitor_analysis.length} competitor pages — content structure, meta tags, schema markup, and more</p>
              {results.competitor_analysis.map((ca, i) => (
                <CompetitorAnalysisCard key={i} analysis={ca} />
              ))}
            </div>
          )}

          {/* Keyword Detail Cards */}
          {results.keywords && results.keywords.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ margin: "0 0 14px", fontSize: 13, fontWeight: 600, color: "#00e5ff", letterSpacing: 0.5, textTransform: "uppercase" }}>Keyword Details</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14 }}>
                {results.keywords.map((kw, i) => (
                  <div key={i} style={{
                    background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 16,
                    borderLeft: `3px solid ${getRankColor(kw.rank, kw.found)}`,
                    transition: "transform 0.2s, box-shadow 0.2s",
                  }}
                    onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = `0 4px 16px ${getRankColor(kw.rank, kw.found)}15`; }}
                    onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}>
                    {/* Card Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "#e8f0fe" }}>{kw.keyword}</span>
                      <span style={{
                        fontSize: 16, fontWeight: 800, padding: "4px 12px", borderRadius: 8,
                        background: `${getRankColor(kw.rank, kw.found)}20`,
                        color: getRankColor(kw.rank, kw.found),
                        fontFamily: "'Sora', sans-serif",
                      }}>{getRankLabel(kw.rank, kw.found)}</span>
                    </div>
                    {/* Snippet */}
                    {kw.snippet && (
                      <div style={{ background: "#0a1628", borderRadius: 8, padding: 10, marginBottom: 10 }}>
                        <span style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 600 }}>Snippet</span>
                        <p style={{ color: "#c8d6e5", fontSize: 12, lineHeight: 1.5, margin: "4px 0 0" }}>{kw.snippet}</p>
                      </div>
                    )}
                    {/* Page Info */}
                    {kw.found && (
                      <div style={{ fontSize: 11, color: "#5a7a95", marginBottom: 10 }}>
                        Found on <span style={{ color: "#00e5ff", fontWeight: 600 }}>Google Page {kw.page}</span> (Position {kw.rank}) out of {kw.total_scanned} results scanned
                      </div>
                    )}
                    {!kw.found && kw.total_scanned > 0 && (
                      <div style={{ fontSize: 11, color: "#ff9100", marginBottom: 10 }}>
                        Not found in top {kw.total_scanned} results ({Math.floor(kw.total_scanned / 10)} pages)
                      </div>
                    )}
                    {/* Top 10 Competitors */}
                    {kw.competing_urls && kw.competing_urls.length > 0 && (
                      <div>
                        <span style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 600 }}>Top 10 Competitors</span>
                        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 3 }}>
                          {kw.competing_urls.map((cu, j) => (
                            <a key={j} href={cu} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "#8899aa", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", textDecoration: "none" }}>
                              {j + 1}. {cu}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Wins */}
          {results.quick_wins && results.quick_wins.length > 0 && (
            <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 20 }}>
              <h4 style={{ margin: "0 0 14px", fontSize: 13, fontWeight: 600, color: "#76ff03", letterSpacing: 0.5, textTransform: "uppercase" }}>Quick Wins & Recommendations</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {results.quick_wins.map((win, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 14px", background: "#0a1628", borderRadius: 8, borderLeft: "2px solid #76ff03" }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#76ff03", flexShrink: 0, fontFamily: "'Sora', sans-serif" }}>{i + 1}.</span>
                    <span style={{ fontSize: 13, color: "#c8d6e5", lineHeight: 1.5 }}>{win}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TechDetector() {
  const [url, setUrl] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedCat, setExpandedCat] = useState(null);

  const CATEGORY_META = {
    "Frontend Framework": { color: "#61dafb", icon: "⚛️" },
    "Backend Framework": { color: "#68d391", icon: "⚙️" },
    "Programming Language": { color: "#e879f9", icon: "💻" },
    "CSS Framework": { color: "#38bdf8", icon: "🎨" },
    "CMS / Platform": { color: "#a78bfa", icon: "🏗️" },
    "JavaScript Library": { color: "#fbbf24", icon: "📦" },
    "State Management": { color: "#c084fc", icon: "🗃️" },
    "Build Tool": { color: "#a3e635", icon: "🔨" },
    "Analytics & Tracking": { color: "#f87171", icon: "📈" },
    "Hosting & CDN": { color: "#34d399", icon: "🚀" },
    "UI & Design": { color: "#f472b6", icon: "✨" },
    "Third-Party Services": { color: "#fb923c", icon: "🔌" },
    "SEO & Metadata": { color: "#60a5fa", icon: "🏷️" },
    "Security": { color: "#4ade80", icon: "🔒" },
    "Server & Infrastructure": { color: "#94a3b8", icon: "🖥️" },
    "Progressive Web": { color: "#22d3ee", icon: "📱" },
    "Other": { color: "#9ca3af", icon: "🔹" },
  };

  const confColor = { High: "#00e676", Medium: "#ffd600", Low: "#ff9100" };

  const detect = async () => {
    if (!url.trim()) return;
    setLoading(true); setResults(null); setExpandedCat(null);
    try {
      const resp = await callBackend("tech", { url: url.trim() });
      setResults(resp);
    } catch (e) { setResults({ error: "Error: " + e.message }); }
    setLoading(false);
  };

  // Donut chart helper
  const DonutChart = ({ categories }) => {
    const entries = Object.entries(categories);
    const total = entries.reduce((s, [, techs]) => s + techs.length, 0);
    if (total === 0) return null;
    const radius = 56, cx = 80, cy = 80, strokeWidth = 18;
    const circumference = 2 * Math.PI * radius;
    let offset = 0;
    const slices = entries.map(([cat, techs]) => {
      const fraction = techs.length / total;
      const dashLen = fraction * circumference;
      const meta = CATEGORY_META[cat] || { color: "#8899aa" };
      const slice = { cat, count: techs.length, color: meta.color, dashLen, gapLen: circumference - dashLen, offset };
      offset += dashLen;
      return slice;
    });
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <svg width="160" height="160" viewBox="0 0 160 160">
          <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#1a2d42" strokeWidth={strokeWidth} />
          {slices.map((s, i) => (
            <circle key={i} cx={cx} cy={cy} r={radius} fill="none" stroke={s.color} strokeWidth={strokeWidth}
              strokeDasharray={`${s.dashLen} ${s.gapLen}`} strokeDashoffset={-s.offset}
              transform={`rotate(-90 ${cx} ${cy})`}
              style={{ transition: "stroke-dasharray 0.8s ease, stroke-dashoffset 0.8s ease" }} />
          ))}
          <text x={cx} y={cy - 4} textAnchor="middle" fill="#e8f0fe" fontSize="26" fontWeight="700" fontFamily="'Sora', sans-serif">{total}</text>
          <text x={cx} y={cy + 14} textAnchor="middle" fill="#5a7a95" fontSize="10" fontFamily="'IBM Plex Sans', sans-serif">technologies</text>
        </svg>
        {/* Legend */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", marginTop: 8, maxWidth: 220 }}>
          {slices.map((s) => (
            <div key={s.cat} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
              <span style={{ fontSize: 9, color: "#8899aa", whiteSpace: "nowrap" }}>{s.cat} ({s.count})</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const r = results;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <label style={styles.label}>Website URL</label>
        <input style={styles.input} placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && detect()} />
      </div>
      <button onClick={detect} disabled={loading} style={{ ...styles.primaryBtn, background: loading ? "#1a2d42" : "linear-gradient(135deg, #76ff03, #00c853)" }}>
        {loading ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Spinner size={16} color="#fff" /> Scanning technologies...</span> : "🔧 Detect Technologies"}
      </button>

      {/* Error state */}
      {r && r.error && (
        <div style={{ marginTop: 24, padding: 16, background: "#1a0a0a", border: "1px solid #3a1a1a", borderRadius: 10, color: "#ff4444", fontSize: 13 }}>
          {r.error}
        </div>
      )}

      {/* Results Dashboard */}
      {r && !r.error && (
        <div style={{ marginTop: 28, animation: "fadeUp 0.5s ease" }}>

          {/* Stats Bar */}
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            {[
              { label: "Total Technologies", value: r.total_detected || 0, color: "#76ff03" },
              { label: "Categories", value: Object.keys(r.categories || {}).length, color: "#00e5ff" },
              { label: "High Confidence", value: r.confidence_summary?.High || 0, color: "#00e676" },
              { label: "Low Confidence", value: r.confidence_summary?.Low || 0, color: "#ff9100" },
            ].map((stat) => (
              <div key={stat.label} style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 8, padding: "10px 16px", flex: "1 1 120px", textAlign: "center" }}>
                <div style={{ fontSize: 9, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 4 }}>{stat.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: stat.color, fontFamily: "'Sora', sans-serif" }}>{stat.value}</div>
              </div>
            ))}
          </div>

          {/* Top Row: Donut + Confidence Breakdown */}
          <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 24, marginBottom: 24, alignItems: "start" }}>
            <DonutChart categories={r.categories || {}} />
            {/* Confidence Breakdown */}
            <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 20 }}>
              <h4 style={{ margin: "0 0 16px", fontSize: 13, fontWeight: 600, color: "#00e5ff", letterSpacing: 0.5, textTransform: "uppercase" }}>Confidence Breakdown</h4>
              {["High", "Medium", "Low"].map((level) => {
                const count = r.confidence_summary?.[level] || 0;
                const pct = r.total_detected > 0 ? (count / r.total_detected) * 100 : 0;
                return (
                  <div key={level} style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: confColor[level], fontWeight: 600 }}>{level}</span>
                      <span style={{ fontSize: 12, color: "#5a7a95" }}>{count} ({Math.round(pct)}%)</span>
                    </div>
                    <div style={{ height: 10, background: "#0a1628", borderRadius: 5, overflow: "hidden" }}>
                      <div style={{
                        height: "100%", borderRadius: 5,
                        background: `linear-gradient(90deg, ${confColor[level]}, ${confColor[level]}88)`,
                        width: `${pct}%`, transition: "width 0.8s ease",
                        boxShadow: `0 0 8px ${confColor[level]}40`,
                      }} />
                    </div>
                  </div>
                );
              })}
              {/* Stacked bar */}
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>Overall Distribution</div>
                <div style={{ display: "flex", height: 20, borderRadius: 6, overflow: "hidden", background: "#0a1628" }}>
                  {["High", "Medium", "Low"].map((level) => {
                    const count = r.confidence_summary?.[level] || 0;
                    const pct = r.total_detected > 0 ? (count / r.total_detected) * 100 : 0;
                    return pct > 0 ? (
                      <div key={level} style={{
                        width: `${pct}%`, background: confColor[level], display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 9, fontWeight: 700, color: "#0a1628", transition: "width 0.8s ease",
                      }}>{count}</div>
                    ) : null;
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Category Cards */}
          <h4 style={{ margin: "0 0 16px", fontSize: 13, fontWeight: 600, color: "#76ff03", letterSpacing: 0.5, textTransform: "uppercase" }}>
            Detected Technology Stack
          </h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14, marginBottom: 24 }}>
            {Object.entries(r.categories || {}).map(([cat, techs]) => {
              const meta = CATEGORY_META[cat] || { color: "#8899aa", icon: "🔹" };
              const isExpanded = expandedCat === cat;
              return (
                <div key={cat} style={{
                  background: "#0d1b2a", border: `1px solid ${meta.color}25`, borderRadius: 12, overflow: "hidden",
                  transition: "all 0.3s ease", borderLeft: `3px solid ${meta.color}`,
                }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = `${meta.color}50`; e.currentTarget.style.boxShadow = `0 4px 20px ${meta.color}12`; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = `${meta.color}25`; e.currentTarget.style.boxShadow = "none"; }}>
                  {/* Card Header */}
                  <button onClick={() => setExpandedCat(isExpanded ? null : cat)} style={{
                    width: "100%", padding: "14px 16px", background: "transparent", border: "none", cursor: "pointer",
                    display: "flex", justifyContent: "space-between", alignItems: "center", textAlign: "left",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 22 }}>{meta.icon}</span>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "#e8f0fe", fontFamily: "'Sora', sans-serif" }}>{cat}</div>
                        <div style={{ fontSize: 11, color: "#5a7a95", marginTop: 2 }}>{techs.length} {techs.length === 1 ? "technology" : "technologies"} detected</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{
                        fontSize: 16, fontWeight: 800, padding: "3px 10px", borderRadius: 8,
                        background: `${meta.color}18`, color: meta.color, fontFamily: "'Sora', sans-serif",
                      }}>{techs.length}</span>
                      <span style={{ color: "#5a7a95", fontSize: 14, transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>▼</span>
                    </div>
                  </button>
                  {/* Tech Pills (always visible) */}
                  <div style={{ padding: "0 16px 12px", display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {techs.map((t) => (
                      <span key={t.name} style={{
                        fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 20,
                        background: `${meta.color}12`, color: meta.color, border: `1px solid ${meta.color}30`,
                        display: "flex", alignItems: "center", gap: 5,
                      }}>
                        {t.name}
                        <span style={{
                          fontSize: 8, padding: "1px 5px", borderRadius: 4, fontWeight: 700,
                          background: `${confColor[t.confidence]}20`, color: confColor[t.confidence],
                        }}>{t.confidence === "High" ? "H" : t.confidence === "Medium" ? "M" : "L"}</span>
                      </span>
                    ))}
                  </div>
                  {/* Expanded Detail */}
                  {isExpanded && (
                    <div style={{ padding: "0 16px 16px", borderTop: `1px solid ${meta.color}15`, animation: "fadeUp 0.3s ease" }}>
                      {techs.map((t) => (
                        <div key={t.name} style={{ padding: "12px 0", borderBottom: "1px solid #1a2d4230" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <span style={{ fontSize: 13, fontWeight: 600, color: "#e8f0fe" }}>{t.name}</span>
                            <span style={{
                              fontSize: 10, fontWeight: 700, padding: "3px 10px", borderRadius: 6,
                              background: `${confColor[t.confidence]}15`, color: confColor[t.confidence],
                            }}>Confidence: {t.confidence}</span>
                          </div>
                          <div style={{ fontSize: 10, color: "#5a7a95", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 4 }}>Evidence</div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            {t.evidence.map((e, j) => (
                              <div key={j} style={{
                                fontSize: 11, color: "#8899aa", padding: "4px 8px", background: "#0a1628",
                                borderRadius: 4, borderLeft: `2px solid ${meta.color}50`, fontFamily: "'JetBrains Mono', monospace",
                              }}>{e}</div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Category Distribution Bar Chart */}
          <div style={{ background: "#0d1b2a", border: "1px solid #1a2d42", borderRadius: 12, padding: 20, marginBottom: 24 }}>
            <h4 style={{ margin: "0 0 16px", fontSize: 13, fontWeight: 600, color: "#00e5ff", letterSpacing: 0.5, textTransform: "uppercase" }}>
              Category Distribution
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {Object.entries(r.categories || {}).sort((a, b) => b[1].length - a[1].length).map(([cat, techs]) => {
                const meta = CATEGORY_META[cat] || { color: "#8899aa", icon: "🔹" };
                const pct = r.total_detected > 0 ? (techs.length / r.total_detected) * 100 : 0;
                return (
                  <div key={cat} style={{ display: "grid", gridTemplateColumns: "160px 36px 1fr", gap: 10, alignItems: "center" }}>
                    <span style={{ fontSize: 11, color: "#c8d6e5", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {meta.icon} {cat}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: meta.color, textAlign: "center" }}>{techs.length}</span>
                    <div style={{ position: "relative", height: 18, background: "#0a1628", borderRadius: 5, overflow: "hidden" }}>
                      <div style={{
                        height: "100%", borderRadius: 5,
                        background: `linear-gradient(90deg, ${meta.color}, ${meta.color}66)`,
                        width: `${Math.max(4, pct)}%`, transition: "width 0.8s ease",
                        boxShadow: `0 0 6px ${meta.color}30`,
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>


        </div>
      )}
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
