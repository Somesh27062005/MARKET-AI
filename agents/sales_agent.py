"""
agents/sales_agent.py
Sales Agent: consolidated single-node architecture.

Consolidating persona analysis, sales pitches, and objection handling 
into a single LLM request respects Groq's 6,000 TPM limit and ensures complete response data.
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .base import invoke_structured, compute_confidence, PITCH_SCHEMA, get_grounding_instruction

class SalesState(TypedDict):
    product: str
    customer: str
    target_role: str
    usp: str
    pain_points: str
    grounding_context: str
    company_name: str
    company_industry: str
    result: dict
    confidence_score: int
    error: Optional[str]

def pitch_node(state: SalesState) -> dict:
    """
    Generate buyer personas, org maps, sales scripts, emails, and objections in a single LLM request.
    """
    from .base import build_company_system_prefix
    grounding = get_grounding_instruction(state.get("grounding_context", ""))
    co_prefix = build_company_system_prefix(
        state.get("company_name", ""), state.get("company_industry", ""),
        role_title="Senior Sales Strategist"
    )
    co_name   = state.get("company_name", "") or "the company"
    product   = state['product']
    customer  = state['customer']
    role      = state.get('target_role', 'C-Suite / VP')
    usp       = state.get('usp', '')
    pain      = state.get('pain_points', '')

    prompt = (
        f"COMPANY: {co_name}\n"
        f"Product/Service: {product}\n"
        f"Customer Type: {customer}\n"
        f"Target Decision Maker: {role}\n"
        f"USPs: {usp}\n"
        f"Pain Points: {pain}\n\n"
        f"Generate a comprehensive sales pitch package for {co_name}'s product. All outputs must refer to {co_name} specifically and be realistic for their industry and business size.\n"
        f"1. Build a detailed buyer persona specific to {co_name}'s typical customer (title, priorities, budget_authority, typical_objections).\n"
        f"2. Map the decision makers involved in a purchase decision for {co_name}'s offering (role, influence, concern).\n"
        f"3. Estimate a sales_readiness_score (0-100) based on fit.\n"
        f"4. Write a 2-3 sentence elevator_pitch starting with '{co_name} helps {customer}...'.\n"
        f"5. Create a value_proposition with a headline and 4 key benefit points.\n"
        f"6. Provide a detailed roi_argument with a headline, ROI calculation, and timeframe.\n"
        f"7. Draft a formal proposal_outline (7-8 sections).\n"
        f"8. Write a closing_script including {co_name}'s name and benefits.\n"
        f"9. Formulate 8 situational discovery_questions.\n"
        f"10. Design a follow_up_strategy (timing and steps).\n"
        f"11. Detail a 5-item meeting_agenda for a demo/discovery call.\n"
        f"12. Draft 6 objection_handling pairs (objection and response).\n"
        f"13. Write a follow-up email_template (subject and body).\n"
        f"14. Write a linkedin_template (connection note ≤300 chars, follow-up ≤500 chars).\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Sales Strategist for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=PITCH_SCHEMA, retries=2, fast=False, max_tokens=2500)
    return {"result": result}

def email_merge_node(state: SalesState) -> dict:
    result = state.get("result", {})
    co_name = state.get("company_name", "") or state['product']
    result.setdefault("sales_readiness_score", 72)
    result.setdefault("elevator_pitch", f"{co_name} helps {state['customer']} achieve their goals faster.")

    required = ["elevator_pitch", "value_proposition", "roi_argument", "objection_handling",
                "discovery_questions", "email_template", "linkedin_template", "meeting_agenda",
                "buyer_persona", "closing_script"]
    score = compute_confidence(result, required)
    return {"result": result, "confidence_score": score}

def build_sales_graph():
    g = StateGraph(SalesState)
    g.add_node("pitch_eval", pitch_node)
    g.add_node("merge",      email_merge_node)
    g.set_entry_point("pitch_eval")
    g.add_edge("pitch_eval", "merge")
    g.add_edge("merge",      END)
    return g.compile()

_sales_graph = None

def run_pitch(product: str, customer: str, target_role: str = "",
              usp: str = "", pain_points: str = "", grounding_context: str = "",
              company_name: str = "", company_industry: str = "") -> dict:
    global _sales_graph
    if _sales_graph is None:
        _sales_graph = build_sales_graph()
    state: SalesState = {
        "product": product, "customer": customer, "target_role": target_role,
        "usp": usp, "pain_points": pain_points,
        "grounding_context": grounding_context,
        "company_name": company_name,
        "company_industry": company_industry,
        "result": {}, "confidence_score": 0, "error": None,
    }
    final = _sales_graph.invoke(state)
    return {"data": final.get("result", {}), "confidence_score": final.get("confidence_score", 0)}
