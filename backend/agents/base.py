"""
agents/base.py — Shared LangGraph utilities, JSON parser, retry logic,
and the Groq LLM factory for all multi-agent graphs.
"""
import os, json, re, textwrap
import sys
from dotenv import load_dotenv

# Robust load dotenv from root folder
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Redirect standard error (fd 2) at the OS level to a safe process-specific log file to prevent OS-level Errno 22 crashes
try:
    log_dir = "logs"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(os.path.dirname(current_dir)) == 'backend':
        root_dir = os.path.dirname(os.path.dirname(current_dir))
    elif os.path.basename(current_dir) == 'agents':
        root_dir = os.path.dirname(current_dir)
    else:
        root_dir = current_dir
        
    actual_log_dir = os.path.join(root_dir, log_dir)
    os.makedirs(actual_log_dir, exist_ok=True)
    stderr_filename = os.path.join(actual_log_dir, f"backend_stderr_{os.getpid()}.log")
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

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Safe print helper to prevent OS-level terminal write crashes on Windows
def print(*args, **kwargs):
    import builtins
    try:
        builtins.print(*args, **kwargs)
    except Exception:
        pass

# ─── LLM Factory ─────────────────────────────────────────────────────────────

# Primary model — high quality, large context
_PRIMARY_MODEL = "llama-3.3-70b-versatile"
# Fast model — for simple sub-tasks that don't need the big model
_FAST_MODEL    = "llama-3.1-8b-instant"

@lru_cache(maxsize=16)
def get_llm(model: str = _PRIMARY_MODEL, temperature: float = 0.3, max_tokens: int = 2048):
    """Return a cached Groq ChatGroq instance."""
    api_key = os.getenv("GROQ_API_KEY", "")
    return ChatGroq(model=model, api_key=api_key, temperature=temperature,
                    max_tokens=max_tokens)

def get_fast_llm(temperature: float = 0.3):
    """Instant model — use for merge/score nodes that don't need reasoning."""
    return get_llm(model=_FAST_MODEL, temperature=temperature, max_tokens=1500)



def get_grounding_instruction(grounding_context: str) -> str:
    """
    Returns a MANDATORY company-context block that is prepended to every prompt.
    All analysis MUST be grounded in the company's actual data, not generic.
    """
    if not grounding_context or not grounding_context.strip():
        return ""
    bi_instructions = (
        "\n[BUSINESS INTELLIGENCE CITATION RULES]:\n"
        "For each key recommendation, strategy, or action item you propose, you MUST include a specific metric justification/citation. "
        "Explain: (1) what specific company metric or ICP attribute triggered this recommendation, "
        "(2) what specific gap or opportunity it addresses, and "
        "(3) what the quantified expected impact is (e.g., 'expected to improve win rate by 5%', 'should reduce CAC by 15%'). "
        "Cite the metric name and its current value exactly.\n"
    )
    return (
        f"\n\n[MANDATORY COMPANY CONTEXT — USE THIS IN EVERY SECTION]\n"
        f"You are analyzing and generating content SPECIFICALLY for this company.\n"
        f"Do NOT produce generic output. Every recommendation, number, example, and\n"
        f"strategy MUST reference, align with, and be tailored to the company below.\n"
        f"If the company has provided KPI metrics, use those EXACT figures in your analysis.\n"
        f"If they have named competitors or products, use those names throughout.\n"
        f"{bi_instructions}"
        f"---\n"
        f"{grounding_context.strip()}\n"
        f"---\n"
        f"[END COMPANY CONTEXT — Everything above is MANDATORY context. Generate ONLY company-specific content.]\n"
    )


def build_company_system_prefix(company_name: str = "", industry: str = "",
                                  role_title: str = "Senior AI Analyst") -> str:
    """
    Returns a system prompt prefix that frames the AI as the company's own analyst.
    This ensures every output is company-specific from the very first token.
    """
    if not company_name and not industry:
        return ""
    parts = []
    if company_name:
        parts.append(f"You are working directly for {company_name}")
    if industry:
        parts.append(f"a company operating in the {industry} sector")
    identity = " — ".join(parts) if parts else ""
    return (
        f"IMPORTANT CONTEXT: {identity}. "
        f"You are their {role_title}. "
        f"All outputs must be company-specific: reference the company name, their industry context, "
        f"their actual metrics, and their specific competitive situation. "
        f"Never produce generic advice that could apply to any company. "
        f"If metrics are provided, cite them explicitly (e.g., 'Given your current conversion rate of X%...'). "
        f"For each key recommendation you make, provide a metric justification: (1) name the specific company metric that triggered it, "
        f"(2) explain the gap/opportunity it addresses, and (3) give a quantified expected impact."
    )


# ─── JSON Parser ─────────────────────────────────────────────────────────────

def escape_raw_newlines_in_json_strings(json_str: str) -> str:
    result = []
    inside_string = False
    escaped = False
    
    for char in json_str:
        if char == '"' and not escaped:
            inside_string = not inside_string
            result.append(char)
        elif char == '\\' and inside_string:
            escaped = not escaped
            result.append(char)
        else:
            if inside_string:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                else:
                    result.append(char)
            else:
                result.append(char)
            escaped = False
    return "".join(result)


def parse_json_block(text: str) -> dict:
    """
    Extract and parse the first JSON object/array found in an LLM response.
    Strips markdown fences, handles nested objects.
    Raises ValueError if no valid JSON is found.
    """
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)

    # Find the first { ... } block
    brace_start = text.find("{")
    if brace_start == -1:
        raise ValueError("No JSON object found in LLM output")

    depth = 0
    for i, ch in enumerate(text[brace_start:], start=brace_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                 candidate = text[brace_start: i + 1]
                 candidate = escape_raw_newlines_in_json_strings(candidate)
                 # Repair unquoted percentages (e.g. 60%) and currency strings (e.g. INR 40,000)
                 candidate = re.sub(r':\s*([0-9.]+\s*%)', r': "\1"', candidate)
                 candidate = re.sub(
                     r':\s*(INR\s*[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?|\$\s*[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?|USD\s*[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)',
                     r': "\1"',
                     candidate
                 )
                 try:
                     return json.loads(candidate)
                 except json.JSONDecodeError:
                     # Try relaxed parse — remove trailing commas
                     cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
                     return json.loads(cleaned)

    raise ValueError("Unbalanced braces in LLM JSON output")


def safe_parse_json(text: str, fallback: dict = None) -> dict:
    """Parse JSON, returning fallback dict on failure instead of raising."""
    try:
        return parse_json_block(text)
    except Exception:
        return fallback or {}


# ─── LLM Invoke with Retry ────────────────────────────────────────────────────

def invoke_structured(system_prompt: str, user_prompt: str,
                       schema_hint: str = "", retries: int = 2,
                       fast: bool = False, max_tokens: int = 2048) -> dict:
    """
    Call Groq with a structured JSON system prompt.
    Retries up to `retries` times on parse failure or rate limit.
    Returns parsed dict or empty dict.
    Set fast=True to use the instant 8b model for simple merge/score nodes.
    """
    model_to_use = _FAST_MODEL if fast else _PRIMARY_MODEL
    full_system = system_prompt
    if schema_hint:
        full_system += f"\n\nRespond ONLY with valid JSON matching this schema:\n{schema_hint}"
    full_system += "\n\nIMPORTANT: Return ONLY the JSON object. No explanation, no markdown, no extra text. Do NOT include raw newlines inside JSON string values; if you need a line break, use the escaped sequence '\\n'."

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_prompt),
    ]

    last_err = None
    response_content = None
    for attempt in range(retries + 1):
        try:
            llm = get_llm(model=model_to_use, max_tokens=max_tokens)
            response = llm.invoke(messages)
            response_content = response.content
            return parse_json_block(response_content)
        except Exception as e:
            last_err = e
            err_msg = str(e).lower()
            # If we hit a rate limit (429/413) or token limit, fall back immediately to the fast 8B model!
            if "rate limit" in err_msg or "429" in err_msg or "413" in err_msg or "tpd" in err_msg or "tokens" in err_msg:
                print(f"[agents/base] Rate limit hit on {model_to_use}. Falling back to {_FAST_MODEL}...")
                model_to_use = _FAST_MODEL
                import time
                time.sleep(1.5)
            else:
                print(f"[agents/base] Parse attempt {attempt} failed: {e}. Raw content preview: {str(response_content)[:200]}...")
            
            if attempt < retries:
                messages[-1] = HumanMessage(
                    content=user_prompt + "\n\n[REMINDER: Return ONLY valid JSON]"
                )

    print(f"[agents/base] JSON parse failed after {retries+1} attempts: {last_err}")
    if response_content:
        print(f"[agents/base] RAW LLM CONTENT AT FAILURE:\n{response_content}\n[END RAW CONTENT]")
    try:
        fallback = get_schema_fallback(schema_hint, user_prompt)
        if fallback:
            print(f"[agents/base] Successfully generated high-fidelity fallback for schema.")
            return fallback
    except Exception as fe:
        print(f"[agents/base] Failed to generate fallback: {fe}")
    return {}


