# django-autotyping

Automatically add type hints for Django powered applications.

[![Python versions](https://img.shields.io/pypi/pyversions/django-autotyping.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/django-autotyping.svg)](https://pypi.org/project/django-autotyping/)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> [!WARNING]\
> Still WIP

<p align="center">
  <img alt="https://carbon.now.sh/?bg=rgba%2874%2C144%2C226%2C1%29&t=material&wt=none&l=auto&width=617&ds=false&dsyoff=20px&dsblur=68px&wc=true&wa=false&pv=56px&ph=56px&ln=false&fl=1&fm=Fira+Code&fs=14px&lh=152%25&si=false&es=2x&wm=false&code=from%2520django.db%2520import%2520models%250Afrom%2520django.db.models%2520import%2520ForeignKey%252C%2520OneToOneField%250A%250A%2523%2520apps%252Freporters%252Fmodels.py%253A%250A%250Aclass%2520Reporter%28models.Model%29%253A%250A%2520%2520%2520%2520address%2520%253D%2520OneToOneField%28%250A%2520%2520%2520%2520%2520%2520%2520%2520%2522OfficeRoom%2522%252C%250A%2520%2520%2520%2520%2520%2520%2520%2520on_delete%253Dmodels.CASCADE%252C%250A%2520%2520%2520%2520%29%250A%250A%250Aclass%2520OfficeRoom%28models.Model%29%253A%250A%2520%2520%2520%2520identifier%2520%253D%2520models.CharField%28max_length%253D3%29%250A%250A%250A%2523%2520apps%252Farticles%252Fmodels.py%253A%250A%250Aclass%2520Article%28models.Model%29%253A%250A%2520%2520%2520%2520reporter%2520%253D%2520ForeignKey%28%250A%2520%2520%2520%2520%2520%2520%2520%2520%2522reporters.Reporter%2522%252C%250A%2520%2520%2520%2520%2520%2520%2520%2520on_delete%253Dmodels.CASCADE%252C%250A%2520%2520%2520%2520%29" src="./assets/before.png" title="Before" width="44%">
&nbsp; &nbsp; &nbsp; &nbsp;
  <img alt="https://carbon.now.sh/?bg=rgba%2874%2C144%2C226%2C1%29&t=material&wt=none&l=auto&width=755.75&ds=false&dsyoff=20px&dsblur=68px&wc=true&wa=false&pv=56px&ph=56px&ln=false&fl=1&fm=Fira+Code&fs=14px&lh=152%25&si=false&es=2x&wm=false&code=from%2520django.db%2520import%2520models%250Afrom%2520django.db.models%2520import%2520ForeignKey%252C%2520OneToOneField%250A%250A%2523%2520apps%252Freporters%252Fmodels.py%253A%250Aif%2520TYPE_CHECKING%253A%250A%2520%2520%2520%2520from%2520apps.articles.models%2520import%2520Article%250A%250Aclass%2520Reporter%28models.Model%29%253A%250A%2520%2520%2520%2520address%253A%2520%2522OneToOneField%255BOfficeRoom%255D%2522%2520%253D%2520OneToOneField%28%250A%2520%2520%2520%2520%2520%2520%2520%2520%2522OfficeRoom%2522%252C%250A%2520%2520%2520%2520%2520%2520%2520%2520on_delete%253Dmodels.CASCADE%252C%250A%2520%2520%2520%2520%29%250A%2520%2520%2520%2520%250A%2520%2520%2520%2520article_set%253A%2520%2522models.Manager%255BArticle%255D%2522%250A%250A%250Aclass%2520OfficeRoom%28models.Model%29%253A%250A%2520%2520%2520%2520identifier%2520%253D%2520models.CharField%28max_length%253D3%29%250A%250A%2523%2520apps%252Farticles%252Fmodels.py%253A%250A%250Aif%2520TYPE_CHECKING%253A%250A%2520%2520%2520%2520from%2520apps.reporters.models%2520import%2520Reporter%250A%250Aclass%2520Article%28models.Model%29%253A%250A%2520%2520%2520%2520reporter%253A%2520%2522ForeignKey%255BReporter%255D%2522%2520%253D%2520ForeignKey%28%250A%2520%2520%2520%2520%2520%2520%2520%2520%2522reporters.Reporter%2522%252C%250A%2520%2520%2520%2520%2520%2520%2520%2520on_delete%253Dmodels.CASCADE%252C%250A%2520%2520%2520%2520%29" src="./assets/after.png" title="After" width="45%">
</p>

`django-autotyping` is built with [LibCST](https://github.com/Instagram/LibCST/).
