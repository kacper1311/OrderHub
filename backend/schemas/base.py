from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from sqlmodel import SQLModel


class CamelModel(SQLModel):
    # W Pythonie pola snake_case (initial_stock), w JSON camelCase (initialStock).
    # validate_by_name pozwala w kodzie tworzyć obiekt po nazwie pythonowej.
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )
