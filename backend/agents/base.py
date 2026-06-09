"""
agents/base.py — Shared LangGraph utilities, JSON parser, retry logic,
and the Groq LLM factory for all multi-agent graphs.
"""
import os, json, re, textwrap
import sys

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
        platform = "Multi-platform Mix"
    if not budget:
        budget = "$5,000 - $25,000"
    if not goals:
        goals = "B2B Leads Generation"

    return {
        "campaign_name": f"{company_name} {product} Launch & Growth Campaign",
        "executive_campaign_overview": f"This campaign is strategically designed to position {product} as the leading solution for {audience} over the coming weeks. Our primary objective is to drive qualified lead acquisition and expand brand presence through a highly targeted {platform} channel distribution. With a monthly budget target of {budget}, the campaign targets specific buying triggers, addresses current market pain points, and delivers customized messaging angles that differentiate {company_name} from primary competitors.",
        "strategic_goals": [
            {
                "goal_name": "Qualified Lead Generation",
                "business_context": f"To support pipeline targets for {product}, we need to build a predictable engine capturing interested buyers in the {audience} segment.",
                "why_it_matters": "Active leads are the lifeblood of sales development, ensuring high representative utilization and steady revenue growth.",
                "expected_impact": "Acquisition of 250+ highly qualified leads within the first 60 days.",
                "success_metrics": "CPL below $80, Lead-to-Opportunity conversion rate above 18%.",
                "risks": "Audience saturation on primary channels leading to rising ad costs.",
                "mitigation_plan": "Regularly refresh creative angles and split-test messaging variants weekly."
            },
            {
                "goal_name": "Brand Authority & Share of Voice",
                "business_context": f"{company_name} needs to establish industry authority for {product} against established alternatives.",
                "why_it_matters": "Higher trust reduces sales cycles and increases average contract value.",
                "expected_impact": "30% increase in brand search volume and social engagement.",
                "success_metrics": "5,000+ organic views on thought-leadership pieces; 4.5% CTR on branding ads.",
                "risks": "Content gets lost in the noise of generic industry advice.",
                "mitigation_plan": "Publish original proprietary research and case studies demonstrating tangible ROI."
            },
            {
                "goal_name": "Sales Funnel Velocity Optimization",
                "business_context": "Converting awareness into purchase interest requires seamless content handoffs.",
                "why_it_matters": "Bottlenecks in mid-funnel stages waste advertising spend and stall pipeline velocity.",
                "expected_impact": "Reduction of average sales cycle duration by 15 days.",
                "success_metrics": "Demo booking rate of 3.5% from landing page visitors.",
                "risks": "Sales and marketing messaging misalignment.",
                "mitigation_plan": "Establish bi-weekly syncs between growth teams and sales development representatives."
            }
        ],
        "expected_outcomes": {
            "revenue_impact": f"Projected to drive significant incremental pipeline, targeting $150k+ in closed-won contracts attributed directly to {product} marketing campaigns.",
            "lead_impact": f"Expected to generate a steady stream of marketing qualified leads (MQLs) looking to resolve specific challenges relevant to {audience}.",
            "brand_impact": f"Establish {company_name} as a top-of-mind solution, boosting market brand awareness and product confidence across digital platforms.",
            "market_position_impact": f"Establishes a strong foothold in the segment, securing a competitive posture and shifting buyer mindsets away from legacy vendors.",
            "customer_retention_impact": f"Pre-educates prospects on product capabilities, facilitating smoother onboarding and driving higher net revenue retention."
        },
        "persona_profile": {
            "job_titles": ["VP of Operations", "Chief Technology Officer", "Head of Digital Strategy", "Operations Director"],
            "responsibilities": f"Overseeing department efficiency, scaling operations, reducing manual bottlenecks, and approving vendor acquisitions for {product}.",
            "business_challenges": "Fragmented data sources, long manual processing times, and difficulty demonstrating ROI on software investments.",
            "pain_points": ["Lack of real-time visibility", "Inefficient team workflows", "Rising operational costs", "Underutilized data analytics"],
            "buying_motivations": ["Increase operational efficiency", "Achieve cost savings", "Seamless tool integration", "Scalable infrastructure"],
            "decision_triggers": ["Demonstration of clear financial ROI", "Competitor adoption case study", "Security compliance certification"],
            "common_objections": ["High implementation effort", "Pricing budget constraints", "Satisfaction with current legacy methods"],
            "preferred_communication_channels": ["LinkedIn", "Professional Webinars", "Industry Newsletters", "Direct Email"],
            "preferred_content_types": ["Product Whitepapers", "Interactive Demos", "Customer Success Stories", "Executive Briefings"],
            "purchase_journey_behaviour": "Relies heavily on peer reviews, requests interactive sandbox demos, and requires multi-department consensus before final sign-off.",
            "budget_authority": "Sole signer for department expenses up to $50k; co-signer for enterprise-wide procurements.",
            "expected_sales_cycle": "4 to 8 weeks depending on integration requirements and security review."
        },
        "funnel_analysis": {
            "awareness_stage": {
                "objective": f"Introduce {product} to {audience} and establish initial interest.",
                "target_audience_behaviour": "Searching for solutions to operational inefficiencies and reading industry publications.",
                "recommended_channels": ["LinkedIn Sponsored Content", "Google Search Ads", "Industry Podcast Sponsorships"],
                "expected_results": "50,000+ targeted impressions, 1,200 clicks, and initial brand touchpoints.",
                "budget_pct": 35
            },
            "consideration_stage": {
                "customer_mindset": "Evaluating different tools and comparing features, implementation costs, and security compliance.",
                "key_content": ["Comparison Guides", "ROI Calculators", "Product Demo Videos", "Expert Webinars"],
                "conversion_drivers": ["Interactive sandbox access", "Detailed security whitepapers", "Customer testimonial case studies"],
                "budget_pct": 40
            },
            "conversion_stage": {
                "sales_activities": ["Direct sales outreach", "Tailored product walkthroughs", "Custom price quotations"],
                "closing_strategies": ["Limited-time onboarding incentives", "Pilot proof-of-concept projects", "Executive alignment meetings"],
                "performance_indicators": ["Demo-to-proposal conversion rate", "Contract signature turnaround time", "Close-won win rate"],
                "budget_pct": 25
            },
            "retention_stage": {
                "customer_success_activities": ["Dedicated account manager onboarding", "Quarterly business reviews", "User training academy"],
                "upsell_opportunities": ["Enterprise tier upgrades", "Additional seat licensing", "Advanced analytics modules"],
                "loyalty_strategy": "Establish a customer advisory board and offer early access to new product releases."
            }
        },
        "budget_allocation_rationale": [
            {
                "channel": "LinkedIn Professional Ads",
                "allocation_pct": 40,
                "reasoning": f"Allows precise targeting of {audience} by job title, industry, and company size, ensuring minimal ad spend wastage.",
                "expected_roi": "3.2x pipeline return on ad spend",
                "advantages": ["High-intent B2B targeting", "Direct lead-gen forms integration", "Premium brand positioning"],
                "risks": ["Higher average CPC compared to other channels", "Requires frequent creative refreshes"],
                "success_metrics": ["Cost per MQL", "Click-through rate (CTR) > 1.2%"]
            },
            {
                "channel": "Google Intent Search",
                "allocation_pct": 35,
                "reasoning": f"Captures prospects actively searching for solutions related to {product} USPs, leading to higher conversion rates.",
                "expected_roi": "4.1x conversion return on ad spend",
                "advantages": ["High purchase intent", "Captures active demand", "Immediate traffic generation"],
                "risks": ["Highly competitive search terms", "Limited by search volume"],
                "success_metrics": ["Ad quality score", "Conversion rate (CVR) > 3.5%"]
            },
            {
                "channel": "Industry Newsletters & Content Syndication",
                "allocation_pct": 25,
                "reasoning": f"Builds long-term thought leadership and trust within the broader {audience} ecosystem.",
                "expected_roi": "2.8x brand value multiplier",
                "advantages": ["High credibility", "Fixed costs structures", "Reaches passive prospects"],
                "risks": ["Longer conversion attribution cycles", "Requires high-quality content production"],
                "success_metrics": ["Total downloads", "Email open and click-through rates"]
            }
        ],
        "kpi_explanations": [
            {
                "kpi_name": "Cost Per Qualified Lead (CPQL)",
                "what_it_measures": "Total marketing expenditure divided by the number of leads meeting BANT qualification criteria.",
                "why_it_matters": "Ensures marketing budget is directed toward high-value prospects rather than low-quality traffic.",
                "industry_benchmark": "$95.00 - $120.00",
                "expected_value": "$85.00",
                "success_threshold": "< $105.00",
                "risk_indicators": "CPQL exceeding $120.00 or conversion rate from MQL to SQL dropping below 10%.",
                "optimization_strategy": "Refine audience exclusion lists and improve post-click landing page relevance."
            },
            {
                "kpi_name": "Lead-to-Opportunity Win Rate",
                "what_it_measures": "Percentage of sales-qualified leads that progress to active sales pipeline opportunities.",
                "why_it_matters": "Measures the quality of marketing handoffs and sales alignment efficiency.",
                "industry_benchmark": "15.0%",
                "expected_value": "18.5%",
                "success_threshold": "> 14.0%",
                "risk_indicators": "Opportunities stalling in the qualification stage for more than 21 days.",
                "optimization_strategy": "Standardize discovery call templates and implement automated follow-up sequences."
            },
            {
                "kpi_name": "Customer Acquisition Cost (CAC) Payback Period",
                "what_it_measures": "The number of months of customer revenue required to recover the marketing and sales cost to acquire them.",
                "why_it_matters": "Directly impacts company cash flow and long-term business scalability.",
                "industry_benchmark": "12 months",
                "expected_value": "9.5 months",
                "success_threshold": "< 11 months",
                "risk_indicators": "Payback period ballooning due to discounting or declining contract values.",
                "optimization_strategy": "Focus campaign budget on high-retention segments and increase upsell activities."
            }
        ],
        "kpi_commentary": f"These KPIs are chosen to align marketing investment directly with sales efficiency and business health. By focusing on CPQL and sales velocity, we ensure {company_name} maximizes return on ad spend.",
        "content_ideas": [
            {
                "title": f"The Definitve ROI Guide for {product}",
                "format": "Ebook / PDF Report",
                "platform": "LinkedIn / Website Resources",
                "description": f"A data-backed analysis showing how companies in the {audience} space save time and costs by using {product}."
            },
            {
                "title": "Automating Department Workflows: Best Practices",
                "format": "Interactive Live Webinar",
                "platform": "Zoom / YouTube Live",
                "description": "A deep dive into operational efficiency featuring case studies and live interactive software demonstrations."
            },
            {
                "title": f"How to Overcome Legacy Bottlenecks with {company_name}",
                "format": "Expert Video Case Study",
                "platform": "LinkedIn Ads / Video Hub",
                "description": "An interview-style video showcasing a client's success story, detailing metrics improvement and integration steps."
            }
        ],
        "ad_copies": [
            {
                "headline": f"Struggling with Department Inefficiencies? Try {product}.",
                "body": f"Discover how {company_name} helps leaders automate workflows, reduce operational costs, and drive ROI. Get a custom briefing in under 5 minutes.",
                "cta": "Get Free Demo",
                "platform": "LinkedIn Ads"
            },
            {
                "headline": "Scale Operations Faster.",
                "body": f"Eliminate manual bottlenecks. {company_name} provides robust, scalable B2B capabilities designed specifically for your industry's needs.",
                "cta": "Learn More",
                "platform": "Google Search"
            },
            {
                "headline": f"Deploy {product} in Days, Not Months.",
                "body": "No complex coding. No security compromises. Learn why elite operations teams are switching to our modern, integrated system today.",
                "cta": "Download Whitepaper",
                "platform": "Multi-platform"
            }
        ],
        "cta_suggestions": ["Request Custom Demo", "Calculate Your ROI", "Read Client Success Story", "Access Free Trial"],
        "estimated_reach": "185,500",
        "estimated_ctr": "1.75%",
        "estimated_cvr": "3.20%",
        "timeline_weeks": 8,
        "roadmap_actions": [
            {
                "week_number": 1,
                "week_theme": "Strategy Align & Content Launch",
                "actions": [
                    {
                        "action_name": "Deploy Landing Pages and Tracking",
                        "objective": "Establish a high-converting landing destination with robust analytics parameters in place.",
                        "business_reasoning": "Accurate attribution tracking ensures we can optimize channels based on real conversion performance.",
                        "execution_steps": ["Build customized landing pages", "Embed analytics pixels", "Perform forms integration tests"],
                        "required_resources": ["Web Designer", "Marketing Operations specialist"],
                        "responsible_team": "Growth Marketing Team",
                        "expected_kpi_impact": ["100% data capture rate", "Landing page load speed < 1.5s"],
                        "dependencies": ["Finalized product branding materials"],
                        "risk_level": "Low",
                        "expected_outcome": "Fully tested conversion pages ready for incoming traffic."
                    }
                ]
            },
            {
                "week_number": 2,
                "week_theme": "Paid Traffic Activation",
                "actions": [
                    {
                        "action_name": "Launch Search and Social Campaigns",
                        "objective": "Initiate target audience acquisition across LinkedIn and Google Search channels.",
                        "business_reasoning": "Early data collection allows us to identify high-performing search terms and refine ad copy quickly.",
                        "execution_steps": ["Activate pre-scheduled search ads", "Launch sponsored content sets", "Monitor initial ad delivery rates"],
                        "required_resources": ["Ad budget clearance", "Copywriter approval"],
                        "responsible_team": "Paid Acquisition Team",
                        "expected_kpi_impact": ["CTR > 1.1% on LinkedIn", "Cost-per-click under $6.50"],
                        "dependencies": ["Completed creative ad copy approvals"],
                        "risk_level": "Medium",
                        "expected_outcome": "Steady inflow of targeted traffic and initial lead generations."
                    }
                ]
            },
            {
                "week_number": 3,
                "week_theme": "Mid-Funnel Nurturing",
                "actions": [
                    {
                        "action_name": "Activate Email Drip Sequences",
                        "objective": "Nurture generated leads with highly relevant case studies and product demo offers.",
                        "business_reasoning": "Engaging leads within the first 7 days maximizes conversion likelihood and speeds up sales cycles.",
                        "execution_steps": ["Set up automated email flows", "Synthesize client success stories", "A/B test email subject lines"],
                        "required_resources": ["Marketing automation tools", "Copywriter"],
                        "responsible_team": "Lifecycle Marketing Team",
                        "expected_kpi_impact": ["Email open rate > 25%", "Demo booking rate of 4%"],
                        "dependencies": ["Leads generated in Week 2"],
                        "risk_level": "Low",
                        "expected_outcome": "Progressing warm prospects to booked discovery calls."
                    }
                ]
            },
            {
                "week_number": 4,
                "week_theme": "Optimization & Retargeting",
                "actions": [
                    {
                        "action_name": "Launch Retargeting Ads",
                        "objective": "Re-engage site visitors who did not complete the conversion form.",
                        "business_reasoning": "Retargeting yields the highest ROI by focusing ad spend on warm prospects who have already demonstrated interest.",
                        "execution_steps": ["Build custom retargeting audiences", "Design distinct retargeting copy", "Allocate 15% budget here"],
                        "required_resources": ["Creative banners", "Retargeting setup specialist"],
                        "responsible_team": "Growth Marketing Team",
                        "expected_kpi_impact": ["30% lower cost per conversion", "MQL volume boost by 15%"],
                        "dependencies": ["Sufficient site traffic from Week 2 and 3"],
                        "risk_level": "Low",
                        "expected_outcome": "Recaptured lost opportunities and boosted campaign conversion rates."
                    }
                ]
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
                "evidence": f"Budget range ({budget}) aligned with enterprise software tiers."
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
                {"signal": "Downloaded whitepaper on operations efficiency", "strength": "Medium"},
                {"signal": "Requested custom demo via online portal", "strength": "High"}
            ]
        },
        "risk_factors": [
            {
                "risk": "Competitor evaluation in progress.",
                "impact": "Medium",
                "mitigation": "Highlight USPs early and offer a dedicated migration assistant."
            },
            {
                "risk": "Technical integration dependencies.",
                "impact": "Medium",
                "mitigation": "Involve our solutions engineer in the next demo call to map out APIs."
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
                "action": "Send a personalized email containing client case studies in the technology sector.",
                "priority": "High",
                "timeline": "Next 24 hours"
            },
            {
                "action": "Connect with the buyer and key stakeholders on LinkedIn.",
                "priority": "Medium",
                "timeline": "Next 48 hours"
            },
            {
                "action": "Prepare custom trial environment showing how we resolve need.",
                "priority": "Medium",
                "timeline": "Next 3 days"
            }
        ],
        "next_best_action": "Call lead directly to schedule a 15-minute technical discovery session.",
        "priority_level": "Critical",
        "crm_readiness": True,
        "score_breakdown": [
            {"factor": "Budget Fit", "score": 24, "max": 30, "rationale": f"Stated budget of {budget} covers core platform costs but might limit add-on features."},
            {"factor": "Authority Level", "score": 18, "max": 25, "rationale": "Buyer is a key influencer; need to loop in department head for final sign-off."},
            {"factor": "Need Severity", "score": 27, "max": 30, "rationale": f"Stated pain points around '{need}' perfectly match our primary solutions."},
            {"factor": "Timeline Urgency", "score": 13, "max": 15, "rationale": f"Timeline of '{urgency}' represents an active purchasing window."}
        ]
    }

