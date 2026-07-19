"""Named entry point for the temporary Master Agent Gradio test UI."""

from .gradio_guardian import build_demo


if __name__ == "__main__":
    build_demo().launch()
