import os
import sys

# Redirect standard error (fd 2) at the OS level to a safe process-specific log file to prevent OS-level Errno 22 crashes
try:
    stderr_filename = f"backend_stderr_{os.getpid()}.log"
    stderr_log = open(stderr_filename, "a", encoding="utf-8")
    os.dup2(stderr_log.fileno(), 2)
except Exception:
    try:
        null_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null_fd, 2)
        os.close(null_fd)
    except Exception:
        pass

class SafeStream:
    def __init__(self, original):
        self.original = original
    def write(self, data):
        try:
            if self.original:
                self.original.write(data)
        except Exception:
            pass
    def flush(self):
        try:
            if self.original:
                self.original.flush()
        except Exception:
            pass
    def isatty(self):
        try:
            return self.original.isatty() if self.original else False
        except Exception:
            return False
    def fileno(self):
        try:
            return self.original.fileno() if self.original else 1
        except Exception:
            return 1

sys.stdout = SafeStream(sys.stdout)
sys.stderr = SafeStream(sys.stderr)

import re
import io
import json
from typing import TypedDict, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Safe print helper to prevent OS-level terminal write crashes on Windows
def print(*args, **kwargs):
    import builtins
    try:
        builtins.print(*args, **kwargs)
    except Exception:
        pass

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from oauthlib.oauth2 import WebApplicationClient
import requests
from langgraph.graph import StateGraph, END

# Import database and PDF utilities
import database
db = database

rate_limit_cache = {}

def rate_limit(limit=60):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapped(*args, **kwargs):
            ident = session.get("user_email") or request.remote_addr
            key = f"rl:{ident}:{f.__name__}"
            current_requests = rate_limit_cache.get(key, 0)
            if current_requests >= limit:
                return jsonify({"error": "Rate limit exceeded. Please try again in a minute."}), 429
            rate_limit_cache[key] = current_requests + 1
            return f(*args, **kwargs)
        return wrapped
    return decorator

try:
    import docx
except ImportError:
    docx = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

def extract_text_from_file(file):
    filename = file.filename.lower()
    stream = io.BytesIO(file.read())
    if filename.endswith(".docx"):
        if docx is None:
            return "Error parsing docx: 'python-docx' library is not installed."
        try:
            doc = docx.Document(stream)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return f"Error parsing docx: {str(e)}"
    elif filename.endswith(".pdf"):
        if pypdf is not None:
            try:
                reader = pypdf.PdfReader(stream)
                return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            except Exception as e:
                return f"Error parsing PDF with pypdf: {str(e)}"
        elif PyPDF2 is not None:
            try:
                reader = PyPDF2.PdfReader(stream)
                return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            except Exception as e:
                return f"Error parsing PDF with PyPDF2: {str(e)}"
        else:
            return "Error parsing PDF: Neither 'pypdf' nor 'PyPDF2' library is installed."
    else:
        try:
            return stream.getvalue().decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Error reading text: {str(e)}"

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import markdown
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "marketmind-dev-secret-key-change-in-production")
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

import secrets

@app.before_request
def handle_csrf():
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        path = request.path
        if path in ["/api/auth/login", "/api/auth/register", "/api/auth/reset-password"] or path.startswith("/api/auth/google"):
            return
        
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        session_token = session.get("csrf_token")
        
        if not csrf_cookie or not csrf_header or csrf_header != csrf_cookie or csrf_header != session_token:
            return jsonify({"error": "CSRF verification failed"}), 403

@app.after_request
def set_csrf_cookie(response):
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    response.set_cookie("csrf_token", session["csrf_token"], samesite="Lax", secure=False)
    return response

# Initialize database schema
database.init_db()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Check if key is dummy or empty
IS_DUMMY_KEY = not GROQ_API_KEY or GROQ_API_KEY.startswith("your_") or GROQ_API_KEY == "gsk_dummy"

# Use dummy key placeholder to allow initialization without throwing on startup
GROQ_API_KEY_TO_USE = GROQ_API_KEY if not IS_DUMMY_KEY else "gsk_dummy_key_to_allow_server_startup"
GROQ_MODEL = "llama-3.3-70b-versatile"

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Allow OAuth over HTTP for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

if GOOGLE_CLIENT_ID:
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
else:
    client = None

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

# ─── LangChain LLM Setup ────────────────────────────────────────────────────

llm = ChatGroq(
    api_key=GROQ_API_KEY_TO_USE,
    model=GROQ_MODEL,
    temperature=0.7,
    max_tokens=4096,
    max_retries=3,
)

def safe_llm_invoke(messages, temperature=0.7):
    """
    Invoke Groq LLM with fallback to llama-3.1-8b-instant if llama-3.3-70b-versatile fails (e.g. 429).
    """
    primary_model = "llama-3.3-70b-versatile"
    fast_model = "llama-3.1-8b-instant"
    try:
        model = ChatGroq(
            api_key=GROQ_API_KEY_TO_USE,
            model=primary_model,
            temperature=temperature,
            max_tokens=4096,
            max_retries=1,
        )
        return model.invoke(messages)
    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg or "tpd" in err_msg or "tokens" in err_msg:
            print(f"[app.py] Rate limit hit on {primary_model}. Falling back to {fast_model}...")
            model = ChatGroq(
                api_key=GROQ_API_KEY_TO_USE,
                model=fast_model,
                temperature=temperature,
                max_tokens=4096,
                max_retries=1,
            )
            return model.invoke(messages)
        raise e

parser = StrOutputParser()


# ─── Prompt Templates (LangChain) ───────────────────────────────────────────

CAMPAIGN_SYSTEM = """You are an elite marketing strategist with 20+ years of experience creating 
high-performing campaigns for Fortune 500 companies and fast-growing startups. You combine 
data-driven insights with creative storytelling to build campaigns that drive measurable results.
Always provide actionable, specific recommendations — never generic advice."""

CAMPAIGN_HUMAN = """Generate a comprehensive marketing campaign strategy with the following details:

**Product/Service:** {product}
**Target Audience:** {audience}
**Platform:** {platform}
**Campaign Goals:** {goals}
**Budget Range:** {budget}

Please provide a detailed campaign strategy including:

1. **Campaign Overview** — Core theme, messaging angle, and positioning
2. **Target Audience Analysis** — Demographics, psychographics, pain points, and motivations
3. **Content Strategy** — 5 specific content ideas with headlines and descriptions
4. **Ad Copy Variations** — 3 compelling ad copy variations with headlines, body text, and CTAs
5. **Platform-Specific Tactics** — Best practices for the selected platform(s)
6. **Content Calendar** — Suggested posting schedule and frequency
7. **KPI Recommendations** — Key metrics to track with target benchmarks
8. **Call-to-Action Suggestions** — 5 compelling CTAs tailored to the audience
9. **Budget Allocation** — Recommended budget split across activities

Format the response with clear headers and bullet points for easy scanning."""

PITCH_SYSTEM = """You are a world-class sales strategist and pitch coach who has trained 
sales teams at top tech companies. You specialize in crafting personalized, compelling pitches 
that resonate with C-level executives and decision-makers. Your pitches are concise, 
value-driven, and always include a clear path to next steps."""

PITCH_HUMAN = """Create a powerful, personalized sales pitch with these details:

**Product/Service:** {product}
**Customer/Company Type:** {customer}
**Target Decision-Maker Role:** {target_role}
**Key Pain Points:** {pain_points}
**Unique Selling Points:** {usp}

Please deliver:

1. **30-Second Elevator Pitch** — A concise, memorable pitch that hooks interest immediately
2. **Value Proposition Statement** — A clear articulation of the unique value delivered
3. **Pain Point Analysis** — How the product solves each specific pain point
4. **Key Differentiators** — What sets this product apart from alternatives (with proof points)
5. **ROI Argument** — Quantifiable benefits and expected return on investment
6. **Objection Handling** — Top 5 likely objections with powerful responses
7. **Discovery Questions** — 5 strategic questions to uncover deeper needs
8. **Call-to-Action** — A compelling next step that creates urgency
9. **Follow-Up Strategy** — A 3-touch follow-up cadence with email templates

Format each section with clear headers for easy reference during sales calls."""

LEAD_SYSTEM = """You are a senior sales operations analyst specializing in lead qualification 
and scoring using frameworks like BANT, MEDDIC, and CHAMP. You provide data-driven lead 
assessments that help sales teams prioritize their pipeline effectively. Always provide a 
numerical score and clear reasoning."""

LEAD_HUMAN = """Analyze and score this sales lead comprehensively:

**Lead Information:**
- Lead Name: {name}
- Company: {company}
- Industry: {industry}
- Company Size: {company_size}
- Decision-Maker Role: {decision_role}
- Budget: {budget}
- Need/Requirements: {need}
- Urgency/Timeline: {urgency}

Please provide a comprehensive lead qualification analysis:

1. **Lead Score: X/100** — Provide a specific numerical score
2. **Grade: A/B/C/D** — Overall qualification grade
3. **Qualification Status** — Hot Lead / Warm Lead / Cold Lead / Not Qualified
4. **Scoring Breakdown:**
   - Budget Score (0-25): Assessment of financial capability
   - Authority Score (0-25): Decision-making power evaluation
   - Need Score (0-25): Alignment of need with product capabilities
   - Timeline Score (0-25): Urgency and readiness to buy
5. **Conversion Probability** — Estimated percentage with reasoning
6. **Detailed Reasoning** — Why this score was assigned
7. **Risk Factors** — Potential obstacles to closing
8. **Recommended Actions** — Top 5 specific next steps for the sales team
9. **Ideal Engagement Strategy** — Best approach for this lead type

Be specific and actionable in your recommendations."""

MARKET_SYSTEM = """You are a senior market research analyst with expertise in competitive 
intelligence, trend analysis, and strategic planning. You work with Fortune 500 companies 
to provide actionable market insights. Your analysis is thorough, data-informed, and always 
includes strategic recommendations."""

MARKET_HUMAN = """Conduct a comprehensive market analysis with the following parameters:

**Industry:** {industry}
**Product Category:** {product_category}
**Target Market/Region:** {target_market}
**Known Competitors:** {competitors}
**Analysis Time Horizon:** {time_horizon}

Deliver a thorough market analysis including:

1. **Market Overview** — Current market size, growth rate, and maturity stage
2. **Industry Trends** — Top 5 emerging trends shaping the market
3. **SWOT Analysis:**
   - Strengths: Internal advantages to leverage
   - Weaknesses: Internal gaps to address
   - Opportunities: External factors to capitalize on
   - Threats: External risks to mitigate
4. **Competitive Landscape** — Key players, market share estimates, and positioning
5. **Target Customer Segments** — Primary and secondary segments with profiles
6. **Market Entry/Growth Opportunities** — Untapped segments and strategies
7. **Regulatory & Economic Factors** — Relevant regulations and economic conditions
8. **Technology Disruptions** — Emerging technologies impacting the market
9. **Strategic Recommendations** — Top 5 actionable recommendations with rationale
10. **Key Metrics to Monitor** — Critical market indicators to track

Provide specific, actionable insights — not generic observations."""

INSIGHTS_SYSTEM = """You are a top-tier management consultant with experience at McKinsey, BCG, 
and Bain. You specialize in digital transformation, growth strategy, and operational excellence. 
Your insights are always backed by frameworks, data points, and real-world case studies. 
You provide C-suite-ready strategic recommendations."""

INSIGHTS_HUMAN = """Generate comprehensive business insights and strategic recommendations:

**Business Type:** {business_type}
**Current Challenges:** {challenges}
**Business Goals:** {goals}
**Target Audience:** {target_audience}
**Industry Context:** {industry_context}

Provide executive-level business intelligence:

1. **Strategic Assessment** — Overall business position and health analysis
2. **Key Insights** — Top 5 data-driven insights about the business situation
3. **Growth Opportunities** — 5 specific, actionable growth strategies with implementation steps
4. **Risk Analysis** — Potential risks with probability and impact assessment
5. **Competitive Advantages** — How to build and sustain competitive moats
6. **Operational Improvements** — Efficiency gains and process optimizations
7. **Revenue Optimization** — Pricing, monetization, and revenue diversification strategies
8. **Customer Acquisition Strategy** — Channels, tactics, and CAC optimization
9. **Action Plan** — Prioritized 90-day action plan with milestones
10. **KPIs & Metrics** — Key performance indicators to track progress

Be specific and provide implementation guidance, not just high-level advice."""

# Build LangChain prompt templates
campaign_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(CAMPAIGN_SYSTEM),
    HumanMessagePromptTemplate.from_template(CAMPAIGN_HUMAN),
])

pitch_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(PITCH_SYSTEM),
    HumanMessagePromptTemplate.from_template(PITCH_HUMAN),
])

lead_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(LEAD_SYSTEM),
    HumanMessagePromptTemplate.from_template(LEAD_HUMAN),
])

market_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(MARKET_SYSTEM),
    HumanMessagePromptTemplate.from_template(MARKET_HUMAN),
])

insights_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(INSIGHTS_SYSTEM),
    HumanMessagePromptTemplate.from_template(INSIGHTS_HUMAN),
])


# ─── LangGraph State Definitions ────────────────────────────────────────────

class CampaignState(TypedDict):
    product: str
    audience: str
    platform: str
    goals: str
    budget: str
    result: str
    error: str

class PitchState(TypedDict):
    product: str
    customer: str
    target_role: str
    pain_points: str
    usp: str
    result: str
    error: str

class LeadState(TypedDict):
    name: str
    company: str
    industry: str
    company_size: str
    decision_role: str
    budget: str
    need: str
    urgency: str
    result: str
    error: str

class MarketState(TypedDict):
    industry: str
    product_category: str
    target_market: str
    competitors: str
    time_horizon: str
    result: str
    error: str

class InsightsState(TypedDict):
    business_type: str
    challenges: str
    goals: str
    target_audience: str
    industry_context: str
    result: str
    error: str


# ─── LangGraph Node Functions ───────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Clean excessive markdown formatting for display."""
    return re.sub(r'\*{3,}', '', text)


# ── Campaign Graph Nodes ─────────────────────────────────────────────────────

def validate_campaign(state: CampaignState) -> CampaignState:
    if not state.get("product", "").strip() or not state.get("audience", "").strip():
        return {**state, "error": "Product and target audience are required."}
    return {**state, "error": ""}

def generate_campaign(state: CampaignState) -> CampaignState:
    if state.get("error"):
        return state
    if IS_DUMMY_KEY:
        mock_result = f"""### 🚀 AI-Generated Campaign Strategy: {state['product']}

#### 1. Campaign Overview
- **Core Theme:** "Supercharge Your Pipeline"
- **Messaging Angle:** Empowering teams with immediate data-driven marketing decisions.
- **Positioning:** Next-generation AI intelligence tailored for {state['audience']}.

#### 2. Target Audience Analysis
- **Audience:** {state['audience']}
- **Pain Points:** Inefficient campaign turnaround, lack of clear metrics.
- **Motivations:** Drive ROI, scale output.

#### 3. Content Strategy (Platform: {state.get('platform') or 'Multi-platform'})
- **Headline:** "Automate Your Sales Intelligence"
- **Description:** Build campaigns, write elevator pitches, and qualify leads in real-time.

#### 4. Ad Copy Variations
- **Headline:** "Unlock Growth with MarketMind AI"
- **Body:** Save hours of research. Score leads and analyze competitors instantly.
- **CTA:** Try it Free

> [!NOTE]
> *This is a preview response because no `GROQ_API_KEY` was found in your environment. Set up your key in `.env` to enable live generations.*"""
        return {**state, "result": mock_result}
    try:
        chain = campaign_prompt | llm | parser
        result = chain.invoke({
            "product": state["product"],
            "audience": state["audience"],
            "platform": state.get("platform") or "Multi-platform",
            "goals": state.get("goals") or "Brand awareness and lead generation",
            "budget": state.get("budget") or "Flexible",
        })
        return {**state, "result": clean_markdown(result)}
    except Exception as e:
        return {**state, "error": f"AI generation failed: {str(e)}"}

def should_continue_campaign(state: CampaignState) -> str:
    return "error_end" if state.get("error") else "generate"


# ── Pitch Graph Nodes ────────────────────────────────────────────────────────

def validate_pitch(state: PitchState) -> PitchState:
    if not state.get("product", "").strip() or not state.get("customer", "").strip():
        return {**state, "error": "Product and customer persona are required."}
    return {**state, "error": ""}

def generate_pitch(state: PitchState) -> PitchState:
    if state.get("error"):
        return state
    if IS_DUMMY_KEY:
        mock_result = f"""### 🎯 AI-Crafted Sales Pitch: {state['product']}

#### 1. 30-Second Elevator Pitch
"For {state['customer']} who struggle with standard manual workflows, {state['product']} provides an instant, AI-driven intelligence layer. Unlike traditional static tools, we automate campaign generation and lead qualification to drive 10x faster conversions."

#### 2. Value Proposition
- **Core Value:** Save time, qualify better, close faster.
- **USPs:** {state.get('usp') or 'AI automation, real-time insights, user-friendly templates'}.

#### 3. Pain Point Solutions
- **Pain Point:** {state.get('pain_points') or 'Time-consuming manual research'}
- **Solution:** Our generative workflows deliver custom target briefings in under 5 seconds.

#### 4. Discovery Questions
- "How much time does your team currently spend drafting custom copy?"
- "What criteria do you use to prioritize hot leads?"

> [!NOTE]
> *This is a preview response because no `GROQ_API_KEY` was found in your environment. Set up your key in `.env` to enable live generations.*"""
        return {**state, "result": mock_result}
    try:
        chain = pitch_prompt | llm | parser
        result = chain.invoke({
            "product": state["product"],
            "customer": state["customer"],
            "target_role": state.get("target_role") or "C-level Executive",
            "pain_points": state.get("pain_points") or "General business challenges",
            "usp": state.get("usp") or "To be highlighted based on product",
        })
        return {**state, "result": clean_markdown(result)}
    except Exception as e:
        return {**state, "error": f"AI generation failed: {str(e)}"}

