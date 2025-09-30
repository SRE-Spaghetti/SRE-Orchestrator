from pydantic import BaseModel, Field
from typing import List, Optional


class Relationship(BaseModel):
    depends_on: str


class Component(BaseModel):
    name: str
    type: str
    relationships: Optional[List[Relationship]] = Field(default_factory=list)


class KnowledgeGraph(BaseModel):
    components: List[Component]
