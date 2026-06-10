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
        f"You are a premium, elite marketing strategist. Generate a highly tailored marketing campaign strategy for {co_name}'s product.\n"
        f"Fill in every field of the schema with high-quality, specific, and realistic content. Keep descriptions and context blocks professional but concise (1-2 sentences per item) to respect token budgets.\n\n"
        f"Follow these guidelines for each schema field:\n"
        f"1. campaign_name: A strategic, high-impact campaign name.\n"
        f"2. executive_campaign_overview: A concise 50-70 word executive summary explaining the growth opportunity and strategic objective.\n"
        f"3. strategic_goals: Provide exactly 3 distinct strategic goals. For each, specify `goal_name` and `business_context` (a short 1-sentence explanation of why it matters).\n"
        f"4. persona_profile: A simplified persona profile matching target demographics. Provide a short description of `business_challenges`, list 3 specific `pain_points`, and list 3 specific `buying_motivations`.\n"
        f"5. funnel: Map out the 3 stages: `awareness`, `consideration`, and `conversion`. For each, provide a list of specific `tactics` (e.g. blog post, demo), a list of `kpis` (e.g. views, signups), and a `budget_pct` integer.\n"
        f"6. budget_allocation: Allocate percentages (totaling 100) across 2-3 marketing channels. Provide `channel` name, integer `percent`, and a brief 1-sentence `rationale`.\n"
        f"7. kpis: Provide at least 3 campaign-level KPIs. For each, specify `metric` name, realistic target value/percentage (`target`), and how it is measured (`measurement`).\n"
        f"8. content_ideas, ad_copies, social_media_posts: Generate creative elements ONLY for the platforms specified in the selected list: {platform}. Do not generate content for any other platforms. Provide at least one content idea, ad copy, and social media post copy for each selected platform.\n"
        f"9. calendar: Provide a week-by-week timeline (weeks 1 to 4). For each week, provide a `theme` and a list of 2-3 specific action `tasks`.\n\n"
        f"{grounding}"
    )

    sys_prompt = f"{co_prefix}You are a Senior Campaign Strategist for {co_name}. Return JSON only."
    result = invoke_structured(sys_prompt, prompt, schema_hint=CAMPAIGN_SCHEMA, retries=2, fast=False, max_tokens=2000)
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

    # Parse requested platforms
    requested_platforms = [p.strip().lower() for p in platform_str.split(',') if p.strip()]
    if not requested_platforms:
        requested_platforms = ["multi-platform"]

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

    # CPM estimation (average of selected platforms)
    cpm_map = {
        "linkedin": 45,
        "twitter": 8,
        "x": 8,
        "google": 15,
        "facebook": 12,
        "youtube": 18,
        "tiktok": 9,
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

    # Natural deterministic variance
    import random
    seed_str = f"{budget_str}_{platform_str}_{goals_str}_{co_name}"
    r_gen = random.Random(abs(hash(seed_str)))
    variance = r_gen.uniform(0.85, 1.15)
    
    calc_reach_val = int((budget_val / cpm_val) * 1000 * variance)
    calc_reach = f"{calc_reach_val:,}" if calc_reach_val >= 1000 else str(calc_reach_val)
    
    # CTR & CVR estimation (average of selected platforms)
    ctr_map = {
        "linkedin": 1.25,
        "twitter": 0.85,
        "x": 0.85,
        "google": 3.40,
        "facebook": 1.50,
        "youtube": 2.10,
        "tiktok": 2.20,
        "whatsapp": 2.00,
        "multi-platform": 1.65
    }
    cvr_map = {
        "linkedin": 2.20,
        "twitter": 1.45,
        "x": 1.45,
        "google": 4.20,
        "facebook": 2.60,
        "youtube": 3.20,
        "tiktok": 3.80,
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
            "name": "Target Persona",
            "age_range": "30-55",
            "role": p_prof.get("business_challenges", ""),
            "industry": state.get("company_industry", ""),
            "pain_points": p_prof.get("pain_points", []),
            "goals": p_prof.get("buying_motivations", []),
            "channels": [platform_str.split(",")[0].strip()] if platform_str else ["LinkedIn"]
        }

    # Filter generated content to match ONLY requested platforms (plus Google Search/Ads in ad copies/ideas)
    content_ideas_in_result = result.get("content_ideas", [])
    if isinstance(content_ideas_in_result, list) and content_ideas_in_result:
        filtered_content_ideas = []
        for idea in content_ideas_in_result:
            idea_platform = str(idea.get("platform", "")).lower().strip()
            if any(req in idea_platform or idea_platform in req for req in requested_platforms) or "google" in idea_platform or "search" in idea_platform:
                filtered_content_ideas.append(idea)
        if filtered_content_ideas:
            result["content_ideas"] = filtered_content_ideas

    ad_copies_in_result = result.get("ad_copies", [])
    if isinstance(ad_copies_in_result, list) and ad_copies_in_result:
        filtered_ad_copies = []
        for ad in ad_copies_in_result:
            ad_platform = str(ad.get("platform", "")).lower().strip()
            if any(req in ad_platform or ad_platform in req for req in requested_platforms) or "google" in ad_platform or "search" in ad_platform:
                filtered_ad_copies.append(ad)
        if filtered_ad_copies:
            result["ad_copies"] = filtered_ad_copies

    posts_in_result = result.get("social_media_posts", [])
    if not isinstance(posts_in_result, list):
        posts_in_result = []
        
    filtered_posts = []
    for post in posts_in_result:
        post_platform = str(post.get("platform", "")).lower().strip()
        if any(req in post_platform or post_platform in req for req in requested_platforms):
            filtered_posts.append(post)

    # Ensure EVERY single requested platform has at least one post in filtered_posts
    existing_platforms = [post.get("platform", "").lower().strip() for post in filtered_posts]
    
    platform_mapping_fallbacks = {
        "linkedin": {
            "platform": "LinkedIn",
            "copy": f"Is your team looking to optimize workflows? 📉 With {co_name}'s latest integration for {state.get('product', 'our product')}, you can automate key tasks, reduce manual errors, and scale departments seamlessly. #Efficiency #Operations #B2B"
        },
        "twitter": {
            "platform": "Twitter/X",
            "copy": f"Stop letting manual processes stall your growth. 🚀 {state.get('product', 'our product')} by {co_name} deploys in days, delivering real-time operations tracking with robust security. Get your custom briefing: [Link] #WorkforceEfficiency #TechSolutions"
        },
        "x": {
            "platform": "Twitter/X",
            "copy": f"Stop letting manual processes stall your growth. 🚀 {state.get('product', 'our product')} by {co_name} deploys in days, delivering real-time operations tracking with robust security. Get your custom briefing: [Link] #WorkforceEfficiency #TechSolutions"
        },
        "facebook": {
            "platform": "Facebook",
            "copy": f"Accelerate your team's output. {co_name} introduces {state.get('product', 'our product')}, a comprehensive operational system built to eliminate manual bottlenecks, secure business logic, and drive high-impact outcomes. Learn how we can help your team scale: [Link]"
        },
        "whatsapp": {
            "platform": "WhatsApp",
            "copy": f"Hello! 👋 Discover how {co_name} helps you scale operations with {state.get('product', 'our product')}. Contact us to learn more! [Link]"
        },
        "google": {
            "platform": "Google Search",
            "copy": f"Ad Headline: Automate Your Operations | Try {state.get('product', 'our product')} Today\nAd Description: Boost efficiency, reduce manual errors, and scale seamlessly with {co_name}. Contact us for a free demo today."
        }
    }

    for req in requested_platforms:
        has_post = any(req in ep or ep in req for ep in existing_platforms)
        if not has_post:
            found = False
            for k, v in platform_mapping_fallbacks.items():
                if k in req or req in k:
                    filtered_posts.append(v)
                    found = True
                    break
            if not found:
                filtered_posts.append({
                    "platform": req.capitalize(),
                    "copy": f"Discover how {co_name} helps you scale operations with {state.get('product', 'our product')}. Contact us to learn more!"
                })
                
    result["social_media_posts"] = filtered_posts

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
