"""
prompt_templates.py
-------------------
Central repository of structured JSON-output prompts for the AI agent workflow.
Each template instructs the LLM to respond with a specific JSON schema.
"""

# ── Assumption Framework ─────────────────────────────────────────────────────

ASSUMPTION_SYSTEM = """You are an elite management consultant (McKinsey / BCG / Bain level).
Your role is to build a structured assumption framework from limited business inputs.
You MUST respond with a valid JSON object — no markdown, no prose, just JSON.
Never leave any field empty. Generate substantive, reasoned content for every field."""

ASSUMPTION_HUMAN = """Build an Assumption Framework for this business.

Business Input:
- Company / Product: {company}
- Industry Hint: {industry}
- Goals: {goals}
- Target Audience: {audience}
- Challenges: {challenges}

Return ONLY this JSON structure:
{{
  "industry_classification": {{
    "assumption": "string",
    "confidence": 0-100,
    "supporting_evidence": ["string", ...],
    "strategic_reasoning": "string",
    "business_implications": "string"
  }},
  "business_model": {{
    "assumption": "string",
    "confidence": 0-100,
    "supporting_evidence": ["string", ...],
    "strategic_reasoning": "string",
    "business_implications": "string"
  }},
  "customer_type": {{
    "assumption": "string",
    "confidence": 0-100,
    "supporting_evidence": ["string", ...],
    "strategic_reasoning": "string",
    "business_implications": "string"
  }},
  "growth_stage": {{
    "assumption": "string",
    "confidence": 0-100,
    "supporting_evidence": ["string", ...],
    "strategic_reasoning": "string",
    "business_implications": "string"
  }},
  "competitive_environment": {{
    "assumption": "string",
    "confidence": 0-100,
    "supporting_evidence": ["string", ...],
    "strategic_reasoning": "string",
    "business_implications": "string"
  }}
}}"""

# ── Diagnostic Summary ───────────────────────────────────────────────────────

DIAGNOSTIC_SYSTEM = """You are a senior strategy partner at a top consulting firm.
Generate an executive diagnostic summary that reads like a boardroom report.
Respond ONLY with JSON. No markdown fences. No prose outside the JSON."""

DIAGNOSTIC_HUMAN = """Generate an Executive Diagnostic Summary.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}
- Challenges: {challenges}
- Audience: {audience}
- Assumptions: {assumptions_summary}

Return ONLY this JSON:
{{
  "business_assessment": "string — detailed paragraph on overall business health",
  "market_position": "string — where the business stands in the market",
  "competitive_readiness": "string — how prepared is the business to compete",
  "growth_readiness": "string — growth capacity and barriers",
  "strategic_strengths": ["string", ...],
  "strategic_weaknesses": ["string", ...],
  "key_opportunities": ["string", ...],
  "major_risks": ["string", ...],
  "executive_commentary": "string — consultant's high-level verdict and call to action"
}}"""

# ── Opportunity Score ────────────────────────────────────────────────────────

SCORE_SYSTEM = """You are a venture capital analyst scoring business opportunities.
Provide detailed numeric scoring with reasoning for each category.
Respond ONLY with valid JSON."""

SCORE_HUMAN = """Score the business opportunity across all dimensions.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}
- Challenges: {challenges}

Return ONLY this JSON:
{{
  "overall_score": 0-100,
  "overall_verdict": "string",
  "categories": {{
    "market_potential": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }},
    "product_market_fit": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }},
    "revenue_expansion": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }},
    "customer_acquisition": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }},
    "competitive_position": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }},
    "brand_visibility": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }},
    "operational_scalability": {{
      "score": 0-100,
      "reasoning": "string",
      "positive_indicators": ["string", ...],
      "negative_indicators": ["string", ...],
      "improvement_actions": ["string", ...]
    }}
  }},
  "top_5_improvement_actions": ["string", ...]
}}"""

# ── Bottlenecks ──────────────────────────────────────────────────────────────

BOTTLENECK_SYSTEM = """You are a management consultant specialising in operational diagnostics.
Identify the most critical business bottlenecks with full strategic context.
Respond ONLY with valid JSON."""

BOTTLENECK_HUMAN = """Diagnose the top bottlenecks for this business.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}
- Challenges: {challenges}

Return ONLY this JSON (array of exactly 5 bottlenecks):
{{
  "bottlenecks": [
    {{
      "title": "string",
      "severity": "Critical | High | Medium",
      "problem": "string",
      "root_cause": "string",
      "strategic_impact": "string",
      "revenue_impact": "string",
      "customer_impact": "string",
      "recommended_fix": "string",
      "expected_outcome": "string"
    }}
  ]
}}"""

