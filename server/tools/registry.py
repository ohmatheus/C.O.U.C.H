import inspect
from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import BaseModel


class ToolParams(BaseModel):
    pass


def _strip_titles(obj: Any) -> None:
    if isinstance(obj, dict):
        obj.pop("title", None)
        for v in obj.values():
            _strip_titles(v)


def _assert_params_match(cls: type) -> None:
    fields = set(cls.params_model.model_fields)
    if not fields:
        return
    sig = inspect.signature(cls.fn)
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if has_var_kw:
        return
    missing = fields - set(sig.parameters)
    assert not missing, f"{cls.__name__}.fn is missing parameters for Params fields: {missing}"


class ToolEntry:
    name: ClassVar[str]
    description: ClassVar[str]
    requires_vision: ClassVar[bool] = False
    params_model: ClassVar[type[ToolParams]] = ToolParams
    fn: ClassVar[Callable[..., str]]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "Params" in cls.__dict__:
            cls.params_model = cls.Params  # type: ignore[attr-defined]
        if "fn" in cls.__dict__:
            _assert_params_match(cls)

    @classmethod
    def to_anthropic_tool(cls) -> dict[str, Any]:
        schema = cls.params_model.model_json_schema()
        _strip_titles(schema)
        return {"name": cls.name, "description": cls.description, "input_schema": schema}


def build_dispatch(entries: list[type[ToolEntry]]) -> dict[str, Callable[..., str]]:
    return {cls.name: cls.fn for cls in entries}