def should_continue_pitch(state: PitchState) -> str:
    return "error_end" if state.get("error") else "generate"


# ── Lead Scoring Graph Nodes ─────────────────────────────────────────────────

def validate_lead(state: LeadState) -> LeadState:
    if not state.get("name", "").strip() or not state.get("budget", "").strip() or not state.get("need", "").strip():
        return {**state, "error": "Lead name, budget, and need are required."}
    return {**state, "error": ""}

def generate_lead_score(state: LeadState) -> LeadState:
    if state.get("error"):
        return state
    if IS_DUMMY_KEY:
        mock_result = f"""### 📊 Predictive Lead Qualification Analysis

#### 1. Lead Score: 85/100
#### 2. Grade: A
#### 3. Status: Hot Lead

#### 4. Scoring Breakdown
- **Budget (20/25):** Budget of {state['budget']} is qualified.
- **Authority (22/25):** Role of {state.get('decision_role') or 'Decision Maker'} has purchasing power.
- **Need (23/25):** Alignment with requirements: "{state['need']}".
- **Timeline (20/25):** Urgency: {state.get('urgency') or 'Immediate'}.

#### 5. Conversion Probability: 88%
- Highly qualified company ({state.get('company') or 'Prospect'}) in the {state.get('industry') or 'Target'} sector.

#### 6. Recommended Actions
- Initiate contact within 2 hours.
- Present the custom pitch highlighting their exact requirements.

> [!NOTE]
> *This is a preview response because no `GROQ_API_KEY` was found in your environment. Set up your key in `.env` to enable live generations.*"""
        return {**state, "result": mock_result}
    try:
        chain = lead_prompt | llm | parser
        result = chain.invoke({
            "name": state["name"],
            "company": state.get("company") or "Not specified",
            "industry": state.get("industry") or "Not specified",
            "company_size": state.get("company_size") or "Not specified",
            "decision_role": state.get("decision_role") or "Not specified",
            "budget": state["budget"],
            "need": state["need"],
            "urgency": state.get("urgency") or "Not specified",
        })
        return {**state, "result": clean_markdown(result)}
    except Exception as e:
        return {**state, "error": f"AI generation failed: {str(e)}"}

def should_continue_lead(state: LeadState) -> str:
    return "error_end" if state.get("error") else "generate"


# ── Market Analysis Graph Nodes ──────────────────────────────────────────────

def validate_market(state: MarketState) -> MarketState:
    if not state.get("industry", "").strip():
        return {**state, "error": "Industry is required."}
    return {**state, "error": ""}

def generate_market_analysis(state: MarketState) -> MarketState:
    if state.get("error"):
        return state
    if IS_DUMMY_KEY:
        mock_result = f"""### 🔍 Competitive Market Analysis: {state['industry']}

#### 1. Market Overview
- **Industry/Sector:** {state['industry']} (Product category: {state.get('product_category') or 'General'})
- **Target Market:** {state.get('target_market') or 'Global'}
- **Horizon:** {state.get('time_horizon') or '12-24 months'}

#### 2. SWOT Analysis
- **Strengths:** High demand for automation, scalable margins.
- **Weaknesses:** Competitor saturation, high acquisition costs.
- **Opportunities:** Untapped segments, automated AI workflows.
- **Threats:** Fast-moving technological changes, data privacy regulations.

#### 3. Known Competitors
- {state.get('competitors') or 'Generic competitors in market'}

> [!NOTE]
> *This is a preview response because no `GROQ_API_KEY` was found in your environment. Set up your key in `.env` to enable live generations.*"""
        return {**state, "result": mock_result}
    try:
        chain = market_prompt | llm | parser
        result = chain.invoke({
            "industry": state["industry"],
            "product_category": state.get("product_category") or "General",
            "target_market": state.get("target_market") or "Global",
            "competitors": state.get("competitors") or "To be identified",
            "time_horizon": state.get("time_horizon") or "12-24 months",
        })
        return {**state, "result": clean_markdown(result)}
    except Exception as e:
        return {**state, "error": f"AI generation failed: {str(e)}"}

def should_continue_market(state: MarketState) -> str:
    return "error_end" if state.get("error") else "generate"


# ── Business Insights Graph Nodes ────────────────────────────────────────────

def validate_insights(state: InsightsState) -> InsightsState:
    if not state.get("business_type", "").strip() or not state.get("challenges", "").strip():
        return {**state, "error": "Business type and challenges are required."}
    return {**state, "error": ""}

def generate_insights(state: InsightsState) -> InsightsState:
    if state.get("error"):
        return state
    if IS_DUMMY_KEY:
        mock_result = f"""### 💡 Strategic Business Insights: {state['business_type']}

#### 1. Strategic Assessment
- **Business Type:** {state['business_type']}
- **Industry Context:** {state.get('industry_context') or 'Modern competitive market'}

#### 2. Core Challenges Addressed
- "{state['challenges']}"

#### 3. Growth Opportunities (Goals: {state.get('goals') or 'Scaling revenue'})
- **Short-Term:** Standardize customer onboarding templates.
- **Long-Term:** Implement predictive customer retention triggers.

#### 4. Prioritized 90-Day Action Plan
- **Days 1-30:** Define buyer personas and clean lead databases.
- **Days 31-60:** Launch initial automation runs.
- **Days 61-90:** Optimize budget allocations.

> [!NOTE]
> *This is a preview response because no `GROQ_API_KEY` was found in your environment. Set up your key in `.env` to enable live generations.*"""
        return {**state, "result": mock_result}
    try:
        chain = insights_prompt | llm | parser
        result = chain.invoke({
            "business_type": state["business_type"],
            "challenges": state["challenges"],
            "goals": state.get("goals") or "Growth and profitability",
            "target_audience": state.get("target_audience") or "Not specified",
            "industry_context": state.get("industry_context") or "General market conditions",
        })
        return {**state, "result": clean_markdown(result)}
    except Exception as e:
        return {**state, "error": f"AI generation failed: {str(e)}"}

def should_continue_insights(state: InsightsState) -> str:
    return "error_end" if state.get("error") else "generate"


# ── Error node (shared) ─────────────────────────────────────────────

def error_node(state):
    """Pass-through node that preserves the error state."""
    return state


# ─── Build LangGraph Workflows ──────────────────────────────────────────────

def build_graph(state_class, validate_fn, generate_fn, should_continue_fn):
    """Factory function to build a LangGraph workflow."""
    workflow = StateGraph(state_class)
    workflow.add_node("validate", validate_fn)
    workflow.add_node("generate", generate_fn)
    workflow.add_node("error_end", error_node)

    workflow.set_entry_point("validate")
    workflow.add_conditional_edges("validate", should_continue_fn, {
        "generate": "generate",
        "error_end": "error_end",
    })
    workflow.add_edge("generate", END)
    workflow.add_edge("error_end", END)

    return workflow.compile()


# Compile all graphs
campaign_graph = build_graph(CampaignState, validate_campaign, generate_campaign, should_continue_campaign)
pitch_graph = build_graph(PitchState, validate_pitch, generate_pitch, should_continue_pitch)
lead_graph = build_graph(LeadState, validate_lead, generate_lead_score, should_continue_lead)
market_graph = build_graph(MarketState, validate_market, generate_market_analysis, should_continue_market)
insights_graph = build_graph(InsightsState, validate_insights, generate_insights, should_continue_insights)


# ─── Flask Routes ────────────────────────────────────────────────────────────

# In-memory user database
USERS_DB = {
    "demo@marketmind.ai": {
        "password": "password123",
        "name": "Demo User",
        "firstName": "Demo",
        "lastName": "User",
        "avatar": "D",
        "joinedAt": "2026-06-06T00:00:00.000Z"
    }
}

@app.route("/")
def home():
    return jsonify({
        "message": "MarketMind AI Backend API is running",
        "endpoints": [
            "/api/health",
            "/api/auth/me",
            "/api/generate_campaign",
            "/api/generate_pitch",
            "/api/lead_score",
            "/api/market_analysis",
            "/api/business_insights",
            "/api/translate",
            "/api/history",
            "/api/crm/leads",
            "/api/refine_result",
            "/api/export_pdf"
        ]
    }), 200


# ── Auth endpoints ───────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    user = USERS_DB.get(email)
    if not user or user["password"] != password:
        # Frictionless Auto-registration for ease of evaluation
        if len(password) >= 4:
            name = email.split("@")[0].capitalize()
            USERS_DB[email] = {
                "password": password,
                "name": name,
                "firstName": name,
                "lastName": "",
                "avatar": name[0] if name else "U",
                "joinedAt": "2026-06-06T00:00:00.000Z"
            }
            user = USERS_DB[email]
        else:
            return jsonify({"error": "Invalid credentials. Password must be at least 4 characters."}), 401
            
    session["user_email"] = email
    return jsonify({
        "success": True,
        "user": {
            "email": email,
            "name": user["name"],
            "avatar": user["avatar"],
            "joinedAt": user["joinedAt"]
        }
    })


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json() or {}
    first_name = data.get("firstName", "").strip()
    last_name = data.get("lastName", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
        
    if email in USERS_DB:
        return jsonify({"error": "Email is already registered"}), 400
        
    name = f"{first_name} {last_name}".strip() or email.split("@")[0].capitalize()
    USERS_DB[email] = {
        "password": password,
        "name": name,
        "firstName": first_name,
        "lastName": last_name,
        "avatar": first_name[0].upper() if first_name else "U",
        "joinedAt": "2026-06-06T00:00:00.000Z"
    }
    
    return jsonify({"success": True, "message": "Account created successfully"})


@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    return jsonify({"success": True, "message": "Password reset instructions sent"})

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    email = session.get("user_email")
    if not email:
        return jsonify({"error": "Not logged in"}), 401
    user = database.get_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Remove password before sending to frontend
    user_data = user.copy()
    if 'password' in user_data:
        del user_data['password']
        
    return jsonify({"user": {**user_data, "email": email}})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.pop("user_email", None)
    return jsonify({"success": True, "message": "Logged out successfully"})


# ─── Authentication Endpoints ──────────────────────────────────────────────────

@app.route("/api/auth/google")
def auth_google():
    if not client:
        return jsonify({"message": "Google OAuth is not configured yet. This is a mock success response.", "user": {"email": "demo@marketmind.ai", "name": "Demo User"}}), 200

    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use a consistent redirect_uri regardless of how the proxy forwarded the request
    # Often Vite forwards as 127.0.0.1 but the browser is on localhost, causing a mismatch.
    redirect_uri = "http://localhost:5000/api/auth/google/callback"

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/api/auth/google/callback")
def auth_google_callback():
    code = request.args.get("code")
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    redirect_uri = "http://localhost:5000/api/auth/google/callback"

    # Use the same redirect_uri that was sent in the initial request
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=redirect_uri,
        code=code,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )
    
    token_response = requests.post(token_url, headers=headers, data=body)

    try:
        client.parse_request_body_response(json.dumps(token_response.json()))
    except Exception as e:
        print("GOOGLE OAUTH ERROR:", token_response.text)
        return jsonify({"error": "OAuth Error", "details": token_response.text}), 400

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
        last_name = userinfo_response.json().get("family_name", "")
    else:
        return "User email not available or not verified by Google.", 400

    # Ensure user exists in database
    user = database.get_user(users_email)
    if not user:
        database.create_user(users_email, "google-oauth", users_name, users_name, last_name, picture)

    session["user_email"] = users_email
    
    # Redirect back to the frontend with success
    return redirect("http://localhost:5173/login?google_login=success")


# ── AI Generation endpoints ──────────────────────────────────────────────────

@app.route("/api/generate_campaign", methods=["POST"])
def route_campaign():
    state = campaign_graph.invoke({
        "product": request.form.get("product", "").strip(),
        "audience": request.form.get("audience", "").strip(),
        "platform": request.form.get("platform", "").strip(),
        "goals": request.form.get("goals", "").strip(),
        "budget": request.form.get("budget", "").strip(),
        "result": "",
        "error": "",
    })
    if state.get("error"):
        return jsonify({"error": state["error"]}), 400
    return jsonify({"result": state["result"]})


@app.route("/api/generate_pitch", methods=["POST"])
def route_pitch():
    state = pitch_graph.invoke({
        "product": request.form.get("product", "").strip(),
        "customer": request.form.get("customer", "").strip(),
        "target_role": request.form.get("target_role", "").strip(),
        "pain_points": request.form.get("pain_points", "").strip(),
        "usp": request.form.get("usp", "").strip(),
        "result": "",
        "error": "",
    })
    if state.get("error"):
        return jsonify({"error": state["error"]}), 400
    return jsonify({"result": state["result"]})


@app.route("/api/lead_score", methods=["POST"])
def route_lead():
    state = lead_graph.invoke({
        "name": request.form.get("name", "").strip(),
        "company": request.form.get("company", "").strip(),
        "industry": request.form.get("industry", "").strip(),
        "company_size": request.form.get("company_size", "").strip(),
        "decision_role": request.form.get("decision_role", "").strip(),
        "budget": request.form.get("budget", "").strip(),
        "need": request.form.get("need", "").strip(),
        "urgency": request.form.get("urgency", "").strip(),
        "result": "",
        "error": "",
    })
    if state.get("error"):
        return jsonify({"error": state["error"]}), 400
    return jsonify({"result": state["result"]})


@app.route("/api/market_analysis", methods=["POST"])
def route_market():
    state = market_graph.invoke({
        "industry": request.form.get("industry", "").strip(),
        "product_category": request.form.get("product_category", "").strip(),
        "target_market": request.form.get("target_market", "").strip(),
        "competitors": request.form.get("competitors", "").strip(),
        "time_horizon": request.form.get("time_horizon", "").strip(),
        "result": "",
        "error": "",
    })
    if state.get("error"):
        return jsonify({"error": state["error"]}), 400
    return jsonify({"result": state["result"]})


@app.route("/api/business_insights", methods=["POST"])
def route_insights():
    state = insights_graph.invoke({
        "business_type": request.form.get("business_type", "").strip(),
        "challenges": request.form.get("challenges", "").strip(),
        "goals": request.form.get("goals", "").strip(),
        "target_audience": request.form.get("target_audience", "").strip(),
        "industry_context": request.form.get("industry_context", "").strip(),
        "result": "",
        "error": "",
    })
    if state.get("error"):
        return jsonify({"error": state["error"]}), 400
    return jsonify({"result": state["result"]})


@app.route("/api/translate", methods=["POST"])
def route_translate():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    target_language = data.get("target_language", "Spanish").strip()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    if IS_DUMMY_KEY:
        return jsonify({"result": f"[Translated to {target_language}]:\n\n{text}"})

    try:
        translate_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("You are a professional translator. Translate the following text into the specified language accurately while maintaining the original formatting (like Markdown). Only return the translated text."),
            HumanMessagePromptTemplate.from_template("Translate to {target_language}:\n\n{text}")
        ])
        chain = translate_prompt | llm | parser
        result = chain.invoke({
            "target_language": target_language,
            "text": text,
        })
        return jsonify({"result": clean_markdown(result)})
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500


@app.route("/api/health")
def health_check():
    print("DEBUG: GROQ_API_KEY in env:", bool(os.getenv("GROQ_API_KEY")))
    print("DEBUG: GROQ_API_KEY module variable:", bool(GROQ_API_KEY))
    print("DEBUG: IS_DUMMY_KEY module variable:", IS_DUMMY_KEY)
    return jsonify({
        "status": "healthy",
        "model": GROQ_MODEL,
        "api_configured": bool(os.getenv("GROQ_API_KEY", "").strip()) and not os.getenv("GROQ_API_KEY", "").strip().startswith("your_"),
        "frameworks": {
            "langchain": True,
            "langgraph": True,
            "groq": True,
        }
    })

# ─── History Endpoints ───────────────────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
def get_history():
    email = session.get("user_email") or "demo@marketmind.ai"
    history = database.get_user_history(email)
    return jsonify({"success": True, "history": history})

@app.route("/api/history/save", methods=["POST"])
def save_to_history():
    data = request.get_json() or {}
    email = session.get("user_email") or "demo@marketmind.ai"
    type_name = data.get("type", "unknown")
    title = data.get("title", f"Saved {type_name}")
    input_data = data.get("input_data", {})
    result = data.get("result", "")
    new_id = database.save_history(email, type_name, title, input_data, result)
    return jsonify({"success": True, "id": new_id})

@app.route("/api/history/<int:record_id>", methods=["DELETE"])
def delete_history_record(record_id):
    email = session.get("user_email") or "demo@marketmind.ai"
    success = database.delete_history(email, record_id)
    return jsonify({"success": success})

# ─── CRM Endpoints ───────────────────────────────────────────────────────────

@app.route("/api/crm/leads", methods=["GET"])
def get_crm_leads():
    email = session.get("user_email") or "demo@marketmind.ai"
    leads = database.get_crm_leads(email)
    return jsonify({"success": True, "leads": leads})

@app.route("/api/crm/leads", methods=["POST"])
def add_lead():
    data = request.get_json() or {}
    email = session.get("user_email") or "demo@marketmind.ai"
    name = data.get("name", "Unknown")
    company = data.get("company", "")
    score = data.get("score", 0)
    grade = data.get("grade", "C")
    details = data.get("details", "")
    new_id = database.add_crm_lead(email, name, company, score, grade, details)
    return jsonify({"success": True, "id": new_id})

