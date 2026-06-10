"""
agents/business_consultant.py
Business Consultant Agent — company-specific analysis.

Consolidating challenges, opportunities, risks, and roadmaps into a single
LLM request respects Groq's 6,000 TPM limit and ensures complete response data.
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .base import invoke_structured, compute_confidence, INSIGHTS_SCHEMA, get_grounding_instruction

class InsightsState(TypedDict):
    business_type: str
    challenges: str
    goals: str
    target_audience: str
    industry_context: str
    grounding_context: str
    company_name: str
    company_industry: str
    result: dict
    confidence_score: int
    error: Optional[str]

def insights_node(state: InsightsState) -> dict:
    """
    Run the entire strategic diagnostic analysis in a single unified LLM request.
    """
    from .base import build_company_system_prefix
    grounding = get_grounding_instruction(state.get("grounding_context", ""))
    co_prefix = build_company_system_prefix(
        state.get("company_name", ""), state.get("company_industry", ""),
        role_title="Senior Strategy Consultant"
    )
    co_name   = state.get("company_name", "") or state['business_type']
    biz_type  = state['business_type']
    industry  = state.get('industry_context', 'General')
    challenges= state['challenges']
    goals     = state.get('goals', 'Business growth')
    audience  = state.get('target_audience', '')

    prompt = (
        f"COMPANY: {co_name}\n"
        f"Business Type: {biz_type}\n"
        f"Industry Context: {industry}\n"
        f"Target Audience: {audience}\n"
        f"Current Challenges: {challenges}\n"
        f"Goals: {goals}\n\n"
        f"Perform a comprehensive business consultancy and strategic insights analysis for {co_name}. All outputs must reference {co_name} specifically and be realistic for their industry and business size.\n"
        f"Follow these strict formatting guidelines to ensure the content size is balanced and professional:\n"
        f"1. Estimate an overall opportunity_score (0-100) reflecting {co_name}'s current business health.\n"
        f"2. Write a concise 50-70 word executive_summary outlining the strategic plan.\n"
        f"3. Diagnose exactly 3 current_challenges. For each specify challenge (3-5 words), severity (High/Medium/Low), and impact (10-15 words).\n"
        f"4. Provide a root_cause_analysis for exactly 3 core problems, detailing problem (4-8 words), root_cause (8-12 words), and evidence (10-15 words).\n"
        f"5. Identify exactly 4 growth_opportunities with scored details (score 0-100), effort (Low/Medium/High), and revenue_impact (Low/Medium/High).\n"
        f"6. Suggest exactly 3 new revenue_opportunities (source: 6-10 words, potential: 4-8 words, timeline: 2-4 words).\n"
        f"7. List exactly 3 cost_optimization opportunities (area: 3-5 words, potential_savings: 4-8 words, action: 10-15 words).\n"
        f"8. Make exactly 4 strategic_recommendations (recommendation: 8-12 words, priority: High/Medium/Low, impact: 8-12 words, effort: Low/Medium/High).\n"
        f"9. Map exactly 4 initiatives on a priority_matrix. For each specify initiative (3-5 words), urgency (High/Medium/Low), and impact (High/Medium/Low).\n"
        f"10. Set exactly 4 KPI targets using actual metrics (kpi: 2-4 words, current, target, timeline: e.g. '60 days').\n"
        f"11. Create a 30/60/90-day implementation roadmap (using arrays plan_30_day, plan_60_day, and plan_90_day). Provide exactly 2 actions per phase. Each item must have: action (3-5 words), description (exactly 2 sentences explaining what to do and why), owner, success_metric (6-10 words), tools (list of exactly 2 specific tools), and kpi (measurable target value).\n"
        f"12. Assess exactly 3 competitive_risks (risk: 6-10 words, competitor: 1-2 words, likelihood: High/Medium/Low) and exactly 3 operational_risks (risk: 6-10 words, probability: High/Medium/Low, impact: High/Medium/Low, mitigation: 10-15 words).\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Strategy Consultant for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=INSIGHTS_SCHEMA, retries=2, fast=False, max_tokens=1800)
    return {"result": result}

def merge_node(state: InsightsState) -> dict:
    result = state.get("result", {})
    co_name = state.get("company_name", "") or state['business_type']
    result.setdefault("opportunity_score", 65)
    result.setdefault("executive_summary", f"Strategic analysis for {co_name}.")

    required = ["opportunity_score", "executive_summary", "current_challenges",
                "root_cause_analysis", "growth_opportunities", "revenue_opportunities",
                "cost_optimization", "strategic_recommendations", "priority_matrix",
                "plan_30_day", "plan_60_day", "plan_90_day", "kpi_targets"]
    score = compute_confidence(result, required)
    return {"result": result, "confidence_score": score}

def build_insights_graph():
    g = StateGraph(InsightsState)
    g.add_node("insights_eval", insights_node)
    g.add_node("merge",         merge_node)
    g.set_entry_point("insights_eval")
    g.add_edge("insights_eval", "merge")
    g.add_edge("merge",         END)
    return g.compile()

_insights_graph = None

def run_business_insights(business_type: str, challenges: str, goals: str = "",
                           target_audience: str = "", industry_context: str = "",
                           grounding_context: str = "",
                           company_name: str = "", company_industry: str = "") -> dict:
    global _insights_graph
    if _insights_graph is None:
        _insights_graph = build_insights_graph()
    state: InsightsState = {
        "business_type": business_type, "challenges": challenges,
        "goals": goals, "target_audience": target_audience,
        "industry_context": industry_context,
        "grounding_context": grounding_context,
        "company_name": company_name,
        "company_industry": company_industry,
        "result": {}, "confidence_score": 0, "error": None,
    }
    final = _insights_graph.invoke(state)
    return {"data": final.get("result", {}), "confidence_score": final.get("confidence_score", 0)}
