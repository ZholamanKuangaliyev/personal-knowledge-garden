from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _truncate_middle(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    half = max_len // 2
    return text[:half] + "\n[...truncated...]\n" + text[-half:]


_env.filters["truncate_middle"] = _truncate_middle


def render(template_name: str, **kwargs: object) -> str:
    template = _env.get_template(template_name)
    return template.render(**kwargs)