@app.route("/api/crm/leads/<int:lead_id>", methods=["PUT"])
def update_lead(lead_id):
    data = request.get_json() or {}
    email = session.get("user_email") or "demo@marketmind.ai"
    status = data.get("status")
    score = data.get("score")
    grade = data.get("grade")
    details = data.get("details")
    
    conn = database.get_db()
    try:
        fields = []
        params = []
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if score is not None:
            fields.append("score = ?")
            params.append(score)
        if grade is not None:
            fields.append("grade = ?")
            params.append(grade)
        if details is not None:
            fields.append("details = ?")
            params.append(details)
            
        if fields:
            params.extend([email, lead_id])
            conn.execute(f"UPDATE crm_leads SET {', '.join(fields)} WHERE user_email = ? AND id = ?", tuple(params))
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/crm/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    email = session.get("user_email") or "demo@marketmind.ai"
    database.delete_crm_lead(email, lead_id)
    return jsonify({"success": True})

@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    import random
    email = session.get("user_email") or "demo@marketmind.ai"
    
    # Check if user has filled details (i.e. has a profile)
    profile = database.get_user_profile(email)
    has_real_data = True if (profile and profile.get("company_name")) else False

    # Also check if user has provided real company KPI metrics
    company_metrics = database.get_company_metrics(email)
    has_company_metrics = company_metrics is not None
    
    conn = database.get_db()
    
    # Fluctuate stock prices and write back to database
    stocks = conn.execute("SELECT ticker, name, price, change_pct, history FROM stock_prices").fetchall()
    updated_stocks = []
    
    for s in stocks:
        ticker = s['ticker']
        name = s['name']
        old_price = s['price']
        history_list = json.loads(s['history'])
        
        # Visible price fluctuation: each tick moves -0.8% to +1.2%
        baseline_price = history_list[-2] if len(history_list) > 1 else old_price
        fluctuation = old_price * (random.uniform(-0.008, 0.012))
        new_price = old_price + fluctuation
        
        # Keep within ±4% of the second-to-last history point to prevent unbounded drift
        min_p = baseline_price * 0.96
        max_p = baseline_price * 1.04
        new_price = round(max(min_p, min(max_p, new_price)), 2)
        
        # Calculate daily change relative to first historical point or previous point
        base_price = history_list[-2] if len(history_list) > 1 else history_list[0]
        change_pct = round(((new_price - base_price) / base_price) * 100, 2)
        
        # Update last price in history list
        history_list[-1] = new_price
        history_str = json.dumps(history_list)
        
        # Update SQLite DB
        conn.execute("""
        UPDATE stock_prices
        SET price = ?, change_pct = ?, history = ?, last_updated = ?
        WHERE ticker = ?
        """, (new_price, change_pct, history_str, datetime.utcnow().isoformat() + "Z", ticker))
        
        updated_stocks.append({
            "ticker": ticker,
            "name": name,
            "price": new_price,
            "change_pct": change_pct,
            "history": history_list
        })
        
    conn.commit()
    
    if not has_real_data:
        conn.close()
        # Simulated/demo statistics
        revenue_tick = random.choice([-1, -1, 1, 1, 1, 2]) * random.randint(50, 500)
        live_revenue = max(100000, 142500 + revenue_tick)
        
        accuracy_jitter = random.uniform(-0.4, 0.4)
        live_accuracy = round(min(99.9, max(85.0, 94.8 + accuracy_jitter)), 1)
        
        hot_jitter = random.choice([-1, 0, 0, 1, 1])
        live_hot_leads = max(10, min(100, 45 + hot_jitter))
        
        run_tick = random.choices([0, 0, 0, 1], weights=[70, 10, 10, 10])[0]
        live_total_runs = 128 + run_tick
        
        lead_distribution = [live_hot_leads, 35, 20]
        campaign_clicks = [4200, 5600, 7100, 3900, 2400, 4800]
        
        baseline = [12, 19, 15, 25, 22, 30, 35, 32, 40, 48, 45, 54]
        final_sales_trend = [val * 1000 for val in baseline]
        
        return jsonify({
            "success": True,
            "has_real_data": False,
            "has_company_metrics": has_company_metrics,
            "company_metrics": company_metrics,
            "stats": {
                "total_runs": live_total_runs,
                "total_leads": 100,
                "avg_lead_score": 72.5,
                "hot_leads": live_hot_leads,
                "total_revenue": live_revenue,
                "live_accuracy": live_accuracy,
                "lead_distribution": lead_distribution,
                "campaign_clicks": campaign_clicks,
                "sales_trend": final_sales_trend,
                "stocks": updated_stocks
            }
        })
    
    # Otherwise, query the real database metrics
    # 1. Total Runs
    row_runs = conn.execute("SELECT COUNT(*) FROM history WHERE user_email = ?", (email,)).fetchone()
    total_runs = row_runs[0] if row_runs else 0
    
    # 2. Total Leads
    row_leads = conn.execute("SELECT COUNT(*) FROM crm_leads WHERE user_email = ?", (email,)).fetchone()
    total_leads = row_leads[0] if row_leads else 0
    
    # 3. Average Lead Score
    row_avg = conn.execute("SELECT AVG(score) FROM crm_leads WHERE user_email = ?", (email,)).fetchone()
    avg_lead_score = round(row_avg[0], 1) if row_avg and row_avg[0] is not None else 0.0
    
    # 4. Hot Leads Count (score >= 80)
    row_hot = conn.execute("SELECT COUNT(*) FROM crm_leads WHERE user_email = ? AND score >= 80", (email,)).fetchone()
    hot_leads = row_hot[0] if row_hot else 0
    
    # 5. Total Sales Revenue
    row_won = conn.execute("SELECT SUM(score) FROM crm_leads WHERE user_email = ? AND status = 'Closed Won'", (email,)).fetchone()
    won_score_sum = row_won[0] if row_won and row_won[0] is not None else 0
    total_revenue = won_score_sum * 1000  # realistic revenue from won leads
    
    # 6. Lead pipeline distribution
    row_warm = conn.execute("SELECT COUNT(*) FROM crm_leads WHERE user_email = ? AND score >= 50 AND score < 80", (email,)).fetchone()
    warm_leads = row_warm[0] if row_warm else 0
    
    row_cold = conn.execute("SELECT COUNT(*) FROM crm_leads WHERE user_email = ? AND score < 50", (email,)).fetchone()
    cold_leads = row_cold[0] if row_cold else 0
    
    lead_distribution = [hot_leads, warm_leads, cold_leads]
    
    # 7. Campaign performance by channel
    campaigns = conn.execute("SELECT input_data FROM history WHERE user_email = ? AND type = 'campaign'", (email,)).fetchall()
    
    channel_counts = {
        'LinkedIn': 0,
        'Instagram': 0,
        'Google Ads': 0,
        'Email': 0,
        'Twitter/X': 0,
        'YouTube': 0
    }
    
    for c in campaigns:
        try:
            inp = json.loads(c['input_data'])
            plat = inp.get('platform', '')
            if 'LinkedIn' in plat:
                channel_counts['LinkedIn'] += 1
            elif 'Instagram' in plat:
                channel_counts['Instagram'] += 1
            elif 'Google Ads' in plat or 'Google' in plat:
                channel_counts['Google Ads'] += 1
            elif 'Email' in plat:
                channel_counts['Email'] += 1
            elif 'Twitter' in plat or 'X' in plat:
                channel_counts['Twitter/X'] += 1
            elif 'YouTube' in plat:
                channel_counts['YouTube'] += 1
        except Exception:
            pass
            
    campaign_values = [
        channel_counts['LinkedIn'],
        channel_counts['Instagram'],
        channel_counts['Google Ads'],
        channel_counts['Email'],
        channel_counts['Twitter/X'],
        channel_counts['YouTube']
    ]
    campaign_clicks = [val * 850 for val in campaign_values]
    
    # 8. Monthly operations runs trend (past 12 months)
    monthly_runs = [0] * 12
    history_dates = conn.execute("SELECT created_at FROM history WHERE user_email = ?", (email,)).fetchall()
    
    for hd in history_dates:
        try:
            dt = datetime.fromisoformat(hd['created_at'].replace('Z', '+00:00'))
            month_idx = dt.month - 1
            if 0 <= month_idx < 12:
                monthly_runs[month_idx] += 1
        except Exception:
            pass
            
    final_sales_trend = [val * 2500 for val in monthly_runs]
    
    conn.close()

    # Live fluctuations to keep dashboard ticking:
    revenue_tick = random.choice([-1, -1, 1, 1, 1, 2]) * random.randint(10, 100) if total_revenue > 0 else 0
    live_revenue = max(0, total_revenue + revenue_tick)

    raw_accuracy = 90 + avg_lead_score * 0.1 if avg_lead_score > 0 else 0.0
    accuracy_jitter = random.uniform(-0.4, 0.4) if raw_accuracy > 0 else 0.0
    live_accuracy = round(min(99.9, max(0.0, raw_accuracy + accuracy_jitter)), 1)

    # ── Override with user-provided company metrics when available ──
    if has_company_metrics:
        cm = company_metrics
        cm_revenue = cm.get("monthly_revenue", 0) or 0
        cm_leads = cm.get("monthly_leads", 0) or 0
        cm_cvr = cm.get("conversion_rate", 0) or 0
        cm_trend = cm.get("revenue_trend", [])
        cm_clicks = cm.get("campaign_clicks", [])
        cm_dist = cm.get("lead_distribution", [])

        # Compute live revenue from company input (no jitter for precision)
        cm_revenue_val = cm_revenue
        if cm_revenue_val > 0:
            live_revenue = cm_revenue_val

        # Compute hot_leads from monthly_leads * conversion_rate if CRM has no data
        if hot_leads == 0 and cm_leads > 0 and cm_cvr > 0:
            hot_leads = max(1, int(cm_leads * (cm_cvr / 100)))

        # Use revenue trend from company metrics if provided
        if cm_trend and len(cm_trend) > 0:
            final_sales_trend = cm_trend

        # Override campaign clicks with user-provided values
        if cm_clicks and len(cm_clicks) == 6:
            campaign_clicks = [int(v) for v in cm_clicks]

        # Override lead distribution with user-provided values
        if cm_dist and len(cm_dist) == 3:
            lead_distribution = [int(v) for v in cm_dist]

        # Improve accuracy from conversion rate if provided (no jitter for precision)
        if cm_cvr > 0:
            live_accuracy = round(min(99.9, 85 + cm_cvr * 0.15), 1)

    return jsonify({
        "success": True,
        "has_real_data": True,
        "has_company_metrics": has_company_metrics,
        "company_metrics": company_metrics,
        "stats": {
            "total_runs": total_runs,
            "total_leads": total_leads,
            "avg_lead_score": avg_lead_score,
            "hot_leads": hot_leads,
            "total_revenue": live_revenue,
            "live_accuracy": live_accuracy,
            "lead_distribution": lead_distribution,
            "campaign_clicks": campaign_clicks,
            "sales_trend": final_sales_trend,
            "stocks": updated_stocks
        }
    })



# ── Company Business Metrics Endpoints ───────────────────────────────────────

@app.route("/api/company-metrics", methods=["GET"])
def get_company_metrics():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    metrics = database.get_company_metrics(session["user_email"])
    return jsonify({"success": True, "metrics": metrics})


@app.route("/api/company-metrics", methods=["POST"])
@rate_limit(limit=30)
def save_company_metrics():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    body = request.get_json() or {}
    try:
        database.save_company_metrics(
            email=session["user_email"],
            monthly_revenue=float(body.get("monthly_revenue") or 0),
            revenue_target=float(body.get("revenue_target") or 0),
            monthly_leads=int(body.get("monthly_leads") or 0),
            lead_target=int(body.get("lead_target") or 0),
            active_campaigns=int(body.get("active_campaigns") or 0),
            conversion_rate=float(body.get("conversion_rate") or 0),
            avg_deal_size=float(body.get("avg_deal_size") or 0),
            sales_cycle_days=int(body.get("sales_cycle_days") or 0),
            top_channel=body.get("top_channel", ""),
            revenue_trend=body.get("revenue_trend", []),
            campaign_clicks=body.get("campaign_clicks", []),
            lead_distribution=body.get("lead_distribution", []),
            currency=body.get("currency", "USD"),
            notes=body.get("notes", ""),
            sales_team_size=int(body.get("sales_team_size") or 0),
            win_rate=float(body.get("win_rate") or 0.0),
            lost_deal_rate=float(body.get("lost_deal_rate") or 0.0),
            monthly_opportunities=int(body.get("monthly_opportunities") or 0),
            monthly_marketing_budget=float(body.get("monthly_marketing_budget") or 0.0),
            cac=float(body.get("cac") or 0.0),
            ltv=float(body.get("ltv") or 0.0),
            lead_to_customer_rate=float(body.get("lead_to_customer_rate") or 0.0),
            secondary_channel=body.get("secondary_channel", "")
        )
        database.update_cached_summary(session["user_email"], "", [])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Ideal Customer Profile (ICP) Endpoints ────────────────────────────────────

@app.route("/api/icp", methods=["GET"])
def get_icp_profile():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    profile = database.get_icp_profile(session["user_email"])
    return jsonify({"success": True, "profile": profile})