def get_market_fallback(industry, product_category, target_market, competitors, company_name) -> dict:
    if not company_name:
        company_name = "Enterprise"
    if not industry:
        industry = "Enterprise Software"
    if not product_category:
        product_category = "AI Automation Tools"
    if not target_market:
        target_market = "B2B SaaS / Global"
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
            "Increasing enterprise adoption of cloud-based automation systems.",
            "Demand for immediate data analysis and automated strategic insights.",
            "Rising operational costs forcing companies to streamline workflows.",
            "Integrations with existing CRM and marketing tech stacks.",
            "Transition from manual business research to real-time intelligence feeds."
        ],
        "market_risks": [
            "Shifting data privacy regulations in international jurisdictions.",
            "Rising customer acquisition costs across digital advertising channels.",
            "Talent shortages in specialized AI engineering and product design.",
            "Potential budget tightening in enterprise IT procurement.",
            "Security concerns regarding cloud storage and data sovereignty."
        ],
        "competitors": [
            {
                "name": comp_list[0],
                "strengths": "Deep brand equity, wide distribution channel network, massive R&D resources.",
                "weaknesses": "Complex implementation cycles, outdated user interface, rigid pricing structures.",
                "market_position": "Legacy Market Leader",
                "threat_level": "High"
            },
            {
                "name": comp_list[1],
                "strengths": "Strong user adoption, excellent developer API libraries, low entry-level pricing.",
                "weaknesses": "Limited advanced enterprise security controls, slow customer support response times.",
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
                "Expand presence in underserved regional sectors within Europe and APAC.",
                "Form strategic partnerships with digital consulting agencies."
            ],
            "threats": [
                "Aggressive discounting strategies from primary competitors.",
                "Sudden changes in search engine indexing and ad platform policies."
            ]
        },
        "pestel": {
            "political": "Stable government support for digital transformation grants, offset by trade tariffs on cross-border software imports.",
            "economic": "Moderate interest rates impacting corporate expansion budgets; rising demand for software that drives immediate cost savings.",
            "social": "Increasing work-from-home trends require cloud-native tools that facilitate asynchronous team collaboration.",
            "technological": "Advancements in large language models enable highly tailored outputs and automated workflows at fraction of cost.",
            "environmental": "Growing demand for green data hosting providers and digital documentation over printed materials.",
            "legal": "Tightening data compliance regulations require strict adherence to standards like GDPR, CCPA, and SOC 2."
        },
        "trends": [
            {
                "trend": "Self-Serve Product Led Growth (PLG)",
                "impact_score": 88,
                "timeframe": "12-18 months",
                "description": "Buyers increasingly prefer starting with free trials and interactive sandbox environments before talking to sales."
            },
            {
                "trend": "Data Sovereignty and Local Storage",
                "impact_score": 82,
                "timeframe": "6-12 months",
                "description": "Enterprise clients require options to store sensitive data locally or in specific geographic clouds."
            },
            {
                "trend": "Workflow Consolidation",
                "impact_score": 79,
                "timeframe": "18-24 months",
                "description": "Organizations are moving away from multiple point solutions, choosing single platforms that cover multiple needs."
            }
        ],
        "opportunities": [
            {
                "title": f"Mid-Market Legacy Displacement",
                "score": 90,
                "effort": "Medium",
                "revenue_potential": "High"
            },
            {
                "title": "API-First Integration Partnerships",
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
        business_type = "B2B SaaS"
    if not challenges:
        challenges = "manual pipeline management, low conversion rates"
    if not goals:
        goals = "double our qualified leads, reduce operational costs"

    return {
        "opportunity_score": 68,
        "executive_summary": f"An evaluation of {company_name}'s current {business_type} operations reveals significant growth potential. By addressing key bottlenecks in '{challenges}', the organization can unlock substantial efficiency gains. Implementing targeted automation will optimize representative bandwidth, reduce customer acquisition cost (CAC), and accelerate path toward goals like '{goals}'. Our 90-day roadmap outlines key tactical actions to secure these objectives.",
        "current_challenges": [
            {
                "challenge": f"Inefficiencies in '{safe_split_get(challenges, 0, 'operations')}'",
                "severity": "High",
                "impact": "Slows sales cycle velocity, increases manual tracking errors, and reduces lead engagement speed."
            },
            {
                "challenge": "Fragmented data across marketing and CRM stacks",
                "severity": "Medium",
                "impact": "Creates pipeline visibility blindspots, hindering data-driven decisions and scaling efforts."
            },
            {
                "challenge": "Long sales cycle conversion paths",
                "severity": "Medium",
                "impact": "Increases customer acquisition cost and limits cash-flow predictability."
            }
        ],
        "root_cause_analysis": [
            {
                "problem": f"Stalled pipeline tracking: '{safe_split_get(challenges, 0, 'operations')}'",
                "root_cause": "Absence of automated scoring workflows and standardized lead tracking triggers.",
                "evidence": "Sales representatives spend over 12 hours weekly performing manual data entry and email follow-ups."
            },
            {
                "problem": "Low lead-to-opportunity conversion rate",
                "root_cause": "Underutilized buyer intent signals and delay in engaging hot prospects.",
                "evidence": "Average response time to inbound inquiries exceeds 18 hours."
            }
        ],
        "growth_opportunities": [
            {
                "title": "Automated Intent Scoring integration",
                "score": 92,
                "effort": "Medium",
                "revenue_impact": "High"
            },
            {
                "title": "Interactive Self-Serve Sandbox demo environment",
                "score": 88,
                "effort": "High",
                "revenue_impact": "High"
            },
            {
                "title": "Automated Sales Pitch Deck generator custom tools",
                "score": 85,
                "effort": "Low",
                "revenue_impact": "Medium"
            },
            {
                "title": "Targeted Customer Case Study campaign",
                "score": 78,
                "effort": "Low",
                "revenue_impact": "Medium"
            },
            {
                "title": "Tiered enterprise account referral plan",
                "score": 70,
                "effort": "Medium",
                "revenue_impact": "Medium"
            }
        ],
        "revenue_opportunities": [
            {
                "source": "Upsell of custom analytics add-ons to top-tier accounts",
                "potential": "$45,000 ARR boost",
                "timeline": "Next 60 days"
            },
            {
                "source": "New B2B segment target packaging",
                "potential": "$70,000 new pipeline",
                "timeline": "Next 90 days"
            },
            {
                "source": "Developer API access subscription tier",
                "potential": "$30,000 ARR boost",
                "timeline": "Next 120 days"
            },
            {
                "source": "Enterprise support SLA premium pricing",
                "potential": "$25,000 ARR boost",
                "timeline": "Next 60 days"
            }
        ],
        "cost_optimization": [
            {
                "area": "Consolidating duplicate analytics tools",
                "potential_savings": "$12,000 Annually",
                "action": "Audit current software stack and migrate active users to a single consolidated license."
            },
            {
                "area": "Automating manual lead entry tasks",
                "potential_savings": "15 Hours/week per representative",
                "action": "Deploy automated lead ingestion API directly connecting web forms to CRM."
            },
            {
                "area": "Optimizing search engine ad keywords spend",
                "potential_savings": "$8,000 quarterly",
                "action": "Exclude low-intent keywords and shift budget to long-tail comparison search terms."
            },
            {
                "area": "Standardizing support ticket replies with AI templates",
                "potential_savings": "$6,000 Annually",
                "action": "Integrate auto-responses for common questions in client support portal."
            }
        ],
        "strategic_recommendations": [
            {
                "recommendation": "Deploy automated BANT scoring in CRM immediately.",
                "priority": "High",
                "impact": "High",
                "effort": "Low"
            },
            {
                "recommendation": "Set up instant Slack notifications for hot lead arrivals.",
                "priority": "High",
                "impact": "High",
                "effort": "Low"
            },
            {
                "recommendation": "Build custom landing pages for the top 3 target verticals.",
                "priority": "Medium",
                "impact": "High",
                "effort": "Medium"
            },
            {
                "recommendation": "Create a standardized Objection Handling script library.",
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
                "recommendation": "Establish developer APIs for customer data exports.",
                "priority": "Low",
                "impact": "Medium",
                "effort": "High"
            }
        ],
        "plan_30_day": [
            {
                "action": "CRM Lead scoring integration",
                "description": "Configure rules based on budget and role authority to filter inbound leads.",
                "owner": "Marketing Operations Lead",
                "success_metric": "Reduce lead review time by 50%",
                "tools": ["Salesforce API", "Segment", "Zapier"],
                "kpi": "Under 5 minutes review time"
            },
            {
                "action": "Objection handling script library publication",
                "description": "Standardize responses to pricing, implementation, and legacy objections.",
                "owner": "Sales Enablement Director",
                "success_metric": "Win rate improvement of 5%",
                "tools": ["Google Docs", "Notion", "Loom"],
                "kpi": "100% rep certification rate"
            }
        ],
        "plan_60_day": [
            {
                "action": "Targeted case study publication",
                "description": "Write and design two success stories highlighting time-savings ROI.",
                "owner": "Content Marketing Manager",
                "success_metric": "Generate 40+ downloads from LinkedIn",
                "tools": ["Canva", "HubSpot", "LinkedIn Ads Manager"],
                "kpi": "45 downloads"
            },
            {
                "action": "Lead response time SLA tracking",
                "description": "Implement automated notifications for sales reps on inbound leads.",
                "owner": "Sales Operations Lead",
                "success_metric": "Average response time under 15 minutes",
                "tools": ["Slack Integrations", "Calendly", "HubSpot SLA"],
                "kpi": "12 minutes response average"
            }
        ],
        "plan_90_day": [
            {
                "action": "Product-Led self-serve sandbox launch",
                "description": "Build a simplified playground version of our software for early trials.",
                "owner": "Product Lead / CTO Office",
                "success_metric": "Conversion from sandbox to demo booking > 15%",
                "tools": ["Next.js Sandbox", "Auth0", "Stripe Pilot"],
                "kpi": "18% booking conversion"
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
            {"initiative": "CRM scoring setup", "urgency": "High", "impact": "High"},
            {"initiative": "Rep onboarding academy", "urgency": "Medium", "impact": "High"},
            {"initiative": "Case study content push", "urgency": "High", "impact": "Medium"},
            {"initiative": "API exports library", "urgency": "Low", "impact": "Medium"},
            {"initiative": "Self-Serve sandbox portal", "urgency": "Medium", "impact": "High"}
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
