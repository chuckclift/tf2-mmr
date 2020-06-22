#!/usr/bin/env python3

import jinja2

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"), autoescape=True
)
index_template = jinja_env.get_template("index.html")

with open("html/index.html", "w", encoding="utf-8") as f:
    f.write(index_template.render())
