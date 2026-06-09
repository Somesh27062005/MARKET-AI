import json
from datetime import datetime
from report_generator import (
    generate_assumptions, generate_diagnostic, generate_opportunity_score,
    generate_bottlenecks, generate_urgency_matrix, generate_roadmap,
    generate_market_intel, generate_competitor_intel, generate_recommendations
)


class AgentOrchestrator:
    """Coordinates the step-wise LLM calls for the full business strategy report.

    Workflow sequence:
    1. Generate Assumption Framework (infer unknowns)
    2. Generate Diagnostic Summary (using assumptions)
    3. Generate Opportunity Score
    4. Generate Bottlenecks
    5. Generate Urgency-Impact Matrix
    6. Generate 30/60/90 Roadmap
    7. Generate Market Intelligence
    8. Generate Competitor Intelligence
    9. Generate Strategic Recommendations
    """

    def generate_full_report(self, user_input: dict) -> dict:
        """Generate the complete structured JSON report.

        user_input should have keys like:
        - company (str)
        - industry (str, optional)
        - goals (str, optional)
        - challenges (str, optional)
        - audience (str, optional)
        - competitors (str, optional)
        """
        # Build context with sensible defaults
        context = {
            'company': user_input.get('company', 'Unknown Company'),
            'industry': user_input.get('industry', 'Technology'),
            'goals': user_input.get('goals', 'Growth and market expansion'),
            'challenges': user_input.get('challenges', 'Competition and scaling'),
            'audience': user_input.get('audience', 'B2B enterprises'),
            'competitors': user_input.get('competitors', 'To be identified'),
        }

        report = {'status': 'success', 'generated_at': datetime.utcnow().isoformat()}

        # Step 1: Assumptions
        assumptions = generate_assumptions(context)
        report['assumptions'] = assumptions

        # Enrich context with assumptions summary for subsequent steps
        assumptions_summary = json.dumps(assumptions, default=str)[:500]
        context['assumptions_summary'] = assumptions_summary

        # Steps 2-9: Generate all remaining sections
        report['diagnostic'] = generate_diagnostic(context)
        report['opportunity_score'] = generate_opportunity_score(context)
        report['bottleneck_report'] = generate_bottlenecks(context)
        report['urgency_matrix'] = generate_urgency_matrix(context)
        report['roadmap'] = generate_roadmap(context)
        report['market_intelligence'] = generate_market_intel(context)
        report['competitor_intelligence'] = generate_competitor_intel(context)
        report['strategic_recommendations'] = generate_recommendations(context)

        return report

    def generate_section(self, section_name: str, user_input: dict) -> dict:
        """Generate a single report section on demand."""
        context = {
            'company': user_input.get('company', 'Unknown Company'),
            'industry': user_input.get('industry', 'Technology'),
            'goals': user_input.get('goals', 'Growth and market expansion'),
            'challenges': user_input.get('challenges', 'Competition and scaling'),
            'audience': user_input.get('audience', 'B2B enterprises'),
            'competitors': user_input.get('competitors', 'To be identified'),
            'assumptions_summary': user_input.get('assumptions_summary', ''),
        }

        generators = {
            'assumptions': generate_assumptions,
            'diagnostic': generate_diagnostic,
            'opportunity_score': generate_opportunity_score,
            'bottlenecks': generate_bottlenecks,
            'urgency_matrix': generate_urgency_matrix,
            'roadmap': generate_roadmap,
            'market_intelligence': generate_market_intel,
            'competitor_intelligence': generate_competitor_intel,
            'recommendations': generate_recommendations,
        }

        gen_fn = generators.get(section_name)
        if not gen_fn:
            return {'error': f'Unknown section: {section_name}'}

        return gen_fn(context)
