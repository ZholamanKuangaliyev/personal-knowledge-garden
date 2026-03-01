from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_name: str, **kwargs: object) -> str:
    template = _env.get_template(template_name)
    return template.render(**kwargs)