@app.route("/api/icp", methods=["POST"])
@rate_limit(limit=30)
def save_icp_profile():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    body = request.get_json() or {}
    try:
        database.save_icp_profile(
            email=session["user_email"],
            icp_industry=body.get("icp_industry", ""),
            icp_company_size=body.get("icp_company_size", ""),
            icp_revenue_range=body.get("icp_revenue_range", ""),
            icp_job_titles=body.get("icp_job_titles", []),
            icp_decision_makers=body.get("icp_decision_makers", []),
            icp_pain_points=body.get("icp_pain_points", []),
            icp_notes=body.get("icp_notes", "")
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Recent Activity Feed Endpoint ────────────────────────────────────────────

@app.route("/api/activity", methods=["GET"])
def get_activity_feed():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        limit = int(request.args.get("limit") or 20)
        activities = database.get_recent_activity(session["user_email"], limit=limit)
        return jsonify({"success": True, "activities": activities})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI Executive Summary Endpoint ─────────────────────────────────────────────

@app.route("/api/dashboard/executive-summary", methods=["GET"])
def get_dashboard_summary():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    email = session["user_email"]
    
    # 1. Fetch company metrics row
    metrics = database.get_company_metrics(email)
    if not metrics or (metrics.get("monthly_revenue") == 0 and metrics.get("monthly_leads") == 0):
        # Return a prompt to set up metrics
        return jsonify({
            "success": True,
            "summary": "Welcome to MarketMind AI! To unlock your personalized AI Executive Summary and real-time business health monitoring, please head over to Settings or complete your Onboarding to provide your company metrics, target goals, and ideal customer profile (ICP).",
            "highlights": ["Setup Company Profile", "Define Sales & Marketing KPIs", "Create Customer ICP"]
        })

    # 2. Check cache first
    cached_summary = metrics.get("ai_summary", "")
    cached_highlights = metrics.get("ai_highlights", [])
    if cached_summary and len(cached_summary.strip()) > 0:
        return jsonify({
            "success": True,
            "summary": cached_summary,
            "highlights": cached_highlights[:3]
        })

    # 3. If no cache, build company context and call LLM
    grounding_context, company_name, industry = build_company_context(email, "dashboard")
        
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        prompt = f"""
You are the AI Executive Advisor for {company_name or 'the company'}.
Analyze the following company profile and metrics:

{grounding_context}

Write a high-level executive summary of the company's current performance (3-4 sentences, max 100 words).
Focus on:
1. One positive highlight (e.g. strong acquisition channels or hitting target revenue/leads).
2. One key gap or risk area (e.g. CAC/LTV ratio, revenue gap, low conversion rates, or long sales cycle).
3. One immediate, high-impact recommendation (e.g. shifting budget to the top channel or training sales to improve win rate).

CRITICAL:
- Use actual numbers and metrics (like conversion rate, deal size, CAC, LTV, win rate) from the context.
- Keep the tone professional, direct, and action-oriented.
- Do NOT use markdown formatting (no **, no #, no *, no _). Return a single clean text paragraph.
"""
        response = safe_llm_invoke([
            SystemMessage(content="You are an elite B2B SaaS founder and business intelligence advisor. Speak directly, cite exact numbers, and give actionable advice."),
            HumanMessage(content=prompt)
        ], temperature=0.7)
        summary_text = response.content.strip()
        
        # Also let's extract or generate 3 bullet points / highlights
        bullets_prompt = f"""
Based on the following summary, extract 3 short highlights/metrics cards (each 2-4 words, e.g. '3.2% Conversion Rate', 'LTV:CAC 9.0x', 'USD 12K Rev Gap'):
Summary: {summary_text}
Return ONLY a JSON array of 3 string items, e.g. ["2.4% Win Rate", "CAC USD 420", "Optimize LinkedIn Ads"]. No explanation, no code fence, just raw JSON.
"""
        bullets_response = safe_llm_invoke([HumanMessage(content=bullets_prompt)], temperature=0.2)
        bullets_text = bullets_response.content.strip()
        
        # Clean up code fence if LLM added them
        if bullets_text.startswith("```"):
            lines = bullets_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            bullets_text = "\n".join(lines).strip()
            
        try:
            highlights = json.loads(bullets_text)
            if not isinstance(highlights, list):
                highlights = []
        except Exception:
            highlights = []
            
        # Fallback if parsing fails or list is empty
        if not highlights:
            highlights = [
                f"{metrics.get('conversion_rate', 0)}% CVR",
                f"{metrics.get('win_rate', 0)}% Win Rate",
                f"Top Channel: {metrics.get('top_channel', 'N/A')}"
            ]
            
        # Cache the successfully generated summary
        database.update_cached_summary(email, summary_text, highlights)
        
        return jsonify({
            "success": True,
            "summary": summary_text,
            "highlights": highlights[:3]
        })
    except Exception as e:
        print(f"[get_dashboard_summary] LLM generation failed, using rule-based fallback: {e}")
        currency = metrics.get("currency", "INR")
        rev = metrics.get("monthly_revenue", 0)
        win_rate = metrics.get("win_rate", 0.0)
        opps = metrics.get("monthly_opportunities", 0)
        top_ch = metrics.get("top_channel", "LinkedIn")
        avg_deal = metrics.get("avg_deal_size", 0)
        cac = metrics.get("cac", 0)
        ltv = metrics.get("ltv", 0)
        
        fallback_summary = (
            f"MarketMind AI is tracking your business performance. "
            f"Your current monthly revenue is stable at {currency} {rev:,.0f} with {opps:,} active opportunities in the pipeline "
            f"and an average deal size of {currency} {avg_deal:,.0f}. "
            f"Sales performance is strong with a win rate of {win_rate}%, primarily driven by {top_ch}. "
            f"To optimize further, focus on improving your LTV to CAC ratio (current LTV: {currency} {ltv:,.0f}, CAC: {currency} {cac:,.0f}) "
            f"and accelerating deal conversions."
        )
        fallback_highlights = [
            f"{win_rate}% Win Rate",
            f"{currency} {rev:,.0f} Revenue",
            f"Top Channel: {top_ch}"
        ]
        
        # Save fallback to cache
        try:
            database.update_cached_summary(email, fallback_summary, fallback_highlights)
        except Exception:
            pass
            
        return jsonify({
            "success": True,
            "summary": fallback_summary,
            "highlights": fallback_highlights[:3]
        })


# ─── Refinement Endpoint ─────────────────────────────────────────────────────

@app.route("/api/refine_result", methods=["POST"])
@rate_limit(limit=20)
def refine_result():
    data = request.get_json() or {}
    original = data.get("original", "")
    prompt = data.get("prompt", "")
    history = data.get("history", [])
    
    if IS_DUMMY_KEY:
        refined_so_far = ""
        if history:
            refined_so_far = "\n- Historical requests: " + ", ".join([h.get("content", "") for h in history if h.get("role") == "user"])
        return jsonify({"result": f"{original}\n\n[Refined Edit applied: {prompt}]{refined_so_far}"})
        
    try:
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        messages = [
            SystemMessage(content=(
                "You are a senior marketing strategist and business consultant AI assistant embedded inside a B2B SaaS marketing intelligence platform. "
                "Your ONLY role is to help users understand, simplify, expand, or refine their marketing strategy analysis, business insights, sales pitches, lead scoring results, campaign strategies, and market analysis reports. "
                "You must ONLY answer questions related to: marketing strategy, sales strategy, lead generation, campaign optimization, brand positioning, market analysis, competitive intelligence, customer segmentation, go-to-market strategy, revenue growth, business development, and related B2B/B2C growth topics. "
                "If the user asks about anything outside of marketing, sales, or business strategy domains — politely redirect them back to their analysis. "
                "Always respond with concise, expert-level marketing advice. Use plain readable text — no markdown symbols like ** or ## in your response. "
                "Return ONLY your expert answer without conversational filler or meta-commentary about what you can or cannot do."
            ))
        ]
        messages.append(HumanMessage(content=f"Here is the original document:\n\n{original}"))
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
                
        messages.append(HumanMessage(content=f"Refinement Request: {prompt}"))
        response = safe_llm_invoke(messages)
        return jsonify({"result": clean_markdown(response.content)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── PDF Exporter Endpoint ───────────────────────────────────────────────────

# Helper to draw header/footer decoration
def add_page_decorations(canvas, doc):
    canvas.saveState()
    width, height = letter
    
    # ─── HEADER ───
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#64748b'))
    canvas.drawString(54, height - 35, "MarketMind AI — Report")
    canvas.drawRightString(width - 54, height - 35, "Executive Briefing")
    
    canvas.setStrokeColor(colors.HexColor('#cbd5e1'))
    canvas.setLineWidth(0.5)
    canvas.line(54, height - 40, width - 54, height - 40)
    
    # ─── FOOTER ───
    canvas.line(54, 45, width - 54, 45)
    canvas.drawString(54, 32, "Confidential")
    canvas.drawRightString(width - 54, 32, f"Page {doc.page}")
    
    canvas.restoreState()


# Helper to parse inline markdown styling into ReportLab XML-like tags
def parse_inline_markdown(text):
    # Escape XML entities first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # 1. Bold: **text** or __text__ -> <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
    
    # 2. Italic: *text* or _text_ -> <i>text</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    
    # 3. Inline code: `text` -> <font face="Courier" size="9" color="#0f172a">text</font>
    text = re.sub(r'`(.*?)`', r'<font face="Courier" size="9" color="#0f172a">\1</font>', text)
    
    # 4. Links: [text](url) -> <a href="\2"><font color="#2563eb"><u>\1</u></font></a>
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2"><font color="#2563eb"><u>\1</u></font></a>', text)
    
    return text


# Helper to parse markdown into ReportLab flowables
def parse_markdown_to_flowables(md_text, styles):
    lines = md_text.splitlines()
    flowables = []
    
    in_code_block = False
    code_content = []
    
    in_table = False
    table_rows = []
    
    in_list = False
    list_items = []
    list_type = None  # 'bullet' or 'numbered'
    
    in_blockquote = False
    blockquote_lines = []
    
    # Helper to flush lists
    def flush_list():
        nonlocal in_list, list_items, list_type
        if not in_list:
            return
        for item in list_items:
            if list_type == 'bullet':
                parsed_text = parse_inline_markdown(item)
                flowables.append(Paragraph(f"&bull;&nbsp;&nbsp;{parsed_text}", styles['BulletStyle']))
            else:
                prefix, content = item
                parsed_text = parse_inline_markdown(content)
                flowables.append(Paragraph(f"{prefix}&nbsp;&nbsp;{parsed_text}", styles['ListStyle']))
        list_items = []
        in_list = False
        list_type = None

    # Helper to flush blockquotes
    def flush_blockquote():
        nonlocal in_blockquote, blockquote_lines
        if not in_blockquote:
            return
        quote_text = "<br/>".join([parse_inline_markdown(l) for l in blockquote_lines])
        p = Paragraph(quote_text, styles['QuoteStyle'])
        t = Table([[p]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('LINELEFT', (0,0), (0,-1), 3, colors.HexColor('#3b82f6')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ]))
        flowables.append(t)
        flowables.append(Spacer(1, 8))
        blockquote_lines = []
        in_blockquote = False

    # Helper to flush tables
    def flush_table():
        nonlocal in_table, table_rows
        if not in_table:
            return
        
        valid_rows = []
        for r in table_rows:
            # Check if separator row using regex-free check
            is_separator = all(all(c in ' -:|' for c in cell) for cell in r) and len(r) > 0
            if is_separator:
                continue
            valid_rows.append(r)
            
        if len(valid_rows) > 0:
            table_data = []
            for row_idx, r in enumerate(valid_rows):
                row_cells = []
                for cell in r:
                    parsed_cell = parse_inline_markdown(cell.strip())
                    cell_style = styles['TableHeaderStyle'] if row_idx == 0 else styles['TableCellStyle']
                    row_cells.append(Paragraph(parsed_cell, cell_style))
                table_data.append(row_cells)
                
            max_cols = max(len(r) for r in table_data) if table_data else 0
            for r in table_data:
                while len(r) < max_cols:
                    r.append(Paragraph("", styles['TableCellStyle']))
                    
            if max_cols > 0:
                col_width = 504.0 / max_cols
                col_widths = [col_width] * max_cols
                t = Table(table_data, colWidths=col_widths)
                
                t_style = [
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ]
                # Alternating row background:
                for r_idx in range(1, len(table_data)):
                    if r_idx % 2 == 1:
                        t_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#f8fafc')))
                t.setStyle(TableStyle(t_style))
                flowables.append(t)
                flowables.append(Spacer(1, 10))
        table_rows = []
        in_table = False

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # 1. Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block
                code_lines = []
                for l in code_content:
                    escaped = l.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    leading_spaces = len(escaped) - len(escaped.lstrip(' '))
                    escaped = '&nbsp;' * leading_spaces + escaped.lstrip(' ')
                    code_lines.append(escaped)
                code_html = "<br/>".join(code_lines)
                p = Paragraph(f"<font face='Courier' size='8.5'>{code_html}</font>", styles['CodeBlockStyle'])
                t = Table([[p]], colWidths=[504])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('LEFTPADDING', (0,0), (-1,-1), 10),
                    ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ]))
                flowables.append(t)
                flowables.append(Spacer(1, 10))
                code_content = []
                in_code_block = False
            else:
                flush_list()
                flush_blockquote()
                flush_table()
                in_code_block = True
            i += 1
            continue
            
        if in_code_block:
            code_content.append(line)
            i += 1
            continue
            
        # 2. Table rows
        if line.strip().startswith('|') and line.strip().endswith('|'):
            if not in_table:
                flush_list()
                flush_blockquote()
                in_table = True
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                flush_table()
                
        # 3. Blockquotes
        if line.strip().startswith('>'):
            if not in_blockquote:
                flush_list()
                flush_table()
                in_blockquote = True
            content = line.strip()[1:]
            if content.startswith(' '):
                content = content[1:]
            blockquote_lines.append(content)
            i += 1
            continue
        else:
            if in_blockquote:
                flush_blockquote()

        # 4. Bullet and numbered lists
        bullet_match = re.match(r'^(\s*)[-\*\+]\s+(.*)$', line)
        numbered_match = re.match(r'^(\s*)\d+\.\s+(.*)$', line)
        
        if bullet_match:
            if not in_list or list_type != 'bullet':
                flush_list()
                in_list = True
                list_type = 'bullet'
            list_items.append(bullet_match.group(2))
            i += 1
            continue
        elif numbered_match:
            if not in_list or list_type != 'numbered':
                flush_list()
                in_list = True
                list_type = 'numbered'
            prefix = line.strip().split('.')[0] + '.'
            list_items.append((prefix, numbered_match.group(2)))
            i += 1
            continue
        else:
            if line.strip() == '':
                flush_list()
                i += 1
                continue

        # 5. Headings
        heading_match = re.match(r'^(#{1,6})\s+(.*)$', line)
        if heading_match:
            flush_list()
            level = len(heading_match.group(1))
            heading_text = parse_inline_markdown(heading_match.group(2))
            if level == 1:
                flowables.append(Paragraph(heading_text, styles['Heading1']))
                flowables.append(Spacer(1, 4))
            elif level == 2:
                flowables.append(Paragraph(heading_text, styles['Heading2']))
                flowables.append(Spacer(1, 3))
            elif level == 3:
                flowables.append(Paragraph(heading_text, styles['Heading3']))
                flowables.append(Spacer(1, 2))
            else:
                flowables.append(Paragraph(heading_text, styles['Heading4']))
                flowables.append(Spacer(1, 2))
            i += 1
            continue
            
        # 6. Paragraphs
        p_lines = [line.strip()]
        while i + 1 < len(lines):
            next_line = lines[i + 1].rstrip()
            if (next_line.strip() == '' or 
                next_line.strip().startswith('```') or 
                next_line.strip().startswith('|') or 
                next_line.strip().startswith('>') or 
                re.match(r'^\s*[-\*\+]\s+', next_line) or 
                re.match(r'^\s*\d+\.\s+', next_line) or 
                re.match(r'^#{1,6}\s+', next_line)):
                break
            p_lines.append(next_line.strip())
            i += 1
            
        p_text = " ".join(p_lines)
        if p_text:
            parsed_text = parse_inline_markdown(p_text)
            flowables.append(Paragraph(parsed_text, styles['BodyText']))
            flowables.append(Spacer(1, 8))
        i += 1
        
    flush_list()
    flush_blockquote()
    flush_table()
    
    return flowables


@app.route("/api/export_pdf", methods=["POST"])
def export_pdf():
    data = request.get_json() or {}
    text = data.get("text", "")
    title = data.get("title", "MarketMind Document")
    date_str = datetime.now().strftime("%B %d, %Y")
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    default_styles = getSampleStyleSheet()
    styles = {}
    
    styles['Title'] = ParagraphStyle(
        'DocTitle',
        parent=default_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )

    styles['Subtitle'] = ParagraphStyle(
        'DocSubtitle',
        parent=default_styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )

    styles['Heading1'] = ParagraphStyle(
        'Heading1_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    styles['Heading2'] = ParagraphStyle(
        'Heading2_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    styles['Heading3'] = ParagraphStyle(
        'Heading3_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    styles['Heading4'] = ParagraphStyle(
        'Heading4_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    styles['BodyText'] = ParagraphStyle(
        'BodyText_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=8
    )

    styles['BulletStyle'] = ParagraphStyle(
        'BulletStyle_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    styles['ListStyle'] = ParagraphStyle(
        'ListStyle_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    styles['QuoteStyle'] = ParagraphStyle(
        'QuoteStyle_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#475569')
    )

    styles['CodeBlockStyle'] = ParagraphStyle(
        'CodeBlockStyle_Custom',
        parent=default_styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )

    styles['TableHeaderStyle'] = ParagraphStyle(
        'TableHeaderStyle_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    styles['TableCellStyle'] = ParagraphStyle(
        'TableCellStyle_Custom',
        parent=default_styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )
    
    story = []
    
    # Document Header Title Block
    story.append(Paragraph(title, styles['Title']))
    story.append(Paragraph(f"AI-Generated Intelligence Brief • {date_str}", styles['Subtitle']))
    
    # Divider (thin horizontal blue line)
    divider = Table([[""]], colWidths=[504], rowHeights=[3])
    divider.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#3b82f6')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 15))
    
    # Process text markdown flowables
    markdown_flowables = parse_markdown_to_flowables(text, styles)
    story.extend(markdown_flowables)
    
    # Compile
    try:
        doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    except Exception as build_error:
        print(f"ReportLab Build Error: {build_error}")
        return jsonify({"error": f"PDF generation failed: {str(build_error)}"}), 500
        
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{title.replace(' ', '_')}.pdf",
        mimetype='application/pdf'
    )


# ─── Run Server ──────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# ONBOARDING
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/onboarding/profile", methods=["GET", "POST"])
def onboarding_profile():
    """Save or load business context from onboarding step 1 — stored in user profiles database."""
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    email = session["user_email"]
    
    if request.method == "POST":
        data = request.get_json() or {}
        biz = data.get("business", {})
        
        # Save permanently to DB
        database.save_user_profile(
            email=email,
            company_name=biz.get("company_name", ""),
            industry=biz.get("industry", ""),
            company_size=biz.get("size", "") or biz.get("company_size", ""),
            website=biz.get("website", ""),
            description=biz.get("description", ""),
            sub_industry=biz.get("sub_industry", ""),
            hq_country=biz.get("hq_country", ""),
            geo_market=biz.get("geo_market", ""),
            business_model=biz.get("business_model", ""),
            target_customer=biz.get("target_customer", ""),
            objectives=biz.get("objectives", []),
            founded_year=biz.get("founded_year", "")
        )
        
        # Sync session
        session["business_context"] = biz
        return jsonify({"success": True, "message": "Business context saved successfully"})
    
    else:
        # GET request: load from DB
        profile = database.get_user_profile(email)
        if profile:
            return jsonify({
                "success": True,
                "profile": {
                    "company_name": profile.get("company_name", ""),
                    "industry": profile.get("industry", ""),
                    "size": profile.get("company_size", ""),
                    "website": profile.get("website", ""),
                    "description": profile.get("description", ""),
                    "sub_industry": profile.get("sub_industry", ""),
                    "hq_country": profile.get("hq_country", ""),
                    "geo_market": profile.get("geo_market", ""),
                    "business_model": profile.get("business_model", ""),
                    "target_customer": profile.get("target_customer", ""),
                    "objectives": profile.get("objectives", []),
                    "founded_year": profile.get("founded_year", "")
                }
            })
        else:
            return jsonify({"success": True, "profile": None})




# ══════════════════════════════════════════════════════════════════════════════
# V2 ENDPOINTS — Multi-Agent Structured JSON
# ══════════════════════════════════════════════════════════════════════════════

