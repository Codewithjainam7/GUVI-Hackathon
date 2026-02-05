"""
Ensemble Risk Engine - Combines all detection layers
Produces final risk score with explainability
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from app.detectors.rule_based import RuleBasedDetector, RuleBasedResult, get_rule_based_detector
from app.orchestrator.model_router import ModelRouter, TaskType, get_model_router

logger = structlog.get_logger()


@dataclass
class RiskSignal:
    """A risk signal with source and weight"""
    source: str  # 'rule_based', 'gemini', 'ensemble'
    signal_type: str
    description: str
    weight: float
    confidence: float
    matched_text: Optional[str] = None


@dataclass
class EnsembleResult:
    """Result from ensemble detection"""
    scam_detected: bool
    risk_score: float
    confidence: float
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    scam_type: Optional[str] = None
    signals: List[RiskSignal] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    
    # Raw results for debugging
    rule_based_score: Optional[float] = None
    llm_score: Optional[float] = None
    
    def add_reason(self, reason: str):
        if reason not in self.reasons:
            self.reasons.append(reason)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'scam_detected': self.scam_detected,
            'risk_score': self.risk_score,
            'confidence': self.confidence,
            'risk_level': self.risk_level,
            'scam_type': self.scam_type,
            'signals': [
                {
                    'source': s.source,
                    'type': s.signal_type,
                    'description': s.description,
                    'weight': s.weight,
                    'confidence': s.confidence,
                    'matched_text': s.matched_text
                }
                for s in self.signals
            ],
            'reasons': self.reasons,
            'models_used': self.models_used,
            'processing_time_ms': self.processing_time_ms
        }


class EnsembleRiskEngine:
    """
    Combines rule-based and LLM-based detection for final risk assessment
    
    Weighting Strategy:
    - Rule-based: 40% (fast, reliable patterns)
    - LLM-based: 60% (context understanding, nuance)
    
    The final score is calibrated and explained
    """
    
    # Weight configuration
    RULE_BASED_WEIGHT = 0.4
    LLM_WEIGHT = 0.6
    
    # Thresholds
    SCAM_THRESHOLD = 0.7
    HIGH_RISK_THRESHOLD = 0.8
    CRITICAL_THRESHOLD = 0.9
    
    def __init__(self):
        self.rule_detector = get_rule_based_detector()
        self.model_router = get_model_router()
        
        logger.info(
            "Ensemble risk engine initialized",
            rule_weight=self.RULE_BASED_WEIGHT,
            llm_weight=self.LLM_WEIGHT
        )
    
    async def analyze(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True
    ) -> EnsembleResult:
        """
        Perform ensemble scam detection
        
        Args:
            message: The message to analyze
            context: Optional context information
            use_llm: Whether to use LLM classification (can skip for speed)
            
        Returns:
            EnsembleResult with final score and explanations
        """
        import time
        start_time = time.time()
        
        result = EnsembleResult(
            scam_detected=False,
            risk_score=0.0,
            confidence=0.0,
            risk_level='low'
        )
        
        # Layer 1: Rule-based detection
        rule_result = self._run_rule_based(message, context)
        result.rule_based_score = rule_result.score
        result.models_used.append('rule_based')
        
        # Add rule-based signals
        for signal in rule_result.signals:
            result.signals.append(RiskSignal(
                source='rule_based',
                signal_type=signal.signal_type,
                description=signal.description,
                weight=signal.weight,
                confidence=signal.confidence,
                matched_text=signal.matched_text
            ))
            result.add_reason(signal.description)
        
        # Layer 2: LLM-based classification (if enabled)
        llm_result = None
        if use_llm:
            try:
                llm_result = await self._run_llm_classification(message, context)
                result.llm_score = llm_result.get('confidence', 0.0) if llm_result.get('is_scam') else 0.0
                result.models_used.append('gemini')
                
                # Add LLM signals
                if llm_result.get('is_scam'):
                    result.signals.append(RiskSignal(
                        source='gemini',
                        signal_type='llm_classification',
                        description=f"LLM classified as {llm_result.get('scam_type', 'scam')}",
                        weight=0.8,
                        confidence=llm_result.get('confidence', 0.5)
                    ))
                    
                    # Add LLM reasons
                    for reason in llm_result.get('reasons', []):
                        result.add_reason(reason)
                    
                    # Set scam type
                    if llm_result.get('scam_type'):
                        result.scam_type = llm_result.get('scam_type')
                        
            except Exception as e:
                logger.error("LLM classification failed", error=str(e))
                # Fall back to rule-based only
                result.llm_score = None
        
        # Calculate ensemble score
        self._calculate_ensemble_score(result, rule_result, llm_result)
        
        # Determine risk level
        result.risk_level = self._determine_risk_level(result.risk_score)
        
        # Set scam detected flag
        result.scam_detected = result.risk_score >= self.SCAM_THRESHOLD
        
        # Calculate processing time
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Ensemble analysis complete",
            scam_detected=result.scam_detected,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            signal_count=len(result.signals),
            processing_time_ms=result.processing_time_ms
        )
        
        return result
    
    def _run_rule_based(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> RuleBasedResult:
        """Run rule-based detection"""
        return self.rule_detector.detect(message, context)
    
    async def _run_llm_classification(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run LLM-based classification"""
        return await self.model_router.route_task(
            TaskType.SCAM_CLASSIFICATION,
            message=message,
            context=context
        )
    
    def _calculate_ensemble_score(
        self,
        result: EnsembleResult,
        rule_result: RuleBasedResult,
        llm_result: Optional[Dict[str, Any]]
    ):
        """Calculate weighted ensemble score"""
        
        rule_score = rule_result.score
        
        if llm_result and result.llm_score is not None:
            # Full ensemble with both layers
            llm_score = result.llm_score
            
            # Weighted average
            raw_score = (
                rule_score * self.RULE_BASED_WEIGHT +
                llm_score * self.LLM_WEIGHT
            )
            
            # Agreement bonus: if both agree, increase confidence
            if (rule_score > 0.5 and llm_score > 0.5) or (rule_score < 0.3 and llm_score < 0.3):
                agreement_bonus = 0.1
            else:
                agreement_bonus = 0
            
            # Calculate confidence based on agreement
            score_diff = abs(rule_score - llm_score)
            confidence = max(0.0, 1.0 - (score_diff * 0.5))  # Clamp to 0, lower confidence if scores disagree
            
            result.risk_score = min(raw_score + agreement_bonus, 1.0)
            result.confidence = confidence
            
        else:
            # Rule-based only
            result.risk_score = rule_score
            result.confidence = 0.6  # Lower confidence without LLM
            
            result.add_reason("Analysis based on pattern matching only (LLM unavailable)")
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score >= self.CRITICAL_THRESHOLD:
            return 'critical'
        elif score >= self.HIGH_RISK_THRESHOLD:
            return 'high'
        elif score >= self.SCAM_THRESHOLD:
            return 'medium'
        else:
            return 'low'
    
    async def explain_detection(
        self,
        result: EnsembleResult,
        verbose: bool = False
    ) -> str:
        """
        Generate a human-readable explanation of the detection
        
        Args:
            result: The ensemble result to explain
            verbose: Whether to include detailed signal info
            
        Returns:
            Human-readable explanation string
        """
        lines = []
        
        # Header
        if result.scam_detected:
            lines.append(f"⚠️ SCAM DETECTED (Risk: {result.risk_level.upper()})")
        else:
            lines.append(f"✓ Message appears safe (Risk: {result.risk_level})")
        
        lines.append(f"Risk Score: {result.risk_score:.2f} (Confidence: {result.confidence:.2f})")
        lines.append("")
        
        # Scam type
        if result.scam_type:
            lines.append(f"Scam Type: {result.scam_type.replace('_', ' ').title()}")
            lines.append("")
        
        # Reasons
        if result.reasons:
            lines.append("Detection Reasons:")
            for i, reason in enumerate(result.reasons[:5], 1):
                lines.append(f"  {i}. {reason}")
            lines.append("")
        
        # Signals (if verbose)
        if verbose and result.signals:
            lines.append("Detection Signals:")
            for signal in result.signals:
                lines.append(f"  [{signal.source}] {signal.signal_type}: {signal.description}")
                if signal.matched_text:
                    lines.append(f"    Matched: '{signal.matched_text}'")
        
        # Models used
        lines.append(f"Models Used: {', '.join(result.models_used)}")
        lines.append(f"Processing Time: {result.processing_time_ms}ms")
        
        return "\n".join(lines)


# Singleton instance
_engine: Optional[EnsembleRiskEngine] = None


def get_ensemble_engine() -> EnsembleRiskEngine:
    """Get or create the ensemble engine singleton"""
    global _engine
    if _engine is None:
        _engine = EnsembleRiskEngine()
    return _engine
