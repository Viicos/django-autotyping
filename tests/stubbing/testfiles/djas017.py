from django.template.loader import get_template, render_to_string, select_template

get_template("customtemplate.html")
get_template("nested/template.html")
get_template("firstapptemplate.html")

get_template("customtemplate.html", using="django_dir")
get_template("nested/template.html", using="django_dir")
get_template("firstapptemplate.html", using="django_app_dirs")

get_template("customtemplate.html", using="django_app_dirs")  # type: ignore
get_template("nested/template.html", using="django_app_dirs")  # type: ignore
get_template("firstapptemplate.html", using="django_dir")  # type: ignore

select_template(["customtemplate.html", "nested/template.html", "firstapptemplate.html"])
select_template(["firstapptemplate.html"], using="django_app_dirs")
select_template(["customtemplate.html", "nested/template.html"], using="django_dir")

select_template(["customtemplate.html"], using="django_app_dis")  # type: ignore
select_template(["firstapptemplate.html"], using="django_dir")  # type: ignore

render_to_string("customtemplate.html")
render_to_string("nested/template.html")
render_to_string("firstapptemplate.html")

render_to_string("customtemplate.html", using="django_dir")
render_to_string("nested/template.html", using="django_dir")
render_to_string("firstapptemplate.html", using="django_app_dirs")

render_to_string("customtemplate.html", using="django_app_dirs")  # type: ignore
render_to_string("nested/template.html", using="django_app_dirs")  # type: ignore
render_to_string("firstapptemplate.html", using="django_dir")  # type: ignore