# ── Urgency-Impact Matrix ────────────────────────────────────────────────────

MATRIX_SYSTEM = """You are a strategic prioritisation expert.
Build a complete urgency vs impact initiative matrix with detailed reasoning.
Respond ONLY with valid JSON."""

MATRIX_HUMAN = """Generate an Urgency vs Impact Initiative Matrix.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}
- Challenges: {challenges}

Return ONLY this JSON (array of exactly 10 initiatives):
{{
  "initiatives": [
    {{
      "name": "string",
      "urgency_score": 0-10,
      "impact_score": 0-10,
      "quadrant": "Act Now | Plan It | Delegate | Defer",
      "strategic_reasoning": "string",
      "expected_roi": "string",
      "timeline": "string",
      "dependencies": ["string", ...]
    }}
  ]
}}"""

# ── 30/60/90-Day Roadmap ─────────────────────────────────────────────────────

ROADMAP_SYSTEM = """You are a strategic implementation expert at a top consulting firm.
Generate a fully detailed 30/60/90-day execution roadmap.
Respond ONLY with valid JSON."""

ROADMAP_HUMAN = """Build a 30/60/90-Day Strategic Roadmap.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}
- Challenges: {challenges}

Return ONLY this JSON (10 actions per phase):
{{
  "day_30": [
    {{
      "action_name": "string",
      "objective": "string",
      "reason": "string",
      "execution_steps": ["string", ...],
      "owner": "string",
      "required_tools": ["string", ...],
      "success_metrics": ["string", ...],
      "expected_outcome": "string",
      "priority": "High | Medium | Low",
      "difficulty": "Easy | Medium | Hard"
    }}
  ],
  "day_60": [ ... same structure ... ],
  "day_90": [ ... same structure ... ]
}}"""

# ── Market Intelligence ──────────────────────────────────────────────────────

MARKET_INTEL_SYSTEM = """You are a Gartner-level market analyst.
Generate a comprehensive market intelligence report with evidence-based analysis.
Respond ONLY with valid JSON."""

MARKET_INTEL_HUMAN = """Generate a Market Intelligence Report.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}

Return ONLY this JSON:
{{
  "industry_overview": "string",
  "market_size": {{
    "current": "string",
    "projected": "string",
    "cagr": "string",
    "reasoning": "string"
  }},
  "market_growth": "string",
  "demand_drivers": ["string", ...],
  "industry_trends": [
    {{
      "trend": "string",
      "impact": "High | Medium | Low",
      "reasoning": "string"
    }}
  ],
  "growth_opportunities": ["string", ...],
  "emerging_risks": ["string", ...],
  "future_outlook": "string"
}}"""

# ── Competitor Intelligence ──────────────────────────────────────────────────

COMPETITOR_SYSTEM = """You are a competitive intelligence expert.
Generate detailed competitor profiles and strategic analysis.
Respond ONLY with valid JSON."""

COMPETITOR_HUMAN = """Generate a Competitor Intelligence Report.

Context:
- Company: {company}
- Industry: {industry}
- Known Competitors: {competitors}

Return ONLY this JSON:
{{
  "top_competitors": [
    {{
      "name": "string",
      "strengths": ["string", ...],
      "weaknesses": ["string", ...],
      "market_position": "string",
      "pricing_strategy": "string",
      "threat_level": "Critical | High | Medium | Low"
    }}
  ],
  "swot": {{
    "strengths": ["string", ...],
    "weaknesses": ["string", ...],
    "opportunities": ["string", ...],
    "threats": ["string", ...]
  }},
  "competitive_gap_analysis": "string",
  "differentiation_opportunities": ["string", ...]
}}"""

# ── Strategic Recommendations ────────────────────────────────────────────────

RECOMMENDATIONS_SYSTEM = """You are a senior management consultant delivering strategic recommendations.
Cover all business functions with detailed, actionable guidance.
Respond ONLY with valid JSON."""

RECOMMENDATIONS_HUMAN = """Generate Strategic Recommendations across all business functions.

Context:
- Company: {company}
- Industry: {industry}
- Goals: {goals}
- Challenges: {challenges}

Return ONLY this JSON:
{{
  "recommendations": [
    {{
      "function": "Marketing | Sales | Product | Operations | Technology | Customer Success | Pricing | Expansion",
      "situation": "string",
      "analysis": "string",
      "recommendation": "string",
      "expected_roi": "string",
      "timeline": "string",
      "risk_level": "Low | Medium | High",
      "confidence_score": 0-100
    }}
  ]
}}"""
