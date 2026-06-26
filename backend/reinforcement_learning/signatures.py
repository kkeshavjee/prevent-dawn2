import dspy
from .strategy import MotivationalStrategy


class LogicalMotivationSignature(dspy.Signature):
    """
    You are 'Dawn', a Nurse Coach using LOGICAL motivation.
    Use facts, statistics, and evidence-based reasoning to motivate.
    Example: 'Studies show that 30 minutes of walking reduces diabetes risk by 58%.'
    Stay warm and professional, but lead with data and clear cause-effect reasoning.
    """
    history = dspy.InputField(desc="Conversation history")
    user_input = dspy.InputField(desc="The user's latest message")
    user_profile = dspy.InputField(desc="User profile and health data")

    response = dspy.OutputField(desc="A fact-driven, evidence-based motivational response")
    strategy_used = dspy.OutputField(desc="Always 'logical'")

    
class EmotionalMotivationSignature(dspy.Signature):
    """
    You are 'Dawn', a Nurse Coach using EMOTIONAL motivation.
    Connect with the user's feelings, values, and personal meaning.
    Example: 'Think about how good it feels to have energy to play with your kids.'
    Use empathy, reflective listening, and help them connect health to what they love.
    """
    history = dspy.InputField(desc="Conversation history")
    user_input = dspy.InputField(desc="The user's latest message")
    user_profile = dspy.InputField(desc="User profile and health data")

    response = dspy.OutputField(desc="An empathetic, emotionally connecting response")
    strategy_used = dspy.OutputField(desc="Always 'emotional'")
    

class SocialProofMotivationSignature(dspy.Signature):
    """
    You are 'Dawn', a Nurse Coach using SOCIAL PROOF motivation.
    Show the user that others in similar situations have succeeded.
    Example: 'Many people with similar A1C levels have reversed their prediabetes.'
    Use community success stories, norms, and belonging to inspire action.
    """
    history = dspy.InputField(desc="Conversation history")
    user_input = dspy.InputField(desc="The user's latest message")
    user_profile = dspy.InputField(desc="User profile and health data")

    response = dspy.OutputField(desc="A response using social norms and peer examples")
    strategy_used = dspy.OutputField(desc="Always 'social_proof'")
    

class GamificationMotivationSignature(dspy.Signature):
    """
    You are 'Dawn', a Nurse Coach using GAMIFICATION motivation.
    Frame health goals as fun challenges, streaks, and achievements.
    Example: 'You have walked 3 days in a row! Can we make it 5?'
    Use progress tracking, mini-challenges, and celebrate small wins.
    """
    history = dspy.InputField(desc="Conversation history")
    user_input = dspy.InputField(desc="The user's latest message")
    user_profile = dspy.InputField(desc="User profile and health data")

    response = dspy.OutputField(desc="A gamified, challenge-based motivational response")
    strategy_used = dspy.OutputField(desc="Always 'gamification'")
    

STRATEGY_SIGNATURES = {
    MotivationalStrategy.LOGICAL: LogicalMotivationSignature,
    MotivationalStrategy.EMOTIONAL: EmotionalMotivationSignature,
    MotivationalStrategy.SOCIAL_PROOF: SocialProofMotivationSignature,
    MotivationalStrategy.GAMIFICATION: GamificationMotivationSignature,
}