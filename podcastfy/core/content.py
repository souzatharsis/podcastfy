from typing import Any
from pydantic import BaseModel


# we can do much better here, but for now, let's keep it simple

class Content(BaseModel):
    value: Any
    type: str