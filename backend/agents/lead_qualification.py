"""
agents/lead_qualification.py
Lead Qualification Agent — BANT + Intent analysis, company-specific.

Consolidating lead qualification and scoring into a single LLM request
respects Groq's 6,000 TPM limit and ensures complete response data.
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .base import invoke_structured, compute_confidence, LEAD_SCHEMA, get_grounding_instruction

class LeadState(TypedDict):
    name: str
    company: str
    industry: str
    company_size: str
    decision_role: str
    budget: str
    need: str
    urgency: str
    grounding_context: str
    company_name: str
    company_industry: str
    result: dict
    confidence_score: int
    error: Optional[str]

def lead_node(state: LeadState) -> dict:
    """
    Evaluate BANT, intent, risks, recommended actions, and lead score in a single request.
    """
    from .base import build_company_system_prefix
    grounding = get_grounding_instruction(state.get("grounding_context", ""))
    co_prefix = build_company_system_prefix(
        state.get("company_name", ""), state.get("company_industry", ""),
        role_title="Senior Lead Qualification Specialist"
    )
    co_name = state.get("company_name", "") or "the company"
    lead_co = state.get("company", "Unknown")

    prompt = (
        f"EVALUATING LEAD FOR: {co_name}\n"
        f"Lead Name: {state['name']}\n"
        f"Lead Company: {lead_co}\n"
        f"Industry: {state.get('industry', 'Unknown')}\n"
        f"Company Size: {state.get('company_size', 'Unknown')}\n"
        f"Decision Role: {state.get('decision_role', 'Unknown')}\n"
        f"Budget Stated: {state['budget']}\n"
        f"Need Stated: {state['need']}\n"
        f"Urgency Stated: {state.get('urgency', 'Unknown')}\n\n"
        f"Perform a comprehensive lead qualification and scoring assessment for this lead's fit with {co_name}:\n"
        f"1. Evaluate budget, authority, need, and timeline (BANT), and provide a score (0-100), detailed assessment, and context-specific evidence for each.\n"
        f"2. Assess buying intent, listing specific intent signals and their strength.\n"
        f"3. Identify 3-4 potential risk factors that could prevent the sale, along with impact levels and mitigations.\n"
        f"4. Recommend 4-5 actions for {co_name}'s sales team, and specify the single next best action.\n"
        f"5. Calculate an overall lead_score (weighted: Budget 30%, Authority 25%, Need 30%, Timeline 15%) and conversion_probability.\n"
        f"6. Determine lead temperature (Hot/Warm/Cold), priority_level, and CRM readiness.\n"
        f"7. Provide a detailed score breakdown and a 2-3 sentence qualification summary.\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Lead Qualification Specialist for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=LEAD_SCHEMA, retries=2, fast=False, max_tokens=2500)
    return {"result": result}

def action_node(state: LeadState) -> dict:
    result = state.get("result", {})
    result.setdefault("lead_score", 50)
    result.setdefault("conversion_probability", 35)
    result.setdefault("temperature", "Warm")
    result.setdefault("priority_level", "Medium")
    result.setdefault("crm_readiness", True)

    required = ["lead_score", "conversion_probability", "temperature", "bant",
                "qualification_summary", "buying_intent", "risk_factors",
                "recommended_actions", "next_best_action"]
    score = compute_confidence(result, required)
    return {"result": result, "confidence_score": score}

def build_lead_graph():
    g = StateGraph(LeadState)
    g.add_node("lead_eval", lead_node)
    g.add_node("action",   action_node)
    g.set_entry_point("lead_eval")
    g.add_edge("lead_eval", "action")
    g.add_edge("action",   END)
    return g.compile()

_lead_graph = None

def run_lead_score(name: str, budget: str, need: str, company: str = "",
                   industry: str = "", company_size: str = "", decision_role: str = "",
                   urgency: str = "", grounding_context: str = "",
                   company_name: str = "", company_industry: str = "") -> dict:
    global _lead_graph
    if _lead_graph is None:
        _lead_graph = build_lead_graph()
    state: LeadState = {
        "name": name, "company": company, "industry": industry,
        "company_size": company_size, "decision_role": decision_role,
        "budget": budget, "need": need, "urgency": urgency,
        "grounding_context": grounding_context,
        "company_name": company_name,
        "company_industry": company_industry,
        "result": {}, "confidence_score": 0, "error": None,
    }
    final = _lead_graph.invoke(state)
    return {"data": final.get("result", {}), "confidence_score": final.get("confidence_score", 0)}
