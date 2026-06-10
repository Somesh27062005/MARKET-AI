"""
MarketMind AI — Project Documentation PDF Generator
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from datetime import datetime
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "MarketMind_AI_Documentation.pdf")

# ── Color Palette ──────────────────────────────────────────────────────────────
DARK_BG      = colors.HexColor("#0a0f1e")
CARD_BG      = colors.HexColor("#111827")
PRIMARY      = colors.HexColor("#3b82f6")
SECONDARY    = colors.HexColor("#8b5cf6")
ACCENT       = colors.HexColor("#60a5fa")
EMERALD      = colors.HexColor("#10b981")
AMBER        = colors.HexColor("#f59e0b")
ROSE         = colors.HexColor("#ef4444")
TEXT_MAIN    = colors.HexColor("#f1f5f9")
TEXT_MUTED   = colors.HexColor("#94a3b8")
TEXT_DIM     = colors.HexColor("#475569")
BORDER       = colors.HexColor("#1e293b")
WHITE        = colors.white

PAGE_W, PAGE_H = A4

# ── Custom Flowables ──────────────────────────────────────────────────────────
class ColoredHR(Flowable):
    def __init__(self, width, color, thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.thickness = thickness
        self.height = thickness + 2

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.thickness / 2, self.width, self.thickness / 2)


class GradientHeader(Flowable):
    """Full-width gradient header block."""
    def __init__(self, width, height, title, subtitle=""):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.title = title
        self.subtitle = subtitle

    def draw(self):
        c = self.canv
        # Dark background
        c.setFillColor(DARK_BG)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        # Accent bar at top
        c.setFillColor(PRIMARY)
        c.rect(0, self.height - 4, self.width, 4, fill=1, stroke=0)
        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 28)
        c.drawString(30, self.height - 55, self.title)
        # Subtitle
        if self.subtitle:
            c.setFillColor(TEXT_MUTED)
            c.setFont("Helvetica", 12)
            c.drawString(30, self.height - 78, self.subtitle)
        # Bottom line
        c.setStrokeColor(PRIMARY)
        c.setLineWidth(0.5)
        c.line(30, 20, self.width - 30, 20)


class SectionBadge(Flowable):
    """Colored section label badge."""
    def __init__(self, text, color=PRIMARY, width=200):
        Flowable.__init__(self)
        self.text = text
        self.color = color
        self.width = width
        self.height = 24

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(10, 7, self.text.upper())


class TechCard(Flowable):
    """Single technology badge card."""
    def __init__(self, name, version, category, color, card_width=120, card_height=60):
        Flowable.__init__(self)
        self.name = name
        self.version = version
        self.category = category
        self.color = color
        self.width = card_width
        self.height = card_height

    def draw(self):
        c = self.canv
        c.setFillColor(CARD_BG)
        c.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        c.setFillColor(self.color)
        c.roundRect(0, self.height - 5, self.width, 5, 3, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(10, self.height - 22, self.name)
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(10, self.height - 34, self.version)
        c.setFillColor(self.color)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(10, 10, self.category)


# ── Styles ─────────────────────────────────────────────────────────────────────
def build_styles():
    styles = getSampleStyleSheet()

    base = dict(fontName="Helvetica", textColor=TEXT_MAIN, spaceAfter=6,
                leading=16, leftIndent=0, rightIndent=0)

    styles.add(ParagraphStyle("MM_DocTitle",   fontSize=32, fontName="Helvetica-Bold",
                               textColor=WHITE, spaceAfter=8, leading=40, alignment=TA_LEFT))
    styles.add(ParagraphStyle("MM_H1",         fontSize=20, fontName="Helvetica-Bold",
                               textColor=WHITE, spaceAfter=10, spaceBefore=20, leading=28))
    styles.add(ParagraphStyle("MM_H2",         fontSize=14, fontName="Helvetica-Bold",
                               textColor=ACCENT, spaceAfter=6, spaceBefore=14, leading=20))
    styles.add(ParagraphStyle("MM_H3",         fontSize=11, fontName="Helvetica-Bold",
                               textColor=TEXT_MAIN, spaceAfter=4, spaceBefore=8, leading=16))
    styles.add(ParagraphStyle("MM_Body",       fontSize=9,  **base))
    styles.add(ParagraphStyle("MM_BodyMuted",  fontSize=9,  fontName="Helvetica",
                               textColor=TEXT_MUTED, spaceAfter=4, leading=14))
    styles.add(ParagraphStyle("MM_Bullet",     fontSize=9,  fontName="Helvetica",
                               textColor=TEXT_MAIN, spaceAfter=3, leading=14, leftIndent=16,
                               bulletIndent=6))
    styles.add(ParagraphStyle("MM_Code",       fontSize=8,  fontName="Courier",
                               textColor=EMERALD, backColor=CARD_BG, spaceAfter=4,
                               leading=13, leftIndent=10, rightIndent=10))
    styles.add(ParagraphStyle("MM_Caption",    fontSize=8,  fontName="Helvetica",
                               textColor=TEXT_DIM, spaceAfter=6, leading=12, alignment=TA_CENTER))
    styles.add(ParagraphStyle("MM_TableHead",  fontSize=8,  fontName="Helvetica-Bold",
                               textColor=WHITE, alignment=TA_CENTER))
    styles.add(ParagraphStyle("MM_TableCell",  fontSize=8,  fontName="Helvetica",
                               textColor=TEXT_MAIN, alignment=TA_LEFT, leading=12))

    return styles


# ── Page Background Callback ──────────────────────────────────────────────────
def dark_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Subtle header band
    canvas.setFillColor(CARD_BG)
    canvas.rect(0, PAGE_H - 28, PAGE_W, 28, fill=1, stroke=0)
    # Page number footer
    canvas.setFillColor(TEXT_DIM)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 30, 18, f"Page {doc.page}")
    canvas.drawString(30, 18, "MarketMind AI  ·  Enterprise Platform Documentation  ·  Confidential")
    # Footer line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(30, 28, PAGE_W - 30, 28)
    # Header project name
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(30, PAGE_H - 18, "MARKETMIND AI")
    canvas.restoreState()


# ── Table Helper ──────────────────────────────────────────────────────────────
def make_table(data, col_widths, header_color=PRIMARY, stripe=True):
    s = getSampleStyleSheet()
    th_style = ParagraphStyle("TH2", fontSize=8, fontName="Helvetica-Bold",
                               textColor=WHITE, alignment=TA_LEFT, leading=12)
    td_style = ParagraphStyle("TD2", fontSize=8, fontName="Helvetica",
                               textColor=TEXT_MAIN, alignment=TA_LEFT, leading=12)

    formatted = []
    for i, row in enumerate(data):
        style = th_style if i == 0 else td_style
        formatted.append([Paragraph(str(cell), style) for cell in row])

    t = Table(formatted, colWidths=col_widths, repeatRows=1)
    ts = [
        ("BACKGROUND",  (0, 0), (-1, 0),  header_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, DARK_BG] if stripe else [CARD_BG]),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.3, BORDER),
        ("ROWBACKGROUNDS", (0, 0), (0, 0), [header_color]),
    ]
    t.setStyle(TableStyle(ts))
    return t


# ── Content Builder ───────────────────────────────────────────────────────────
def build_document():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        rightMargin=2.5 * cm, leftMargin=2.5 * cm,
        topMargin=1.5 * cm,   bottomMargin=2 * cm,
    )
    styles = build_styles()
    S = styles
    story = []
    CONTENT_W = PAGE_W - 5 * cm

    # ══════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════
    story.append(GradientHeader(CONTENT_W, 120,
                                "MarketMind AI",
                                "Enterprise Sales & Marketing Intelligence Platform"))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Technical Documentation", S["MM_H1"]))
    story.append(Paragraph(
        "A comprehensive reference covering architecture, technology stack, "
        "agent design, database schema, API catalogue, and deployment guide.",
        S["MM_BodyMuted"]
    ))
    story.append(Spacer(1, 12))

    meta = [
        ["Document Version", "2.0.0"],
        ["Release Date",     datetime.now().strftime("%B %d, %Y")],
        ["Platform",         "Web — React 18 + Flask 3"],
        ["Classification",   "Internal / Confidential"],
        ["Maintainer",       "Engineering Team"],
    ]
    t = make_table(meta, [5 * cm, 10 * cm], header_color=SECONDARY)
    story.append(t)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 1. EXECUTIVE OVERVIEW
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("1.  Executive Overview", PRIMARY, 220))
    story.append(Spacer(1, 8))
    story.append(Paragraph("What is MarketMind AI?", S["MM_H1"]))
    story.append(Paragraph(
        "MarketMind AI is an enterprise-grade B2B SaaS platform that transforms how "
        "sales and marketing teams generate intelligence, qualify leads, and craft campaigns. "
        "Unlike traditional tools that return plain text, MarketMind employs a "
        "<b>multi-agent LangGraph pipeline</b> to produce structured JSON data that renders "
        "as interactive dashboards, charts, and downloadable reports.",
        S["MM_Body"]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Core Capabilities", S["MM_H2"]))
    caps = [
        ("🔍 Market Intelligence", "Multi-agent industry analysis with SWOT, PESTEL, competitor radar charts, and market-size projections."),
        ("🚀 Campaign Generator",  "AI-crafted campaign strategies with funnel visualization, budget allocation charts, and campaign calendars."),
        ("🎯 Sales Pitch Engine",  "Personalized pitches, objection handlers, email templates, LinkedIn outreach, and meeting agendas."),
        ("📊 Lead Qualification",  "BANT-framework scoring (0-100), conversion probability, lead temperature, and CRM-ready output."),
        ("💡 Business Insights",   "30/60/90-day roadmaps, opportunity matrices, risk registers, and KPI dashboards."),
        ("📈 Live Stock Ticker",   "Real-time price feed for 17 US and Indian equities, auto-refreshing every 8 seconds."),
        ("🗄️  CRM Pipeline",       "Full CRUD lead management with status tracking, grading, and revenue calculation."),
        ("🔐 Authentication",      "Email/password + Google OAuth 2.0 with Flask session management."),
    ]
    for title, desc in caps:
        story.append(Paragraph(f"<b>{title}</b>", S["MM_H3"]))
        story.append(Paragraph(desc, S["MM_BodyMuted"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 2. TECHNOLOGY STACK
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("2.  Technology Stack", SECONDARY, 220))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Technology Stack", S["MM_H1"]))
    story.append(Paragraph(
        "MarketMind AI is built on a modern, production-tested stack optimised for "
        "AI-heavy workloads, real-time data, and developer velocity.",
        S["MM_BodyMuted"]
    ))
    story.append(Spacer(1, 12))

    # --- Frontend ---
    story.append(Paragraph("Frontend", S["MM_H2"]))
    fe_data = [
        ["Technology",       "Version",   "Purpose",                       "License"],
        ["React",            "18.3.x",    "Component-based UI framework",  "MIT"],
        ["Vite",             "5.x",       "Build tool & HMR dev server",   "MIT"],
        ["Tailwind CSS",     "3.4.x",     "Utility-first styling system",  "MIT"],
        ["Recharts",         "2.x",       "Declarative chart library",     "MIT"],
        ["Framer Motion",    "11.x",      "Animation & gesture library",   "MIT"],
        ["Chart.js",         "4.x",       "Dashboard canvas charts",       "MIT"],
        ["React Router v6",  "6.x",       "SPA client-side routing",       "MIT"],
        ["React-chartjs-2",  "5.x",       "Chart.js React bindings",       "MIT"],
    ]
    story.append(make_table(fe_data, [3.5 * cm, 2 * cm, 6 * cm, 2 * cm]))
    story.append(Spacer(1, 14))

    # --- Backend ---
    story.append(Paragraph("Backend", S["MM_H2"]))
    be_data = [
        ["Technology",       "Version",   "Purpose",                           "License"],
        ["Python",           "3.12",      "Runtime language",                  "PSF"],
        ["Flask",            "3.x",       "Lightweight WSGI web framework",    "BSD"],
        ["Flask-CORS",       "4.x",       "Cross-Origin Resource Sharing",     "MIT"],
        ["SQLAlchemy",       "2.x",       "ORM for PostgreSQL / SQLite",       "MIT"],
        ["psycopg2-binary",  "2.9",       "PostgreSQL adapter for Python",     "LGPL"],
        ["python-dotenv",    "1.x",       "Environment variable loader",       "BSD"],
        ["Gunicorn",         "22.x",      "Production WSGI HTTP server",       "MIT"],
    ]
    story.append(make_table(be_data, [3.5 * cm, 2 * cm, 6 * cm, 2 * cm]))
    story.append(Spacer(1, 14))

    # --- AI / LLM ---
    story.append(Paragraph("Artificial Intelligence & Orchestration", S["MM_H2"]))
    ai_data = [
        ["Technology",           "Version",   "Purpose",                            "License"],
        ["Groq API",             "Cloud",     "LLM inference (ultra-fast Llama 3)", "Commercial"],
        ["Llama 3.3 70B",        "Groq",      "Primary language model",             "Meta Llama"],
        ["LangChain",            "0.2.x",     "LLM chain composition layer",        "MIT"],
        ["LangGraph",            "0.1.x",     "Multi-agent stateful graph engine",  "MIT"],
        ["LangChain-Groq",       "0.1.x",     "Groq provider for LangChain",       "MIT"],
        ["python-docx",          "1.1",       "DOCX report generation",            "MIT"],
        ["python-pptx",          "0.6",       "PPTX report generation",            "MIT"],
        ["ReportLab",            "4.x",       "PDF generation",                    "BSD"],
        ["Markdown",             "3.x",       "Markdown→HTML conversion",          "BSD"],
    ]
    story.append(make_table(ai_data, [3.5 * cm, 2 * cm, 6 * cm, 2 * cm]))
    story.append(Spacer(1, 14))

    # --- Database ---
    story.append(Paragraph("Database & Storage", S["MM_H2"]))
    db_data = [
        ["Technology",   "Version",  "Purpose",                            "License"],
        ["PostgreSQL",   "16",       "Primary relational database",        "PostgreSQL"],
        ["SQLite",       "3.x",      "Local development / fallback DB",   "Public Domain"],
        ["cachetools",   "5.x",      "In-memory LRU cache (Redis-free)",  "MIT"],
    ]
    story.append(make_table(db_data, [3.5 * cm, 2 * cm, 6 * cm, 2 * cm]))
    story.append(Spacer(1, 14))

    # --- Auth ---
    story.append(Paragraph("Authentication & Security", S["MM_H2"]))
    auth_data = [
        ["Technology",           "Purpose",                            "Standard"],
        ["Flask Sessions",       "Server-side session management",     "HTTP Cookie"],
        ["Google OAuth 2.0",     "Social login via Google account",    "RFC 6749"],
        ["oauthlib",             "OAuth 2.0 client implementation",    "BSD"],
        ["requests-oauthlib",    "HTTP OAuth wrapper",                 "ISC"],
        ["Werkzeug",             "Password hashing & security utils",  "BSD"],
    ]
    story.append(make_table(auth_data, [4 * cm, 7 * cm, 2.5 * cm]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 3. ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("3.  System Architecture", EMERALD, 240))
    story.append(Spacer(1, 8))
    story.append(Paragraph("System Architecture", S["MM_H1"]))

    story.append(Paragraph("High-Level Architecture", S["MM_H2"]))
    story.append(Paragraph(
        "MarketMind AI follows a clean <b>3-tier architecture</b>: "
        "React SPA (Presentation) ↔ Flask REST API (Application) ↔ PostgreSQL (Data). "
        "The AI layer is embedded in the Application tier as LangGraph agent graphs "
        "that run synchronously within the Flask request/response cycle.",
        S["MM_Body"]
    ))
    story.append(Spacer(1, 8))

    arch_data = [
        ["Tier",             "Technology",            "Responsibility"],
        ["Presentation",     "React 18 + Vite",       "SPA, routing, state, charts, forms"],
        ["API Gateway",      "Flask 3 + Flask-CORS",  "REST endpoints, auth, session mgmt"],
        ["AI Engine",        "LangGraph + Groq",      "Multi-agent graphs, structured output"],
        ["Data",             "PostgreSQL 16",         "Users, leads, history, reports, stocks"],
        ["Export",           "ReportLab / python-docx / python-pptx", "PDF / DOCX / PPTX generation"],
        ["Cache",            "cachetools LRU",        "In-process response cache"],
    ]
    story.append(make_table(arch_data, [3 * cm, 5 * cm, 6 * cm], header_color=EMERALD))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Multi-Agent Pipeline", S["MM_H2"]))
    story.append(Paragraph(
        "Each analysis module runs a dedicated LangGraph StateGraph. "
        "Nodes communicate through a typed state dict. Every node calls "
        "Groq with a structured JSON prompt and a schema example, then "
        "validates + merges the parsed output into the shared state.",
        S["MM_Body"]
    ))
    story.append(Spacer(1, 6))

    agents_data = [
        ["Agent Graph",              "Nodes",                                               "Output"],
        ["MarketIntelligenceGraph",  "research → competitor → synthesis → score",           "Structured market report JSON"],
        ["CampaignStrategyGraph",    "audience → funnel → content → metrics",               "Campaign plan + KPI JSON"],
        ["SalesGraph",               "persona → pitch → objection → email",                 "Full sales package JSON"],
        ["LeadQualificationGraph",   "bant → scoring → intent → action",                    "BANT scores + lead priority JSON"],
        ["BusinessConsultantGraph",  "challenge → opportunity → risk → roadmap",             "90-day plan + strategy JSON"],
        ["ReportGenerationAgent",    "compile → template → render → export",                "PDF / DOCX / PPTX bytes"],
    ]
    story.append(make_table(agents_data,
                             [4.5 * cm, 5 * cm, 4.5 * cm], header_color=AMBER))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Request / Response Data Flow", S["MM_H2"]))
    flow = [
        "1.  User submits form on React page (POST /api/v2/[module])",
        "2.  Flask validates input, starts LangGraph graph execution",
        "3.  Node 1: Industry / persona research prompt → Groq → parsed JSON",
        "4.  Node 2: Competitive / strategy analysis → Groq → parsed JSON merged",
        "5.  Node 3: Synthesis + confidence scoring",
        "6.  Node 4: Final schema validation + fallback defaults applied",
        "7.  Flask returns { success: true, data: { ...structured_json } }",
        "8.  React renders sections: charts, tables, cards, export buttons",
        "9.  User clicks Export → POST /api/v2/export/pdf → binary PDF download",
    ]
    for step in flow:
        story.append(Paragraph(f"• {step}", S["MM_Bullet"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 4. DATABASE SCHEMA
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("4.  Database Schema", AMBER, 220))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Database Schema — PostgreSQL 16", S["MM_H1"]))

    tables = {
        "users": [
            ["Column",      "Type",         "Constraints",       "Description"],
            ["email",       "VARCHAR(255)", "PRIMARY KEY",       "User email (unique identifier)"],
            ["password",    "TEXT",         "NOT NULL",          "Hashed password"],
            ["name",        "VARCHAR(200)", "NOT NULL",          "Full display name"],
            ["first_name",  "VARCHAR(100)", "",                  "Given name"],
            ["last_name",   "VARCHAR(100)", "",                  "Family name"],
            ["avatar",      "VARCHAR(10)",  "",                  "Initial(s) for avatar"],
            ["joined_at",   "TIMESTAMPTZ",  "NOT NULL",          "Account creation timestamp"],
        ],
        "history": [
            ["Column",      "Type",         "Constraints",       "Description"],
            ["id",          "SERIAL",       "PRIMARY KEY",       "Auto-increment ID"],
            ["user_email",  "VARCHAR(255)", "FK → users",        "Owner"],
            ["type",        "VARCHAR(50)",  "NOT NULL",          "campaign / pitch / lead / market / insights"],
            ["title",       "TEXT",         "NOT NULL",          "Human-readable label"],
            ["input_data",  "JSONB",        "NOT NULL",          "Form input snapshot"],
            ["result",      "TEXT",         "NOT NULL",          "Raw v1 text result"],
            ["created_at",  "TIMESTAMPTZ",  "NOT NULL",          "Creation time"],
        ],
        "crm_leads": [
            ["Column",      "Type",         "Constraints",       "Description"],
            ["id",          "SERIAL",       "PRIMARY KEY",       ""],
            ["user_email",  "VARCHAR(255)", "FK → users",        "Owner"],
            ["name",        "VARCHAR(200)", "NOT NULL",          "Lead / contact name"],
            ["company",     "VARCHAR(200)", "",                  "Organisation"],
            ["score",       "INTEGER",      "CHECK 0-100",       "Lead quality score"],
            ["grade",       "CHAR(1)",      "",                  "A / B / C / D"],
            ["status",      "VARCHAR(50)",  "NOT NULL",          "New / Contacted / Proposal / Closed Won"],
            ["details",     "TEXT",         "",                  "Free-text notes"],
            ["created_at",  "TIMESTAMPTZ",  "NOT NULL",          ""],
        ],
        "stock_prices": [
            ["Column",        "Type",          "Constraints",    "Description"],
            ["ticker",        "VARCHAR(20)",   "PRIMARY KEY",    "Ticker symbol"],
            ["name",          "VARCHAR(200)",  "NOT NULL",       "Full security name"],
            ["price",         "NUMERIC(14,2)", "NOT NULL",       "Latest price"],
            ["change_pct",    "NUMERIC(6,2)",  "",               "Intraday % change"],
            ["history",       "JSONB",         "NOT NULL",       "12-month price array"],
            ["last_updated",  "TIMESTAMPTZ",   "NOT NULL",       ""],
        ],
        "analysis_reports  (NEW)": [
            ["Column",          "Type",          "Constraints",   "Description"],
            ["id",              "SERIAL",        "PRIMARY KEY",   ""],
            ["user_email",      "VARCHAR(255)",  "FK → users",    "Owner"],
            ["module",          "VARCHAR(50)",   "NOT NULL",      "market / campaign / pitch / lead / insights"],
            ["title",           "TEXT",          "NOT NULL",      ""],
            ["input_data",      "JSONB",         "NOT NULL",      "Form inputs"],
            ["result_json",     "JSONB",         "NOT NULL",      "Full structured agent output"],
            ["confidence_score","SMALLINT",      "",              "AI confidence 0-100"],
            ["created_at",      "TIMESTAMPTZ",   "NOT NULL",      ""],
        ],
        "exported_reports  (NEW)": [
            ["Column",      "Type",          "Constraints",           "Description"],
            ["id",          "SERIAL",        "PRIMARY KEY",           ""],
            ["user_email",  "VARCHAR(255)",  "FK → users",            "Owner"],
            ["report_id",   "INTEGER",       "FK → analysis_reports", "Parent analysis"],
            ["format",      "VARCHAR(10)",   "NOT NULL",              "pdf / docx / pptx"],
            ["file_path",   "TEXT",          "NOT NULL",              "Server-side file path"],
            ["file_size",   "INTEGER",       "",                      "Bytes"],
            ["created_at",  "TIMESTAMPTZ",   "NOT NULL",              ""],
        ],
        "watchlists  (NEW)": [
            ["Column",      "Type",          "Constraints",   "Description"],
            ["id",          "SERIAL",        "PRIMARY KEY",   ""],
            ["user_email",  "VARCHAR(255)",  "FK → users",    "Owner"],
            ["industry",    "VARCHAR(200)",  "NOT NULL",      "Industry / topic label"],
            ["keywords",    "JSONB",         "NOT NULL",      "Array of monitored keywords"],
            ["created_at",  "TIMESTAMPTZ",   "NOT NULL",      ""],
        ],
    }

    for table_name, rows in tables.items():
        is_new = "(NEW)" in table_name
        color = EMERALD if is_new else PRIMARY
        label = "NEW TABLE — " if is_new else ""
        story.append(Paragraph(f"{label}<b>{table_name.replace('  (NEW)', '')}</b>", S["MM_H2"]))
        story.append(make_table(rows, [3 * cm, 3 * cm, 3 * cm, 5 * cm], header_color=color))
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 5. API ENDPOINTS
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("5.  API Endpoint Catalogue", ROSE, 240))
    story.append(Spacer(1, 8))
    story.append(Paragraph("API Endpoint Catalogue", S["MM_H1"]))
    story.append(Paragraph(
        "All endpoints require an active Flask session cookie unless marked (public). "
        "v1 endpoints return raw markdown text. v2 endpoints return structured JSON.",
        S["MM_BodyMuted"]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Authentication Endpoints", S["MM_H2"]))
    auth_eps = [
        ["Method", "Path",                        "Description"],
        ["POST",   "/api/auth/login",              "Email + password login, sets session cookie"],
        ["POST",   "/api/auth/register",           "Create new user account"],
        ["POST",   "/api/auth/logout",             "Clear session cookie"],
        ["GET",    "/api/auth/me",                 "Return current session user data"],
        ["GET",    "/api/auth/google",             "Initiate Google OAuth 2.0 flow"],
        ["GET",    "/api/auth/google/callback",    "Handle OAuth redirect + set session"],
        ["POST",   "/api/auth/reset-password",     "Trigger password reset email"],
    ]
    story.append(make_table(auth_eps, [1.5 * cm, 5 * cm, 7 * cm], header_color=ROSE))
    story.append(Spacer(1, 12))

    story.append(Paragraph("v1 AI Generation Endpoints (Legacy — Text Output)", S["MM_H2"]))
    v1_eps = [
        ["Method", "Path",                    "Description"],
        ["POST",   "/api/market_analysis",    "Raw markdown market analysis text"],
        ["POST",   "/api/generate_campaign",  "Raw markdown campaign strategy text"],
        ["POST",   "/api/generate_pitch",     "Raw markdown sales pitch text"],
        ["POST",   "/api/lead_score",         "Raw markdown lead scoring text"],
        ["POST",   "/api/business_insights",  "Raw markdown business insights text"],
        ["POST",   "/api/translate",          "Translate result text to target language"],
        ["POST",   "/api/refine_result",      "Refine/edit result with follow-up prompt"],
        ["POST",   "/api/export_pdf",         "Export v1 text result as PDF"],
    ]
    story.append(make_table(v1_eps, [1.5 * cm, 5 * cm, 7 * cm], header_color=TEXT_DIM))
    story.append(Spacer(1, 12))

    story.append(Paragraph("v2 Structured AI Endpoints (Multi-Agent JSON Output)", S["MM_H2"]))
    v2_eps = [
        ["Method", "Path",                        "Returns"],
        ["POST",   "/api/v2/market_analysis",     "Full market intel JSON (SWOT, PESTEL, charts data)"],
        ["POST",   "/api/v2/campaign",             "Campaign plan JSON (funnel, KPIs, calendar)"],
        ["POST",   "/api/v2/pitch",                "Sales package JSON (pitch, emails, objections)"],
        ["POST",   "/api/v2/lead_score",           "BANT JSON (score, probability, actions)"],
        ["POST",   "/api/v2/business_insights",    "Strategy JSON (30/60/90 plan, matrix)"],
        ["POST",   "/api/v2/export/pdf",           "Binary PDF bytes (Content-Disposition: attachment)"],
        ["POST",   "/api/v2/export/docx",          "Binary DOCX bytes"],
        ["GET",    "/api/v2/reports",              "List user's analysis_reports (paginated)"],
        ["DELETE", "/api/v2/reports/:id",          "Delete a saved report"],
        ["GET",    "/api/v2/analytics/summary",    "Aggregated usage stats for Analytics dashboard"],
        ["POST",   "/api/v2/watchlist",            "Add industry to user's watchlist"],
        ["GET",    "/api/v2/watchlist",            "Get user's watchlists"],
    ]
    story.append(make_table(v2_eps, [1.5 * cm, 5.5 * cm, 7 * cm], header_color=PRIMARY))
    story.append(Spacer(1, 12))

    story.append(Paragraph("CRM & Data Endpoints", S["MM_H2"]))
    crm_eps = [
        ["Method",   "Path",                   "Description"],
        ["GET",      "/api/crm/leads",         "List user's CRM leads"],
        ["POST",     "/api/crm/leads",         "Add new lead to CRM"],
        ["PATCH",    "/api/crm/leads/:id",     "Update lead status"],
        ["DELETE",   "/api/crm/leads/:id",     "Remove lead from CRM"],
        ["GET",      "/api/history",           "Get user's generation history"],
        ["POST",     "/api/history/save",      "Manually save a result to history"],
        ["DELETE",   "/api/history/:id",       "Delete a history record"],
        ["GET",      "/api/dashboard/stats",   "Live dashboard KPI + stock prices"],
    ]
    story.append(make_table(crm_eps, [1.5 * cm, 5 * cm, 7 * cm], header_color=EMERALD))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 6. FRONTEND STRUCTURE
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("6.  Frontend Structure", ACCENT, 220))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Frontend Structure & Pages", S["MM_H1"]))

    story.append(Paragraph("Page Routes", S["MM_H2"]))
    pages_data = [
        ["Route",              "Component",            "Auth",    "Description"],
        ["/",                  "Dashboard.jsx",        "✓",       "Live KPI cards, stock ticker, charts"],
        ["/market-analysis",   "MarketAnalysis.jsx",   "✓",       "Multi-agent market intelligence"],
        ["/campaign",          "CampaignGenerator.jsx","✓",       "AI campaign strategy builder"],
        ["/pitch",             "SalesPitch.jsx",       "✓",       "Sales pitch & outreach tools"],
        ["/lead-scoring",      "LeadScoring.jsx",      "✓",       "BANT lead qualification engine"],
        ["/business-insights", "BusinessInsights.jsx", "✓",       "Strategic intelligence & roadmaps"],
        ["/analytics",         "Analytics.jsx",        "✓",       "Aggregated platform analytics  (NEW)"],
        ["/reports",           "ReportHistory.jsx",    "✓",       "Report history & downloads  (NEW)"],
        ["/crm",               "CRM.jsx",              "✓",       "CRM lead pipeline management"],
        ["/history",           "History.jsx",          "✓",       "Generation history log"],
        ["/profile",           "Profile.jsx",          "✓",       "User account settings"],
        ["/themes-store",      "ThemesStore.jsx",      "✓",       "UI theme customization"],
        ["/login",             "Login.jsx",            "Public",  "Email + Google OAuth login"],
        ["/register",          "Register.jsx",         "Public",  "New account registration"],
        ["/reset-password",    "ResetPassword.jsx",    "Public",  "Password reset flow"],
    ]
    story.append(make_table(pages_data, [3.5 * cm, 4 * cm, 1.5 * cm, 5 * cm]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Chart Component Library  (components/charts/)", S["MM_H2"]))
    chart_data = [
        ["Component",             "Chart Type",   "Used In"],
        ["MarketGrowthChart",     "LineChart",    "Market Analysis — growth projections"],
        ["CompetitorRadar",       "RadarChart",   "Market Analysis — competitor scoring"],
        ["MarketSharePie",        "PieChart",     "Market Analysis — market share"],
        ["OpportunityHeatmap",    "ScatterChart", "Market Analysis — effort vs impact"],
        ["ConversionFunnel",      "BarChart",     "Campaign — funnel stages"],
        ["BudgetAllocation",      "BarChart",     "Campaign — channel spend split"],
        ["LeadGauge",             "Custom SVG",   "Lead Scoring — 0-100 arc gauge"],
        ["BANTScoreBar",          "Custom SVG",   "Lead Scoring — BANT factors"],
        ["AgentProgressBar",      "Custom CSS",   "All v2 pages — agent node steps"],
        ["SkeletonCard",          "CSS pulse",    "All v2 pages — loading placeholders"],
    ]
    story.append(make_table(chart_data, [4 * cm, 3 * cm, 7 * cm], header_color=SECONDARY))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 7. FOLDER STRUCTURE
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("7.  Project Folder Structure", AMBER, 260))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Project Folder Structure", S["MM_H1"]))

    tree = """\
