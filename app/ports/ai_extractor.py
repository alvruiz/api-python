from abc import ABC, abstractmethod

class AIExtractor(ABC):
    """" Abstract base class for AI extractor """
    @abstractmethod
    async def extract_intent(self, user_input: str) -> str:
        """Extract the intent from user input"""
        pass
