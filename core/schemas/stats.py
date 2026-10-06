from pydantic import BaseModel


class Stats(BaseModel):
    transformer_calls: int
    transformer_version: str
