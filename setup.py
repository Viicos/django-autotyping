from pathlib import Path

from setuptools import setup

DEMO_TAG = """
<p align="center">
  <img src="./docs/assets/demo.svg">
</p>
"""


def dynamic_readme() -> str:
    readme = Path(__file__).parent / "README.md"
    content = readme.read_text()
    content = content.replace(DEMO_TAG, "").replace("> [!WARNING]", "").replace("> [!TIP]", "")
    return content


setup(
    long_description=dynamic_readme(),
    long_description_content_type="text/markdown",
)
