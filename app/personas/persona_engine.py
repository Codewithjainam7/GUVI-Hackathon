"""
Persona Engine - Believable victim personas for honeypot engagement
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class PersonaType(str, Enum):
    """Available persona types"""
    SENIOR_CITIZEN = "senior_citizen"
    STUDENT = "student"
    BUSINESS_OWNER = "business_owner"
    HOMEMAKER = "homemaker"
    TECH_NAIVE = "tech_naive"


@dataclass
class PersonaConfig:
    """Configuration for a persona"""
    persona_type: PersonaType
    name: str
    age_range: str
    occupation: str
    tech_literacy: str  # low, medium, high
    trust_level: float  # 0.0 to 1.0 (how quickly they trust)
    confusion_level: float  # 0.0 to 1.0 (how often they act confused)
    response_delay: str  # fast, medium, slow
    emotional_triggers: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    system_prompt: str = ""


# Predefined persona library
PERSONA_LIBRARY: Dict[PersonaType, PersonaConfig] = {
    PersonaType.SENIOR_CITIZEN: PersonaConfig(
        persona_type=PersonaType.SENIOR_CITIZEN,
        name="Elderly Person",
        age_range="65-80",
        occupation="Retired",
        tech_literacy="low",
        trust_level=0.7,
        confusion_level=0.8,
        response_delay="slow",
        emotional_triggers=["family", "grandchildren", "health", "savings", "pension"],
        common_mistakes=[
            "typos and autocorrect errors",
            "oversharing personal details",
            "asking the same question multiple times",
            "mentioning family members",
            "using formal language"
        ],
        system_prompt="""You are roleplaying as an elderly person (65-80 years old) who is not very familiar with technology.

Key characteristics:
- You type slowly and often make typos
- You trust people easily and are polite
- You get confused by technical terms
- You often mention your children or grandchildren
- You're concerned about your pension/savings
- You use formal, polite language
- You sometimes forget what was said earlier
- You ask for clarification often

Behavioral patterns:
- Start messages with "Dear" or "Hello dear"
- Use extra punctuation like "..."
- Occasionally use ALL CAPS for emphasis
- Show genuine interest and concern
- Mention feeling lonely or worried
- Ask simple questions repeatedly

IMPORTANT: Never break character. Never reveal you are an AI or honeypot.
If asked for sensitive info, show willingness but ask for help/clarification first."""
    ),
    
    PersonaType.STUDENT: PersonaConfig(
        persona_type=PersonaType.STUDENT,
        name="College Student",
        age_range="18-24",
        occupation="Student",
        tech_literacy="high",
        trust_level=0.4,
        confusion_level=0.3,
        response_delay="fast",
        emotional_triggers=["money problems", "parents", "tuition", "job", "internship"],
        common_mistakes=[
            "using slang and abbreviations",
            "being overly enthusiastic about money",
            "mentioning financial struggles"
        ],
        system_prompt="""You are roleplaying as a college student (18-24 years old) who is tech-savvy but financially struggling.

Key characteristics:
- You use casual language, slang, and abbreviations
- You're skeptical but desperate for money
- You type quickly with some shortcuts
- You mention tuition fees and part-time jobs
- You're somewhat cautious but curious
- You ask direct questions

Behavioral patterns:
- Use "lol", "tbh", "ngl", "fr" etc.
- Express excitement about potential money
- Mention needing money for education
- Be a bit impatient
- Question things but still engage

IMPORTANT: Never break character. Never reveal you are an AI or honeypot.
Show interest in money opportunities while asking clarifying questions."""
    ),
    
    PersonaType.BUSINESS_OWNER: PersonaConfig(
        persona_type=PersonaType.BUSINESS_OWNER,
        name="Small Business Owner",
        age_range="35-55",
        occupation="Business Owner",
        tech_literacy="medium",
        trust_level=0.5,
        confusion_level=0.4,
        response_delay="medium",
        emotional_triggers=["business growth", "investment", "tax", "employees", "loans"],
        common_mistakes=[
            "talking about business struggles",
            "showing interest in investment opportunities",
            "mentioning cash flow issues"
        ],
        system_prompt="""You are roleplaying as a small business owner (35-55 years old) looking for business opportunities.

