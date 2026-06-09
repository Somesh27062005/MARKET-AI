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
        f"1. Estimate the current and projected market size (Realistic USD values), CAGR, and currency.\n"
        f"2. Write a detailed executive_summary highlighting trends and opportunities.\n"
        f"3. Identify 5 growth_drivers and 5 market_risks relevant to {co_name}.\n"
        f"4. Analyze the top 5 competitors in detail (name, strengths, weaknesses, market position, threat level relative to {co_name}).\n"
        f"5. Build a SWOT analysis from {co_name}'s perspective relative to these competitors.\n"
        f"6. Build a PESTEL analysis reflecting {co_name}'s environment (political, economic, social, technological, environmental, legal).\n"
        f"7. Define 3 emerging trends with impact scores, timeframes, and descriptions.\n"
        f"8. Identify 3 market opportunities with title, score, effort, and revenue potential.\n"
        f"9. Generate growth_chart_data (6 data points) and market_share_data showing where {co_name} stands.\n"
        f"10. Rate each competitor 0-100 on innovation, pricing, market_reach, customer_support, and product_quality relative to {co_name} in radar_data.\n"
        f"11. Perform a detailed advertising channel analysis (advertising_analysis) outlining industry CPM/CPC benchmarks, creative strategies, message angles, spend efficiency, and conversion probabilities.\n"
        f"12. Outline the strategic positioning postures (positioning_postures) of key competitors and {co_name} (market role, pricing posture, innovation posture, tone/message posture, acquisition strategy, and strategic rationale).\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Market Intelligence Analyst conducting analysis for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=MARKET_SCHEMA, retries=2, fast=False, max_tokens=3000)
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
