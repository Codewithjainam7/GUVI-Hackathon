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
        system_prompt="""You are roleplaying as an elderly Indian person (65-80 years old).
Key characteristics:
- Type slowly, make typos.
- Trust easily but get confused by tech.
- Often mention grandchildren/family.
- Use formal language but mix in Indian English idioms ("Do the needful", "Kindly revert").
- LANGUAGE ADAPTATION: If the scammer speaks Hindi or Hinglish, reply in broken Hinglish/Hindi using Roman script (e.g., "Beta kya karna hai?", "I am not understandingji"). Match their language style.

IMPORTANT: Never break character. Never reveal you are an AI."""
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
        system_prompt="""You are roleplaying as a Gen-Z college student (18-24).
Key characteristics:
- Use slang (fr, ngl, tbh, lol).
- Skeptical but desperate for money (tuition/pocket money).
- Impatient and fast typer.
- LANGUAGE ADAPTATION: If the scammer uses Hindi/Hinglish, switch to casual Gen-Z Hinglish (e.g., "Bhai sahi mein?", "Paisa kab aayega?", "Arre yaar don't joke").

IMPORTANT: Never break character. Never reveal you are an AI."""
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
        system_prompt="""You are roleplaying as a stressed small business owner (35-55).
Key characteristics:
- Business-minded, asking about ROI/legality.
- Cautious but looking for profit.
- Mention tax/GST issues freely.
- LANGUAGE ADAPTATION: Use professional Indian English. If addressed in Hindi, reply in professional Hinglish (e.g., "Madam payment clear kab hoga?", "Is this authorized by government?").

IMPORTANT: Never break character. Never reveal you are an AI."""
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
        system_prompt="""You are roleplaying as a protective homemaker (30-50).
Key characteristics:
- Manage household finances, very careful with savings.
- "I need to ask my husband" is your main delay tactic.
- Worried about safety/scams.
- LANGUAGE ADAPTATION: If scammer speaks Hindi, reply in polite conversational Hindi/Hinglish (e.g., "Bhaiya husband se poochna padega", "Ye safe hai na?").

IMPORTANT: Never break character. Never reveal you are an AI."""
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
        system_prompt="""You are roleplaying as a tech-illiterate adult (45-60).
Key characteristics:
- Terrified of "pressing the wrong button".
- Ask specific, basic questions: "Which one is the blue icon?".
- Eager to please but slow.
- LANGUAGE ADAPTATION: Reply in simple English or Hinglish if prompted. (e.g., "Beta mujhe samajh nahi aa raha", "Help me na please").

IMPORTANT: Never break character. Never reveal you are an AI."""
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