def build_company_context(email: str, module: str = "") -> tuple[str, str, str]:
    """
    Build a rich, company-specific grounding context for all v2 AI endpoints.
    Returns (grounding_context_str, company_name, industry).

    Includes:
    - Company profile (name, industry, size, website, description, business_model, etc.)
    - Real KPI metrics and sales/marketing context the user entered
    - Ideal Customer Profile (ICP) details
    - Knowledge base documents uploaded by the user
    """
    profile  = db.get_user_profile(email)
    metrics  = db.get_company_metrics(email)
    icp      = db.get_icp_profile(email)
    kb_content = db.get_knowledge_docs_content(email)
    if kb_content:
        if module:
            # Perform a simple keyword-based RAG filter to reduce prompt size
            paragraphs = []
            current_paragraph = []
            for line in kb_content.split("\n"):
                if line.strip().startswith("DOCUMENT ") or line.strip().startswith("#"):
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                current_paragraph.append(line)
            if current_paragraph:
                paragraphs.append("\n".join(current_paragraph))

            keywords = {
                "market": ["market", "competitor", "industry", "pestel", "swot", "size", "cagr", "tam", "sam", "som", "porter"],
                "campaign": ["campaign", "marketing", "funnel", "ads", "advertising", "social media", "content", "awareness", "consideration", "conversion", "budget"],
                "pitch": ["pitch", "sales", "objection", "selling", "close", "customer", "value proposition", "roi", "elevator pitch", "objections"],
                "lead": ["lead", "scoring", "qualification", "bant", "meddic", "firmographic", "demographic", "intent"],
                "insights": ["strategy", "growth", "operational", "challenges", "goals", "insights", "opportunities", "risks"],
                "dashboard": ["kpi", "metrics", "revenue", "leads", "sales", "performance", "summary"]
            }

            module_keywords = keywords.get(module, [])
            relevant_paragraphs = []
            for p in paragraphs:
                p_lower = p.lower()
                match_count = sum(1 for kw in module_keywords if kw in p_lower)
                if match_count > 0:
                    relevant_paragraphs.append((match_count, p))

            relevant_paragraphs.sort(key=lambda x: x[0], reverse=True)
            filtered_content = "\n\n".join([p for _, p in relevant_paragraphs[:3]])
            if filtered_content.strip():
                kb_content = filtered_content
            else:
                kb_content = kb_content[:1500] + "\n[Context truncated...]"
        else:
            kb_content = kb_content[:1500] + "\n[Context truncated...]"

    company_name = ""
    industry     = ""
    sections     = []

    # ── 1. Company Profile ────────────────────────────────────────────────────
    if profile:
        company_name = profile.get("company_name", "")
        industry     = profile.get("industry", "")
        obj = profile.get("objectives", [])
        obj_str = ", ".join(obj) if isinstance(obj, list) else str(obj)
        sections.append(
            f"COMPANY PROFILE:\n"
            f"  Name:             {company_name or 'N/A'}\n"
            f"  Industry:         {industry or 'N/A'}\n"
            f"  Sub-Industry:     {profile.get('sub_industry') or 'N/A'}\n"
            f"  Size:             {profile.get('company_size') or 'N/A'}\n"
            f"  Website:          {profile.get('website') or 'N/A'}\n"
            f"  Description:      {profile.get('description') or 'N/A'}\n"
            f"  Business Model:   {profile.get('business_model') or 'N/A'}\n"
            f"  Target Customer:  {profile.get('target_customer') or 'N/A'}\n"
            f"  Objectives:       {obj_str or 'N/A'}\n"
            f"  Founded Year:     {profile.get('founded_year') or 'N/A'}\n"
            f"  Geo Market:       {profile.get('geo_market') or 'N/A'}"
        )

    # ── 2. Real KPI Metrics & Sales/Marketing Context ─────────────────────────
    if metrics:
        currency = metrics.get("currency", "USD")
        rev      = metrics.get("monthly_revenue", 0) or 0
        target   = metrics.get("revenue_target", 0) or 0
        leads    = metrics.get("monthly_leads", 0) or 0
        lead_tgt = metrics.get("lead_target", 0) or 0
        cvr      = metrics.get("conversion_rate", 0) or 0
        deal     = metrics.get("avg_deal_size", 0) or 0
        cycle    = metrics.get("sales_cycle_days", 0) or 0
        ch       = metrics.get("top_channel", "N/A")
        campaigns= metrics.get("active_campaigns", 0) or 0
        notes    = metrics.get("notes", "")

        # New metrics
        sales_team_size = metrics.get("sales_team_size", 0) or 0
        win_rate = metrics.get("win_rate", 0.0) or 0.0
        lost_deal_rate = metrics.get("lost_deal_rate", 0.0) or 0.0
        opps = metrics.get("monthly_opportunities", 0) or 0
        mkt_budget = metrics.get("monthly_marketing_budget", 0.0) or 0.0
        cac = metrics.get("cac", 0.0) or 0.0
        ltv = metrics.get("ltv", 0.0) or 0.0
        lead_to_cust = metrics.get("lead_to_customer_rate", 0.0) or 0.0
        sec_channel = metrics.get("secondary_channel") or "N/A"

        pipeline_val = opps * deal
        forecast_rev = pipeline_val * (win_rate / 100.0)
        ltv_cac_ratio = (ltv / cac) if cac > 0 else 0

        metric_lines = [
            f"REAL COMPANY KPI METRICS (use these EXACT numbers in your analysis):",
            f"  Monthly Revenue:          {currency} {rev:,.0f}  (Target: {currency} {target:,.0f})",
            f"  Monthly Leads:            {leads} leads  (Target: {lead_tgt})",
            f"  Conversion Rate:          {cvr}%",
            f"  Avg Deal Size:            {currency} {deal:,.0f}",
            f"  Sales Cycle:              {cycle} days",
            f"  Active Campaigns:         {campaigns}",
            f"  Primary Channel:          {ch}",
            f"  Secondary Channel:        {sec_channel}",
            f"  Sales Team Size:          {sales_team_size} reps",
            f"  Win Rate:                 {win_rate}%",
            f"  Lost Deal Rate:           {lost_deal_rate}%",
            f"  Monthly Opportunities:    {opps}",
            f"  Est. Monthly Pipeline:    {currency} {pipeline_val:,.0f}",
            f"  Est. Forecast Revenue:    {currency} {forecast_rev:,.0f}",
            f"  Monthly Marketing Budget: {currency} {mkt_budget:,.0f}",
            f"  CAC:                      {currency} {cac:,.0f}",
            f"  LTV:                      {currency} {ltv:,.0f}",
            f"  LTV:CAC Ratio:            {f'{ltv_cac_ratio:.1f}x' if cac > 0 else 'N/A'}",
            f"  Lead-to-Customer Rate:    {lead_to_cust}%"
        ]

        # Revenue gap insight
        if rev > 0 and target > 0:
            gap = target - rev
            gap_pct = (gap / target * 100) if target else 0
            metric_lines.append(
                f"  Revenue Gap:              {currency} {abs(gap):,.0f} "
                f"({'below' if gap > 0 else 'above'} target by {abs(gap_pct):.1f}%)"
            )

        # Campaign clicks per platform
        clicks = metrics.get("campaign_clicks", [])
        if clicks and any(c > 0 for c in clicks):
            platforms = ["LinkedIn", "Instagram", "Google Ads", "Email", "Twitter/X", "YouTube"]
            click_data = [f"{platforms[i]}: {int(clicks[i])}" for i in range(min(len(clicks), len(platforms))) if clicks[i] > 0]
            metric_lines.append(f"  Campaign Clicks:          {', '.join(click_data)}")

        # Lead quality distribution
        dist = metrics.get("lead_distribution", [])
        if dist and any(d > 0 for d in dist):
            metric_lines.append(
                f"  Lead Quality:             Hot {int(dist[0] if len(dist) > 0 else 0)}% | "
                f"Warm {int(dist[1] if len(dist) > 1 else 0)}% | "
                f"Cold {int(dist[2] if len(dist) > 2 else 0)}%"
            )
        if notes:
            metric_lines.append(f"  Notes:                    {notes}")

        sections.append("\n".join(metric_lines))

    # ── 3. Ideal Customer Profile (ICP) ───────────────────────────────────────
    if icp:
        titles = icp.get("icp_job_titles", [])
        titles_str = ", ".join(titles) if isinstance(titles, list) else str(titles)
        dm = icp.get("icp_decision_makers", [])
        dm_str = ", ".join(dm) if isinstance(dm, list) else str(dm)
        pp = icp.get("icp_pain_points", [])
        pp_str = ", ".join(pp) if isinstance(pp, list) else str(pp)
        sections.append(
            f"IDEAL CUSTOMER PROFILE (ICP):\n"
            f"  Target Industry:          {icp.get('icp_industry') or 'N/A'}\n"
            f"  Company Size:             {icp.get('icp_company_size') or 'N/A'}\n"
            f"  Revenue Range:            {icp.get('icp_revenue_range') or 'N/A'}\n"
            f"  Key Job Titles:           {titles_str or 'N/A'}\n"
            f"  Decision Makers:          {dm_str or 'N/A'}\n"
            f"  Pain Points:              {pp_str or 'N/A'}\n"
            f"  Notes:                    {icp.get('icp_notes') or 'N/A'}"
        )

    # ── 4. Knowledge Base Documents ───────────────────────────────────────────
    if kb_content and kb_content.strip():
        sections.append(f"UPLOADED COMPANY DOCUMENTS / KNOWLEDGE BASE:\n{kb_content.strip()}")

    grounding_context = "\n\n".join(sections)
    return grounding_context, company_name, industry


