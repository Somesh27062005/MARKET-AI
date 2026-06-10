"""
agents/market_intelligence.py
Market Research Agent + Competitor Intelligence Agent

Consolidating market research and competitor intelligence into a single
LLM request respects Groq's 6,000 TPM limit and ensures complete response data.
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .base import invoke_structured, compute_confidence, MARKET_SCHEMA, get_grounding_instruction

# ── State ──────────────────────────────────────────────────────────────────────
class MarketState(TypedDict):
    industry: str
    product_category: str
    target_market: str
    competitors_raw: str
    time_horizon: str
    grounding_context: str
    company_name: str
    company_industry: str
    result: dict
    confidence_score: int
    error: Optional[str]

# ── Node 1: Unified market research + competitor analysis ────────────────────

def market_node(state: MarketState) -> dict:
    """
    Run market size sizing, SWOT, PESTEL, and competitors in a single request.
    """
    from .base import build_company_system_prefix
    grounding = get_grounding_instruction(state.get("grounding_context", ""))
    co_prefix = build_company_system_prefix(
        state.get("company_name", ""), state.get("company_industry", ""),
        role_title="Senior Market Intelligence Analyst"
    )
    co_name  = state.get("company_name", "") or "the company"
    industry  = state['industry']
    category  = state.get('product_category', 'General')
    target    = state.get('target_market', 'Global')
    horizon   = state.get('time_horizon', '12 months')
    known     = state.get('competitors_raw', '')

    prompt = (
        f"COMPANY: {co_name}\n"
        f"Industry: {industry}\n"
        f"Product Category: {category}\n"
        f"Target Market: {target}\n"
        f"Time Horizon: {horizon}\n"
        f"Known Competitors: {known or 'Auto-detect top 5 competitors'}\n\n"
        f"Conduct a comprehensive market research and competitor analysis for {co_name}. All outputs must reference {co_name} specifically and be realistic for their industry and business size.\n"
        f"Follow these strict formatting guidelines to ensure the content size is balanced and professional:\n"
        f"1. Estimate the current and projected market size (Realistic USD values), CAGR, and currency.\n"
        f"2. Write a concise 50-70 word executive_summary highlighting trends and opportunities.\n"
        f"3. Identify exactly 4 growth_drivers (8-12 words each) and exactly 4 market_risks (8-12 words each) relevant to {co_name}.\n"
        f"4. Analyze exactly 4 competitors in detail (name: 1-3 words, strengths: 8-12 words, weaknesses: 8-12 words, market position: 2-3 words, threat_level: High/Medium/Low).\n"
        f"5. Build a SWOT analysis from {co_name}'s perspective: strengths (exactly 3, 6-10 words each), weaknesses (exactly 3, 6-10 words each), opportunities (exactly 3, 6-10 words each), threats (exactly 3, 6-10 words each).\n"
        f"6. Build a PESTEL analysis reflecting {co_name}'s environment: each of the 6 fields must be exactly 1 sentence (12-18 words).\n"
        f"7. Define exactly 3 emerging trends. For each specify trend (2-4 words), impact_score (0-100), timeframe (e.g. '12-18 months'), and description (12-18 words).\n"
        f"8. Identify exactly 3 market opportunities with title (3-5 words), score (0-100), effort (Low/Medium/High), and revenue_potential (Low/Medium/High).\n"
        f"9. Generate growth_chart_data (exactly 5 data points) and market_share_data (exactly 4 competitors plus 'Others').\n"
        f"10. Rate exactly 3 competitors 0-100 on innovation, pricing, reach, support, and product relative to {co_name} in radar_data.\n"
        f"11. Perform advertising channel analysis (advertising_analysis) for exactly 3 channels. Specify channel (2-4 words), cpm_cpc_benchmark (e.g. 'CPC: $3.50'), creative_strategy (8-12 words), message_angle (8-12 words), ad_spend_efficiency (High/Medium/Low), conversion_probability (e.g. '2.5%').\n"
        f"12. Outline the strategic positioning postures (positioning_postures) of exactly 3 competitors. Specify brand_name (1-3 words), market_role (Leader/Challenger/Follower/Niche), pricing_posture (Premium/Value/Economy), innovation_posture (Pioneer/Fast-Follower/Conservative), message_posture (Educational/Authoritative/Emotional/Disruptive), customer_acquisition_posture (Inbound/Outbound/PLG/Partnerships), and strategic_rationale (10-15 words).\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Market Intelligence Analyst conducting analysis for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=MARKET_SCHEMA, retries=2, fast=False, max_tokens=2500)
    return {"result": result}


# ── Node 2: Synthesis ─────────────────────────────────────────────────────────
def synthesis_node(state: MarketState) -> dict:
    merged = state.get("result", {})
    # Ensure defaults so frontend never gets undefined
    merged.setdefault("growth_drivers", [])
    merged.setdefault("market_risks", [])
    merged.setdefault("trends", [])
    merged.setdefault("opportunities", [])
    merged.setdefault("growth_chart_data", [
        {"period": "2020", "value": 2.0}, {"period": "2021", "value": 2.4},
        {"period": "2022", "value": 2.9}, {"period": "2023", "value": 3.5},
        {"period": "2024", "value": 4.2}, {"period": "2025E", "value": 5.1},
        {"period": "2026E", "value": 6.2},
    ])
    merged.setdefault("market_share_data", [
        {"name": "Leader", "value": 35}, {"name": "Challenger", "value": 22},
        {"name": "Niche A", "value": 15}, {"name": "Niche B", "value": 12},
        {"name": "Others", "value": 16},
    ])
    merged.setdefault("advertising_analysis", [])
    merged.setdefault("positioning_postures", [])
    return {"result": merged}


# ── Node 3: Confidence Scoring ────────────────────────────────────────────────
def score_node(state: MarketState) -> dict:
    result = state.get("result", {})
    required = ["executive_summary", "market_size", "competitors", "swot",
                "pestel", "trends", "opportunities", "growth_chart_data"]
    score = compute_confidence(result, required)
    return {"confidence_score": score}


# ── Graph ────────────────────────────────────────────────────────────────────────
def build_market_graph():
    g = StateGraph(MarketState)
    g.add_node("market_eval", market_node)
    g.add_node("synthesis",   synthesis_node)
    g.add_node("score",       score_node)

    g.set_entry_point("market_eval")
    g.add_edge("market_eval", "synthesis")
    g.add_edge("synthesis",  "score")
    g.add_edge("score",      END)
    return g.compile()


_market_graph = None

def run_market_analysis(industry: str, product_category: str = "",
                         target_market: str = "", competitors_raw: str = "",
                         time_horizon: str = "12 months", grounding_context: str = "",
                         company_name: str = "", company_industry: str = "") -> dict:
    global _market_graph
    if _market_graph is None:
        _market_graph = build_market_graph()

    initial_state: MarketState = {
        "industry": industry,
        "product_category": product_category,
        "target_market": target_market,
        "competitors_raw": competitors_raw,
        "time_horizon": time_horizon,
        "grounding_context": grounding_context,
        "company_name": company_name,
        "company_industry": company_industry,
        "result": {},
        "confidence_score": 0,
        "error": None,
    }

    final_state = _market_graph.invoke(initial_state)
    return {
        "data": final_state.get("result", {}),
        "confidence_score": final_state.get("confidence_score", 0),
    }
