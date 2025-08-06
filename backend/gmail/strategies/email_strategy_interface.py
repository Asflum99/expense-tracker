from abc import ABC, abstractmethod

class EmailStrategy(ABC):

    @abstractmethod
    async def process_messages(self, after, before, refresh_token, sub, headers, db) -> list[dict]:
        pass