resilient-pascal/
├── app.py                          ← Flask application entry point
├── database.py                     ← DB connection, models, helpers
├── generate_docs.py                ← Documentation PDF generator
├── requirements.txt                ← Python package manifest
├── .env                            ← Secrets (gitignored)
├── .gitignore
├── agents/                         ← Multi-agent LangGraph graphs
│   ├── __init__.py
│   ├── base.py                     ← Shared chain, JSON parser, retry
│   ├── market_intelligence.py
│   ├── campaign_strategy.py
│   ├── sales_agent.py
│   ├── lead_qualification.py
│   ├── business_consultant.py
│   └── report_generation.py
├── exports/                        ← Generated reports (gitignored)
├── static/                         ← Flask static assets
├── templates/                      ← Flask HTML templates
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── pages/
        │   ├── Dashboard.jsx
        │   ├── MarketAnalysis.jsx
        │   ├── CampaignGenerator.jsx
        │   ├── SalesPitch.jsx
        │   ├── LeadScoring.jsx
        │   ├── BusinessInsights.jsx
        │   ├── Analytics.jsx           ← NEW
        │   ├── ReportHistory.jsx       ← NEW
        │   ├── CRM.jsx
        │   ├── History.jsx
        │   ├── Profile.jsx
        │   ├── ThemesStore.jsx
        │   ├── Login.jsx
        │   ├── Register.jsx
        │   └── ResetPassword.jsx
        ├── components/
        │   ├── Navbar.jsx
        │   ├── ChatPanel.jsx
        │   ├── TranslatorBlock.jsx
        │   └── charts/                 ← NEW
        │       ├── MarketGrowthChart.jsx
        │       ├── CompetitorRadar.jsx
        │       ├── MarketSharePie.jsx
        │       ├── OpportunityHeatmap.jsx
        │       ├── ConversionFunnel.jsx
        │       ├── BudgetAllocation.jsx
        │       ├── LeadGauge.jsx
        │       ├── BANTScoreBar.jsx
        │       ├── AgentProgressBar.jsx
        │       └── SkeletonCard.jsx
        ├── context/
        │   ├── AuthContext.jsx
        │   └── ThemeContext.jsx
        └── services/
            ├── api.js                  ← v1 API calls
            └── apiV2.js                ← NEW — v2 structured + export calls"""

    story.append(Paragraph(f"<pre>{tree}</pre>", ParagraphStyle(
        "Tree", fontName="Courier", fontSize=7.2, textColor=EMERALD,
        backColor=CARD_BG, leading=11, spaceAfter=6,
        leftIndent=8, rightIndent=8
    )))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # 8. ENVIRONMENT & DEPLOYMENT
    # ══════════════════════════════════════════════════════════════════════
    story.append(SectionBadge("8.  Environment & Deployment", EMERALD, 260))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Environment Variables & Deployment", S["MM_H1"]))

    story.append(Paragraph("Required Environment Variables  (.env)", S["MM_H2"]))
    env_data = [
        ["Variable",           "Example Value",              "Description"],
        ["GROQ_API_KEY",       "gsk_xxx...",                 "Groq Cloud API key for LLM inference"],
        ["SECRET_KEY",         "random-32-char-string",      "Flask session signing key"],
        ["DATABASE_URL",       "postgresql://user:pw@host/db","PostgreSQL connection string"],
        ["GOOGLE_CLIENT_ID",   "xxx.apps.googleusercontent.com","Google OAuth client ID"],
        ["GOOGLE_CLIENT_SECRET","GOCSPX-xxx",               "Google OAuth client secret"],
    ]
    story.append(make_table(env_data, [3.5 * cm, 4.5 * cm, 6 * cm], header_color=EMERALD))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Local Development Setup", S["MM_H2"]))
    setup_steps = [
        "1.  Clone repository and cd into project root",
        "2.  Copy .env.example to .env and fill in all variables",
        "3.  Install Python deps:  pip install -r requirements.txt",
        "4.  Start PostgreSQL and create database:  createdb marketmind",
        "5.  Run backend:  python app.py  (starts on port 5000)",
        "6.  Install frontend deps:  cd frontend && npm install",
        "7.  Start frontend:  npm run dev  (starts on port 5173)",
        "8.  Open browser at  http://localhost:5173",
    ]
    for step in setup_steps:
        story.append(Paragraph(f"• {step}", S["MM_Bullet"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Implementation Roadmap", S["MM_H2"]))
    roadmap_data = [
        ["Sprint",    "Scope",                     "Duration", "Status"],
        ["Sprint 1",  "Backend: agents/ + v2 endpoints + PostgreSQL migration", "3 days",  "In Progress"],
        ["Sprint 2",  "Market Analysis v2 output + chart library",  "2 days",  "Planned"],
        ["Sprint 3",  "Campaign, Pitch, Lead, Insights v2 output",  "3 days",  "Planned"],
        ["Sprint 4",  "Analytics page, Reports page, Polish",        "2 days",  "Planned"],
    ]
    story.append(make_table(roadmap_data,
                             [1.8 * cm, 7 * cm, 2 * cm, 2.5 * cm],
                             header_color=AMBER))
    story.append(Spacer(1, 12))

    # Footer credits
    story.append(ColoredHR(CONTENT_W, BORDER, 0.5))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Generated automatically on {datetime.now().strftime('%B %d, %Y at %H:%M')}  ·  "
        "MarketMind AI Enterprise Platform  ·  All rights reserved.",
        S["MM_Caption"]
    ))

    # ── Build ──
    doc.build(story, onFirstPage=dark_page, onLaterPages=dark_page)
    print(f"✅ Documentation PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_document()
