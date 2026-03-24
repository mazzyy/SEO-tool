from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from services import serp, tech_detect, uiux, audit, performance, crawler, content, report

app = FastAPI(title="SEO Audit Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ──────────────────────────────────────────────

class SERPRequest(BaseModel):
    url: str
    keywords: list[str]
    max_pages: int = 5

class URLRequest(BaseModel):
    url: str

class UIUXRequest(BaseModel):
    url: str
    pages: list[str] = []

class CrawlRequest(BaseModel):
    url: str
    depth: int = 3

class ContentRequest(BaseModel):
    url: str
    target_keywords: str = ""

class ReportRequest(BaseModel):
    url: str
    sections: dict[str, bool] = {}


# ── Endpoints ───────────────────────────────────────────────────

@app.post("/api/serp")
async def serp_endpoint(req: SERPRequest):
    result = await serp.analyze(req.url, req.keywords, req.max_pages)
    return {"result": result}

@app.post("/api/tech")
async def tech_endpoint(req: URLRequest):
    result = await tech_detect.detect(req.url)
    return {"result": result}

@app.post("/api/uiux")
async def uiux_endpoint(req: UIUXRequest):
    result = await uiux.analyze(req.url, req.pages)
    return {"result": result}

@app.post("/api/audit")
async def audit_endpoint(req: URLRequest):
    result = await audit.full_audit(req.url)
    return {"result": result}

@app.post("/api/performance")
async def performance_endpoint(req: URLRequest):
    result = await performance.check(req.url)
    return {"result": result}

@app.post("/api/crawl")
async def crawl_endpoint(req: CrawlRequest):
    result = await crawler.crawl(req.url, req.depth)
    return {"result": result}

@app.post("/api/content")
async def content_endpoint(req: ContentRequest):
    result = await content.analyze(req.url, req.target_keywords)
    return {"result": result}

@app.post("/api/report")
async def report_endpoint(req: ReportRequest):
    result = await report.generate(req.url, req.sections)
    return {"result": result}