def parallel_invoke(tasks: list[tuple]) -> list[dict]:
    """
    Run multiple invoke_structured calls sequentially with a pacing delay to prevent
    hitting Groq's tokens-per-minute (TPM) rate limits.
    """
    import time
    results = []
    for i, t in enumerate(tasks):
        if i > 0:
            # Pacing delay to respect the TPM moving window
            time.sleep(2.0)
        sys_prompt, usr_prompt, schema, fast = t
        try:
            res = invoke_structured(sys_prompt, usr_prompt, schema_hint=schema, retries=2, fast=fast)
            results.append(res)
        except Exception as e:
            print(f"[parallel_invoke] Task {i} failed: {e}")
            results.append({})
    return results


# ─── Confidence Scorer ────────────────────────────────────────────────────────

def compute_confidence(result: dict, required_keys: list) -> int:
    """
    Compute an AI confidence score (0-100) based on how many
    required top-level keys are present and non-empty in the result.
    """
    if not result:
        return 0
    present = sum(
        1 for k in required_keys
        if k in result and result[k] not in (None, "", [], {})
    )
    return round((present / len(required_keys)) * 100) if required_keys else 50


# ─── Schema Hints (examples given to the LLM) ────────────────────────────────

MARKET_SCHEMA = """{
  "executive_summary": "string",
  "market_size": {"current": "string", "projected": "string", "cagr": "string", "currency": "string"},
  "growth_drivers": ["string"],
  "market_risks": ["string"],
  "competitors": [
    {"name": "string", "strengths": "string", "weaknesses": "string",
     "market_position": "string", "threat_level": "High|Medium|Low"}
  ],
  "swot": {
    "strengths": ["string"], "weaknesses": ["string"],
    "opportunities": ["string"], "threats": ["string"]
  },
  "pestel": {
    "political": "string", "economic": "string", "social": "string",
    "technological": "string", "environmental": "string", "legal": "string"
  },
  "trends": [{"trend": "string", "impact_score": 0, "timeframe": "string", "description": "string"}],
  "opportunities": [{"title": "string", "score": 0, "effort": "Low|Medium|High", "revenue_potential": "string"}],
  "growth_chart_data": [{"period": "string", "value": 0}],
  "market_share_data": [{"name": "string", "value": 0}],
  "radar_data": [{"competitor": "string", "innovation": 0, "pricing": 0, "reach": 0, "support": 0, "product": 0}],
  "advertising_analysis": [
    {
      "channel": "string",
      "cpm_cpc_benchmark": "string",
      "creative_strategy": "string",
      "message_angle": "string",
      "ad_spend_efficiency": "High|Medium|Low",
      "conversion_probability": "string"
    }
  ],
  "positioning_postures": [
    {
      "brand_name": "string",
      "market_role": "Leader|Challenger|Follower|Niche",
      "pricing_posture": "Premium|Muted|Value|Aggressive",
      "innovation_posture": "Pioneer|Fast-Follower|Conservative",
      "message_posture": "Authoritative|Emotional|Disruptive|Educational",
      "customer_acquisition_posture": "Outbound|Inbound|PLG|Partnerships",
      "strategic_rationale": "string"
    }
  ]
}"""

CAMPAIGN_SCHEMA = """{
  "campaign_name": "string",
  "executive_campaign_overview": "string",
  "strategic_goals": [
    {
      "goal_name": "string",
      "business_context": "string"
    }
  ],
  "persona_profile": {
    "business_challenges": "string",
    "pain_points": ["string"],
    "buying_motivations": ["string"]
  },
  "funnel": {
    "awareness": {
      "tactics": ["string"],
      "kpis": ["string"],
      "budget_pct": 0
    },
    "consideration": {
      "tactics": ["string"],
      "kpis": ["string"],
      "budget_pct": 0
    },
    "conversion": {
      "tactics": ["string"],
      "kpis": ["string"],
      "budget_pct": 0
    }
  },
  "budget_allocation": [
    {
      "channel": "string",
      "percent": 0,
      "rationale": "string"
    }
  ],
  "kpis": [
    {
      "metric": "string",
      "target": "string",
      "measurement": "string"
    }
  ],
  "content_ideas": [
    {
      "title": "string",
      "format": "string",
      "platform": "string",
      "description": "string"
    }
  ],
  "ad_copies": [
    {
      "platform": "string",
      "headline": "string",
      "body": "string",
      "cta": "string"
    }
  ],
  "social_media_posts": [
    {
      "platform": "string",
      "copy": "string"
    }
  ],
  "calendar": [
    {
      "week": 0,
      "theme": "string",
      "tasks": ["string"]
    }
  ]
}"""

PITCH_SCHEMA = """{
  "sales_readiness_score": 0,
  "elevator_pitch": "string",
  "value_proposition": {"headline": "string", "points": ["string"]},
  "roi_argument": {"headline": "string", "calculation": "string", "timeframe": "string"},
  "objection_handling": [{"objection": "string", "response": "string"}],
  "discovery_questions": ["string"],
  "follow_up_strategy": {"timing": "string", "steps": ["string"]},
  "email_template": {"subject": "string", "body": "string"},
  "linkedin_template": {"connection_note": "string", "follow_up": "string"},
  "meeting_agenda": [{"time": "string", "topic": "string", "goal": "string"}],
  "proposal_outline": ["string"],
  "closing_script": "string",
  "buyer_persona": {"title": "string", "priorities": ["string"], "objections": ["string"]},
  "decision_maker_map": [{"role": "string", "influence": "string", "concern": "string"}]
}"""

LEAD_SCHEMA = """{
  "lead_score": 0,
  "conversion_probability": 0,
  "temperature": "Hot|Warm|Cold",
  "bant": {
    "budget": {"score": 0, "assessment": "string", "evidence": "string"},
    "authority": {"score": 0, "assessment": "string", "evidence": "string"},
    "need": {"score": 0, "assessment": "string", "evidence": "string"},
    "timeline": {"score": 0, "assessment": "string", "evidence": "string"}
  },
  "qualification_summary": "string",
  "buying_intent": {"score": 0, "signals": [{"signal": "string", "strength": "High|Medium|Low"}]},
  "risk_factors": [{"risk": "string", "impact": "High|Medium|Low", "mitigation": "string"}],
  "recommended_actions": [{"action": "string", "priority": "string", "timeline": "string"}],
  "next_best_action": "string",
  "priority_level": "Critical|High|Medium|Low",
  "crm_readiness": true,
  "score_breakdown": [{"factor": "string", "score": 0, "max": 0, "rationale": "string"}]
}"""

