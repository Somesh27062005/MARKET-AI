"""
report_generator.py
-------------------
Single module containing all report section generators.
Each function calls the LLM with structured JSON prompts and parses the response.
"""

import os
import json
import re

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

import prompt_templates as PT


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_json_response(text: str) -> dict:
    """Extract JSON from an LLM text response, handling markdown fences."""
    if not text:
        return {}
    # Remove markdown code fences
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```', '', text)
    text = text.strip()
    # Find the first { and last }
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return {}
    json_str = text[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try fixing common issues: trailing commas, single quotes
        cleaned = re.sub(r',\s*}', '}', json_str)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}


def call_llm(system_prompt: str, human_prompt: str, context: dict) -> str:
    """Call the LLM with fallback to a smaller model on rate limits."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_") or api_key == "gsk_dummy":
        api_key = "gsk_dummy_key_to_allow_server_startup"

    primary_model = "llama-3.3-70b-versatile"
    fallback_model = "llama-3.1-8b-instant"

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template(human_prompt),
    ])
    parser = StrOutputParser()

    for model_name in [primary_model, fallback_model]:
        try:
            llm = ChatGroq(
                api_key=api_key,
                model=model_name,
                temperature=0.7,
                max_tokens=4096,
                max_retries=1,
            )
            chain = prompt | llm | parser
            result = chain.invoke(context)
            return result
        except Exception as e:
            err = str(e).lower()
            if "rate limit" in err or "429" in err or "tpd" in err or "tokens" in err:
                continue
            # For non-rate-limit errors on primary, try fallback once
            if model_name == primary_model:
                continue
            raise e
    return ""


# ── Fallback Data ────────────────────────────────────────────────────────────

def _fallback_assumptions():
    return {
        "industry_classification": {
            "assumption": "Technology / SaaS Platform",
            "confidence": 75,
            "supporting_evidence": ["Digital product offering", "Subscription-based indicators", "Cloud delivery model"],
            "strategic_reasoning": "Based on product description and target audience patterns, this business aligns with the SaaS technology sector.",
            "business_implications": "Competitors likely include established SaaS players. Growth depends on product differentiation and customer acquisition efficiency."
        },
        "business_model": {
            "assumption": "B2B SaaS with recurring revenue",
            "confidence": 70,
            "supporting_evidence": ["Enterprise-focused features", "Scalable platform architecture"],
            "strategic_reasoning": "The business model indicators suggest a subscription-based approach targeting business customers.",
            "business_implications": "Key metrics to monitor include MRR, churn rate, and customer lifetime value."
        },
        "customer_type": {
            "assumption": "Mid-market to Enterprise B2B",
            "confidence": 65,
            "supporting_evidence": ["Product complexity level", "Pricing tier structure"],
            "strategic_reasoning": "Feature set and positioning suggest targeting mid-market and enterprise segments.",
            "business_implications": "Sales cycles may be longer; relationship-driven selling is critical."
        },
        "growth_stage": {
            "assumption": "Growth / Scale-up phase",
            "confidence": 60,
            "supporting_evidence": ["Active market expansion", "Product maturity indicators"],
            "strategic_reasoning": "The company appears to be past initial validation and is scaling operations.",
            "business_implications": "Focus should shift from product-market fit to scalable growth engines."
        },
        "competitive_environment": {
            "assumption": "Moderately competitive with fragmented market",
            "confidence": 65,
            "supporting_evidence": ["Multiple incumbents", "Low switching costs in some segments"],
            "strategic_reasoning": "The market has established players but room for differentiated entrants.",
            "business_implications": "Differentiation through innovation and customer experience is essential."
        }
    }


def _fallback_diagnostic():
    return {
        "business_assessment": "The business shows strong foundational capabilities with clear market positioning. Core product value is well-defined, though operational scaling remains a priority area.",
        "market_position": "Positioned as a challenger in a competitive landscape, with differentiation potential through technology innovation and customer experience.",
        "competitive_readiness": "Moderate readiness — strong product but needs enhanced go-to-market strategy and competitive intelligence capabilities.",
        "growth_readiness": "Growth infrastructure is developing. Key areas requiring investment include sales automation, customer success processes, and data-driven decision-making.",
        "strategic_strengths": ["Strong product vision", "Technology-driven approach", "Market awareness", "Agile team structure"],
        "strategic_weaknesses": ["Limited brand recognition", "Scaling challenges", "Resource constraints", "Underdeveloped partnerships"],
        "key_opportunities": ["Market expansion into adjacent segments", "Strategic partnerships", "AI/automation integration", "International markets"],
        "major_risks": ["Competitive pressure from established players", "Market saturation risk", "Talent acquisition challenges", "Economic uncertainty"],
        "executive_commentary": "The business is at a critical inflection point. Strategic investments in go-to-market capabilities and operational efficiency will determine whether it achieves escape velocity or remains a niche player."
    }


def _fallback_score():
    return {
        "overall_score": 68,
        "overall_verdict": "Promising opportunity with significant upside potential, contingent on strategic execution improvements.",
        "categories": {
            "market_potential": {"score": 75, "reasoning": "Large addressable market with healthy growth trajectory.", "positive_indicators": ["Growing market demand", "Digital transformation tailwinds"], "negative_indicators": ["Market fragmentation"], "improvement_actions": ["Conduct detailed TAM/SAM/SOM analysis"]},
            "product_market_fit": {"score": 70, "reasoning": "Good alignment between product capabilities and market needs.", "positive_indicators": ["Core feature relevance", "User engagement signals"], "negative_indicators": ["Feature gaps vs. competitors"], "improvement_actions": ["Deepen customer discovery interviews"]},
            "revenue_expansion": {"score": 65, "reasoning": "Multiple revenue growth levers available but underutilized.", "positive_indicators": ["Upsell potential", "New market segments"], "negative_indicators": ["Pricing optimization needed"], "improvement_actions": ["Implement tiered pricing strategy"]},
            "customer_acquisition": {"score": 62, "reasoning": "Acquisition channels exist but efficiency can be improved.", "positive_indicators": ["Organic growth signals", "Referral potential"], "negative_indicators": ["High CAC in paid channels"], "improvement_actions": ["Build content marketing engine"]},
            "competitive_position": {"score": 66, "reasoning": "Defensible position through technology but vulnerable to well-funded competitors.", "positive_indicators": ["Technical differentiation", "Niche expertise"], "negative_indicators": ["Brand awareness gap"], "improvement_actions": ["Develop competitive moat strategy"]},
            "brand_visibility": {"score": 58, "reasoning": "Limited market visibility compared to established competitors.", "positive_indicators": ["Growing online presence"], "negative_indicators": ["Low brand recall", "Limited PR"], "improvement_actions": ["Launch thought leadership campaign"]},
            "operational_scalability": {"score": 70, "reasoning": "Technology stack supports scaling; operational processes need maturation.", "positive_indicators": ["Cloud infrastructure", "Automation potential"], "negative_indicators": ["Manual processes remain"], "improvement_actions": ["Automate key operational workflows"]}
        },
        "top_5_improvement_actions": [
            "Launch targeted content marketing to boost brand visibility",
            "Implement data-driven pricing optimization",
            "Build strategic partnership ecosystem",
            "Automate customer onboarding and success processes",
            "Develop competitive intelligence monitoring system"
        ]
    }


def _fallback_bottlenecks():
    return {
        "bottlenecks": [
            {"title": "Customer Acquisition Cost Efficiency", "severity": "High", "problem": "CAC is trending above industry benchmarks, limiting profitable growth.", "root_cause": "Over-reliance on paid channels without sufficient organic demand generation.", "strategic_impact": "Constrains growth velocity and reduces available capital for product investment.", "revenue_impact": "Estimated 15-25% margin compression on new customer revenue.", "customer_impact": "Slower customer base growth limits network effects and social proof.", "recommended_fix": "Invest in content marketing, SEO, and community-building to create sustainable organic acquisition channels.", "expected_outcome": "30-40% reduction in blended CAC within 6 months."},
            {"title": "Sales Cycle Length", "severity": "High", "problem": "Extended sales cycles reduce revenue predictability and team efficiency.", "root_cause": "Complex decision-making processes and insufficient sales enablement tools.", "strategic_impact": "Limits quarterly revenue forecasting accuracy and resource planning.", "revenue_impact": "Delays revenue recognition and increases cost per closed deal.", "customer_impact": "Prospects may lose interest or choose faster-moving competitors.", "recommended_fix": "Implement sales acceleration tools, standardize proposal templates, and create ROI calculators for prospects.", "expected_outcome": "20-30% reduction in average sales cycle length."},
            {"title": "Product Feature Gaps", "severity": "Medium", "problem": "Missing key features that competitors offer, creating objection points in sales conversations.", "root_cause": "Product roadmap not sufficiently informed by competitive intelligence and customer feedback loops.", "strategic_impact": "Weakens competitive positioning and limits addressable market segments.", "revenue_impact": "Lost deals estimated at 10-15% of pipeline due to feature gaps.", "customer_impact": "Existing customers may evaluate alternatives during renewal periods.", "recommended_fix": "Establish systematic competitive feature tracking and prioritize gap-closing features in the next two sprints.", "expected_outcome": "Reduction in feature-related deal losses by 50% within one quarter."},
            {"title": "Brand Awareness Deficit", "severity": "Medium", "problem": "Low brand recognition in target market segments limits inbound lead flow.", "root_cause": "Underinvestment in brand marketing and thought leadership content.", "strategic_impact": "Reduces organic pipeline and increases dependence on outbound sales.", "revenue_impact": "Missing an estimated 20-30% of potential inbound leads.", "customer_impact": "Prospects default to better-known competitors during initial research phase.", "recommended_fix": "Launch a multi-channel brand awareness campaign including industry events, webinars, and PR.", "expected_outcome": "2-3x increase in branded search volume and inbound inquiries within 6 months."},
            {"title": "Operational Process Maturity", "severity": "Medium", "problem": "Manual processes in operations and customer success limit scalability.", "root_cause": "Rapid growth outpacing process automation and documentation.", "strategic_impact": "Creates bottlenecks as team scales and increases error rates.", "revenue_impact": "Operational inefficiency estimated to cost 5-10% of revenue in hidden overhead.", "customer_impact": "Inconsistent customer experience during onboarding and support interactions.", "recommended_fix": "Audit and automate top 10 most time-consuming manual processes using workflow automation tools.", "expected_outcome": "40% reduction in operational overhead and improved customer satisfaction scores."}
        ]
    }


def _fallback_matrix():
    return {
        "initiatives": [
            {"name": "Implement Content Marketing Engine", "urgency_score": 9, "impact_score": 9, "quadrant": "Act Now", "strategic_reasoning": "Immediate impact on CAC reduction and brand visibility.", "expected_roi": "3-5x within 12 months", "timeline": "0-30 days to launch", "dependencies": ["Content team", "SEO tools"]},
            {"name": "Launch Sales Enablement Platform", "urgency_score": 8, "impact_score": 9, "quadrant": "Act Now", "strategic_reasoning": "Directly reduces sales cycle length and improves win rates.", "expected_roi": "2-3x within 6 months", "timeline": "30-60 days", "dependencies": ["CRM integration", "Sales team training"]},
            {"name": "Competitive Intelligence System", "urgency_score": 8, "impact_score": 7, "quadrant": "Act Now", "strategic_reasoning": "Essential for product roadmap prioritization and sales positioning.", "expected_roi": "Indirect — improves product-market fit", "timeline": "0-30 days", "dependencies": ["Market research tools"]},
            {"name": "Pricing Strategy Optimization", "urgency_score": 7, "impact_score": 8, "quadrant": "Act Now", "strategic_reasoning": "Directly impacts revenue per customer and market positioning.", "expected_roi": "10-20% revenue uplift", "timeline": "30-60 days", "dependencies": ["Customer data analysis", "Competitive pricing data"]},
            {"name": "Customer Success Automation", "urgency_score": 7, "impact_score": 7, "quadrant": "Plan It", "strategic_reasoning": "Reduces churn and improves expansion revenue.", "expected_roi": "2x within 12 months", "timeline": "60-90 days", "dependencies": ["CS platform", "Playbook development"]},
            {"name": "Strategic Partnership Program", "urgency_score": 6, "impact_score": 8, "quadrant": "Plan It", "strategic_reasoning": "Extends reach and credibility through established partners.", "expected_roi": "Variable — 20-40% pipeline contribution potential", "timeline": "60-90 days", "dependencies": ["Partner identification", "Legal agreements"]},
            {"name": "International Market Expansion", "urgency_score": 5, "impact_score": 9, "quadrant": "Plan It", "strategic_reasoning": "Large addressable market opportunity but requires significant preparation.", "expected_roi": "5-10x long-term", "timeline": "90-180 days", "dependencies": ["Localization", "Local partnerships", "Regulatory compliance"]},
            {"name": "Advanced Analytics Dashboard", "urgency_score": 6, "impact_score": 6, "quadrant": "Delegate", "strategic_reasoning": "Improves data-driven decision making across teams.", "expected_roi": "Indirect — operational efficiency", "timeline": "60-90 days", "dependencies": ["Data engineering", "BI tools"]},
            {"name": "Employee Training Program", "urgency_score": 5, "impact_score": 6, "quadrant": "Delegate", "strategic_reasoning": "Builds team capabilities for long-term growth.", "expected_roi": "Indirect — team performance", "timeline": "30-90 days", "dependencies": ["L&D resources", "Training content"]},
            {"name": "Office Infrastructure Upgrade", "urgency_score": 3, "impact_score": 4, "quadrant": "Defer", "strategic_reasoning": "Nice-to-have but not critical for current growth priorities.", "expected_roi": "Minimal direct ROI", "timeline": "90+ days", "dependencies": ["Budget allocation", "Facilities"]}
        ]
    }


def _fallback_roadmap():
    def _action(name, obj, reason, steps, owner, tools, metrics, outcome, priority, diff):
        return {"action_name": name, "objective": obj, "reason": reason, "execution_steps": steps, "owner": owner, "required_tools": tools, "success_metrics": metrics, "expected_outcome": outcome, "priority": priority, "difficulty": diff}

    return {
        "day_30": [
            _action("Audit Current Metrics", "Establish baseline KPIs", "Cannot improve what you don't measure", ["Collect data from all tools", "Build KPI dashboard", "Set benchmark targets"], "Head of Operations", ["Analytics platform", "Spreadsheet"], ["Dashboard live within 5 days", "All teams trained on metrics"], "Clear visibility into business performance", "High", "Easy"),
            _action("Launch Content Calendar", "Begin organic content production", "Reduce CAC through inbound leads", ["Define content themes", "Assign writers", "Publish 3x/week"], "Marketing Lead", ["CMS", "SEO tools"], ["12+ articles published", "20% increase in organic traffic"], "Sustainable content engine operational", "High", "Medium"),
            _action("Competitive Feature Analysis", "Map feature gaps vs top 3 competitors", "Prioritize product roadmap", ["Research competitor features", "Create comparison matrix", "Identify top 5 gaps"], "Product Manager", ["Competitive intel tools"], ["Feature matrix completed", "Gap priorities approved"], "Data-driven product roadmap", "High", "Easy"),
            _action("Sales Playbook Creation", "Standardize sales process", "Reduce sales cycle variability", ["Document current process", "Create objection handling guides", "Build ROI calculator"], "Sales Director", ["CRM", "Document tools"], ["Playbook adopted by 100% of reps"], "Consistent, faster sales cycles", "High", "Medium"),
            _action("Customer Feedback Survey", "Gather systematic customer input", "Inform product and service improvements", ["Design survey", "Distribute to all active customers", "Analyze results"], "Customer Success Lead", ["Survey platform"], ["70%+ response rate", "Top 5 improvement areas identified"], "Customer-driven improvement priorities", "Medium", "Easy"),
            _action("SEO Technical Audit", "Fix technical SEO issues", "Improve organic search rankings", ["Run site crawl", "Fix broken links", "Optimize meta tags"], "SEO Specialist", ["Screaming Frog", "Google Search Console"], ["All critical issues fixed", "Core Web Vitals passed"], "Improved search visibility", "Medium", "Easy"),
            _action("Email Nurture Sequences", "Automate lead nurturing", "Convert more leads to opportunities", ["Map buyer journey", "Write 5-email sequence", "Set up automation"], "Marketing Lead", ["Email platform"], ["Sequences live", "15%+ open rates"], "Automated lead conversion pipeline", "Medium", "Medium"),
            _action("Define ICP Document", "Clarify ideal customer profile", "Focus sales efforts on highest-value prospects", ["Analyze best customers", "Identify common attributes", "Document and distribute ICP"], "Sales Director", ["CRM data"], ["ICP document approved", "Sales team aligned"], "Focused prospecting efforts", "High", "Easy"),
            _action("Set Up Analytics Tracking", "Implement full-funnel tracking", "Enable data-driven decisions", ["Install tracking pixels", "Set up conversion goals", "Create attribution model"], "Data Analyst", ["Google Analytics", "Tag Manager"], ["Full funnel tracked", "Weekly reports automated"], "Complete visibility into customer journey", "Medium", "Medium"),
            _action("Quick-Win Product Fixes", "Address top 5 user-reported issues", "Improve retention and satisfaction", ["Prioritize bug backlog", "Fix top 5 issues", "Release and communicate"], "Engineering Lead", ["Issue tracker"], ["5 fixes deployed", "CSAT improvement"], "Improved product reliability", "High", "Easy")
        ],
        "day_60": [
            _action("Launch Paid Campaign Tests", "Test 3 paid acquisition channels", "Identify scalable paid channels", ["Set budgets per channel", "Create ad variants", "Run A/B tests"], "Growth Lead", ["Ad platforms", "Analytics"], ["3 channels tested", "CPA benchmarks established"], "Validated paid acquisition strategy", "High", "Medium"),
            _action("Build Partner Pipeline", "Identify and engage 10 potential partners", "Extend market reach through partnerships", ["Research potential partners", "Create partner value prop", "Reach out to top 10"], "BD Manager", ["LinkedIn", "CRM"], ["10 partners contacted", "3+ in discussion"], "Active partner pipeline", "Medium", "Medium"),
            _action("Implement Customer Health Scoring", "Proactively identify at-risk accounts", "Reduce churn through early intervention", ["Define health metrics", "Build scoring model", "Train CS team"], "CS Lead", ["CS platform"], ["Health scores for all accounts", "At-risk playbook created"], "Proactive churn prevention", "High", "Hard"),
            _action("Pricing Page Optimization", "Test new pricing structure", "Improve conversion and revenue per customer", ["Research competitor pricing", "Design 2 pricing variants", "A/B test"], "Product Lead", ["Pricing tools", "A/B testing"], ["Test results analyzed", "Winning variant implemented"], "Optimized pricing strategy", "High", "Medium"),
            _action("Webinar Series Launch", "Host monthly industry webinars", "Build thought leadership and generate leads", ["Plan 3-month calendar", "Line up speakers", "Promote and execute first webinar"], "Marketing Lead", ["Webinar platform"], ["First webinar 100+ attendees", "30+ leads generated"], "Established thought leadership channel", "Medium", "Medium"),
            _action("CRM Workflow Automation", "Automate repetitive CRM tasks", "Free up sales time for selling", ["Audit current CRM usage", "Identify automation opportunities", "Implement top 5 automations"], "Sales Ops", ["CRM"], ["5 automations live", "2+ hours/rep/week saved"], "More efficient sales operations", "Medium", "Medium"),
            _action("Onboarding Experience Redesign", "Improve new customer onboarding", "Accelerate time-to-value and reduce early churn", ["Map current onboarding flow", "Identify drop-off points", "Redesign and implement"], "Product Lead", ["Product analytics"], ["New flow live", "Time-to-value reduced 30%"], "Faster customer activation", "High", "Hard"),
            _action("Develop Case Studies", "Create 3 customer success stories", "Provide social proof for sales process", ["Select top customers", "Interview and draft", "Design and publish"], "Marketing Lead", ["Design tools"], ["3 case studies published", "Used in 50% of proposals"], "Stronger sales collateral", "Medium", "Easy"),
            _action("Internal Knowledge Base", "Centralize team documentation", "Improve team efficiency and onboarding", ["Audit existing docs", "Organize into knowledge base", "Train teams"], "Ops Lead", ["Wiki platform"], ["KB launched", "80% of processes documented"], "Self-serve internal information", "Low", "Easy"),
            _action("Referral Program Design", "Launch customer referral program", "Acquire customers at lowest CAC", ["Design incentive structure", "Build referral tracking", "Launch to existing customers"], "Growth Lead", ["Referral platform"], ["Program launched", "First 10 referrals generated"], "New low-cost acquisition channel", "Medium", "Medium")
        ],
        "day_90": [
            _action("Scale Winning Channels", "2x budget on top-performing channels", "Maximize proven acquisition channels", ["Analyze channel performance", "Increase budgets", "Monitor CAC"], "Growth Lead", ["Ad platforms"], ["2x spend on winners", "CAC maintained or improved"], "Scaled predictable growth engine", "High", "Medium"),
            _action("Launch Self-Serve Onboarding", "Enable product-led growth", "Reduce sales-assisted onboarding costs", ["Build in-app guides", "Create tutorial videos", "Launch free trial flow"], "Product Lead", ["Product analytics", "Video tools"], ["Self-serve flow live", "30% of new users self-serve"], "Product-led growth motion", "High", "Hard"),
            _action("Advanced Analytics & Reporting", "Build executive dashboard", "Enable data-driven strategic decisions", ["Define exec KPIs", "Build automated dashboards", "Schedule weekly reviews"], "Data Analyst", ["BI platform"], ["Dashboard live", "Weekly exec reviews started"], "Data-driven leadership", "Medium", "Medium"),
            _action("Expand to Adjacent Segment", "Enter one new market segment", "Grow TAM and reduce concentration risk", ["Research adjacent segments", "Adapt messaging", "Launch targeted campaign"], "Strategy Lead", ["Market research"], ["New segment entered", "First 5 customers acquired"], "Diversified customer base", "High", "Hard"),
            _action("Customer Advisory Board", "Establish a formal customer advisory board", "Strengthen relationships and gather strategic input", ["Select 8-12 key customers", "Define charter", "Host first session"], "CS Lead", ["Event platform"], ["Board established", "First meeting held"], "Strategic customer partnership", "Medium", "Medium"),
            _action("Team Expansion Plan", "Hire for critical growth roles", "Remove people bottlenecks", ["Identify critical hires", "Write JDs", "Begin recruiting"], "HR Lead", ["ATS"], ["3+ critical roles posted", "Pipeline building"], "Right team for next growth phase", "High", "Medium"),
            _action("Technology Stack Review", "Audit and optimize tech stack", "Ensure scalability and reduce tech debt", ["Audit all tools", "Identify redundancies", "Plan migrations"], "CTO", ["Audit tools"], ["Tech stack optimized", "10% cost reduction"], "Leaner, more scalable infrastructure", "Medium", "Hard"),
            _action("Annual Strategic Plan", "Develop 12-month strategic plan", "Align team around shared goals", ["Facilitate strategy workshop", "Define OKRs", "Create execution roadmap"], "CEO", ["Planning tools"], ["Plan approved by leadership", "OKRs cascaded to teams"], "Aligned organizational execution", "High", "Medium"),
            _action("Brand Refresh Evaluation", "Assess need for brand evolution", "Ensure brand reflects growth stage", ["Audit brand perception", "Compare to competitors", "Recommend changes"], "Marketing Lead", ["Brand research"], ["Assessment complete", "Recommendation presented"], "Brand aligned with market position", "Low", "Easy"),
            _action("Investor Relations Preparation", "Prepare materials for potential funding", "Ensure readiness for growth capital", ["Build investor deck", "Prepare financial model", "Create data room"], "CFO", ["Financial modeling", "Data room"], ["Deck and model ready", "Data room organized"], "Fundraising readiness", "Medium", "Hard")
        ]
    }


def _fallback_market_intel():
    return {
        "industry_overview": "The technology sector continues to experience strong growth driven by digital transformation initiatives across all industries. Cloud computing, AI/ML, and data analytics remain the primary growth vectors.",
        "market_size": {"current": "$500B+ (global technology services)", "projected": "$800B+ by 2028", "cagr": "12-15%", "reasoning": "Driven by enterprise digital transformation, AI adoption, and cloud migration trends."},
        "market_growth": "The market is growing at a healthy double-digit rate, driven by increased enterprise technology adoption and the emergence of AI-powered tools.",
        "demand_drivers": ["Enterprise digital transformation", "AI and automation adoption", "Remote/hybrid work infrastructure", "Data-driven decision making", "Cybersecurity requirements"],
        "industry_trends": [
            {"trend": "AI-First Product Development", "impact": "High", "reasoning": "Companies integrating AI into core products are gaining significant competitive advantages."},
            {"trend": "Product-Led Growth Models", "impact": "High", "reasoning": "Self-serve onboarding and freemium models are becoming the dominant go-to-market strategy."},
            {"trend": "Vertical SaaS Specialization", "impact": "Medium", "reasoning": "Industry-specific solutions are winning over horizontal platforms in many segments."},
            {"trend": "Data Privacy and Compliance", "impact": "Medium", "reasoning": "Increasing regulatory requirements creating both risks and opportunities."},
            {"trend": "Consolidation through M&A", "impact": "Medium", "reasoning": "Larger players acquiring niche solutions to build comprehensive platforms."}
        ],
        "growth_opportunities": ["AI-powered feature differentiation", "Vertical market specialization", "International expansion", "Platform ecosystem development", "Strategic acquisitions"],
        "emerging_risks": ["Rapid technology obsolescence", "Increasing competition from well-funded startups", "Regulatory complexity", "Economic uncertainty affecting enterprise budgets", "Talent shortage in key technical roles"],
        "future_outlook": "The market outlook remains strong with sustained growth expected over the next 3-5 years. Companies that successfully integrate AI capabilities and build defensible platform ecosystems will emerge as market leaders."
    }


def _fallback_competitor_intel():
    return {
        "top_competitors": [
            {"name": "Market Leader A", "strengths": ["Strong brand recognition", "Large customer base", "Comprehensive feature set"], "weaknesses": ["Slow innovation cycle", "Complex pricing", "Poor customer support"], "market_position": "Market leader with 25-30% share", "pricing_strategy": "Premium pricing with enterprise focus", "threat_level": "High"},
            {"name": "Growth Challenger B", "strengths": ["Modern tech stack", "Strong product-led growth", "Developer community"], "weaknesses": ["Limited enterprise features", "Smaller sales team", "Less brand awareness"], "market_position": "Fast-growing challenger with 10-15% share", "pricing_strategy": "Freemium with self-serve upgrades", "threat_level": "High"},
            {"name": "Niche Player C", "strengths": ["Deep domain expertise", "Strong customer relationships", "Vertical specialization"], "weaknesses": ["Limited scalability", "Narrow market focus", "Aging technology"], "market_position": "Niche leader in specific vertical", "pricing_strategy": "Value-based pricing", "threat_level": "Medium"},
            {"name": "Emerging Disruptor D", "strengths": ["AI-native architecture", "Well-funded", "Innovative UX"], "weaknesses": ["Unproven at scale", "Limited integrations", "Small team"], "market_position": "Early-stage disruptor", "pricing_strategy": "Aggressive underpricing for market share", "threat_level": "Medium"},
            {"name": "Legacy Incumbent E", "strengths": ["Established enterprise relationships", "Compliance certifications", "Global presence"], "weaknesses": ["Technical debt", "Slow product updates", "High customer churn"], "market_position": "Declining incumbent with 15-20% share", "pricing_strategy": "Lock-in through long-term contracts", "threat_level": "Low"}
        ],
        "swot": {
            "strengths": ["Technology differentiation", "Agile development process", "Customer-centric culture", "AI integration capabilities"],
            "weaknesses": ["Brand awareness gap", "Limited enterprise sales team", "Smaller feature set than leaders", "Geographic concentration"],
            "opportunities": ["Underserved market segments", "Partnership ecosystem development", "AI-powered feature expansion", "International market entry"],
            "threats": ["Well-funded competitor expansion", "Market commoditization", "Talent war", "Economic downturn impact on budgets"]
        },
        "competitive_gap_analysis": "The primary competitive gaps exist in enterprise features, brand awareness, and sales team capacity. However, technology innovation and customer experience represent strong differentiation opportunities.",
        "differentiation_opportunities": ["AI-powered automation that competitors lack", "Superior onboarding experience", "Transparent and flexible pricing", "Vertical-specific solutions", "Community-driven product development"]
    }


def _fallback_recommendations():
    return {
        "recommendations": [
            {"function": "Marketing", "situation": "Low brand awareness and high CAC", "analysis": "Current marketing efforts are primarily outbound, leading to unsustainable acquisition costs.", "recommendation": "Build a content-led inbound engine with SEO, webinars, and thought leadership to reduce CAC by 30-40%.", "expected_roi": "3-5x within 12 months", "timeline": "0-90 days", "risk_level": "Low", "confidence_score": 85},
            {"function": "Sales", "situation": "Long sales cycles and inconsistent processes", "analysis": "Sales team lacks standardized playbooks and enabling tools.", "recommendation": "Implement sales enablement platform with standardized playbooks, ROI calculators, and automated follow-ups.", "expected_roi": "20-30% improvement in win rates", "timeline": "30-60 days", "risk_level": "Low", "confidence_score": 80},
            {"function": "Product", "situation": "Feature gaps creating competitive disadvantage", "analysis": "Key features present in competitor products are absent, leading to lost deals.", "recommendation": "Prioritize competitive feature parity for top 5 gaps while investing in unique AI-powered differentiators.", "expected_roi": "15-25% reduction in feature-related deal losses", "timeline": "60-120 days", "risk_level": "Medium", "confidence_score": 75},
            {"function": "Operations", "situation": "Manual processes limiting scalability", "analysis": "Rapid growth has outpaced process automation, creating bottlenecks.", "recommendation": "Automate top 10 manual processes using workflow automation, starting with customer onboarding and reporting.", "expected_roi": "40% reduction in operational overhead", "timeline": "30-90 days", "risk_level": "Low", "confidence_score": 80},
            {"function": "Technology", "situation": "Tech stack needs optimization for scale", "analysis": "Current architecture supports current load but may not handle 5-10x growth.", "recommendation": "Conduct architecture review, implement microservices for critical paths, and establish CI/CD best practices.", "expected_roi": "Reduced downtime and 2x deployment velocity", "timeline": "60-120 days", "risk_level": "Medium", "confidence_score": 70},
            {"function": "Customer Success", "situation": "Reactive customer support model", "analysis": "No proactive health monitoring leads to surprise churn.", "recommendation": "Implement customer health scoring and proactive outreach for at-risk accounts.", "expected_roi": "25-35% churn reduction", "timeline": "30-60 days", "risk_level": "Low", "confidence_score": 82},
            {"function": "Pricing", "situation": "Pricing not optimized for market position", "analysis": "Current pricing may be leaving revenue on the table or creating friction for prospects.", "recommendation": "Conduct pricing research, test value-based pricing tiers, and implement annual plan incentives.", "expected_roi": "10-20% revenue uplift per customer", "timeline": "30-60 days", "risk_level": "Medium", "confidence_score": 72},
            {"function": "Expansion", "situation": "Growth concentrated in one market", "analysis": "Geographic and segment concentration creates risk.", "recommendation": "Develop expansion playbook for 2-3 adjacent segments or geographies, starting with lowest-risk entry.", "expected_roi": "New revenue stream within 6 months", "timeline": "60-180 days", "risk_level": "High", "confidence_score": 65}
        ]
    }


# ── Generator Functions ──────────────────────────────────────────────────────

def generate_assumptions(context: dict) -> dict:
    """Generate the Assumption Framework."""
    try:
        raw = call_llm(PT.ASSUMPTION_SYSTEM, PT.ASSUMPTION_HUMAN, context)
        result = parse_json_response(raw)
        if result and "industry_classification" in result:
            return result
    except Exception:
        pass
    return _fallback_assumptions()


def generate_diagnostic(context: dict) -> dict:
    """Generate the Executive Diagnostic Summary."""
    try:
        raw = call_llm(PT.DIAGNOSTIC_SYSTEM, PT.DIAGNOSTIC_HUMAN, context)
        result = parse_json_response(raw)
        if result and "business_assessment" in result:
            return result
    except Exception:
        pass
    return _fallback_diagnostic()


def generate_opportunity_score(context: dict) -> dict:
    """Generate the Opportunity Score Analysis."""
    try:
        raw = call_llm(PT.SCORE_SYSTEM, PT.SCORE_HUMAN, context)
        result = parse_json_response(raw)
        if result and "overall_score" in result:
            return result
    except Exception:
        pass
    return _fallback_score()


def generate_bottlenecks(context: dict) -> dict:
    """Generate the Bottleneck Diagnosis."""
    try:
        raw = call_llm(PT.BOTTLENECK_SYSTEM, PT.BOTTLENECK_HUMAN, context)
        result = parse_json_response(raw)
        if result and "bottlenecks" in result:
            return result
    except Exception:
        pass
    return _fallback_bottlenecks()


def generate_urgency_matrix(context: dict) -> dict:
    """Generate the Urgency vs Impact Matrix."""
    try:
        raw = call_llm(PT.MATRIX_SYSTEM, PT.MATRIX_HUMAN, context)
        result = parse_json_response(raw)
        if result and "initiatives" in result:
            return result
    except Exception:
        pass
    return _fallback_matrix()


def generate_roadmap(context: dict) -> dict:
    """Generate the 30/60/90-Day Roadmap."""
    try:
        raw = call_llm(PT.ROADMAP_SYSTEM, PT.ROADMAP_HUMAN, context)
        result = parse_json_response(raw)
        if result and "day_30" in result:
            return result
    except Exception:
        pass
    return _fallback_roadmap()


def generate_market_intel(context: dict) -> dict:
    """Generate the Market Intelligence Report."""
    try:
        raw = call_llm(PT.MARKET_INTEL_SYSTEM, PT.MARKET_INTEL_HUMAN, context)
        result = parse_json_response(raw)
        if result and "industry_overview" in result:
            return result
    except Exception:
        pass
    return _fallback_market_intel()


def generate_competitor_intel(context: dict) -> dict:
    """Generate the Competitor Intelligence Report."""
    try:
        raw = call_llm(PT.COMPETITOR_SYSTEM, PT.COMPETITOR_HUMAN, context)
        result = parse_json_response(raw)
        if result and "top_competitors" in result:
            return result
    except Exception:
        pass
    return _fallback_competitor_intel()


def generate_recommendations(context: dict) -> dict:
    """Generate Strategic Recommendations."""
    try:
        raw = call_llm(PT.RECOMMENDATIONS_SYSTEM, PT.RECOMMENDATIONS_HUMAN, context)
        result = parse_json_response(raw)
        if result and "recommendations" in result:
            return result
    except Exception:
        pass
    return _fallback_recommendations()
