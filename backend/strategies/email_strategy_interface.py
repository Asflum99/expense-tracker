from abc import ABC, abstractmethod

class EmailStrategy(ABC):

    @abstractmethod
    def process_messages(self, after, before, refresh_token, sub, headers):
        pass