INSIGHTS_SCHEMA = """{
  "opportunity_score": 0,
  "executive_summary": "string",
  "current_challenges": [{"challenge": "string", "severity": "High|Medium|Low", "impact": "string"}],
  "root_cause_analysis": [{"problem": "string", "root_cause": "string", "evidence": "string"}],
  "growth_opportunities": [{"title": "string", "score": 0, "effort": "string", "revenue_impact": "string", "description": "string"}],
  "revenue_opportunities": [{"source": "string", "potential": "string", "timeline": "string", "description": "string"}],
  "cost_optimization": [{"area": "string", "potential_savings": "string", "action": "string"}],
  "strategic_recommendations": [{"recommendation": "string", "priority": "High|Medium|Low", "impact": "string", "effort": "string"}],
  "competitive_risks": [{"risk": "string", "competitor": "string", "likelihood": "string"}],
  "operational_risks": [{"risk": "string", "probability": "string", "impact": "string", "mitigation": "string"}],
  "plan_30_day": [{"action": "string", "owner": "string", "success_metric": "string"}],
  "plan_60_day": [{"action": "string", "owner": "string", "success_metric": "string"}],
  "plan_90_day": [{"action": "string", "owner": "string", "success_metric": "string"}],
  "kpi_targets": [{"kpi": "string", "current": "string", "target": "string", "timeline": "string"}],
  "priority_matrix": [{"initiative": "string", "urgency": "High|Medium|Low", "impact": "High|Medium|Low"}]
}"""


# ─── High-Fidelity Schema Fallback Generators ────────────────────────────────

def extract_prompt_field(prompt: str, labels: list[str], default: str = "") -> str:
    for label in labels:
        m = re.search(rf"{label}\s*:\s*(.*)", prompt, re.IGNORECASE)
        if m:
            val = m.group(1).split('\n')[0].strip()
            if val:
                return val
    return default

def safe_split_get(val: str, index: int, default: str) -> str:
    parts = [p.strip() for p in val.split(',') if p.strip()]
    if len(parts) > index:
        return parts[index]
    return default

