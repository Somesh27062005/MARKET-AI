"""
schemas.py
----------
Pydantic models defining the structured JSON schema for the full strategic report.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class AssumptionItem(BaseModel):
    assumption: str = ""
    confidence: int = Field(default=0, ge=0, le=100)
    supporting_evidence: List[str] = Field(default_factory=list)
    strategic_reasoning: str = ""
    business_implications: str = ""


class AssumptionFramework(BaseModel):
    industry_classification: AssumptionItem = Field(default_factory=AssumptionItem)
    business_model: AssumptionItem = Field(default_factory=AssumptionItem)
    customer_type: AssumptionItem = Field(default_factory=AssumptionItem)
    growth_stage: AssumptionItem = Field(default_factory=AssumptionItem)
    competitive_environment: AssumptionItem = Field(default_factory=AssumptionItem)


class DiagnosticSummary(BaseModel):
    business_assessment: str = ""
    market_position: str = ""
    competitive_readiness: str = ""
    growth_readiness: str = ""
    strategic_strengths: List[str] = Field(default_factory=list)
    strategic_weaknesses: List[str] = Field(default_factory=list)
    key_opportunities: List[str] = Field(default_factory=list)
    major_risks: List[str] = Field(default_factory=list)
    executive_commentary: str = ""


class ScoreCategory(BaseModel):
    score: int = Field(default=0, ge=0, le=100)
    reasoning: str = ""
    positive_indicators: List[str] = Field(default_factory=list)
    negative_indicators: List[str] = Field(default_factory=list)
    improvement_actions: List[str] = Field(default_factory=list)


class OpportunityScore(BaseModel):
    overall_score: int = Field(default=0, ge=0, le=100)
    overall_verdict: str = ""
    categories: Dict[str, ScoreCategory] = Field(default_factory=dict)
    top_5_improvement_actions: List[str] = Field(default_factory=list)


class Bottleneck(BaseModel):
    title: str = ""
    severity: str = "Medium"
    problem: str = ""
    root_cause: str = ""
    strategic_impact: str = ""
    revenue_impact: str = ""
    customer_impact: str = ""
    recommended_fix: str = ""
    expected_outcome: str = ""


class BottleneckReport(BaseModel):
    bottlenecks: List[Bottleneck] = Field(default_factory=list)


class Initiative(BaseModel):
    name: str = ""
    urgency_score: int = Field(default=0, ge=0, le=10)
    impact_score: int = Field(default=0, ge=0, le=10)
    quadrant: str = "Defer"
    strategic_reasoning: str = ""
    expected_roi: str = ""
    timeline: str = ""
    dependencies: List[str] = Field(default_factory=list)


class UrgencyImpactMatrix(BaseModel):
    initiatives: List[Initiative] = Field(default_factory=list)


class RoadmapAction(BaseModel):
    action_name: str = ""
    objective: str = ""
    reason: str = ""
    execution_steps: List[str] = Field(default_factory=list)
    owner: str = ""
    required_tools: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    expected_outcome: str = ""
    priority: str = "Medium"
    difficulty: str = "Medium"


class Roadmap(BaseModel):
    day_30: List[RoadmapAction] = Field(default_factory=list)
    day_60: List[RoadmapAction] = Field(default_factory=list)
    day_90: List[RoadmapAction] = Field(default_factory=list)


class MarketSize(BaseModel):
    current: str = ""
    projected: str = ""
    cagr: str = ""
    reasoning: str = ""


class IndustryTrend(BaseModel):
    trend: str = ""
    impact: str = "Medium"
    reasoning: str = ""


class MarketIntelligence(BaseModel):
    industry_overview: str = ""
    market_size: MarketSize = Field(default_factory=MarketSize)
    market_growth: str = ""
    demand_drivers: List[str] = Field(default_factory=list)
    industry_trends: List[IndustryTrend] = Field(default_factory=list)
    growth_opportunities: List[str] = Field(default_factory=list)
    emerging_risks: List[str] = Field(default_factory=list)
    future_outlook: str = ""


class Competitor(BaseModel):
    name: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    market_position: str = ""
    pricing_strategy: str = ""
    threat_level: str = "Medium"


class SWOT(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    threats: List[str] = Field(default_factory=list)


class CompetitorIntelligence(BaseModel):
    top_competitors: List[Competitor] = Field(default_factory=list)
    swot: SWOT = Field(default_factory=SWOT)
    competitive_gap_analysis: str = ""
    differentiation_opportunities: List[str] = Field(default_factory=list)


class StrategicRec(BaseModel):
    function: str = ""
    situation: str = ""
    analysis: str = ""
    recommendation: str = ""
    expected_roi: str = ""
    timeline: str = ""
    risk_level: str = "Medium"
    confidence_score: int = Field(default=0, ge=0, le=100)


class StrategicRecommendations(BaseModel):
    recommendations: List[StrategicRec] = Field(default_factory=list)


class FullReport(BaseModel):
    status: str = "success"
    generated_at: str = ""
    assumptions: AssumptionFramework = Field(default_factory=AssumptionFramework)
    diagnostic: DiagnosticSummary = Field(default_factory=DiagnosticSummary)
    opportunity_score: OpportunityScore = Field(default_factory=OpportunityScore)
    bottleneck_report: BottleneckReport = Field(default_factory=BottleneckReport)
    urgency_matrix: UrgencyImpactMatrix = Field(default_factory=UrgencyImpactMatrix)
    roadmap: Roadmap = Field(default_factory=Roadmap)
    market_intelligence: MarketIntelligence = Field(default_factory=MarketIntelligence)
    competitor_intelligence: CompetitorIntelligence = Field(default_factory=CompetitorIntelligence)
    strategic_recommendations: StrategicRecommendations = Field(default_factory=StrategicRecommendations)

    def to_dict(self):
        return self.model_dump()
