from abc import abstractmethod, ABC
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class StructuredBase(ABC):
    @abstractmethod
    def response(self, system: str, prompt: str, result_type: Type[T]) -> T:
        pass

class StructuredOpenAI(StructuredBase):
    """
        Class to interact with OpenAI
    """
    def __init__(self, client, model: str):
        self.client = client
        self.model  = model

    def response(self, system: str, prompt: str, result_type: Type[T]) -> T:
        roles_input = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        response = self.client.responses.parse(
            model=self.model,
            input=roles_input,
            text_format=result_type,
        )
        return response.output_parsed  # type: ignore