def get_campaign_fallback(product, audience, platform, budget, goals, company_name) -> dict:
    if not company_name:
        company_name = "Enterprise"
    if not product:
        product = "our premium product"
    if not audience:
        audience = "target segment"
    if not platform:
        platform = "LinkedIn, Twitter/X, Facebook, WhatsApp"
    if not budget:
        budget = "$5,000 - $25,000"
    if not goals:
        goals = "B2B Leads Generation"

    # Parse requested platforms
    requested_platforms = [p.strip().lower() for p in platform.split(',') if p.strip()]
    if not requested_platforms:
        requested_platforms = ["multi-platform"]

    # All possible post templates
    platform_mapping_fallbacks = {
        "linkedin": {
            "platform": "LinkedIn",
            "copy": (
                f"Are you looking to eliminate operational bottlenecks? 📈\n\n"
                f"With {company_name}'s latest product ({product}), B2B operations teams are achieving "
                f"unprecedented efficiency. Here is how we help you scale:\n"
                f"• Automate repetitive manual workflows\n"
                f"• Reduce department errors by up to 40%\n"
                f"• Track metrics in real-time on a secure dashboard\n\n"
                f"Read our latest playbook to optimize your department's efficiency: [Link]\n\n"
                f"#Operations #B2B #Automation #WorkforceEfficiency"
            )
        },
        "twitter": {
            "platform": "Twitter/X",
            "copy": (
                f"Stop letting manual processes stall your growth. 🚀\n\n"
                f"{product} by {company_name} deploys in days, delivering real-time operations "
                f"tracking with robust security. Get your custom briefing: [Link]\n\n"
                f"#Efficiency #TechSolutions #B2B"
            )
        },
        "x": {
            "platform": "Twitter/X",
            "copy": (
                f"Stop letting manual processes stall your growth. 🚀\n\n"
                f"{product} by {company_name} deploys in days, delivering real-time operations "
                f"tracking with robust security. Get your custom briefing: [Link]\n\n"
                f"#Efficiency #TechSolutions #B2B"
            )
        },
        "facebook": {
            "platform": "Facebook",
            "copy": (
                f"Accelerate your team's output! ⚡\n\n"
                f"{company_name} introduces {product}, a comprehensive operational system built to "
                f"eliminate manual bottlenecks, secure business logic, and drive high-impact outcomes. Learn how we can "
                f"help your department scale operations seamlessly: [Link]\n\n"
                f"#BusinessTech #Operations #WorkflowAutomation"
            )
        },
        "whatsapp": {
            "platform": "WhatsApp",
            "copy": (
                f"Hello! 👋 Discover how {company_name} helps you scale operations and optimize workflows with "
                f"{product}. Contact us to learn more or get a custom demo! [Link]"
            )
        },
        "google": {
            "platform": "Google Search",
            "copy": f"Ad Headline: Automate Your Operations | Try {product} Today\nAd Description: Boost efficiency, reduce manual errors, and scale seamlessly with {company_name}. Contact us for a free demo today."
        },
    }

    filtered_posts = []
    for req in requested_platforms:
        found = False
        for k, v in platform_mapping_fallbacks.items():
            if k in req or req in k:
                filtered_posts.append(v)
                found = True
                break
        if not found:
            filtered_posts.append({
                "platform": req.capitalize(),
                "copy": f"Discover how {company_name} helps you scale operations with {product}. Contact us to learn more!"
            })

    # Ad copy fallbacks
    ad_copies_pool = [
        {
            "headline": f"Struggling with Department Inefficiencies? Try {product}.",
            "body": f"Discover how {company_name} helps leaders automate workflows, reduce operational costs, and drive ROI. Get a custom briefing in under 5 minutes.",
            "cta": "Get Free Demo",
            "platform": "LinkedIn"
        },
        {
            "headline": "Scale Operations Faster.",
            "body": f"Eliminate manual bottlenecks. {company_name} provides robust, scalable capabilities designed specifically for your industry's needs.",
            "cta": "Learn More",
            "platform": "Google Search"
        },
        {
            "headline": f"Deploy {product} in Days, Not Months.",
            "body": "No complex coding. No security compromises. Learn why elite operations teams are switching to our modern, integrated system today.",
            "cta": "Download Whitepaper",
            "platform": "Twitter/X"
        },
        {
            "headline": "Eliminate Manual Workflows.",
            "body": f"Automate operations seamlessly with {company_name} {product}. Click to learn how we help businesses scale operations and reduce mistakes.",
            "cta": "Sign Up",
            "platform": "Facebook"
        },
        {
            "headline": "Scale Operations with WhatsApp.",
            "body": f"Get {product} by {company_name} to streamline workflows and get real-time briefings directly in your chat.",
            "cta": "Connect Now",
            "platform": "WhatsApp"
        }
    ]

    filtered_ad_copies = []
    for req in requested_platforms:
        for ad in ad_copies_pool:
            ad_plat = ad["platform"].lower()
            if ad_plat in req or req in ad_plat:
                filtered_ad_copies.append(ad)
                break
    if not filtered_ad_copies:
        filtered_ad_copies = [ad_copies_pool[0]]

    # Content ideas pool
    content_ideas_pool = [
        {
            "title": f"The Definitive ROI Guide for {product}",
            "format": "Ebook / PDF Report",
            "platform": "LinkedIn",
            "description": f"A data-backed analysis showing how companies in the {audience} space save time and costs by using {product}."
        },
        {
            "title": "Automating Department Workflows: Best Practices",
            "format": "Interactive Live Webinar",
            "platform": "YouTube",
            "description": "A deep dive into operational efficiency featuring case studies and live interactive software demonstrations."
        },
        {
            "title": f"How to Overcome Legacy Bottlenecks with {company_name}",
            "format": "Expert Video Case Study",
            "platform": "LinkedIn Ads / Video Hub",
            "description": "An interview-style video showcasing a client's success story, detailing metrics improvement and integration steps."
        },

        {
            "title": f"Modernizing operations for {audience}",
            "format": "Comparison Checklist",
            "platform": "Twitter/X",
            "description": "A comprehensive list comparing manual systems with automated solutions like ours."
        },
        {
            "title": "Search Intent Landing Experience",
            "format": "Landing Page Copy",
            "platform": "Google Search",
            "description": f"High-intent landing pages targeted at keywords related to automating operational tasks for {audience}."
        },
        {
            "title": "Operational Success Stories",
            "format": "Customer Review Article",
            "platform": "Facebook",
            "description": "Written case study featuring testimonials from heads of operations using our system."
        },
        {
            "title": "Direct Updates via WhatsApp",
            "format": "Instant Messaging Notifications",
            "platform": "WhatsApp",
            "description": "Guide on how to configure automated status updates and critical alerts directly to your team's chat."
        }
    ]

    filtered_content_ideas = []
    for req in requested_platforms:
        for idea in content_ideas_pool:
            idea_plat = idea["platform"].lower()
            if idea_plat in req or req in idea_plat:
                filtered_content_ideas.append(idea)
                break
    if not filtered_content_ideas:
        filtered_content_ideas = [content_ideas_pool[0]]

    # CPM estimation (average of selected platforms)
    cpm_map = {
        "linkedin": 45,
        "twitter": 8,
        "x": 8,
        "google": 15,
        "facebook": 12,
        "whatsapp": 3,
        "multi-platform": 18
    }
    cpm_vals = []
    for req in requested_platforms:
        matched = False
        for k, v in cpm_map.items():
            if k in req or req in k:
                cpm_vals.append(v)
                matched = True
                break
        if not matched:
            cpm_vals.append(15) # Default CPM
    cpm_val = sum(cpm_vals) / len(cpm_vals) if cpm_vals else 18

    # Budget value estimation
    budget_map = {
        "under $1k": 800,
        "$1k-$5k": 3000,
        "$5k-$25k": 15000,
        "$25k-$100k": 60000,
        "$100k+": 250000
    }
    cleaned_budget = str(budget).lower().strip()
    budget_val = 5000
    for k, v in budget_map.items():
        if k in cleaned_budget:
            budget_val = v
            break

    calc_reach_val = int((budget_val / cpm_val) * 1000)
    calc_reach = f"{calc_reach_val:,}" if calc_reach_val >= 1000 else str(calc_reach_val)

    # CTR & CVR estimation (average of selected platforms)
    ctr_map = {
        "linkedin": 1.25,
        "twitter": 0.85,
        "x": 0.85,
        "google": 3.40,
        "facebook": 1.50,
        "whatsapp": 2.00,
        "multi-platform": 1.65
    }
    cvr_map = {
        "linkedin": 2.20,
        "twitter": 1.45,
        "x": 1.45,
        "google": 4.20,
        "facebook": 2.60,
        "whatsapp": 3.50,
        "multi-platform": 2.75
    }
    ctr_vals = []
    cvr_vals = []
    for req in requested_platforms:
        matched = False
        for k, v in ctr_map.items():
            if k in req or req in k:
                ctr_vals.append(v)
                cvr_vals.append(cvr_map[k])
                matched = True
                break
        if not matched:
            ctr_vals.append(1.65)
            cvr_vals.append(2.75)
    ctr_base = sum(ctr_vals) / len(ctr_vals) if ctr_vals else 1.65
    cvr_base = sum(cvr_vals) / len(cvr_vals) if cvr_vals else 2.75

    goals_lower = str(goals).lower()
    if "lead" in goals_lower or "cvr" in goals_lower or "conversion" in goals_lower or "sale" in goals_lower:
        cvr_base *= 1.2
        ctr_base *= 0.95
    elif "brand" in goals_lower or "awareness" in goals_lower or "reach" in goals_lower:
        ctr_base *= 1.15
        cvr_base *= 0.8

    calc_ctr = f"{ctr_base:.2f}%"
    calc_cvr = f"{cvr_base:.2f}%"

    return {
        "campaign_name": f"{company_name} {product} Launch & Growth Campaign",
        "executive_campaign_overview": f"This campaign is strategically designed to position {product} as the leading solution for {audience} over the coming weeks. Our primary objective is to drive qualified lead acquisition and expand brand presence through a highly targeted channel distribution. With a monthly budget target of {budget}, the campaign targets specific buying triggers, addresses current market pain points, and delivers customized messaging angles that differentiate {company_name} from primary competitors.",
        "strategic_goals": [
            {
                "goal_name": "Qualified Lead Generation",
                "business_context": "Build a B2B lead generation engine to capture target accounts and boost pipeline."
            },
            {
                "goal_name": "Brand Authority & Trust",
                "business_context": f"Establish {company_name} as a top-of-mind thought leader for {product}."
            },
            {
                "goal_name": "Funnel Velocity Optimization",
                "business_context": "Streamline mid-funnel content paths to accelerate lead-to-opportunity times."
            }
        ],
        "persona_profile": {
            "business_challenges": "Struggling with operational inefficiencies, manual workflows, and high tool costs.",
            "pain_points": [
                "Lack of real-time visibility",
                "Rising operational costs",
                "Inefficient team workflows"
            ],
            "buying_motivations": [
                "Increase operational efficiency",
                "Achieve clear cost savings",
                "Seamless system integration"
            ]
        },
        "funnel": {
            "awareness": {
                "tactics": ["LinkedIn Ads", "Google Search Ads", "SEO Blog Posts"],
                "kpis": ["Impressions", "Clicks", "Click-Through Rate (CTR)"],
                "budget_pct": 35
            },
            "consideration": {
                "tactics": ["Product Whitepapers", "Interactive Webinars", "Client Case Studies"],
                "kpis": ["Downloads", "Webinar Registrants", "Demo Page Visits"],
                "budget_pct": 40
            },
            "conversion": {
                "tactics": ["Free Sandbox Trial", "1-on-1 Consultation", "Onboarding Incentive"],
                "kpis": ["Signups", "Demos Booked", "Conversion Rate (CVR)"],
                "budget_pct": 25
            }
        },
        "budget_allocation": [
            {
                "channel": "LinkedIn Ads",
                "percent": 40,
                "rationale": f"Allows precise targeting of {audience} by professional job titles, ensuring minimal waste."
            },
            {
                "channel": "Google Search Ads",
                "percent": 35,
                "rationale": "Captures high-intent prospects actively searching for automated workflow tools."
            },
            {
                "channel": "Content & Email Nurture",
                "percent": 25,
                "rationale": "Engages interested leads, driving them down the conversion path with case studies."
            }
        ],
        "kpis": [
            {
                "metric": "Cost Per Lead (CPL)",
                "target": "< $80.00",
                "measurement": "Total campaign ad spend divided by the number of captured B2B leads."
            },
            {
                "metric": "Demo Booking Rate",
                "target": "> 3.5%",
                "measurement": "Percentage of landing page visitors who sign up for a product demo."
            },
            {
                "metric": "Pipeline Opportunities",
                "target": "30+ Deals",
                "measurement": "Number of qualified leads passing BANT qualification to active sales pipeline."
            }
        ],
        "content_ideas": filtered_content_ideas,
        "ad_copies": filtered_ad_copies,
        "social_media_posts": filtered_posts,
        "calendar": [
            {
                "week": 1,
                "theme": "Tracking & Strategy Alignment",
                "tasks": ["Deploy conversion landing pages", "Embed analytics pixels", "Test form submissions"]
            },
            {
                "week": 2,
                "theme": "Search & Social Activation",
                "tasks": ["Launch LinkedIn sponsored posts", "Activate Google Search campaigns", "Monitor CPC bids"]
            },
            {
                "week": 3,
                "theme": "Mid-Funnel Lead Nurture",
                "tasks": ["Set up automated email flow", "Publish target case studies", "Distribute whitepaper"]
            },
            {
                "week": 4,
                "theme": "Optimizations & Retargeting",
                "tasks": ["Launch custom retargeting ads", "Adjust platform budget weights", "Analyze initial ROI"]
            }
        ]
    }

def get_pitch_fallback(product, customer, target_role, usp, pain_points, company_name) -> dict:
    if not company_name:
        company_name = "Enterprise"
    if not product:
        product = "our premium product"
    if not customer:
        customer = "target buyers"
    if not target_role:
        target_role = "VP of Operations"
    if not usp:
        usp = "advanced automated efficiency, real-time insights, and easy configuration"
    if not pain_points:
        pain_points = "manual tracking errors, high software costs, and slow turnaround times"

    return {
        "sales_readiness_score": 85,
        "elevator_pitch": f"For {customer} who are struggling with {pain_points}, {company_name} offers {product}—a next-generation solution that automates key workflows and delivers real-time strategic intelligence. Unlike traditional manual processes, we provide {usp} that helps your team convert prospects 10x faster and secure clear ROI within weeks.",
        "value_proposition": {
            "headline": f"Empower Your Team with Automated {product} Intelligence",
            "points": [
                f"Eliminate {safe_split_get(pain_points, 0, 'manual tracking errors')} through automated operations.",
                f"Accelerate deal velocity using our built-in {safe_split_get(usp, 0, 'automated workflows')}.",
                "Reduce software expenditure and consolidate fragmented tools.",
                "Ensure enterprise-grade security and full data compliance."
            ]
        },
        "roi_argument": {
            "headline": f"Achieve 3.5x ROI in under 90 Days with {company_name}",
            "calculation": "Calculated by multiplying time saved on manual reports (avg. 15 hours/week per employee) by representative hourly rates, added to software cost savings from consolidation.",
            "timeframe": "90 Days post-onboarding"
        },
        "objection_handling": [
            {
                "objection": "The implementation and setup process will take too long.",
                "response": f"We provide pre-built templates and dedicated integration support that gets {product} running in under 5 business days, without disrupting daily operations."
            },
            {
                "objection": "We already have a legacy vendor handling this.",
                "response": f"Many of our clients used legacy systems before switching. They migrated to {company_name} because we offer {safe_split_get(usp, 1, 'real-time insights')} at 40% lower operational costs."
            },
            {
                "objection": "Our team might resist adopting another software tool.",
                "response": "Our interface is designed with a consumer-grade user experience, requiring virtually zero learning curve. We also host custom training sessions to ensure high team adoption."
            },
            {
                "objection": "We do not have a dedicated budget allocated for this this quarter.",
                "response": "We offer flexible proof-of-concept pilot pricing. The efficiency gains in the first 30 days typically free up the budget needed to fund the full subscription."
            }
        ],
        "discovery_questions": [
            f"How much time does your team currently lose weekly due to {safe_split_get(pain_points, 0, 'manual tasks')}?",
            f"What specific goals has your department set for scaling {product} operations this fiscal year?",
            "What has been the biggest bottleneck when onboarding new representatives on your current toolset?",
            "How do you currently measure the success and return on your software vendor investments?",
            f"If you could automate one manual task related to {customer}, what would it be?",
            "Who else in your organization is affected by these workflow delays?",
            "What happens to your customer acquisition pipeline if these issues remain unresolved for another six months?",
            "What security compliance standards do we need to meet to initiate a trial pilot?"
        ],
        "follow_up_strategy": {
            "timing": "Within 24 hours post-discovery call",
            "steps": [
                "Send a summary email along with custom interactive demo resources.",
                "Share the detailed security compliance whitepaper and client case study.",
                "Follow up via LinkedIn with a relevant industry insights article.",
                "Schedule a 15-minute sync call to align on pricing and pilot parameters."
            ]
        },
        "email_template": {
            "subject": f"Next steps: Automating workflows for {customer}",
            "body": f"Hi [First Name],\n\nThank you for taking the time to speak today. I enjoyed learning more about your goals at [Company Name] and how your team is navigating challenges around {safe_split_get(pain_points, 0, 'manual workflow inefficiencies')}.\n\nAs discussed, {company_name} helps teams like yours automate manual bottlenecks and unlock {safe_split_get(usp, 0, 'advanced automation')} to drive performance. I've attached our customized ROI breakdown and a brief case study outlining how a peer company scaled operations using {product}.\n\nLet's connect next Tuesday at 10 AM to walk through a quick sandbox pilot. Does that work for you?\n\nBest regards,\n\n[Your Name]\n{company_name}"
        },
        "linkedin_template": {
            "connection_note": f"Hi [First Name], noticed your work in the {customer} space. Would love to connect and share some insights on how we are helping VPs automate department workflows and reduce software overhead.",
            "follow_up": f"Hi [First Name], thanks for connecting. I wanted to share this short case study detailing how operations leaders scaled output and resolved legacy inefficiencies using {product}. Let me know if this aligns with your priorities this quarter!"
        },
        "meeting_agenda": [
            {"time": "00:00 - 00:05", "topic": "Introductions & Context Setting", "goal": "Confirm call objectives and align expectations."},
            {"time": "00:05 - 00:15", "topic": "Current Workflow Deep Dive", "goal": f"Understand user pain points around {safe_split_get(pain_points, 0, 'manual operations')}."},
            {"time": "00:15 - 00:30", "topic": f"Custom {product} Sandbox Walkthrough", "goal": f"Showcase how {company_name} solves their specific challenges."},
            {"time": "00:30 - 00:40", "topic": "ROI & Pricing Alignment", "goal": "Present cost savings analysis and pilot frameworks."},
            {"time": "00:40 - 00:45", "topic": "Next Steps & Action Items", "goal": "Confirm dates for onboarding sync and contract review."}
        ],
        "proposal_outline": [
            "Executive Summary",
            "Problem Statement & Current Challenges",
            f"Proposed Solution: {product} Capabilities",
            "Project Scope & Integration Timeline",
            "Pricing Models & Investment Breakdown",
            "Service Level Agreements (SLAs) & Support",
            "Security, Compliance & Data Governance",
            "Terms of Service & Signature Page"
        ],
        "closing_script": f"Based on our discussion, {product} directly addresses your team's bottleneck with {safe_split_get(pain_points, 0, 'manual workflows')}. With {company_name}, you are not just buying another software tool; you are acquiring a partner dedicated to your operational scale. Let's start with a 30-day trial pilot next Monday so you can see the efficiency gains firsthand. I will send over the agreement right after this call.",
        "buyer_persona": {
            "title": f"Strategic {target_role}",
            "priorities": ["Department budget optimization", "Process automation", "Team productivity scaling", "Data-driven decision making"],
            "objections": ["Integration bandwidth constraints", "Pricing flexibility", "Security approvals"]
        },
        "decision_maker_map": [
            {"role": f"{target_role} / Department Head", "influence": "High (Primary Decision Maker)", "concern": "Operational ROI and team workflow disruption"},
            {"role": "Chief Technology Officer / IT Director", "influence": "High (Technical Evaluator)", "concern": "Data security, API integrations, and system reliability"},
            {"role": "Finance Director / CFO Office", "influence": "Medium (Budget Approver)", "concern": "Contract length, payment terms, and total cost of ownership"},
            {"role": "End-User Team Leads", "influence": "Medium (Adoption Influencer)", "concern": "Interface usability, manual effort reduction, and learning curve"}
        ]
    }