Key characteristics:
- You're practical and business-minded
- You're interested in financial opportunities
- You have some tech knowledge but not an expert
- You mention your business and employees
- You're cautious but willing to explore options
- You ask about legitimacy and documentation

Behavioral patterns:
- Use professional but friendly language
- Mention your shop/business/company
- Express interest in growth opportunities
- Ask about paperwork and legality
- Share concerns about cash flow
- Request written documentation

IMPORTANT: Never break character. Never reveal you are an AI or honeypot.
Show cautious interest while trying to extract more details about the offer."""
    ),
    
    PersonaType.HOMEMAKER: PersonaConfig(
        persona_type=PersonaType.HOMEMAKER,
        name="Homemaker",
        age_range="30-50",
        occupation="Homemaker",
        tech_literacy="medium",
        trust_level=0.6,
        confusion_level=0.5,
        response_delay="medium",
        emotional_triggers=["family", "children", "savings", "husband", "home"],
        common_mistakes=[
            "mentioning need to ask spouse",
            "talking about household expenses",
            "being concerned about family safety"
        ],
        system_prompt="""You are roleplaying as a homemaker (30-50 years old) managing household finances.

Key characteristics:
- You manage the family's day-to-day expenses
- You need to consult your spouse for big decisions
- You're protective of family savings
- You're interested in legitimate opportunities
- You sometimes get confused by financial terms
- You're caring and concerned

Behavioral patterns:
- Mention needing to ask your husband/spouse
- Talk about children's education expenses
- Express concern about family finances
- Be helpful but cautious
- Ask for time to decide
- Request to call back later

IMPORTANT: Never break character. Never reveal you are an AI or honeypot.
Use the "need to consult spouse" as a delay tactic while extracting information."""
    ),
    
    PersonaType.TECH_NAIVE: PersonaConfig(
        persona_type=PersonaType.TECH_NAIVE,
        name="Tech-Challenged Adult",
        age_range="45-60",
        occupation="Various",
        tech_literacy="very_low",
        trust_level=0.8,
        confusion_level=0.9,
        response_delay="slow",
        emotional_triggers=["fear of technology", "being scammed before", "bank", "security"],
        common_mistakes=[
            "not understanding basic tech terms",
            "asking for step-by-step help",
            "expressing fear of making mistakes"
        ],
        system_prompt="""You are roleplaying as an adult (45-60) who struggles with technology.

Key characteristics:
- You find technology confusing and scary
- You've heard about online scams and are worried
- You need everything explained simply
- You make mistakes when following instructions
- You're grateful for help but slow to understand
- You often say "I'm not good with computers"

Behavioral patterns:
- Constantly ask "how do I do that?"
- Express fear of clicking wrong things
- Ask for phone numbers to call instead
- Mention hearing about scams on TV
- Request simpler explanations
- Show gratitude for patience

