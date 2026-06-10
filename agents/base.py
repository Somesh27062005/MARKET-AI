"""
agents/base.py — Shared LangGraph utilities, JSON parser, retry logic,
and the Groq LLM factory for all multi-agent graphs.
"""
import os, json, re, textwrap
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
    full_system += "\n\nIMPORTANT: Return ONLY the JSON object. No explanation, no markdown, no extra text."

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
      "business_context": "string",
      "why_it_matters": "string",
      "expected_impact": "string",
      "success_metrics": "string",
      "risks": "string",
      "mitigation_plan": "string"
    }
  ],
  "expected_outcomes": {
    "revenue_impact": "string",
    "lead_impact": "string",
    "brand_impact": "string",
    "market_position_impact": "string",
    "customer_retention_impact": "string"
  },
  "persona_profile": {
    "job_titles": ["string"],
    "responsibilities": "string",
    "business_challenges": "string",
    "pain_points": ["string"],
    "buying_motivations": ["string"],
    "decision_triggers": ["string"],
    "common_objections": ["string"],
    "preferred_communication_channels": ["string"],
    "preferred_content_types": ["string"],
    "purchase_journey_behaviour": "string",
    "budget_authority": "string",
    "expected_sales_cycle": "string"
  },
  "funnel_analysis": {
    "awareness_stage": {
      "objective": "string",
      "target_audience_behaviour": "string",
      "recommended_channels": ["string"],
      "expected_results": "string",
      "budget_pct": 0
    },
    "consideration_stage": {
      "customer_mindset": "string",
      "key_content": ["string"],
      "conversion_drivers": ["string"],
      "budget_pct": 0
    },
    "conversion_stage": {
      "sales_activities": ["string"],
      "closing_strategies": ["string"],
      "performance_indicators": ["string"],
      "budget_pct": 0
    },
    "retention_stage": {
      "customer_success_activities": ["string"],
      "upsell_opportunities": ["string"],
      "loyalty_strategy": "string"
    }
  },
  "budget_allocation_rationale": [
    {
      "channel": "string",
      "allocation_pct": 0,
      "reasoning": "string",
      "expected_roi": "string",
      "advantages": ["string"],
      "risks": ["string"],
      "success_metrics": ["string"]
    }
  ],
  "kpi_explanations": [
    {
      "kpi_name": "string",
      "what_it_measures": "string",
      "why_it_matters": "string",
      "industry_benchmark": "string",
      "expected_value": "string",
      "success_threshold": "string",
      "risk_indicators": "string",
      "optimization_strategy": "string"
    }
  ],
  "kpi_commentary": "string",
  "content_ideas": [{"title": "string", "format": "string", "platform": "string", "description": "string"}],
  "ad_copies": [{"headline": "string", "body": "string", "cta": "string", "platform": "string"}],
  "cta_suggestions": ["string"],
  "estimated_reach": "string",
  "estimated_ctr": "string",
  "estimated_cvr": "string",
  "timeline_weeks": 0,
  "roadmap_actions": [
    {
      "week_number": 0,
      "week_theme": "string",
      "actions": [
        {
          "action_name": "string",
          "objective": "string",
          "business_reasoning": "string",
          "execution_steps": ["string"],
          "required_resources": ["string"],
          "responsible_team": "string",
          "expected_kpi_impact": ["string"],
          "dependencies": ["string"],
          "risk_level": "Low|Medium|High",
          "expected_outcome": "string"
        }
      ]
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
  "growth_opportunities": [{"title": "string", "score": 0, "effort": "string", "revenue_impact": "string"}],
  "revenue_opportunities": [{"source": "string", "potential": "string", "timeline": "string"}],
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