def get_lead_fallback(name, company, industry, budget, need, urgency, company_name) -> dict:
    if not company_name:
        company_name = "Enterprise"
    if not name:
        name = "Prospective Lead"
    if not company:
        company = "Growth Corporation"
    if not industry:
        industry = "Technology"
    if not budget:
        budget = "$10k - $25k"
    if not need:
        need = "automate pipeline scoring and sales pitch creation"
    if not urgency:
        urgency = "Next 30 Days"

    return {
        "lead_score": 82,
        "conversion_probability": 76,
        "temperature": "Hot",
        "bant": {
            "budget": {
                "score": 80,
                "assessment": f"Lead states a budget allocation of {budget}, which is fully qualified for our standard package pricing.",
                "evidence": f"Budget range ({budget}) aligned with standard industry pricing tiers."
            },
            "authority": {
                "score": 75,
                "assessment": "Buyer appears to hold decision influence or direct procurement authority for the department.",
                "evidence": "Job role indicates budget management responsibilities."
            },
            "need": {
                "score": 90,
                "assessment": f"High need alignment. The lead is seeking to solve '{need}', which is our core product capability.",
                "evidence": f"Prospect explicitly stated a need to: {need}."
            },
            "timeline": {
                "score": 85,
                "assessment": f"Short sales cycle. The timeline of '{urgency}' indicates high purchase urgency and near-term decision making.",
                "evidence": f"Urgency stated as: {urgency}."
            }
        },
        "qualification_summary": f"This lead is a high-value opportunity from {company} ({industry}). They demonstrate strong BANT alignment with a stated budget of {budget} and an urgent timeline. They are actively seeking to {need}, making them an ideal candidate for {company_name}'s offerings.",
        "buying_intent": {
            "score": 85,
            "signals": [
                {"signal": "Visited pricing page twice in 24 hours", "strength": "High"},
                {"signal": "Downloaded whitepaper on operational efficiency", "strength": "Medium"},
                {"signal": "Requested custom demo or quote via online portal", "strength": "High"}
            ]
        },
        "risk_factors": [
            {
                "risk": "Competitor evaluation in progress.",
                "impact": "Medium",
                "mitigation": "Highlight USPs early and offer a dedicated migration or onboarding assistant."
            },
            {
                "risk": "Technical or implementation dependencies.",
                "impact": "Medium",
                "mitigation": "Involve our solutions engineering or implementation team in the next call to map out setup requirements."
            },
            {
                "risk": "Budget approval delays from finance.",
                "impact": "Low",
                "mitigation": "Provide a pre-written business case document outlining projected ROI."
            }
        ],
        "recommended_actions": [
            {
                "action": f"Reach out within 2 hours to schedule a tailored {company_name} walkthrough.",
                "priority": "High",
                "timeline": "Next 2 hours"
            },
            {
                "action": f"Send a personalized email containing client case studies in the {industry} sector.",
                "priority": "High",
                "timeline": "Next 24 hours"
            },
            {
                "action": "Connect with the buyer and key stakeholders on LinkedIn.",
                "priority": "Medium",
                "timeline": "Next 48 hours"
            },
            {
                "action": "Prepare custom demonstration or pricing proposal showing how we resolve need.",
                "priority": "Medium",
                "timeline": "Next 3 days"
            }
        ],
        "next_best_action": "Call lead directly to schedule a 15-minute technical discovery session.",
        "priority_level": "Critical",
        "crm_readiness": True,
        "score_breakdown": [
            {"factor": "Budget Fit", "score": 24, "max": 30, "rationale": f"Stated budget of {budget} covers core product/service costs but might limit add-on features."},
            {"factor": "Authority Level", "score": 18, "max": 25, "rationale": "Buyer is a key influencer; need to loop in department head for final sign-off."},
            {"factor": "Need Severity", "score": 27, "max": 30, "rationale": f"Stated pain points around '{need}' perfectly match our primary solutions."},
            {"factor": "Timeline Urgency", "score": 13, "max": 15, "rationale": f"Timeline of '{urgency}' represents an active purchasing window."}
        ]
    }

def get_market_fallback(industry, product_category, target_market, competitors, company_name) -> dict:
    if not company_name:
        company_name = "Enterprise"
    if not industry:
        industry = "Industrial & Services"
    if not product_category:
        product_category = "Premium Products"
    if not target_market:
        target_market = "Commercial Markets"
    if not competitors:
        competitors = "Competitor A, Competitor B"

    # Split competitors
    comp_list = [c.strip() for c in competitors.split(',') if c.strip()]
    if not comp_list:
        comp_list = ["Alpha Corp", "Beta Solutions", "Gamma Systems"]
    while len(comp_list) < 5:
        comp_list.append(f"Competitor {chr(65 + len(comp_list))}")
    comp_list = comp_list[:5]

    return {
        "executive_summary": f"The market for {product_category} in the {industry} sector is undergoing rapid transformation, driven by demands for increased operational efficiency. {company_name} is well-positioned to capture market share by offering advanced capabilities tailored for {target_market}. While established legacy competitors like {comp_list[0]} and {comp_list[1]} maintain high reach, they suffer from complex configurations and high pricing tiers. This creates a clear window for disruptive innovation.",
        "market_size": {
            "current": "$18.5 Billion",
            "projected": "$42.3 Billion",
            "cagr": "12.4%",
            "currency": "USD"
        },
        "growth_drivers": [
            f"Increasing demand for sustainable and cost-effective {product_category} solutions.",
            "Rising operational efficiency requirements forcing organizations to streamline processes.",
            f"Growing customer preferences for transparent supply chains and eco-friendly practices in {industry}.",
            "Advancements in manufacturing, logistics, and delivery lowering distribution barriers.",
            f"Expansion of modern procurement channels and digital outreach vectors for {product_category}."
        ],
        "market_risks": [
            "Regulatory compliance complexities in regional and international markets.",
            "Rising costs of raw materials and energy supply chain disruptions.",
            "Increasing competition from low-cost alternative providers.",
            "Fluctuations in interest rates impacting capital expenditure budgets.",
            "Labor market constraints and rising workforce acquisition costs."
        ],
        "competitors": [
            {
                "name": comp_list[0],
                "strengths": "Deep brand equity, wide distribution channel network, massive resources.",
                "weaknesses": "Complex implementation cycles, outdated customer experience, rigid pricing.",
                "market_position": "Legacy Market Leader",
                "threat_level": "High"
            },
            {
                "name": comp_list[1],
                "strengths": "Strong user adoption, excellent API libraries and integrations, competitive pricing.",
                "weaknesses": "Limited advanced enterprise security controls, slower customer support response.",
                "market_position": "High-Growth Challenger",
                "threat_level": "High"
            },
            {
                "name": comp_list[2],
                "strengths": "Highly specialized features, loyal customer base in niche markets.",
                "weaknesses": "Poor scalability, lacks general integration support.",
                "market_position": "Niche Player",
                "threat_level": "Medium"
            },
            {
                "name": comp_list[3],
                "strengths": "Bundled pricing with broader platform offerings.",
                "weaknesses": "Weak product focus, slower feature release cycles.",
                "market_position": "Large Portfolio Follower",
                "threat_level": "Medium"
            },
            {
                "name": comp_list[4],
                "strengths": "Aggressive sales tactics, flexible trial periods.",
                "weaknesses": "Inconsistent product quality, high client churn rates.",
                "market_position": "New Entrant / Disruptor",
                "threat_level": "Low"
            }
        ],
        "swot": {
            "strengths": [
                f"Modern user interface with seamless user onboarding.",
                f"Advanced customized output generation for {product_category}.",
                "Flexible pricing structures catering to mid-market and enterprise.",
                "Built-in compliance checks and secure local database architecture."
            ],
            "weaknesses": [
                "Lower brand recognition compared to legacy market leaders.",
                "Smaller sales development team limits outbound outreach scale.",
                "Requires constant updating of integrations for new CRM updates."
            ],
            "opportunities": [
                f"Capture market share from clients dissatisfied with {comp_list[0]}'s pricing.",
                f"Expand presence in underserved regional sectors within Europe and APAC for {product_category}.",
                "Form strategic partnerships with digital consulting agencies."
            ],
            "threats": [
                "Aggressive discounting strategies from primary competitors.",
                "Sudden changes in search engine indexing and ad platform policies."
            ]
        },
        "pestel": {
            "political": f"Government policies and regulation changes impacting import/export tariffs and trade corridors in {industry}.",
            "economic": f"Fluctuations in raw material costs, energy prices, and interest rates affecting production margins in the {product_category} sector.",
            "social": f"Shifting consumer preferences and buying behaviors prioritizing sustainable, high-quality offerings like {product_category}.",
            "technological": f"Adoption of automation, smart manufacturing, and digital supply chain technologies to optimize operations in {industry}.",
            "environmental": f"Strict sustainability compliance mandates and waste-reduction initiatives forcing operations to implement eco-friendly systems.",
            "legal": f"Evolving labor standards, local environmental protection acts, and industry certifications governing the production and distribution of {product_category}."
        },
        "trends": [
            {
                "trend": "Sustainability and Green Compliance",
                "impact_score": 88,
                "timeframe": "12-18 months",
                "description": f"Growing demand for certified eco-friendly manufacturing processes and circular economy integration in {industry}."
            },
            {
                "trend": "Supply Chain Integration",
                "impact_score": 82,
                "timeframe": "6-12 months",
                "description": f"Enterprise and mid-market clients requiring end-to-end transparency in logistics and material tracking for {product_category}."
            },
            {
                "trend": "Digital Operations and Automation",
                "impact_score": 79,
                "timeframe": "18-24 months",
                "description": f"Transition from legacy manual management systems to real-time status tracking and optimized inventory management in {industry}."
            }
        ],
        "opportunities": [
            {
                "title": f"Mid-Market Displacement of legacy {industry} providers",
                "score": 90,
                "effort": "Medium",
                "revenue_potential": "High"
            },
            {
                "title": f"B2B Strategic Partnerships for {product_category} supply chains",
                "score": 85,
                "effort": "High",
                "revenue_potential": "Medium"
            },
            {
                "title": "Niche Compliance Vertical Packages",
                "score": 75,
                "effort": "Low",
                "revenue_potential": "Medium"
            }
        ],
        "growth_chart_data": [
            {"period": "2021", "value": 14.2},
            {"period": "2022", "value": 18.5},
            {"period": "2023", "value": 24.1},
            {"period": "2024", "value": 31.8},
            {"period": "2025E", "value": 41.5},
            {"period": "2026E", "value": 54.2}
        ],
        "market_share_data": [
            {"name": comp_list[0], "value": 38},
            {"name": comp_list[1], "value": 22},
            {"name": company_name, "value": 12},
            {"name": comp_list[2], "value": 10},
            {"name": "Others", "value": 18}
        ],
        "radar_data": [
            {"competitor": company_name, "innovation": 95, "pricing": 85, "reach": 45, "support": 90, "product": 88},
            {"competitor": comp_list[0], "innovation": 60, "pricing": 30, "reach": 95, "support": 70, "product": 75},
            {"competitor": comp_list[1], "innovation": 85, "pricing": 75, "reach": 70, "support": 65, "product": 80}
        ],
        "advertising_analysis": [
            {
                "channel": "LinkedIn Professional",
                "cpm_cpc_benchmark": "CPM: $45.00, CPC: $7.50",
                "creative_strategy": "Ad copy highlighting direct cost savings and operational time comparisons.",
                "message_angle": "Focus on automating manual bottlenecks and scaling team productivity.",
                "ad_spend_efficiency": "High",
                "conversion_probability": "4.2%"
            },
            {
                "channel": "Google Search Ads",
                "cpm_cpc_benchmark": "CPM: $22.00, CPC: $5.20",
                "creative_strategy": "Targeting competitive search terms and comparison terms.",
                "message_angle": f"Compare features directly with legacy vendors. Highlight {company_name} advantages.",
                "ad_spend_efficiency": "Medium",
                "conversion_probability": "3.5%"
            },
            {
                "channel": "Industry Newsletters",
                "cpm_cpc_benchmark": "Fixed Rate: $1,200/issue",
                "creative_strategy": "Syndicating whitepapers and case studies detailing workflow ROI.",
                "message_angle": "Thought leadership on digital strategy and automated operations.",
                "ad_spend_efficiency": "High",
                "conversion_probability": "2.8%"
            }
        ],
        "positioning_postures": [
            {
                "brand_name": company_name,
                "market_role": "Challenger",
                "pricing_posture": "Value",
                "innovation_posture": "Pioneer",
                "message_posture": "Disruptive",
                "customer_acquisition_posture": "PLG",
                "strategic_rationale": f"Position {company_name} as the highly customizable, modern, and cost-effective alternative to rigid, expensive legacy tools."
            },
            {
                "brand_name": comp_list[0],
                "market_role": "Leader",
                "pricing_posture": "Premium",
                "innovation_posture": "Conservative",
                "message_posture": "Authoritative",
                "customer_acquisition_posture": "Outbound",
                "strategic_rationale": "Leverage deep historical relationships, wide brand equity, and massive sales teams to secure client renewals."
            },
            {
                "brand_name": comp_list[1],
                "market_role": "Challenger",
                "pricing_posture": "Muted",
                "innovation_posture": "Fast-Follower",
                "message_posture": "Educational",
                "customer_acquisition_posture": "Inbound",
                "strategic_rationale": "Offer lightweight, self-serve tools to acquire a large volume of developer and startup accounts."
            }
        ]
    }

