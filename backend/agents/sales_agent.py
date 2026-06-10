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
        f"Follow these strict formatting guidelines to ensure the content size is balanced and professional:\n"
        f"1. buyer_persona: title (2-4 words), priorities (exactly 3 items, 4-8 words each), and objections (exactly 3 items, 4-8 words each).\n"
        f"2. decision_maker_map: exactly 3 key roles. Provide role (2-4 words), influence (1-2 words), concern (6-12 words).\n"
        f"3. sales_readiness_score: an integer from 0 to 100.\n"
        f"4. elevator_pitch: exactly 2 sentences (25-35 words) starting with '{co_name} helps {customer}...'.\n"
        f"5. value_proposition: a headline (4-8 words) and exactly 4 benefit points (8-12 words each).\n"
        f"6. roi_argument: a headline (4-8 words), ROI calculation description (15-25 words), and timeframe (2-4 words).\n"
        f"7. proposal_outline: exactly 6 sections (2-4 words each).\n"
        f"8. closing_script: exactly 3-4 sentences (40-60 words) including {co_name}'s name and benefits.\n"
        f"9. discovery_questions: exactly 6 situational questions (8-15 words each).\n"
        f"10. follow_up_strategy: timing (2-4 words) and exactly 3 steps (6-12 words each).\n"
        f"11. meeting_agenda: exactly 4 items. For each specify time (e.g. '5 mins'), topic (2-4 words), and goal (6-12 words).\n"
        f"12. objection_handling: exactly 4 pairs of objection (6-12 words) and response (15-25 words).\n"
        f"13. email_template: subject (4-8 words) and body (60-90 words).\n"
        f"14. linkedin_template: connection_note (20-30 words, max 300 chars) and follow_up (40-60 words, max 500 chars).\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Sales Strategist for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=PITCH_SCHEMA, retries=2, fast=False, max_tokens=1800)
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