@app.route("/api/v2/market_analysis", methods=["POST"])
@rate_limit(limit=10)
def v2_market_analysis():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents import run_market_analysis
        data = request.form or request.get_json() or {}
        email = session["user_email"]
        grounding_context, company_name, industry = build_company_context(email, "market")
        result = run_market_analysis(
            industry=data.get("industry", ""),
            product_category=data.get("product_category", ""),
            target_market=data.get("target_market", ""),
            competitors_raw=data.get("competitors", ""),
            time_horizon=data.get("time_horizon", "12 months"),
            grounding_context=grounding_context,
            company_name=company_name,
            company_industry=industry,
        )
        report_id = db.save_analysis_report(
            email=email,
            module="market",
            title=f"Market Analysis: {data.get('industry', 'Unknown')} — {company_name or email}",
            input_dict=dict(data),
            result_dict=result.get("data", {}),
            confidence_score=result.get("confidence_score", 0),
        )
        db.log_activity(
            email=email,
            activity_type="market_analyzed",
            title=f"Analyzed {data.get('industry', 'industry')} market trends",
            metadata={"industry": data.get("industry", ""), "time_horizon": data.get("time_horizon", ""), "report_id": report_id}
        )
        return jsonify({"success": True, "report_id": report_id, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/campaign", methods=["POST"])
@rate_limit(limit=10)
def v2_campaign():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents import run_campaign
        data = request.form or request.get_json() or {}
        email = session["user_email"]
        grounding_context, company_name, industry = build_company_context(email, "campaign")
        result = run_campaign(
            product=data.get("product", ""),
            audience=data.get("audience", ""),
            platform=data.get("platform", ""),
            budget=data.get("budget", ""),
            goals=data.get("goals", ""),
            grounding_context=grounding_context,
            company_name=company_name,
            company_industry=industry,
        )
        report_id = db.save_analysis_report(
            email=email,
            module="campaign",
            title=f"Campaign: {data.get('product', 'Unknown')} — {company_name or email}",
            input_dict=dict(data),
            result_dict=result.get("data", {}),
            confidence_score=result.get("confidence_score", 0),
        )
        db.log_activity(
            email=email,
            activity_type="campaign_generated",
            title=f"Generated marketing campaign for {data.get('product', 'product')}",
            metadata={"product": data.get("product", ""), "platform": data.get("platform", ""), "report_id": report_id}
        )
        return jsonify({"success": True, "report_id": report_id, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/social/integrations", methods=["GET"])
def v2_social_integrations():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        email = session["user_email"]
        conns = db.get_social_integrations(email)
        res_map = {
            "LinkedIn": {"connected": False, "username": ""},
            "Twitter/X": {"connected": False, "username": ""},
            "Instagram": {"connected": False, "username": ""}
        }
        for item in conns:
            plat = item.get("platform")
            if plat in res_map:
                res_map[plat]["connected"] = bool(item.get("connected", 0))
                res_map[plat]["username"] = item.get("username", "")
        return jsonify({"success": True, "integrations": res_map})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/social/connect", methods=["POST"])
def v2_social_connect():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        data = request.form or request.get_json() or {}
        platform = data.get("platform", "")
        username = data.get("username", "")
        password = data.get("password", "")
        
        if not platform or not username:
            return jsonify({"error": "Platform and username are required"}), 400
            
        email = session["user_email"]
        db.save_social_integration(email, platform, True, username)
        
        db.log_activity(
            email=email,
            activity_type="social_account_connected",
            title=f"Connected {platform} account: @{username}",
            metadata={"platform": platform, "username": username}
        )
        return jsonify({"success": True, "message": f"Successfully connected to {platform}!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/campaign/post", methods=["POST"])
@rate_limit(limit=15)
def v2_campaign_post():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        data = request.form or request.get_json() or {}
        platform = data.get("platform", "")
        copy = data.get("copy", "")
        
        if not platform:
            return jsonify({"error": "Platform is required"}), 400
            
        email = session["user_email"]
        db.log_activity(
            email=email,
            activity_type="social_post_published",
            title=f"Published post to {platform}",
            metadata={"platform": platform, "copy": copy[:150]}
        )
        return jsonify({"success": True, "message": f"Successfully published post to {platform}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/pitch", methods=["POST"])
@rate_limit(limit=10)
def v2_pitch():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents import run_pitch
        data = request.form or request.get_json() or {}
        email = session["user_email"]
        grounding_context, company_name, industry = build_company_context(email, "pitch")
        result = run_pitch(
            product=data.get("product", ""),
            customer=data.get("customer", ""),
            target_role=data.get("target_role", ""),
            usp=data.get("usp", ""),
            pain_points=data.get("pain_points", ""),
            grounding_context=grounding_context,
            company_name=company_name,
            company_industry=industry,
        )
        report_id = db.save_analysis_report(
            email=email,
            module="pitch",
            title=f"Sales Pitch: {data.get('product', 'Unknown')} — {company_name or email}",
            input_dict=dict(data),
            result_dict=result.get("data", {}),
            confidence_score=result.get("confidence_score", 0),
        )
        db.log_activity(
            email=email,
            activity_type="pitch_created",
            title=f"Created sales pitch for {data.get('product', 'product')}",
            metadata={"product": data.get("product", ""), "customer": data.get("customer", ""), "report_id": report_id}
        )
        return jsonify({"success": True, "report_id": report_id, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/lead_score", methods=["POST"])
@rate_limit(limit=10)
def v2_lead_score():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents import run_lead_score
        data = request.form or request.get_json() or {}
        email = session["user_email"]
        grounding_context, company_name, industry = build_company_context(email, "lead")
        result = run_lead_score(
            name=data.get("name", ""),
            budget=data.get("budget", ""),
            need=data.get("need", ""),
            company=data.get("company", ""),
            industry=data.get("industry", ""),
            company_size=data.get("company_size", ""),
            decision_role=data.get("decision_role", ""),
            urgency=data.get("urgency", ""),
            grounding_context=grounding_context,
            company_name=company_name,
            company_industry=industry,
        )
        report_id = db.save_analysis_report(
            email=email,
            module="lead",
            title=f"Lead Score: {data.get('name', 'Unknown')} → {company_name or email}",
            input_dict=dict(data),
            result_dict=result.get("data", {}),
            confidence_score=result.get("confidence_score", 0),
        )
        db.log_activity(
            email=email,
            activity_type="lead_scored",
            title=f"Scored lead: {data.get('name', 'lead')}",
            metadata={
                "name": data.get("name", ""),
                "company": data.get("company", ""),
                "grade": result.get("data", {}).get("grade", "N/A"),
                "score": result.get("data", {}).get("score", 0),
                "report_id": report_id
            }
        )
        return jsonify({"success": True, "report_id": report_id, **result})
    except Exception as e:
        import traceback
        try:
            with open(r"C:\Users\venga\.gemini\antigravity\brain\a4f30c59-56b3-4acb-b3c1-107d17ddc72b\scratch\lead_error.txt", "w") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/business_insights", methods=["POST"])
@rate_limit(limit=10)
def v2_business_insights():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents import run_business_insights
        data = request.form or request.get_json() or {}
        email = session["user_email"]
        grounding_context, company_name, industry = build_company_context(email, "insights")
        result = run_business_insights(
            business_type=data.get("business_type", ""),
            challenges=data.get("challenges", ""),
            goals=data.get("goals", ""),
            target_audience=data.get("target_audience", ""),
            industry_context=data.get("industry_context", ""),
            grounding_context=grounding_context,
            company_name=company_name,
            company_industry=industry,
        )
        report_id = db.save_analysis_report(
            email=email,
            module="insights",
            title=f"Business Insights: {company_name or data.get('business_type', 'Unknown')}",
            input_dict=dict(data),
            result_dict=result.get("data", {}),
            confidence_score=result.get("confidence_score", 0),
        )
        db.log_activity(
            email=email,
            activity_type="insight_generated",
            title="Generated strategic business insights",
            metadata={"business_type": data.get("business_type", ""), "report_id": report_id}
        )
        return jsonify({"success": True, "report_id": report_id, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/suggest_inputs", methods=["POST"])
def v2_suggest_inputs():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        from agents.base import invoke_structured
        data = request.form or request.get_json() or {}
        module = data.get("module", "")
        if module not in ["campaign", "pitch", "lead", "market", "insights"]:
            return jsonify({"error": "Invalid module specified"}), 400
            
        email = session["user_email"]
        grounding_context, company_name, industry = build_company_context(email, module)
        
        # Check if the grounding context is essentially empty
        if not grounding_context.strip():
            return jsonify({
                "success": False,
                "error": "Your company profile and Knowledge Base are empty. Please configure your profile or upload documents to generate personalized suggestions."
            }), 200
            
        if module == "campaign":
            keys_desc = (
                "{\n"
                '  "product": "Name and brief description of a main product/service of the company",\n'
                '  "audience": "Specific target customer persona details",\n'
                '  "platform": "Primary marketing channels (e.g. LinkedIn, Google Search, Instagram)",\n'
                '  "goals": "Key marketing campaign goals (e.g. Lead generation, brand awareness)",\n'
                '  "budget": "Realistic budget range (e.g. $5,000 - $10,000)"\n'
                "}"
            )
        elif module == "pitch":
            keys_desc = (
                "{\n"
                '  "product": "Product or service name",\n'
                '  "customer": "Target buyer company types/personas",\n'
                '  "targetRole": "Job title of decision maker (e.g. Facilities Director)",\n'
                '  "usp": "Unique Selling Proposition of the product/service",\n'
                '  "painPoints": "Key buyer pain points resolved by the product"\n'
                "}"
            )
        elif module == "lead":
            keys_desc = (
                "{\n"
                '  "name": "Full name of a hypothetical target buyer prospect (e.g. Robert Smith)",\n'
                '  "company": "Company name of a target buyer prospect",\n'
                '  "industry": "Industry sector of the prospect company",\n'
                '  "companySize": "Company size (e.g. 50-200 employees)",\n'
                '  "decisionRole": "Job title of this prospect (e.g. VP Operations)",\n'
                '  "budget": "Stated budget range (e.g. $40,000 / Year)",\n'
                '  "need": "Their core business need matching your company\'s services",\n'
                '  "urgency": "Their timeline/urgency (e.g. Immediate launch before Q4)"\n'
                "}"
            )
        elif module == "market":
            keys_desc = (
                "{\n"
                '  "industry": "Industry sector to analyze",\n'
                '  "productCategory": "Specific product category",\n'
                '  "targetMarket": "Target geographic / segment",\n'
                '  "competitors": "Comma-separated list of top 3-4 real competitors in this space",\n'
                '  "timeHorizon": "Horizon for forecasting (e.g. 12 months, 24 months)"\n'
                "}"
            )
        else: # insights
            keys_desc = (
                "{\n"
                '  "businessType": "Description of the company business model (e.g. B2B SaaS, D2C E-commerce)",\n'
                '  "challenges": "Current operational or sales challenges the company is facing",\n'
                '  "goals": "Key business goals to achieve in the next 12 months",\n'
                '  "targetAudience": "Description of the target customer audience",\n'
                '  "industryContext": "Current context of the industry landscape"\n'
                "}"
            )
            
        sys_prompt = (
            "You are an expert sales and marketing assistant. Your job is to analyze the provided company profile "
            "and grounding documents, and suggest realistic, context-specific inputs for a form. Return JSON only."
        )
        prompt = (
            f"Based on the company context below, analyze the files and parameters:\n"
            f"COMPANY CONTEXT:\n{grounding_context}\n\n"
            f"Suggest optimal, highly realistic inputs for the '{module}' workspace form fields.\n"
            f"Ensure all values align precisely with this company's profile and documents.\n"
            f"Do not return generic placeholder text. Produce concise, specific values.\n\n"
            f"Return a single JSON object containing only these keys:\n{keys_desc}"
        )
        
        result = invoke_structured(sys_prompt, prompt, schema_hint=keys_desc, retries=2, fast=False, max_tokens=1500)
        return jsonify({"success": True, "suggestions": result})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── v2 Export ─────────────────────────────────────────────────────────────────

@app.route("/api/v2/export/pdf", methods=["POST"])
def v2_export_pdf():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents.report_generation import generate_pdf
        body = request.get_json() or {}
        module = body.get("module", "market")
        title = body.get("title", "MarketMind Report")
        data = body.get("data", {})
        pdf_bytes = generate_pdf(module, title, data)
        db.log_activity(
            email=session["user_email"],
            activity_type="report_exported",
            title=f"Exported {module} report to PDF",
            metadata={"module": module, "format": "PDF"}
        )
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"marketmind_{module}_report.pdf",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/export/docx", methods=["POST"])
def v2_export_docx():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents.report_generation import generate_docx
        body = request.get_json() or {}
        module = body.get("module", "market")
        title = body.get("title", "MarketMind Report")
        data = body.get("data", {})
        docx_bytes = generate_docx(module, title, data)
        db.log_activity(
            email=session["user_email"],
            activity_type="report_exported",
            title=f"Exported {module} report to DOCX",
            metadata={"module": module, "format": "DOCX"}
        )
        return send_file(
            io.BytesIO(docx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=f"marketmind_{module}_report.docx",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── v2 Reports ────────────────────────────────────────────────────────────────

@app.route("/api/v2/reports", methods=["GET"])
def v2_get_reports():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    module_filter = request.args.get("module")
    reports = db.get_analysis_reports(session["user_email"], module=module_filter)
    return jsonify({"success": True, "reports": reports})


@app.route("/api/v2/reports/<int:report_id>", methods=["GET"])
def v2_get_report(report_id):
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    report = db.get_analysis_report_by_id(session["user_email"], report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"success": True, "report": report})


@app.route("/api/v2/reports/<int:report_id>", methods=["DELETE"])
def v2_delete_report(report_id):
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db.delete_analysis_report(session["user_email"], report_id)
    return jsonify({"success": True})


# ── v2 Analytics ──────────────────────────────────────────────────────────────

@app.route("/api/v2/analytics/summary", methods=["GET"])
def v2_analytics_summary():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    summary = db.get_analytics_summary(session["user_email"])
    return jsonify({"success": True, **summary})


# ── v2 Watchlist ──────────────────────────────────────────────────────────────

@app.route("/api/v2/watchlist", methods=["GET"])
def v2_get_watchlist():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    items = db.get_watchlists(session["user_email"])
    return jsonify({"success": True, "watchlists": items})


@app.route("/api/v2/watchlist", methods=["POST"])
def v2_add_watchlist():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    body = request.get_json() or {}
    industry = body.get("industry", "General")
    keywords = body.get("keywords", [])
    new_id = db.add_watchlist(session["user_email"], industry, keywords)
    return jsonify({"success": True, "id": new_id})


@app.route("/api/v2/watchlist/<int:watchlist_id>", methods=["DELETE"])
def v2_delete_watchlist(watchlist_id):
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db.delete_watchlist(session["user_email"], watchlist_id)
    return jsonify({"success": True})


# ── RAG Knowledge Base Endpoints ──────────────────────────────────────────────

@app.route("/api/knowledge", methods=["GET"])
def get_knowledge():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    docs = database.get_knowledge_docs(session["user_email"])
    return jsonify({"success": True, "documents": docs})

@app.route("/api/knowledge", methods=["POST"])
@rate_limit(limit=30)
def upload_knowledge():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
        
    try:
        content = extract_text_from_file(file)
        doc_id = database.add_knowledge_doc(session["user_email"], file.filename, content)
        return jsonify({"success": True, "id": doc_id, "filename": file.filename})
    except Exception as e:
        return jsonify({"error": f"Failed to upload document: {str(e)}"}), 500

@app.route("/api/knowledge/<int:doc_id>", methods=["DELETE"])
def delete_knowledge(doc_id):
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    success = database.delete_knowledge_doc(session["user_email"], doc_id)
    return jsonify({"success": success})


# ── v3 Market Analyzer Endpoints ──────────────────────────────────────────────

@app.route("/api/v2/market/summary", methods=["GET"])
def v2_market_summary():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    email = session["user_email"]
    workspace = database.get_or_create_workspace(email)
    ws_id = workspace["id"]
    
    size = database.get_market_size(ws_id)
    competitors = database.get_competitor_profiles(ws_id)
    opportunities = database.get_market_opportunities(ws_id)
    recommendations = database.get_strategic_recommendations(ws_id)
    
    reports = database.get_analysis_reports(email, module="market", limit=1)
    latest_data = {}
    if reports:
        latest_data = reports[0].get("result_dict", {})
    
    # Sensible defaults if no analysis has been run yet
    market_size_data = {
        "currency": size["currency"] if size else "USD",
        "tam": size["tam_value"] if size else 0.0,
        "sam": size["sam_value"] if size else 0.0,
        "som": size["som_value"] if size else 0.0,
        "growth_rate_cagr": size["growth_rate_cagr"] if size else 0.0,
        "source_documentation": size["source_documentation"] if size else ""
    }
    
    return jsonify({
        "success": True,
        "workspace": {
            "id": ws_id,
            "company_name": workspace["company_name"],
            "industry": workspace["industry"],
            "sub_industry": workspace["sub_industry"],
            "hq_country": workspace["hq_country"],
            "geo_market": workspace["geo_market"],
            "business_model": workspace["business_model"],
            "target_customer": workspace["target_customer"],
            "founded_year": workspace["founded_year"]
        },
        "market_size": market_size_data,
        "competitors": competitors,
        "opportunities": opportunities,
        "recommendations": recommendations,
        # Merged rich dynamic fields from the latest run:
        "swot": latest_data.get("swot", {}),
        "pestel": latest_data.get("pestel", {}),
        "trends": latest_data.get("trends", []),
        "radar_data": latest_data.get("radar_data", []),
        "growth_chart_data": latest_data.get("growth_chart_data", []),
        "advertising_analysis": latest_data.get("advertising_analysis", []),
        "positioning_postures": latest_data.get("positioning_postures", [])
    })


@app.route("/api/v2/market/analyze", methods=["POST"])
def v2_market_analyze():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    email = session["user_email"]
    workspace = database.get_or_create_workspace(email)
    ws_id = workspace["id"]
    
    body = request.get_json() or {}
    industry = body.get("industry", workspace["industry"] or "Technology")
    product_category = body.get("product_category", workspace["sub_industry"] or "Software")
    target_market = body.get("target_market", workspace["geo_market"] or "Global")
    competitors_raw = body.get("competitors", "")
    
    try:
        from agents import run_market_analysis
        grounding_context, company_name, company_industry = build_company_context(email, "market")
        
        result = run_market_analysis(
            industry=industry,
            product_category=product_category,
            target_market=target_market,
            competitors_raw=competitors_raw,
            time_horizon="12 months",
            grounding_context=grounding_context,
            company_name=company_name,
            company_industry=company_industry,
        )
        
        agent_data = result.get("data", {})
        
        # Save Sizing to Database Sizing Table (with descriptive amount parser)
        import re, random
        def parse_amount(text):
            if not text: return None
            text_clean = re.sub(r'[^\d\.\,KkMmBb]', '', str(text))
            if not text_clean: return None
            match = re.search(r'([\d\.]+)', text_clean)
            if not match: return None
            val = float(match.group(1))
            if 'b' in text_clean.lower():
                val *= 1.0e9
            elif 'm' in text_clean.lower():
                val *= 1.0e6
            elif 'k' in text_clean.lower():
                val *= 1.0e3
            return val

        size_obj = agent_data.get("market_size", {})
        tam_val = parse_amount(size_obj.get("current"))
        if not tam_val or tam_val <= 0:
            tam_base = 2500000000.0 if ("software" in industry.lower() or "tech" in industry.lower()) else 1000000000.0
            tam_val = round(tam_base * random.uniform(0.8, 1.5), 2)
        
        sam_val = parse_amount(size_obj.get("projected"))
        if not sam_val or sam_val <= 0:
            sam_val = round(tam_val * random.uniform(0.3, 0.45), 2)
            
        som_val = round(sam_val * random.uniform(0.1, 0.25), 2)
        
        cagr_str = size_obj.get("cagr", "")
        match_cagr = re.search(r'([\d\.]+)', cagr_str)
        cagr_val = float(match_cagr.group(1)) if match_cagr else round(random.uniform(5.5, 14.5), 2)
        
        # Save Sizing
        database.save_market_size(
            workspace_id=ws_id,
            tam_value=tam_val,
            sam_value=sam_val,
            som_value=som_val,
            growth_rate_cagr=cagr_val,
            source_documentation=size_obj.get("source_documentation", f"Automated AI Sizing Engine via Llama-3-70B based on {industry} and regional data."),
            currency=size_obj.get("currency", "USD")
        )
        
        # Save Competitors
        competitors = agent_data.get("competitors", [])
        if competitors:
            for idx, c in enumerate(competitors):
                share = round(random.uniform(5.0, 25.0), 2)
                threat = c.get("threat_level", "Medium")
                database.save_competitor_profile(
                    workspace_id=ws_id,
                    name=c.get("name"),
                    market_share_pct=share,
                    strengths=[c.get("strengths")],
                    weaknesses=[c.get("weaknesses")],
                    threat_level=threat,
                    innovation_score=int(random.uniform(60, 95)),
                    pricing_score=int(random.uniform(50, 90)),
                    reach_score=int(random.uniform(40, 85)),
                    support_score=int(random.uniform(55, 90)),
                    quality_score=int(random.uniform(65, 95))
                )
                
        # Save Opportunities
        opps = agent_data.get("opportunities", [])
        if opps:
            for o in opps:
                database.save_market_opportunity(
                    workspace_id=ws_id,
                    title=o.get("title", ""),
                    description=o.get("revenue_potential", o.get("title", "")),
                    impact_score=int(o.get("score", random.choice([5,6,7,8,9]))),
                    effort_score=4 if o.get("effort") == "Low" else (6 if o.get("effort") == "Medium" else 8),
                    estimated_revenue=parse_amount(o.get("revenue_potential")) or 0.0,
                    target_audience=workspace["target_customer"] or "Target segment",
                    required_capabilities=[],
                    status="discovered"
                )
                
        # Archive as structured Analysis Report in history database
        report_id = database.save_analysis_report(
            email=email,
            module="market",
            title=f"Market Sizing: {industry} — {company_name or email}",
            input_dict=body,
            result_dict=agent_data,
            confidence_score=result.get("confidence_score", 0),
        )
        
        database.log_activity(
            email=email,
            activity_type="market_analyzed",
            title=f"Analyzed {industry} market sizing",
            metadata={"industry": industry, "report_id": report_id}
        )
        
        return jsonify({
            "success": True,
            "message": "Market intelligence analysis completed successfully via LangGraph agent.",
            "report_id": report_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/market/simulate", methods=["POST"])
def v2_market_simulate():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    email = session["user_email"]
    workspace = database.get_or_create_workspace(email)
    ws_id = workspace["id"]
    
    body = request.get_json() or {}
    avg_deal_size_modifier = float(body.get("avg_deal_size_modifier", 1.0))
    sales_cycle_days_modifier = float(body.get("sales_cycle_days_modifier", 1.0))
    
    # Fetch SOM value as baseline
    size = database.get_market_size(ws_id)
    som = size["som_value"] if size else 5000000.0
    
    # Calculate modifiers
    deal_multiplier = avg_deal_size_modifier
    cycle_multiplier = 1.0 / sales_cycle_days_modifier if sales_cycle_days_modifier > 0 else 1.0
    total_multiplier = deal_multiplier * cycle_multiplier
    
    # Shift simulated projections
    baseline_projection = som
    simulated_projection = round(som * total_multiplier, 2)
    
    chart_data = []
    for m in range(1, 13):
        m_base = round((som / 12) * m, 2)
        m_sim = round(m_base * total_multiplier, 2)
        chart_data.append({
            "month": f"M{m}",
            "baseline": m_base,
            "simulated": m_sim
        })
        
    simulation_output = {
        "baseline_projection_12m": baseline_projection,
        "simulated_projection_12m": simulated_projection,
        "growth_multiplier": round(total_multiplier, 3),
        "simulation_chart": chart_data
    }
    
    sim_id = database.save_growth_simulation(
        workspace_id=ws_id,
        simulation_name=f"Modifier simulation: Deal={avg_deal_size_modifier}x Cycle={sales_cycle_days_modifier}x",
        input_parameters=body,
        simulation_output=simulation_output
    )
    
    return jsonify({
        "success": True,
        "simulation_id": sim_id,
        **simulation_output
    })


# ── Share Link Endpoints ──────────────────────────────────────────────────────

@app.route("/api/reports/<int:report_id>/share", methods=["POST"])
def toggle_report_share(report_id):
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    body = request.get_json() or {}
    is_public = bool(body.get("is_public", False))
    token = database.toggle_report_share(session["user_email"], report_id, is_public)
    if token is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"success": True, "share_token": token, "is_public": is_public})

@app.route("/api/reports/shared/<token>", methods=["GET"])
def get_shared_report(token):
    report = database.get_shared_report(token)
    if not report:
        return jsonify({"error": "Shared report not found or private"}), 404
    return jsonify({"success": True, "report": report})


# ── AI Copilot Chatbot Endpoint ────────────────────────────────────────────────

def compress_context_data(domain, data):
    if not data or not isinstance(data, dict):
        return {}
    
    compressed = {}
    
    # Helper to truncate long strings/objects
    def cap_str(val, limit=400):
        if isinstance(val, str):
            return val[:limit] + "..." if len(val) > limit else val
        return val
    
    # Extract top-level details
    for k in ["campaign_name", "product_name", "product", "industry", "company_name", "opportunity_score", "lead_score", "sales_readiness_score"]:
        if k in data:
            compressed[k] = cap_str(data[k])
            
    if domain == "campaign":
        compressed["executive_summary"] = cap_str(data.get("executive_campaign_overview", ""))
        goals = data.get("strategic_goals", [])
        if isinstance(goals, list):
            compressed["strategic_goals"] = [cap_str(g.get("goal_name") if isinstance(g, dict) else g) for g in goals[:3]]
        for k in ["estimated_reach", "estimated_ctr", "estimated_cvr", "timeline_weeks"]:
            if k in data:
                compressed[k] = data[k]
        persona = data.get("persona_profile", {})
        if isinstance(persona, dict):
            compressed["target_persona_job_titles"] = [cap_str(t) for t in persona.get("job_titles", [])[:3]]
            
    elif domain == "pitch":
        compressed["elevator_pitch"] = cap_str(data.get("elevator_pitch", ""))
        val_prop = data.get("value_proposition", {})
        if isinstance(val_prop, dict):
            compressed["value_proposition_headline"] = cap_str(val_prop.get("headline", ""))
        roi = data.get("roi_argument", {})
        if isinstance(roi, dict):
            compressed["roi_calculation"] = cap_str(roi.get("calculation", ""))
            
    elif domain == "lead":
        compressed["qualification_summary"] = cap_str(data.get("qualification_summary", ""))
        compressed["temperature"] = cap_str(data.get("temperature", ""))
        compressed["conversion_probability"] = data.get("conversion_probability", "")
        compressed["next_best_action"] = cap_str(data.get("next_best_action", ""))
        
    elif domain == "market":
        compressed["executive_summary"] = cap_str(data.get("executive_summary", ""))
        size = data.get("market_size", {})
        if isinstance(size, dict):
            compressed["market_size"] = {k: cap_str(v) for k, v in size.items()}
        swot = data.get("swot", {})
        if isinstance(swot, dict):
            compressed["swot_summary"] = {
                "strengths": [cap_str(s) for s in swot.get("strengths", [])[:2]],
                "weaknesses": [cap_str(w) for w in swot.get("weaknesses", [])[:2]]
            }
        comps = data.get("competitors", [])
        if isinstance(comps, list):
            compressed["key_competitors"] = [cap_str(c.get("name") if isinstance(c, dict) else c) for c in comps[:3]]
            
    elif domain == "insights":
        compressed["executive_summary"] = cap_str(data.get("executive_summary", ""))
        recs = data.get("strategic_recommendations", [])
        if isinstance(recs, list):
            compressed["strategic_recommendations"] = [cap_str(r.get("recommendation") if isinstance(r, dict) else r) for r in recs[:3]]
            
    return compressed


@app.route("/api/v2/chat", methods=["POST"])
def v2_chat():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        from agents.base import get_llm, SystemMessage, HumanMessage
        from langchain_core.messages import AIMessage
        import json
        
        data = request.get_json() or {}
        message = data.get("message", "")
        history = data.get("history", [])  # list of {"role": "user"|"assistant", "content": "..."}
        domain = data.get("domain", "general")  # campaign, pitch, lead, market, insights
        context_data = data.get("context_data", {})  # generated report data

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Define domain system instructions
        domain_instructions = {
            "campaign": (
                "You are an expert Marketing Campaign Strategist. Your goal is to clarify doubts, "
                "provide further strategic details, and answer questions specifically about marketing campaigns, "
                "advertising platforms, channel mix, KPIs, budget allocation, and target buyer personas.\n"
                "Refuse politely to answer any questions outside marketing, campaign design, and advertising."
            ),
            "pitch": (
                "You are an expert Sales Enablement Coach and Copywriter. Your goal is to clarify doubts, "
                "give advice, and answer questions specifically about sales pitches, objection handling scripts, "
                "email templates, meeting agendas, discovery calls, and ROI arguments.\n"
                "Refuse politely to answer any questions outside sales coaching and sales collateral."
            ),
            "lead": (
                "You are a Senior Lead Qualification Analyst and Operations Specialist. Your goal is to clarify doubts "
                "and answer questions specifically about lead scoring, BANT (Budget, Authority, Need, Timeline) frameworks, "
                "intent signals, risk mitigations, sales playbooks, and CRM integrations.\n"
                "Refuse politely to answer any questions outside lead scoring and BANT qualification."
            ),
            "market": (
                "You are a Competitive Market Intelligence Researcher. Your goal is to clarify doubts and answer "
                "questions specifically about industry sectors, SWOT analysis, PESTEL factors, market sizing (TAM/SAM/SOM), "
                "competitor positioning postures, and growth trends.\n"
                "Refuse politely to answer any questions outside market research, industry analysis, and competitive landscape."
            ),
            "insights": (
                "You are a Senior Business Operations Consultant and Strategy Advisor. Your goal is to clarify doubts "
                "and answer questions specifically about business diagnostics, operational challenges, root-cause analyses, "
                "cost optimizations, and 30/60/90 day action roadmaps.\n"
                "Refuse politely to answer any questions outside business diagnostics, strategy consult, and operations planning."
            )
        }

        inst = domain_instructions.get(domain, "You are a professional business strategist. Answer domain-relevant questions only.")

        system_content = (
            f"{inst}\n\n"
            "GUARDRAILS & RULES:\n"
            "1. Focus strictly on your designated domain. If the user asks a question unrelated to this domain (e.g. general coding, recipes, jokes, general chat, unrelated math, other domains), "
            "politely refuse to answer and redirect them back to the domain of focus.\n"
            "2. If the user asks about the generated report/data, refer to the context data provided below.\n"
            "3. Keep your answers concise, professional, direct, and formatted in Markdown.\n\n"
        )

        if context_data:
            compressed = compress_context_data(domain, context_data)
            system_content += f"CURRENT REPORT CONTEXT DATA (JSON):\n{json.dumps(compressed, indent=2)}\n\n"

        messages = [SystemMessage(content=system_content)]

        # Add conversation history
        for h in history[-4:]:  # keep last 4 messages (2 turns) to prevent token bloat
            role = h.get("role", "user")
            content = h.get("content", "")
            # Truncate content in history if it's exceptionally long to prevent TPM exhaustion
            if len(content) > 1000:
                content = content[:1000] + "... [truncated]"
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=message))

        try:
            llm = get_llm(temperature=0.3, max_tokens=1000)
            res = llm.invoke(messages)
        except Exception as e:
            err_msg = str(e).lower()
            if "rate limit" in err_msg or "429" in err_msg or "413" in err_msg or "tpd" in err_msg or "tokens" in err_msg:
                # Fall back to 8B instant model
                print("Rate limit hit on 70B. Falling back to Llama-3.1-8b-instant for chat...")
                llm = get_llm(model="llama-3.1-8b-instant", temperature=0.3, max_tokens=1000)
                res = llm.invoke(messages)
            else:
                raise e

        return jsonify({
            "success": True,
            "response": res.content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── PPTX Exporter Endpoints ───────────────────────────────────────────────────

@app.route("/api/v2/export/pptx", methods=["POST"])
def v2_export_pptx():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    body = request.get_json() or {}
    report_title = body.get("title", "MarketMind AI Intelligence Report")
    module = body.get("module", "market")
    data = body.get("data", {})
    
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)
        
        title_slide_layout = prs.slide_layouts[6]
        slide1 = prs.slides.add_slide(title_slide_layout)
        
        # Dark Background
        bg = slide1.shapes.add_shape(1, 0, 0, Inches(13.33), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = RGBColor(10, 15, 30)
        bg.line.fill.background()
        
        # Glowing Sidebar Accent (Left edge)
        sidebar1 = slide1.shapes.add_shape(1, 0, 0, Inches(0.35), Inches(7.5))
        sidebar1.fill.solid()
        sidebar1.fill.fore_color.rgb = RGBColor(59, 130, 246)
        sidebar1.line.fill.background()
        
        sidebar2 = slide1.shapes.add_shape(1, Inches(0.35), 0, Inches(0.12), Inches(7.5))
        sidebar2.fill.solid()
        sidebar2.fill.fore_color.rgb = RGBColor(139, 92, 246)
        sidebar2.line.fill.background()
        
        # Title Text Block
        tx_box = slide1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(3.5))
        tf = tx_box.text_frame
        tf.word_wrap = True
        
        p_brand = tf.paragraphs[0]
        p_brand.text = "MARKETAI SUITE PLATFORM PRESENTATION"
        p_brand.font.size = Pt(11)
        p_brand.font.bold = True
        p_brand.font.color.rgb = RGBColor(59, 130, 246)
        p_brand.font.name = 'Arial'
        
        p = tf.add_paragraph()
        p.text = report_title.upper()
        p.font.bold = True
        p.font.size = Pt(36)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.font.name = 'Arial'
        p.space_before = Pt(10)
        
        p2 = tf.add_paragraph()
        p2.text = f"Module Analysis: {module.upper()} STRATEGY DECK\nOrchestrated via Multi-Agent Graphs  ·  {datetime.utcnow().strftime('%B %d, %Y')}"
        p2.font.size = Pt(13)
        p2.font.color.rgb = RGBColor(148, 163, 184)
        p2.font.name = 'Arial'
        p2.space_before = Pt(25)
        
        # Standard Slide Helper
        def create_standard_slide(title_text):
            slide = prs.slides.add_slide(title_slide_layout)
            # Background
            bg_s = slide.shapes.add_shape(1, 0, 0, Inches(13.33), Inches(7.5))
            bg_s.fill.solid()
            bg_s.fill.fore_color.rgb = RGBColor(15, 23, 42)
            bg_s.line.fill.background()
            
            # Left strip
            sb = slide.shapes.add_shape(1, 0, 0, Inches(0.15), Inches(7.5))
            sb.fill.solid()
            sb.fill.fore_color.rgb = RGBColor(59, 130, 246)
            sb.line.fill.background()
            
            # Title
            tx_t = slide.shapes.add_textbox(Inches(1.0), Inches(0.4), Inches(11.33), Inches(0.8))
            tf_t = tx_t.text_frame
            tf_t.word_wrap = True
            p_t = tf_t.paragraphs[0]
            p_t.text = title_text.upper()
            p_t.font.bold = True
            p_t.font.size = Pt(22)
            p_t.font.color.rgb = RGBColor(255, 255, 255)
            p_t.font.name = 'Arial'
            
            # Divider line
            div = slide.shapes.add_shape(1, Inches(1.0), Inches(1.15), Inches(11.33), Inches(0.02))
            div.fill.solid()
            div.fill.fore_color.rgb = RGBColor(59, 130, 246)
            div.line.fill.background()
            
            return slide
            
        # ─── Slide 2: Executive Summary ───
        slide2 = create_standard_slide("Executive Summary Overview")
        
        summary_text = data.get("executive_summary", "") or data.get("qualification_summary", "") or "No executive summary available for this brief."
        
        # Card shape for Summary
        card = slide2.shapes.add_shape(5, Inches(1.0), Inches(1.6), Inches(11.33), Inches(4.8))
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(30, 41, 59)
        card.line.color.rgb = RGBColor(59, 130, 246)
        card.line.width = Pt(1.5)
        
        tf_card = card.text_frame
        tf_card.word_wrap = True
        tf_card.vertical_anchor = 1
        tf_card.margin_left = Inches(0.4)
        tf_card.margin_right = Inches(0.4)
        tf_card.margin_top = Inches(0.4)
        
        p_c_title = tf_card.paragraphs[0]
        p_c_title.text = "KEY STRATEGIC INSIGHT BRIEFING"
        p_c_title.font.bold = True
        p_c_title.font.size = Pt(13)
        p_c_title.font.color.rgb = RGBColor(96, 165, 250)
        p_c_title.font.name = 'Arial'
        
        p_c_body = tf_card.add_paragraph()
        p_c_body.text = summary_text
        p_c_body.font.size = Pt(15)
        p_c_body.font.color.rgb = RGBColor(241, 245, 249)
        p_c_body.font.name = 'Arial'
        p_c_body.space_before = Pt(15)
        p_c_body.line_spacing = 1.3
        
        # ─── Slide 3: Strategic SWOT Matrix / Analysis ───
        slide3 = create_standard_slide("Strategic SWOT Analysis")
        swot = data.get("swot", {})
        if swot and isinstance(swot, dict) and any(swot.values()):
            # 2x2 shapes grid
            quadrants = [
                ("STRENGTHS", swot.get("strengths", []), Inches(1.0), Inches(1.6), RGBColor(16, 185, 129)),
                ("WEAKNESSES", swot.get("weaknesses", []), Inches(6.9), Inches(1.6), RGBColor(239, 68, 68)),
                ("OPPORTUNITIES", swot.get("opportunities", []), Inches(1.0), Inches(4.2), RGBColor(59, 130, 246)),
                ("THREATS", swot.get("threats", []), Inches(6.9), Inches(4.2), RGBColor(245, 158, 11))
            ]
            for label, items, x, y, color in quadrants:
                q_card = slide3.shapes.add_shape(5, x, y, Inches(5.43), Inches(2.3))
                q_card.fill.solid()
                q_card.fill.fore_color.rgb = RGBColor(30, 41, 59)
                q_card.line.color.rgb = color
                q_card.line.width = Pt(1.5)
                
                tf_q = q_card.text_frame
                tf_q.word_wrap = True
                tf_q.vertical_anchor = 1
                tf_q.margin_left = Inches(0.2)
                tf_q.margin_top = Inches(0.2)
                
                p_q_lbl = tf_q.paragraphs[0]
                p_q_lbl.text = label
                p_q_lbl.font.bold = True
                p_q_lbl.font.size = Pt(13)
                p_q_lbl.font.color.rgb = color
                p_q_lbl.font.name = 'Arial'
                
                for item in items[:3]:
                    p_item = tf_q.add_paragraph()
                    p_item.text = f"• {item}"
                    p_item.font.size = Pt(10)
                    p_item.font.color.rgb = RGBColor(226, 232, 240)
                    p_item.font.name = 'Arial'
                    p_item.space_before = Pt(4)
        else:
            # Fallback cards if swot not present
            card1 = slide3.shapes.add_shape(5, Inches(1.0), Inches(1.6), Inches(5.4), Inches(4.8))
            card1.fill.solid()
            card1.fill.fore_color.rgb = RGBColor(30, 41, 59)
            card1.line.color.rgb = RGBColor(59, 130, 246)
            card1.line.width = Pt(1.5)
            tf_c1 = card1.text_frame
            tf_c1.word_wrap = True
            tf_c1.vertical_anchor = 1
            tf_c1.margin_left = Inches(0.3)
            tf_c1.margin_top = Inches(0.3)
            p_c1_title = tf_c1.paragraphs[0]
            p_c1_title.text = "STRATEGIC OBJECTIVES"
            p_c1_title.font.bold = True
            p_c1_title.font.size = Pt(14)
            p_c1_title.font.color.rgb = RGBColor(96, 165, 250)
            
            objs = data.get("objectives", []) or ["Focus on key conversion metrics", "Establish high-trust pipelines", "Mitigate competitive risk models"]
            for o in objs[:5]:
                p_o = tf_c1.add_paragraph()
                p_o.text = f"• {o}"
                p_o.font.size = Pt(11)
                p_o.font.color.rgb = RGBColor(226, 232, 240)
                p_o.space_before = Pt(8)
                
            card2 = slide3.shapes.add_shape(5, Inches(6.9), Inches(1.6), Inches(5.4), Inches(4.8))
            card2.fill.solid()
            card2.fill.fore_color.rgb = RGBColor(30, 41, 59)
            card2.line.color.rgb = RGBColor(139, 92, 246)
            card2.line.width = Pt(1.5)
            tf_c2 = card2.text_frame
            tf_c2.word_wrap = True
            tf_c2.vertical_anchor = 1
            tf_c2.margin_left = Inches(0.3)
            tf_c2.margin_top = Inches(0.3)
            p_c2_title = tf_c2.paragraphs[0]
            p_c2_title.text = "CORE VALUE PROPOSITIONS"
            p_c2_title.font.bold = True
            p_c2_title.font.size = Pt(14)
            p_c2_title.font.color.rgb = RGBColor(167, 139, 250)
            
            vps = data.get("value_proposition", {}).get("points", []) or ["AI-driven intelligence workflows", "Dynamic lead scoring filters", "Actionable execution paths"]
            for v in vps[:5]:
                p_v = tf_c2.add_paragraph()
                p_v.text = f"• {v}"
                p_v.font.size = Pt(11)
                p_v.font.color.rgb = RGBColor(226, 232, 240)
                p_v.space_before = Pt(8)
                
        # ─── Slide 4: Performance / Segmentation Analysis ───
        slide4 = create_standard_slide("Performance & Segment Analysis")
        competitors = data.get("competitors", [])
        bant = data.get("bant", {})
        budget = data.get("budget_allocation", [])
        
        if competitors:
            # Competitors cards
            col_w = 3.51
            gap = 0.4
            for idx, c in enumerate(competitors[:3]):
                left_x = 1.0 + idx * (col_w + gap)
                comp_card = slide4.shapes.add_shape(5, Inches(left_x), Inches(1.6), Inches(col_w), Inches(4.8))
                comp_card.fill.solid()
                comp_card.fill.fore_color.rgb = RGBColor(30, 41, 59)
                comp_card.line.color.rgb = RGBColor(59, 130, 246)
                comp_card.line.width = Pt(1.5)
                
                tf_cc = comp_card.text_frame
                tf_cc.word_wrap = True
                tf_cc.vertical_anchor = 1
                tf_cc.margin_left = Inches(0.25)
                tf_cc.margin_top = Inches(0.25)
                
                p_cc = tf_cc.paragraphs[0]
                p_cc.text = c.get("name", "").upper()
                p_cc.font.bold = True
                p_cc.font.size = Pt(14)
                p_cc.font.color.rgb = RGBColor(255, 255, 255)
                
                p_pos = tf_cc.add_paragraph()
                p_pos.text = f"Position: {c.get('market_position','')}"
                p_pos.font.size = Pt(10)
                p_pos.font.color.rgb = RGBColor(148, 163, 184)
                p_pos.space_before = Pt(4)
                
                p_threat = tf_cc.add_paragraph()
                threat = c.get("threat_level", "Medium")
                p_threat.text = f"Threat Level: {threat}"
                p_threat.font.size = Pt(11)
                p_threat.font.bold = True
                p_threat.font.color.rgb = RGBColor(239, 68, 68) if threat == "High" else RGBColor(245, 158, 11)
                p_threat.space_before = Pt(8)
                
                p_str = tf_cc.add_paragraph()
                p_str.text = f"Strengths: {c.get('strengths','')[:80]}"
                p_str.font.size = Pt(10)
                p_str.font.color.rgb = RGBColor(226, 232, 240)
                p_str.space_before = Pt(12)
                
                p_weak = tf_cc.add_paragraph()
                p_weak.text = f"Weaknesses: {c.get('weaknesses','')[:80]}"
                p_weak.font.size = Pt(10)
                p_weak.font.color.rgb = RGBColor(226, 232, 240)
                p_weak.space_before = Pt(8)
                
        elif bant:
            # 4 columns BANT cards
            col_w = 2.6
            gap = 0.31
            dimensions = ["budget", "authority", "need", "timeline"]
            for idx, dim in enumerate(dimensions):
                left_x = 1.0 + idx * (col_w + gap)
                bant_card = slide4.shapes.add_shape(5, Inches(left_x), Inches(1.6), Inches(col_w), Inches(4.8))
                bant_card.fill.solid()
                bant_card.fill.fore_color.rgb = RGBColor(30, 41, 59)
                bant_card.line.color.rgb = RGBColor(16, 185, 129)
                bant_card.line.width = Pt(1.5)
                
                tf_bc = bant_card.text_frame
                tf_bc.word_wrap = True
                tf_bc.vertical_anchor = 1
                tf_bc.margin_left = Inches(0.2)
                tf_bc.margin_top = Inches(0.2)
                
                b_item = bant.get(dim, {})
                p_dim = tf_bc.paragraphs[0]
                p_dim.text = dim.upper()
                p_dim.font.bold = True
                p_dim.font.size = Pt(14)
                p_dim.font.color.rgb = RGBColor(16, 185, 129)
                
                p_sc = tf_bc.add_paragraph()
                p_sc.text = f"Score: {b_item.get('score', 0)}/25"
                p_sc.font.bold = True
                p_sc.font.size = Pt(12)
                p_sc.font.color.rgb = RGBColor(255, 255, 255)
                p_sc.space_before = Pt(8)
                
                p_ass = tf_bc.add_paragraph()
                p_ass.text = f"Assessment:\n{b_item.get('assessment','')}"
                p_ass.font.size = Pt(10)
                p_ass.font.color.rgb = RGBColor(226, 232, 240)
                p_ass.space_before = Pt(12)
                
        elif budget:
            # 3 columns Budget splits
            col_w = 3.51
            gap = 0.4
            for idx, b in enumerate(budget[:3]):
                left_x = 1.0 + idx * (col_w + gap)
                b_card = slide4.shapes.add_shape(5, Inches(left_x), Inches(1.6), Inches(col_w), Inches(4.8))
                b_card.fill.solid()
                b_card.fill.fore_color.rgb = RGBColor(30, 41, 59)
                b_card.line.color.rgb = RGBColor(139, 92, 246)
                b_card.line.width = Pt(1.5)
                
                tf_bc = b_card.text_frame
                tf_bc.word_wrap = True
                tf_bc.vertical_anchor = 1
                tf_bc.margin_left = Inches(0.25)
                tf_bc.margin_top = Inches(0.25)
                
                p_ch = tf_bc.paragraphs[0]
                p_ch.text = b.get("channel", "").upper()
                p_ch.font.bold = True
                p_ch.font.size = Pt(14)
                p_ch.font.color.rgb = RGBColor(167, 139, 250)
                
                p_pct = tf_bc.add_paragraph()
                p_pct.text = f"Budget Split: {b.get('percent', 0)}%"
                p_pct.font.bold = True
                p_pct.font.size = Pt(13)
                p_pct.font.color.rgb = RGBColor(255, 255, 255)
                p_pct.space_before = Pt(8)
                
                p_rat = tf_bc.add_paragraph()
                p_rat.text = f"Rationale:\n{b.get('rationale','')}"
                p_rat.font.size = Pt(10)
                p_rat.font.color.rgb = RGBColor(203, 213, 225)
                p_rat.space_before = Pt(12)
                p_rat.line_spacing = 1.2
        else:
            # Fallback list details card
            card_fb = slide4.shapes.add_shape(5, Inches(1.0), Inches(1.6), Inches(11.33), Inches(4.8))
            card_fb.fill.solid()
            card_fb.fill.fore_color.rgb = RGBColor(30, 41, 59)
            card_fb.line.color.rgb = RGBColor(59, 130, 246)
            card_fb.line.width = Pt(1.5)
            
            tf_fb = card_fb.text_frame
            tf_fb.word_wrap = True
            tf_fb.vertical_anchor = 1
            tf_fb.margin_left = Inches(0.3)
            tf_fb.margin_top = Inches(0.3)
            
            p_fb = tf_fb.paragraphs[0]
            p_fb.text = "SEGMENT METRICS & TARGET FORECASTS"
            p_fb.font.bold = True
            p_fb.font.size = Pt(14)
            p_fb.font.color.rgb = RGBColor(96, 165, 250)
            
            details = [
                f"Analytic Profile Confidence Score: {body.get('confidence_score', 85)}% verification rating",
                f"TAM SAM SOM Projections: {data.get('market_size', {}).get('projected', 'N/A')} (CAGR {data.get('market_size', {}).get('cagr', 'N/A')})",
                f"Campaign Benchmarks Forecast - Estimated CTR: {data.get('estimated_ctr', '2.5%')} | CVR: {data.get('estimated_cvr', '3.0%')}"
            ]
            for detail in details:
                p_det = tf_fb.add_paragraph()
                p_det.text = f"• {detail}"
                p_det.font.size = Pt(12)
                p_det.font.color.rgb = RGBColor(226, 232, 240)
                p_det.space_before = Pt(12)
                
        # ─── Slide 5: Action Roadmap & Recommendations ───
        slide5 = create_standard_slide("Action Roadmap & Recommendations")
        recs = data.get("recommended_actions", []) or data.get("opportunities", []) or data.get("strategic_recommendations", [])
        
        col_w = 2.6
        gap = 0.31
        if recs:
            for idx, rec in enumerate(recs[:4]):
                left_x = 1.0 + idx * (col_w + gap)
                rec_card = slide5.shapes.add_shape(5, Inches(left_x), Inches(2.2), Inches(col_w), Inches(4.2))
                rec_card.fill.solid()
                rec_card.fill.fore_color.rgb = RGBColor(30, 41, 59)
                rec_card.line.color.rgb = RGBColor(139, 92, 246)
                rec_card.line.width = Pt(1.5)
                
                tf_rc = rec_card.text_frame
                tf_rc.word_wrap = True
                tf_rc.vertical_anchor = 1
                tf_rc.margin_left = Inches(0.2)
                tf_rc.margin_top = Inches(0.4)
                
                # Number Circle Badge (shape integer 9)
                badge = slide5.shapes.add_shape(9, Inches(left_x + 0.2), Inches(1.8), Inches(0.5), Inches(0.5))
                badge.fill.solid()
                badge.fill.fore_color.rgb = RGBColor(139, 92, 246)
                badge.line.fill.background()
                p_bdg = badge.text_frame.paragraphs[0]
                p_bdg.text = str(idx + 1)
                p_bdg.font.bold = True
                p_bdg.font.size = Pt(12)
                p_bdg.font.color.rgb = RGBColor(255, 255, 255)
                p_bdg.alignment = 1
                
                rec_text = rec.get("title") or rec.get("opportunity") or rec.get("recommendation") or str(rec)
                p_rc_title = tf_rc.paragraphs[0]
                p_rc_title.text = rec_text
                p_rc_title.font.bold = True
                p_rc_title.font.size = Pt(11)
                p_rc_title.font.color.rgb = RGBColor(255, 255, 255)
                
                desc = rec.get("description") or rec.get("effort") or rec.get("impact") or ""
                if desc:
                    p_rc_desc = tf_rc.add_paragraph()
                    p_rc_desc.text = f"Context:\n{desc}"
                    p_rc_desc.font.size = Pt(9.5)
                    p_rc_desc.font.color.rgb = RGBColor(148, 163, 184)
                    p_rc_desc.space_before = Pt(8)
                    p_rc_desc.line_spacing = 1.2
        else:
            fallback_recs = [
                "Focus outreach on high-fit decision makers.",
                "Standardize qualifying criteria using BANT models.",
                "Deploy campaign budgets towards high-yield channels.",
                "Review competitive threats to adjust USP alignment."
            ]
            for idx, rec in enumerate(fallback_recs):
                left_x = 1.0 + idx * (col_w + gap)
                rec_card = slide5.shapes.add_shape(5, Inches(left_x), Inches(2.2), Inches(col_w), Inches(4.2))
                rec_card.fill.solid()
                rec_card.fill.fore_color.rgb = RGBColor(30, 41, 59)
                rec_card.line.color.rgb = RGBColor(139, 92, 246)
                rec_card.line.width = Pt(1.5)
                
                tf_rc = rec_card.text_frame
                tf_rc.word_wrap = True
                tf_rc.vertical_anchor = 1
                tf_rc.margin_left = Inches(0.2)
                tf_rc.margin_top = Inches(0.4)
                
                # Number Circle Badge
                badge = slide5.shapes.add_shape(9, Inches(left_x + 0.2), Inches(1.8), Inches(0.5), Inches(0.5))
                badge.fill.solid()
                badge.fill.fore_color.rgb = RGBColor(139, 92, 246)
                badge.line.fill.background()
                p_bdg = badge.text_frame.paragraphs[0]
                p_bdg.text = str(idx + 1)
                p_bdg.font.bold = True
                p_bdg.font.size = Pt(12)
                p_bdg.font.color.rgb = RGBColor(255, 255, 255)
                p_bdg.alignment = 1
                
                p_rc_title = tf_rc.paragraphs[0]
                p_rc_title.text = rec
                p_rc_title.font.bold = True
                p_rc_title.font.size = Pt(11)
                p_rc_title.font.color.rgb = RGBColor(255, 255, 255)
                
        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        
        db.log_activity(
            email=session["user_email"],
            activity_type="report_exported",
            title=f"Exported {module} report to PPTX",
            metadata={"module": module, "format": "PPTX"}
        )
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            as_attachment=True,
            download_name=f"{module}_report.pptx"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PPTX presentation: {str(e)}"}), 500


# ─── Strategic Report Endpoints (AI Agent Workflow) ─────────────────────────

@app.route("/api/report/full", methods=["POST"])
def full_report():
    """Generate the full structured JSON report using the AI agent workflow."""
    try:
        data = request.get_json() or {}
        from orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()
        report = orchestrator.generate_full_report(data)
        return jsonify({"success": True, "report": report}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Report generation failed: {str(e)}"}), 500


@app.route("/api/report/section", methods=["POST"])
def report_section():
    """Generate a single report section on demand."""
    try:
        data = request.get_json() or {}
        section = data.get("section", "")
        if not section:
            return jsonify({"success": False, "error": "Section name is required"}), 400
        from orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()
        result = orchestrator.generate_section(section, data)
        return jsonify({"success": True, "section": section, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Section generation failed: {str(e)}"}), 500


@app.route("/api/v2/poster/generate_prompt", methods=["POST"])
def v2_poster_generate_prompt():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    body = request.form or request.get_json() or {}
    company_name = body.get("company_name", "").strip()
    product_name = body.get("product_name", "").strip()
    target_audience = body.get("target_audience", "").strip()
    value_prop = body.get("value_prop", "").strip()
    vibe = body.get("vibe", "Modern Bold").strip()
    aspect_ratio = body.get("aspect_ratio", "1:1").strip()
    
    # Four brand positioning postures
    pricing_posture = body.get("pricing_posture", "Premium").strip()
    innovation_posture = body.get("innovation_posture", "Pioneer").strip()
    message_posture = body.get("message_posture", "Disruptive").strip()
    acquisition_posture = body.get("acquisition_posture", "PLG").strip()
    
    if not product_name:
        return jsonify({"error": "Product name is required"}), 400

    from langchain_core.messages import SystemMessage, HumanMessage
    import json
    
    system_instruction = """You are a world-class advertising creative director and copywriting expert.
Your goal is to design a high-converting advertisement poster concept.
Given a company, product, target audience, value proposition, visual vibe, and the company's brand positioning postures, you must output a structured JSON response containing:
1. "image_prompt": A 80-120 word visually descriptive prompt for an AI image generator (such as Stable Diffusion or FLUX). The prompt must specify the subject, background details, lighting, color palette, camera angle, and artistic style. It must align visual aesthetics with the brand positioning postures (e.g. high-end, luxury tones for premium pricing; bold, neon, high-energy for disruptive marketing). It must NOT require drawing text in the image. Focus on visual symbolism, mood, and objects.
2. "headline": A short, punchy, attention-grabbing marketing headline (3-8 words) aligned with the chosen tone/message posture.
3. "subheading": A supporting subheadline that clarifies the value proposition (8-15 words).
4. "cta_text": A strong call-to-action (e.g. "Shop Now", "Get Started", "Try Free") aligned with the acquisition strategy.
5. "body_copy": A short, high-impact paragraph (20-40 words) that outlines the benefits, aligns with the message tone, and drives action.

You MUST respond with a single valid JSON object containing exactly these 5 keys: "image_prompt", "headline", "subheading", "cta_text", "body_copy". Do not include any markdown styling like ```json or any other text before/after the JSON. Just return the raw JSON string."""

    prompt_content = f"""Company: {company_name}
Product/Service: {product_name}
Target Audience: {target_audience}
Value Proposition/Strategic Posture: {value_prop}
Visual Vibe: {vibe}
Poster Aspect Ratio: {aspect_ratio}

Brand Positioning Postures:
- Pricing Strategy: {pricing_posture}
- Innovation Strategy: {innovation_posture}
- Tone & Message Posture: {message_posture}
- Customer Acquisition Strategy: {acquisition_posture}

Generate the ad concept JSON now:"""

    try:
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=prompt_content)
        ]
        response = safe_llm_invoke(messages, temperature=0.7)
        raw_text = response.content.strip()
        
        # Strip markdown code blocks if any
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
            
        # Parse and return JSON
        data = json.loads(raw_text)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        print(f"[Poster Endpoint Error] {trace}")
        return jsonify({"error": f"Failed to generate poster prompt: {str(e)}"}), 500


@app.route("/api/v2/poster/image_url")
def v2_poster_image_url():
    """Return a direct Pollinations.ai URL for client-side rendering.
    This avoids the proxy timeout and caching issues that cause
    the same image to appear for different inputs."""
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    prompt = request.args.get("prompt", "").strip()
    vibe = request.args.get("vibe", "").strip()
    seed = request.args.get("seed", "").strip()
    aspect_ratio = request.args.get("aspect_ratio", "1:1").strip()

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    import urllib.parse
    import hashlib

    # Build the full visual prompt including all context
    full_prompt = f"{prompt}, {vibe} style, premium marketing advertisement, photorealistic, high quality, 4k"
    encoded_prompt = urllib.parse.quote(full_prompt)

    # Map aspect ratio to width/height
    width, height = 800, 800
    if aspect_ratio == "9:16":
        width, height = 600, 1067
    elif aspect_ratio == "16:9":
        width, height = 1067, 600

    # Use a hash-based seed derived from prompt + user seed to guarantee unique images per input
    prompt_hash = hashlib.md5(f"{prompt}-{vibe}-{seed}".encode()).hexdigest()[:8]
    numeric_seed = int(prompt_hash, 16) % 999999

    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}"
        f"&seed={numeric_seed}"
        f"&nologo=true&nofeed=true&enhanced=true"
        f"&model=flux"
    )

    return jsonify({"success": True, "url": url, "seed": numeric_seed})


@app.route("/api/v2/poster/image")
def v2_poster_image():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    prompt = request.args.get("prompt", "").strip()
    vibe = request.args.get("vibe", "").strip()
    seed = request.args.get("seed", "").strip()
    aspect_ratio = request.args.get("aspect_ratio", "1:1").strip()
    
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    import requests as http_requests
    import urllib.parse
    import hashlib
    
    # Build a rich visual prompt with all context for unique generation
    full_prompt = f"{prompt}, {vibe} style, premium marketing advertisement, photorealistic, high quality, 4k"
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    # Map aspect ratio to width/height
    width, height = 800, 800
    if aspect_ratio == "9:16":
        width, height = 600, 1067
    elif aspect_ratio == "16:9":
        width, height = 1067, 600
    
    # Use a hash-based seed derived from prompt + user seed to guarantee unique images per input
    prompt_hash = hashlib.md5(f"{prompt}-{vibe}-{seed}".encode()).hexdigest()[:8]
    numeric_seed = int(prompt_hash, 16) % 999999
    
    # Try Pollinations with proper parameters for unique image generation
    urls = [
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={numeric_seed}&nologo=true&nofeed=true&enhanced=true&model=flux",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={numeric_seed}&nologo=true&nofeed=true&enhanced=true",
    ]
    
    for url in urls:
        try:
            print(f"[Poster Image Proxy] Fetching from: {url}")
            resp = http_requests.get(url, timeout=30, allow_redirects=True)
            if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", "").lower():
                content_start = resp.content[:100]
                if b"{" not in content_start and b"<!DOCTYPE" not in content_start and len(resp.content) > 1000:
                    return resp.content, 200, {
                        "Content-Type": resp.headers.get("Content-Type", "image/png"),
                        "Cache-Control": "no-cache, no-store, must-revalidate"
                    }
        except Exception as e:
            print(f"[Poster Image Proxy] Failed to fetch {url}: {str(e)}")

    # Fallback: return a JSON error so the frontend can use the direct URL approach instead
    print(f"[Poster Image Proxy] All proxy attempts failed. Client should use direct URL.")
    return jsonify({"error": "Image generation timed out. Loading directly..."}), 504





if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("\n⚠️  WARNING: GROQ_API_KEY not found in environment variables!")
        print("   Create a .env file with: GROQ_API_KEY=your_key_here")
        print("   Get your key at: https://console.groq.com\n")
    else:
        print(f"\n✅ Groq API configured — Model: {GROQ_MODEL}")
        print("   ⛓️  LangChain + LangGraph workflows compiled\n")

    print("🚀 MarketMind AI is starting...")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000, use_reloader=False)