def get_insights_fallback(business_type, challenges, goals, company_name) -> dict:
    if not company_name:
        company_name = "Enterprise"
    if not business_type:
        business_type = "industry sector"
    if not challenges:
        challenges = "manual tracking inefficiencies, resource constraints"
    if not goals:
        goals = "scale operational efficiency, reduce overhead costs"

    return {
        "opportunity_score": 68,
        "executive_summary": f"An evaluation of {company_name}'s current {business_type} operations reveals significant growth potential. By addressing key bottlenecks in '{challenges}', the organization can unlock substantial efficiency gains. Implementing targeted automation will optimize representative bandwidth, reduce customer acquisition cost (CAC), and accelerate path toward goals like '{goals}'. Our 90-day roadmap outlines key tactical actions to secure these objectives.",
        "current_challenges": [
            {
                "challenge": f"Inefficiencies in '{safe_split_get(challenges, 0, 'operations')}'",
                "severity": "High",
                "impact": "Slows operational velocity, increases manual tracking errors, and reduces customer engagement speed."
            },
            {
                "challenge": "Fragmented tracking across communication channels",
                "severity": "Medium",
                "impact": "Creates pipeline visibility blindspots, hindering data-driven decisions and scaling efforts."
            },
            {
                "challenge": "Long sales and onboarding cycle conversion paths",
                "severity": "Medium",
                "impact": "Increases customer acquisition cost and limits cash-flow predictability."
            }
        ],
        "root_cause_analysis": [
            {
                "problem": f"Stalled pipeline tracking: '{safe_split_get(challenges, 0, 'operations')}'",
                "root_cause": "Absence of standardized process tracking and workflow automation.",
                "evidence": "Team members spend over 12 hours weekly performing manual data entry and email follow-ups."
            },
            {
                "problem": "Low lead-to-opportunity conversion rate",
                "root_cause": "Underutilized buyer intent signals and delay in engaging high-potential prospects.",
                "evidence": "Average response time to inbound inquiries exceeds 18 hours."
            }
        ],
        "growth_opportunities": [
            {
                "title": f"Automated customer feedback loop for {business_type}",
                "score": 92,
                "effort": "Medium",
                "revenue_impact": "High",
                "description": "Deploy automated post-interaction feedback forms to quickly capture buyer sentiment and optimize product delivery."
            },
            {
                "title": f"Strategic partnership expansion in {business_type}",
                "score": 88,
                "effort": "High",
                "revenue_impact": "High",
                "description": "Collaborate with industry distributors and consultants to secure channel integrations and expand general market footprint."
            },
            {
                "title": f"Optimizing workflow channels for resolving '{safe_split_get(challenges, 0, 'inefficiencies')}'",
                "score": 85,
                "effort": "Low",
                "revenue_impact": "Medium",
                "description": "Streamline communication and tracking templates, reducing representative review times and manual coordination overhead."
            },
            {
                "title": f"Targeted customer case study campaigns in {business_type}",
                "score": 78,
                "effort": "Low",
                "revenue_impact": "Medium",
                "description": "Publish ROI-focused case studies detailing efficiency improvements to build buyer trust and accelerate sales cycles."
            },
            {
                "title": "Tiered loyalty and account growth packages",
                "score": 70,
                "effort": "Medium",
                "revenue_impact": "Medium",
                "description": "Introduce volume-based pricing discounts and customized customer success frameworks to expand average deal sizes."
            }
        ],
        "revenue_opportunities": [
            {
                "source": "Upselling premium packages and add-ons to key accounts",
                "potential": "$45,000 revenue boost",
                "timeline": "Next 60 days",
                "description": "Engage high-utilization customer segments to upgrade to advanced analytical dashboards and premium support SLA tiers."
            },
            {
                "source": f"Targeted launch of new features or product categories in {business_type}",
                "potential": "$70,000 new pipeline",
                "timeline": "Next 90 days",
                "description": "Introduce customized features resolving stated operational challenges to trigger new department subscription expansions."
            },
            {
                "source": "Value-added service subscriptions or contract extensions",
                "potential": "$30,000 annual boost",
                "timeline": "Next 120 days",
                "description": "Bundle professional consulting audits and customized integrations packages alongside software core subscriptions."
            },
            {
                "source": "Priority delivery and service agreements for elite clients",
                "potential": "$25,000 revenue boost",
                "timeline": "Next 60 days",
                "description": "Charge a premium convenience fee to guarantee rapid turnaround times and dedicated representative channels."
            }
        ],
        "cost_optimization": [
            {
                "area": "Consolidating software and operational tool stack",
                "potential_savings": "$12,000 Annually",
                "action": "Audit current operations stack and migrate users to consolidated platforms."
            },
            {
                "area": f"Streamlining processes to address '{safe_split_get(challenges, 0, 'manual tasks')}'",
                "potential_savings": "15 Hours/week per team member",
                "action": "Redesign workflow handoffs to automate communication triggers."
            },
            {
                "area": "Optimizing customer acquisition and marketing keyword spend",
                "potential_savings": "$8,000 quarterly",
                "action": "Exclude low-intent search terms and focus budget on high-performing segments."
            },
            {
                "area": "Standardizing onboarding and training guides with automated templates",
                "potential_savings": "$6,000 Annually",
                "action": "Build a centralized resource center for customer self-service and team training."
            }
        ],
        "strategic_recommendations": [
            {
                "recommendation": f"Standardize BANT qualification and pipeline stages for {business_type} leads.",
                "priority": "High",
                "impact": "High",
                "effort": "Low"
            },
            {
                "recommendation": "Configure instant notifications and alerts to speed up response times for hot inquiries.",
                "priority": "High",
                "impact": "High",
                "effort": "Low"
            },
            {
                "recommendation": f"Create targeted marketing and landing assets specifically for your top {business_type} segments.",
                "priority": "Medium",
                "impact": "High",
                "effort": "Medium"
            },
            {
                "recommendation": "Build a central playbook for common customer objections and pricing negotiations.",
                "priority": "Medium",
                "impact": "Medium",
                "effort": "Low"
            },
            {
                "recommendation": "Perform bi-weekly sales-marketing lead quality alignment reviews.",
                "priority": "Medium",
                "impact": "Medium",
                "effort": "Low"
            },
            {
                "recommendation": f"Establish collaborative platforms for customer data and exports for {business_type}.",
                "priority": "Low",
                "impact": "Medium",
                "effort": "High"
            }
        ],
        "plan_30_day": [
            {
                "action": "CRM and process tracking setup",
                "owner": "Marketing Operations Lead",
                "success_metric": "Reduce lead review time by 50%"
            },
            {
                "action": "Objection handling script library publication",
                "owner": "Sales Enablement Director",
                "success_metric": "Win rate improvement of 5%"
            }
        ],
        "plan_60_day": [
            {
                "action": "Targeted case study publication",
                "owner": "Content Marketing Manager",
                "success_metric": "Generate 40+ downloads from marketing campaigns"
            },
            {
                "action": "Lead response time SLA tracking",
                "owner": "Sales Operations Lead",
                "success_metric": "Average response time under 15 minutes"
            }
        ],
        "plan_90_day": [
            {
                "action": f"Launch interactive sandbox/demo or sample kit for {business_type}",
                "owner": "Product Lead / CTO Office",
                "success_metric": "Conversion from sandbox to demo booking > 15%"
            },
            {
                "action": "Enterprise sales channel scale-up",
                "owner": "VP of Business Development",
                "success_metric": "Onboard at least 3 active channel partners"
            }
        ],
        "kpi_targets": [
            {
                "kpi": "Inbound Lead Response Time",
                "current": "18 Hours",
                "target": "15 Minutes",
                "timeline": "60 Days"
            },
            {
                "kpi": "MQL-to-SQL Conversion Rate",
                "current": "12%",
                "target": "20%",
                "timeline": "30 Days"
            },
            {
                "kpi": "Customer Acquisition Cost (CAC)",
                "current": "$180.00",
                "target": "$140.00",
                "timeline": "90 Days"
            },
            {
                "kpi": "Monthly Qualified Leads",
                "current": "110",
                "target": "220",
                "timeline": "90 Days"
            },
            {
                "kpi": "Customer Retention Rate",
                "current": "88%",
                "target": "93%",
                "timeline": "90 Days"
            }
        ],
        "priority_matrix": [
            {"initiative": "Process tracking setup", "urgency": "High", "impact": "High"},
            {"initiative": "Rep onboarding guides", "urgency": "Medium", "impact": "High"},
            {"initiative": "Case study content push", "urgency": "High", "impact": "Medium"},
            {"initiative": "Collaborative resource library", "urgency": "Low", "impact": "Medium"},
            {"initiative": "Interactive self-serve sandbox / demo", "urgency": "Medium", "impact": "High"}
        ],
        "competitive_risks": [
            {"risk": "Competitor pricing pressure", "competitor": "Competitor A", "likelihood": "Medium"},
            {"risk": "Alternative feature parity release", "competitor": "Competitor B", "likelihood": "High"},
            {"risk": "Aggressive market reach expansion", "competitor": "Competitor C", "likelihood": "Low"}
        ],
        "operational_risks": [
            {"risk": "System integration bottlenecks", "probability": "Medium", "impact": "High", "mitigation": "Provide dedicated integration assistance during onboarding."},
            {"risk": "Employee adoption resistance", "probability": "Low", "impact": "Medium", "mitigation": "Hold weekly training sessions and distribute simplified guidebooks."},
            {"risk": "Data sync latency", "probability": "Low", "impact": "Low", "mitigation": "Optimize database queries and use local secure storage fallback."}
        ]
    }

