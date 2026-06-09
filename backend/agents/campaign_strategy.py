"""
agents/campaign_strategy.py
Campaign Strategy Agent — consolidated single-node architecture.

Consolidating audience, funnel, and content into a single LLM call saves 
~3,500 tokens and avoids hitting Groq's 6,000 TPM limit.
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .base import invoke_structured, compute_confidence, CAMPAIGN_SCHEMA, get_grounding_instruction

class CampaignState(TypedDict):
    product: str
    audience: str
    platform: str
    budget: str
    goals: str
    grounding_context: str
    company_name: str
    company_industry: str
    result: dict
    confidence_score: int
    error: Optional[str]

def campaign_node(state: CampaignState) -> dict:
    """
    Run the entire campaign generation in a single unified LLM request to respect TPM limits.
    """
    from .base import build_company_system_prefix
    grounding    = get_grounding_instruction(state.get("grounding_context", ""))
    co_prefix    = build_company_system_prefix(
        state.get("company_name", ""), state.get("company_industry", ""),
        role_title="Senior Campaign Strategist"
    )
    product  = state['product']
    audience = state['audience']
    platform = state.get('platform', 'Multi-platform')
    budget   = state.get('budget', 'Flexible')
    goals    = state.get('goals', 'Brand awareness and lead generation')
    co_name  = state.get('company_name', 'the company')
    prompt = (
        f"COMPANY: {co_name}\n"
        f"Product/Service: {product}\n"
        f"Target Audience: {audience}\n"
        f"Platform: {platform}\n"
        f"Budget: {budget}\n"
        f"Goals: {goals}\n\n"
        f"You are a premium, elite management consultant. Generate a highly comprehensive, detailed, and realistic marketing marketing campaign strategy for {co_name}'s product. "
        f"Every section of the dashboard must generate rich, structured, consultant-grade content. Never generate only scores, short bullets, or generic roadmap tasks. "
        f"Every insight must include Context, Strategic Reasoning, Business Impact, Expected Outcome, and Recommended Actions.\n\n"
        f"Follow these strict content depth and structure rules:\n\n"
        f"1. campaign_name: A strategic, high-impact campaign name.\n\n"
        f"2. executive_campaign_overview:\n"
        f"   - Write a detailed 100-150 word executive summary.\n"
        f"   - Explain: Why this campaign exists, Current business situation, Growth opportunity, Strategic objective, and Expected business impact.\n"
        f"   - Avoid placeholders or generic intros.\n\n"
        f"3. strategic_goals:\n"
        f"   - Provide 3 distinct strategic goals.\n"
        f"   - For EACH goal, specify:\n"
        f"     - goal_name: Strategic goal title.\n"
        f"     - business_context: Detailed market/business background.\n"
        f"     - why_it_matters: Why this is critical to the organization.\n"
        f"     - expected_impact: Quantitative or qualitative outcome.\n"
        f"     - success_metrics: Precise indicators of success.\n"
        f"     - risks: Real risk factors associated with this goal.\n"
        f"     - mitigation_plan: Specific, actionable counter-measures.\n\n"
        f"4. expected_outcomes:\n"
        f"   - Provide detailed consulting-grade explanations (2 sentences each) for each of the following:\n"
        f"     - revenue_impact\n"
        f"     - lead_impact\n"
        f"     - brand_impact\n"
        f"     - market_position_impact\n"
        f"     - customer_retention_impact\n\n"
        f"5. persona_profile:\n"
        f"   - Provide a comprehensive buyer profile of 80-100 words.\n"
        f"   - Fill in details for: job_titles, responsibilities, business_challenges, pain_points, buying_motivations, decision_triggers, common_objections, preferred_communication_channels, preferred_content_types, purchase_journey_behaviour, budget_authority, expected_sales_cycle.\n\n"
        f"6. funnel_analysis:\n"
        f"   - Write 50-75 words for each of the 4 funnel stages detailing these exact sub-fields:\n"
        f"     - awareness_stage: objective, target_audience_behaviour, recommended_channels (list of strings), expected_results, budget_pct (int)\n"
        f"     - consideration_stage: customer_mindset, key_content (list of strings), conversion_drivers (list of strings), budget_pct (int)\n"
        f"     - conversion_stage: sales_activities (list of strings), closing_strategies (list of strings), performance_indicators (list of strings), budget_pct (int)\n"
        f"     - retention_stage: customer_success_activities (list of strings), upsell_opportunities (list of strings), loyalty_strategy\n\n"
        f"7. budget_allocation_rationale:\n"
        f"   - For each marketing channel (3 channels), explain with 40-50 words per channel:\n"
        f"     - channel: Name (e.g. LinkedIn, Google Ads)\n"
        f"     - allocation_pct: Percentage (int)\n"
        f"     - reasoning: In-depth consulting explanation for this allocation\n"
        f"     - expected_roi: Anticipated return\n"
        f"     - advantages: List of key advantages\n"
        f"     - risks: List of key risks\n"
        f"     - success_metrics: List of success indicators\n\n"
        f"8. kpi_explanations:\n"
        f"   - For each KPI (at least 3), write 40-50 words covering:\n"
        f"     - kpi_name: e.g. Cost Per Qualified Lead (CPQL)\n"
        f"     - what_it_measures: Description\n"
        f"     - why_it_matters: Why it is critical\n"
        f"     - industry_benchmark: Realistic benchmark value\n"
        f"     - expected_value: Target value\n"
        f"     - success_threshold: Minimum threshold\n"
        f"     - risk_indicators: Warn signals if underperforming\n"
        f"     - optimization_strategy: Action plan to optimize it\n\n"
        f"9. kpi_commentary: Brief strategic commentary summarizing why these KPIs were selected (40-50 words).\n\n"
        f"10. roadmap_actions:\n"
        f"    - Provide a week-by-week timeline (weeks 1 to 4).\n"
        f"    - For each week, provide a week_theme and a list containing exactly ONE highly detailed action card (each action card 60-85 words, no generic summaries):\n"
        f"      - action_name: Detailed action card name\n"
        f"      - objective: Precise goal of this action\n"
        f"      - business_reasoning: Rationale for executing this\n"
        f"      - execution_steps: Detailed step-by-step list\n"
        f"      - required_resources: Resources needed\n"
        f"      - responsible_team: e.g., Growth Marketing Team, Product Team\n"
        f"      - expected_kpi_impact: Projected changes in metrics\n"
        f"      - dependencies: Pre-requisites/Dependencies\n"
        f"      - risk_level: Low, Medium, or High\n"
        f"      - expected_outcome: Outcome description\n\n"
        f"11. Provide content_ideas, ad_copies, cta_suggestions, estimated_reach, estimated_ctr, estimated_cvr, timeline_weeks, and social_media_posts (a list of social media posts, each with platform, copy, and media_suggestion. Generate at least 3 engaging posts for relevant platforms like LinkedIn, Twitter/X, or Instagram).\n"
        f"IMPORTANT: Reach must be calculated dynamically based on budget ({budget}) and platform ({platform}) and avoid simple round placeholder numbers (e.g. use realistic numbers like 142,500 instead of 100,000).\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Campaign Strategist for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=CAMPAIGN_SCHEMA, retries=2, fast=False, max_tokens=4000)
    return {"result": result}

def metrics_node(state: CampaignState) -> dict:
    result = state.get("result", {})
    co_name = state.get('company_name', '') or state['product']
    result.setdefault("campaign_name", f"{co_name} Growth Campaign")
    result.setdefault("objectives", ["Increase brand awareness", "Drive qualified leads"])
    
    # Calculate realistic metric values
    budget_str = state.get('budget', 'Flexible')
    platform_str = state.get('platform', 'Multi-platform')
    goals_str = state.get('goals', 'Brand awareness')

    # Base budget estimation
    budget_map = {
        "under $1k": 800,
        "$1k-$5k": 3000,
        "$5k-$25k": 15000,
        "$25k-$100k": 60000,
        "$100k+": 250000
    }
    cleaned_budget = str(budget_str).lower().strip()
    budget_val = 5000
    for k, v in budget_map.items():
        if k in cleaned_budget:
            budget_val = v
            break

    # CPM estimation
    cpm_map = {
        "linkedin": 45,
        "instagram": 10,
        "twitter": 8,
        "google": 15,
        "email": 2,
        "multi-platform": 18
    }
    cleaned_platform = str(platform_str).lower().strip()
    cpm_val = 18
    for k, v in cpm_map.items():
        if k in cleaned_platform:
            cpm_val = v
            break

    # Natural deterministic variance
    import random
    seed_str = f"{budget_str}_{platform_str}_{goals_str}_{co_name}"
    r_gen = random.Random(abs(hash(seed_str)))
    variance = r_gen.uniform(0.85, 1.15)
    
    calc_reach_val = int((budget_val / cpm_val) * 1000 * variance)
    calc_reach = f"{calc_reach_val:,}" if calc_reach_val >= 1000 else str(calc_reach_val)
    
    # CTR & CVR estimation
    ctr_map = {
        "linkedin": 1.25,
        "instagram": 1.75,
        "twitter": 0.85,
        "google": 3.40,
        "email": 2.60,
        "multi-platform": 1.65
    }
    cvr_map = {
        "linkedin": 2.20,
        "instagram": 3.10,
        "twitter": 1.45,
        "google": 4.20,
        "email": 5.80,
        "multi-platform": 2.75
    }
    
    ctr_base = ctr_map.get(cleaned_platform, 1.65)
    cvr_base = cvr_map.get(cleaned_platform, 2.75)
    
    goals_lower = str(goals_str).lower()
    if "lead" in goals_lower or "cvr" in goals_lower or "conversion" in goals_lower or "sale" in goals_lower:
        cvr_base *= 1.2
        ctr_base *= 0.95
    elif "brand" in goals_lower or "awareness" in goals_lower or "reach" in goals_lower:
        ctr_base *= 1.15
        cvr_base *= 0.8
        
    calc_ctr = f"{ctr_base * r_gen.uniform(0.9, 1.1):.2f}%"
    calc_cvr = f"{cvr_base * r_gen.uniform(0.9, 1.1):.2f}%"

    # Set or clean up static values
    reach = result.get("estimated_reach", "")
    ctr = result.get("estimated_ctr", "")
    cvr = result.get("estimated_cvr", "")

    if not reach or reach in ("10,000,000", "10M", "string", "50K-100K", "50,000"):
        result["estimated_reach"] = calc_reach
    if not ctr or ctr in ("2%", "2.0%", "2.1%", "string"):
        result["estimated_ctr"] = calc_ctr
    if not cvr or cvr in ("5%", "5.0%", "3.4%", "string"):
        result["estimated_cvr"] = calc_cvr

    result.setdefault("timeline_weeks", 8)

    # ─── BACKWARD COMPATIBILITY MAPPINGS ──────────────────────────────────────
    # Map new strategic_goals to objectives
    if "strategic_goals" in result and isinstance(result["strategic_goals"], list):
        result["objectives"] = [goal.get("goal_name", "") for goal in result["strategic_goals"] if goal.get("goal_name")]
    
    # Map new persona_profile to persona
    if "persona_profile" in result and isinstance(result["persona_profile"], dict):
        p_prof = result["persona_profile"]
        result["persona"] = {
            "name": p_prof.get("job_titles", ["Decision Maker"])[0] if p_prof.get("job_titles") else "Target Persona",
            "age_range": "30-55",
            "role": p_prof.get("responsibilities", ""),
            "industry": state.get("company_industry", ""),
            "pain_points": p_prof.get("pain_points", []),
            "goals": p_prof.get("buying_motivations", []),
            "channels": p_prof.get("preferred_communication_channels", [])
        }
        
    # Map new funnel_analysis to funnel
    if "funnel_analysis" in result and isinstance(result["funnel_analysis"], dict):
        f_anal = result["funnel_analysis"]
        aw = f_anal.get("awareness_stage", {})
        co = f_anal.get("consideration_stage", {})
        cv = f_anal.get("conversion_stage", {})
        result["funnel"] = {
            "awareness": {
                "tactics": aw.get("recommended_channels", []),
                "kpis": [aw.get("expected_results", "")] if aw.get("expected_results") else [],
                "budget_pct": aw.get("budget_pct", 30)
            },
            "consideration": {
                "tactics": co.get("key_content", []),
                "kpis": co.get("conversion_drivers", []),
                "budget_pct": co.get("budget_pct", 40)
            },
            "conversion": {
                "tactics": cv.get("sales_activities", []),
                "kpis": cv.get("performance_indicators", []),
                "budget_pct": cv.get("budget_pct", 30)
            }
        }
        
    # Map new budget_allocation_rationale to budget_allocation
    if "budget_allocation_rationale" in result and isinstance(result["budget_allocation_rationale"], list):
        result["budget_allocation"] = [
            {
                "channel": item.get("channel", "Other"),
                "percent": item.get("allocation_pct", 0),
                "rationale": item.get("reasoning", "")
            }
            for item in result["budget_allocation_rationale"]
        ]
        
    # Map new kpi_explanations to kpis
    if "kpi_explanations" in result and isinstance(result["kpi_explanations"], list):
        result["kpis"] = [
            {
                "metric": item.get("kpi_name", ""),
                "target": item.get("expected_value", ""),
                "measurement": item.get("what_it_measures", "")
            }
            for item in result["kpi_explanations"]
        ]
        
    # Map new roadmap_actions to calendar
    if "roadmap_actions" in result and isinstance(result["roadmap_actions"], list):
        result["calendar"] = [
            {
                "week": item.get("week_number", 1),
                "theme": item.get("week_theme", "Strategic Steps"),
                "tasks": [act.get("action_name", "") for act in item.get("actions", []) if act.get("action_name")]
            }
            for item in result["roadmap_actions"]
        ]

    # Ensure social_media_posts is always populated
    if "social_media_posts" not in result or not isinstance(result["social_media_posts"], list) or not result["social_media_posts"]:
        result["social_media_posts"] = [
            {
                "platform": "LinkedIn",
                "copy": f"Is your team looking to optimize workflows? 📉 With {co_name}'s latest integration for {state.get('product', 'our product')}, you can automate key tasks, reduce manual errors, and scale departments seamlessly. #Efficiency #Operations #B2B",
                "media_suggestion": "An infographic showing workflow comparison."
            },
            {
                "platform": "Twitter/X",
                "copy": f"Stop letting manual processes stall your growth. 🚀 {state.get('product', 'our product')} by {co_name} deploys in days, delivering real-time operations tracking with robust security. Get your custom briefing: [Link] #WorkforceEfficiency #TechSolutions",
                "media_suggestion": "A product demo GIF showing user dashboard features."
            }
        ]

    required = ["campaign_name", "objectives", "persona", "funnel", "content_ideas",
                "ad_copies", "budget_allocation", "kpis", "calendar", "social_media_posts"]
    score = compute_confidence(result, required)
    return {"result": result, "confidence_score": score}

def build_campaign_graph():
    g = StateGraph(CampaignState)
    g.add_node("campaign", campaign_node)
    g.add_node("metrics",  metrics_node)
    g.set_entry_point("campaign")
    g.add_edge("campaign", "metrics")
    g.add_edge("metrics",  END)
    return g.compile()

_campaign_graph = None

def run_campaign(product: str, audience: str, platform: str = "",
                 budget: str = "", goals: str = "", grounding_context: str = "",
                 company_name: str = "", company_industry: str = "") -> dict:
    global _campaign_graph
    if _campaign_graph is None:
        _campaign_graph = build_campaign_graph()

    state: CampaignState = {
        "product": product, "audience": audience, "platform": platform,
        "budget": budget, "goals": goals,
        "grounding_context": grounding_context,
        "company_name": company_name,
        "company_industry": company_industry,
        "result": {}, "confidence_score": 0, "error": None,
    }
    final = _campaign_graph.invoke(state)
    return {"data": final.get("result", {}), "confidence_score": final.get("confidence_score", 0)}
