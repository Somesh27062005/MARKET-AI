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
        f"You are a premium, elite marketing strategist. Generate a concise, high-impact marketing campaign strategy for {co_name}'s product.\n"
        f"Fill in every field of the schema with specific, realistic content. Keep descriptions concise and punchy to optimize readability and generation time.\n\n"
        f"Follow these guidelines for each schema field:\n"
        f"1. campaign_name: A strategic, high-impact campaign name (2-4 words).\n"
        f"2. executive_campaign_overview: A concise, clear executive summary (40-50 words) explaining the growth opportunity and campaign targets.\n"
        f"3. strategic_goals: Provide exactly 3 distinct strategic goals. For each, specify `goal_name` (2-4 words) and `business_context` (a short, clear explanation of 10-15 words showing how this aligns with metrics).\n"
        f"4. persona_profile: Provide a concise description of `business_challenges` (15-20 words), exactly 3 `pain_points` (6-10 words each), and exactly 3 `buying_motivations` (6-10 words each).\n"
        f"5. funnel: Map out the 3 stages: `awareness`, `consideration`, and `conversion`. For each, provide exactly 2 specific `tactics` (short B2B tactics, 6-10 words each), exactly 2 `kpis` (specific metrics, 3-6 words each), and `budget_pct` integer.\n"
        f"6. budget_allocation: Allocate percentages (totaling 100) across exactly 2-3 marketing channels. Provide `channel` name, integer `percent`, and a concise `rationale` (10-15 words explaining the strategic selection).\n"
        f"7. kpis: Provide exactly 3 campaign-level KPIs. For each, specify `metric` name, realistic target value/percentage (`target`), and `measurement` method (a short explanation of 8-12 words detailing tracking tools).\n"
        f"8. content_ideas: Generate exactly 1 content idea for each of the selected platforms: {platform}. Specify `title`, `format`, `platform` (name), and `description` (a short explanation of 10-15 words outlining the content angle).\n"
        f"9. ad_copies: Generate exactly 1 ad copy variation for each of the selected platforms: {platform}. Specify `platform`, `headline` (compelling B2B headline, 4-8 words), `body` (persuasive, punchy ad copy, 15-25 words), and `cta` (clear call-to-action, 2-3 words).\n"
        f"10. social_media_posts: Generate exactly 1 high-quality social post for each of the selected platforms: {platform}. Specify `platform` and `copy`.\n"
        f"    - For LinkedIn, Facebook, and WhatsApp, the `copy` MUST be a B2B marketing post of 8 to 12 lines (approx. 80 to 120 words) containing a hook, a brief problem statement, 3 short benefit bullet points, a CTA link, and 3-4 relevant hashtags.\n"
        f"    - For Twitter/X, the `copy` MUST be a short post of 4 to 6 lines (approx. 40 to 60 words) containing a hook, a single core benefit, and 2-3 hashtags.\n"
        f"11. calendar: Provide a week-by-week timeline for exactly 4 weeks (weeks 1 to 4). Specify `week` (integer), `theme` (weekly focus, 3-5 words), and exactly 2 action `tasks` (actionable and short, 6-10 words each).\n\n"
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
    
    # Defensive key initialization
    if "funnel" not in result or not isinstance(result["funnel"], dict):
        result["funnel"] = {
            "awareness": {
                "tactics": ["LinkedIn Sponsored Content", "Google Search Ads"],
                "kpis": ["CTR", "Impressions"],
                "budget_pct": 35
            },
            "consideration": {
                "tactics": ["Product Whitepaper", "Expert Webinar"],
                "kpis": ["Downloads", "Registrants"],
                "budget_pct": 40
            },
            "conversion": {
                "tactics": ["Free Sandbox Demo", "1-on-1 Consultation"],
                "kpis": ["Demos Booked", "Conversion Rate"],
                "budget_pct": 25
            }
        }
    else:
        for stage in ["awareness", "consideration", "conversion"]:
            if stage not in result["funnel"] or not isinstance(result["funnel"][stage], dict):
                result["funnel"][stage] = {"tactics": ["Paid Search / Social"], "kpis": ["Clicks"], "budget_pct": 33}
            else:
                s_data = result["funnel"][stage]
                s_data.setdefault("tactics", ["Paid Search / Social"])
                s_data.setdefault("kpis", ["Clicks"])
                s_data.setdefault("budget_pct", 33)

    if "calendar" not in result or not isinstance(result["calendar"], list) or not result["calendar"]:
        result["calendar"] = [
            {"week": 1, "theme": "Tracking & Strategy Align", "tasks": ["Deploy landing pages", "Embed analytics pixels"]},
            {"week": 2, "theme": "Search & Social Launch", "tasks": ["Activate ad campaigns", "Monitor CPC bids"]},
            {"week": 3, "theme": "Lead Nurture Flow", "tasks": ["Set up automated emails", "Distribute case study"]},
            {"week": 4, "theme": "Budget Optimization", "tasks": ["Adjust channel weights", "Review conversions"]}
        ]
        
    if "budget_allocation" not in result or not isinstance(result["budget_allocation"], list) or not result["budget_allocation"]:
        result["budget_allocation"] = [
            {"channel": "LinkedIn Professional Ads", "percent": 50, "rationale": "High-fidelity targeting of professional buyer personas."},
            {"channel": "Google Intent Search", "percent": 50, "rationale": "Captures active demand for operations optimization tools."}
        ]

    if "kpis" not in result or not isinstance(result["kpis"], list) or not result["kpis"]:
        result["kpis"] = [
            {"metric": "Cost Per Lead (CPL)", "target": "< $90.00", "measurement": "Total ad spend divided by qualified B2B leads."},
            {"metric": "Demo Booking Rate", "target": "> 3.0%", "measurement": "Percentage of visitors completing the demo booking form."},
            {"metric": "Sales Pipeline Deals", "target": "20+ Opportunities", "measurement": "Qualified prospects passing BANT qualification criteria."}
        ]
    
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
            "copy": (
                f"📊 Modern B2B operations departments are facing a silent crisis: manual bottleneck fatigue.\n\n"
                f"Every day, high-value teams waste up to 40% of their working hours on repetitive manual data entries, "
                f"siloed systems coordination, and human-error corrections. These bottlenecks don't just stall growth; "
                f"they increase operational risks and lead to key talent burnout.\n\n"
                f"At {co_name}, we built {state.get('product', 'our software solution')} to solve this exact challenge.\n\n"
                f"Here is how our custom operational framework streamlines your workflow and drives success:\n"
                f"• ⚡ AUTOMATED FLOWS: Eliminate legacy manual pipelines with intelligent, trigger-based task execution.\n"
                f"• 📉 ERROR REDUCTION: Standardize operational logic to minimize system errors by up to 45%.\n"
                f"• 🔍 CENTRALIZED TRACKING: Gain instant visibility with secure, real-time KPI health dashboards.\n"
                f"• 🛠️ NATIVE INTEGRATION: Connect seamlessly with your existing tech stack without complex coding overrides.\n\n"
                f"Operations leaders from mid-market to enterprise firms are using our playbook to optimize their teams, "
                f"reduce operational overhead, and achieve higher ROI.\n\n"
                f"Ready to unlock your team's true potential? Read our latest B2B case study guide and discover how easy "
                f"it is to deploy automated workflows in days, not months.\n\n"
                f"👉 Get your copy here: [Link]\n\n"
                f"#Operations #B2B #Automation #WorkflowEfficiency #TechSolutions #BusinessGrowth"
            )
        },
        "twitter": {
            "platform": "Twitter/X",
            "copy": (
                f"Stop letting legacy manual processes stall your team's growth. 🚀\n\n"
                f"{state.get('product', 'our product')} by {co_name} deploys in days, delivering "
                f"real-time operations tracking with robust security. Here is what you get:\n"
                f"• ⚡ Automated trigger-based workflows\n"
                f"• 📉 Up to 40% reduction in errors\n"
                f"• 📊 Real-time health dashboard\n\n"
                f"Optimize your B2B department and scale today. Get your custom briefing:\n"
                f"👉 [Link]\n\n"
                f"#Efficiency #TechSolutions #B2B #Automation"
            )
        },
        "x": {
            "platform": "Twitter/X",
            "copy": (
                f"Stop letting legacy manual processes stall your team's growth. 🚀\n\n"
                f"{state.get('product', 'our product')} by {co_name} deploys in days, delivering "
                f"real-time operations tracking with robust security. Here is what you get:\n"
                f"• ⚡ Automated trigger-based workflows\n"
                f"• 📉 Up to 40% reduction in errors\n"
                f"• 📊 Real-time health dashboard\n\n"
                f"Optimize your B2B department and scale today. Get your custom briefing:\n"
                f"👉 [Link]\n\n"
                f"#Efficiency #TechSolutions #B2B #Automation"
            )
        },
        "facebook": {
            "platform": "Facebook",
            "copy": (
                f"Accelerate your team's output! ⚡\n\n"
                f"Are your operations stalled by manual bottlenecks and fragmented systems? You're not alone. "
                f"Many mid-market B2B departments struggle with administrative overhead that costs time and revenue.\n\n"
                f"{co_name} introduces {state.get('product', 'our product')}, a comprehensive operational system built to "
                f"eliminate manual bottlenecks, secure business logic, and drive high-impact outcomes. We help you:\n"
                f"• Automate task transitions between departments\n"
                f"• Secure database workflows with B2B compliance standards\n"
                f"• Gain real-time executive summaries of performance metrics\n\n"
                f"Deploy our workflow framework to increase efficiency and support department scalability.\n\n"
                f"Read our playbook and start optimizing today:\n"
                f"👉 [Link]\n\n"
                f"#BusinessTech #Operations #WorkflowAutomation #B2B #TechFlow"
            )
        },
        "whatsapp": {
            "platform": "WhatsApp",
            "copy": (
                f"Hello! 👋 Discover how {co_name} helps you scale operations and optimize workflows with "
                f"{state.get('product', 'our product')}.\n\n"
                f"Key Benefits:\n"
                f"✅ Automate repetitive B2B workflows\n"
                f"✅ Reduce operational errors by up to 40%\n"
                f"✅ Monitor key stats on real-time dashboards\n\n"
                f"Contact us or schedule a custom demo today! [Link]"
            )
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