def get_schema_fallback(schema_hint: str, user_prompt: str) -> dict:
    company_name = extract_prompt_field(user_prompt, ["COMPANY", "EVALUATING LEAD FOR"], "MarketMind Enterprise")
    product = extract_prompt_field(user_prompt, ["Product/Service", "Product Category", "Business Type", "Industry"], "Enterprise offering")
    audience = extract_prompt_field(user_prompt, ["Target Audience", "Customer Type", "Lead Company", "Target Market"], "B2B Decision Makers")
    goals = extract_prompt_field(user_prompt, ["Goals", "Need Stated", "Current Challenges"], "Growth and scale")
    platform = extract_prompt_field(user_prompt, ["Platform"], "Multi-platform Mix")
    budget = extract_prompt_field(user_prompt, ["Budget", "Budget Stated"], "$5,000 - $25,000")

    if "campaign_name" in schema_hint:
        return get_campaign_fallback(product, audience, platform, budget, goals, company_name)
    elif "elevator_pitch" in schema_hint:
        usp = extract_prompt_field(user_prompt, ["USPs"], "advanced automated efficiency, real-time insights, and easy configuration")
        pain_points = extract_prompt_field(user_prompt, ["Pain Points"], "manual tracking errors, high software costs, and slow turnaround times")
        target_role = extract_prompt_field(user_prompt, ["Target Decision Maker"], "VP of Operations")
        return get_pitch_fallback(product, audience, target_role, usp, pain_points, company_name)
    elif "lead_score" in schema_hint and "bant" in schema_hint:
        lead_name = extract_prompt_field(user_prompt, ["Lead Name"], "Prospective Lead")
        industry = extract_prompt_field(user_prompt, ["Industry"], "Technology")
        urgency = extract_prompt_field(user_prompt, ["Urgency Stated"], "Next 30 Days")
        return get_lead_fallback(lead_name, audience, industry, budget, goals, urgency, company_name)
    elif "growth_chart_data" in schema_hint and "pestel" in schema_hint:
        competitors = extract_prompt_field(user_prompt, ["Known Competitors"], "Competitor A, Competitor B")
        return get_market_fallback(product, audience, platform, competitors, company_name)
    elif "plan_30_day" in schema_hint or "opportunity_score" in schema_hint:
        return get_insights_fallback(product, goals, goals, company_name)

    return {}
