from pydantic import BaseModel
from typing import Union

def to_dict(data: Union[dict, BaseModel], for_update: bool = False) -> dict:
    if isinstance(data, BaseModel):
        return data.model_dump(exclude_unset=for_update)
    return data

