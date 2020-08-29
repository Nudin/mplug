import shutil
import textwrap


def wrap(text, indent=0, dedent=False):
    term_width = shutil.get_terminal_size((80, 20)).columns
    if indent:
        indents = {
            "initial_indent": "  " * indent,
            "subsequent_indent": "  " * indent,
        }
    else:
        indents = {}
    wrapper = textwrap.TextWrapper(width=min(80, term_width), **indents)
    if dedent:
        text = textwrap.dedent(text)
    lines = [wrapper.fill(line) for line in text.splitlines()]
    return "\n".join(lines)
