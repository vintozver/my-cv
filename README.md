# my-cv

A small Python CV website built with Flask and Jinja2. Flask exposes a WSGI application so it can be served by a WSGI-compatible web server.

## Run locally

Install the project, then start Flask's development server:

```sh
python -m pip install .
PYTHONPATH=src python -m flask --app my_cv.app run
```

Open <http://127.0.0.1:5000/>. Each resume section renders on its own page, with shared navigation between `/profile`, `/experience`, `/projects`, `/skills`, `/education`, `/credentials`, and `/interests`. The home page redirects to `/profile`. Edit the section templates in `src/my_cv/templates/sections/` to update resume content, `src/my_cv/templates/index.html` to update the shared layout and navigation, and `src/my_cv/static/style.css` to customize its appearance.

## WSGI deployment

The WSGI callable is `application` in `my_cv.app` (`my_cv.app:application` in servers that accept `module:callable` notation). Configure your server's Python import path to include the project's `src` directory. The hosting server is responsible for providing the WSGI server; it is not pinned as a project dependency.