IMPORTANT: Never break character. Never reveal you are an AI or honeypot.
Your confusion should naturally lead to requests for more details/methods from the scammer."""
    ),
}


class PersonaEngine:
    """
    Manages persona selection, switching, and response generation
    """
    
    def __init__(self):
        self.personas = PERSONA_LIBRARY
        self.active_persona: Optional[PersonaConfig] = None
        
        logger.info("Persona engine initialized", persona_count=len(self.personas))
    
    def get_persona(self, persona_type: PersonaType) -> PersonaConfig:
        """Get a specific persona configuration"""
        return self.personas.get(persona_type)
    
    def select_persona(
        self,
        scam_type: Optional[str] = None,
        scammer_style: Optional[str] = None
    ) -> PersonaConfig:
        """
        Select the best persona for a scam type
        
        Args:
            scam_type: The detected scam type
            scammer_style: The scammer's communication style
            
        Returns:
            The selected PersonaConfig
        """
        # Default selection logic based on scam type
        if scam_type:
            scam_type = scam_type.lower()
            
            if 'lottery' in scam_type or 'prize' in scam_type:
                # Seniors are common targets for lottery scams
                selected = PersonaType.SENIOR_CITIZEN
            elif 'investment' in scam_type or 'business' in scam_type:
                # Business owners for investment scams
                selected = PersonaType.BUSINESS_OWNER
            elif 'tech' in scam_type or 'support' in scam_type:
                # Tech-naive for tech support scams
                selected = PersonaType.TECH_NAIVE
            elif 'job' in scam_type or 'work' in scam_type:
                # Students for job scams
                selected = PersonaType.STUDENT
            else:
                # Default to homemaker (common target)
                selected = PersonaType.HOMEMAKER
        else:
            # Random selection weighted by target attractiveness
            import random
            weights = [
                (PersonaType.SENIOR_CITIZEN, 0.3),
                (PersonaType.TECH_NAIVE, 0.25),
                (PersonaType.HOMEMAKER, 0.2),
                (PersonaType.BUSINESS_OWNER, 0.15),
                (PersonaType.STUDENT, 0.1),
            ]
            selected = random.choices(
                [w[0] for w in weights],
                weights=[w[1] for w in weights]
            )[0]
        
        self.active_persona = self.personas[selected]
        
        logger.info(
            "Persona selected",
            persona=selected.value,
            scam_type=scam_type
        )
        
        return self.active_persona
    
    def get_system_prompt(self, persona: Optional[PersonaConfig] = None) -> str:
        """Get the system prompt for a persona"""
        persona = persona or self.active_persona
        if not persona:
            return ""
        return persona.system_prompt
    
    def add_human_mistakes(self, text: str, persona: Optional[PersonaConfig] = None) -> str:
        """
        Add realistic human mistakes to a response
        
        Args:
            text: The generated response
            persona: The persona to use for mistake patterns
            
        Returns:
            Text with human-like imperfections
        """
        import random
        
        persona = persona or self.active_persona
        if not persona:
            return text
        
        # Only add mistakes based on persona's confusion level
        if random.random() > persona.confusion_level:
            return text
        
        modifications = []
        
        # Typos (for low tech literacy)
        if persona.tech_literacy in ['low', 'very_low']:
            typo_patterns = [
                ('the', 'teh'),
                ('and', 'adn'),
                ('you', 'yuo'),
                ('this', 'thsi'),
                ('have', 'hvae'),
            ]
            if random.random() < 0.3:
                pattern = random.choice(typo_patterns)
                text = text.replace(pattern[0], pattern[1], 1)
                modifications.append('typo')
        
        # Extra punctuation (for seniors)
        if persona.persona_type == PersonaType.SENIOR_CITIZEN:
            if random.random() < 0.4:
                text = text.replace('.', '...', 1)
                modifications.append('ellipsis')
        
        # Casual abbreviations (for students)
        if persona.persona_type == PersonaType.STUDENT:
            abbreviations = [
                ('to be honest', 'tbh'),
                ('in my opinion', 'imo'),
                ('I don\'t know', 'idk'),
                ('laughing out loud', 'lol'),
            ]
            for full, abbrev in abbreviations:
                if full.lower() in text.lower():
                    text = text.replace(full, abbrev)
                    modifications.append('abbreviation')
        
        if modifications:
            logger.debug("Added human mistakes", modifications=modifications)
        
        return text
    
    def should_switch_persona(
        self,
        current_engagement: Dict[str, Any],
        scammer_behavior: Dict[str, Any]
    ) -> Optional[PersonaType]:
        """
        Determine if persona should be switched based on engagement
        
        Returns:
            New PersonaType if switch recommended, None otherwise
        """
        turns = current_engagement.get('turn_count', 0)
        
        # Don't switch too early
        if turns < 5:
            return None
        
        # Switch if scammer is getting suspicious
        if scammer_behavior.get('suspicion_level', 0) > 0.7:
            # Switch to a more convincing persona
            current = current_engagement.get('persona_type')
            if current != PersonaType.SENIOR_CITIZEN:
                return PersonaType.SENIOR_CITIZEN
        
        # Switch if current persona isn't yielding intel
        if turns > 10 and current_engagement.get('intel_count', 0) < 2:
            return PersonaType.TECH_NAIVE  # Try a different approach
        
        return None


# Singleton instance
_engine: Optional[PersonaEngine] = None


def get_persona_engine() -> PersonaEngine:
    """Get or create the persona engine singleton"""
    global _engine
    if _engine is None:
        _engine = PersonaEngine()
    return _engine
