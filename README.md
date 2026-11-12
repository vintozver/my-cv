# my-cv

A small Python CV website built with Flask and Jinja2. Flask exposes a WSGI application so it can be served by a WSGI-compatible web server.

## Run locally

Install the project, then start Flask's development server:

```sh
python -m pip install .
PYTHONPATH=src python -m flask --app my_cv.main run
```

Open <http://127.0.0.1:5000/>. Each resume section renders on its own page, with shared navigation between `/profile`, `/experience`, `/projects`, `/skills`, `/education`, `/credentials`, and `/interests`. The home page redirects to `/profile`. Edit the Markdown files in `src/my_cv/templates/sections/` to update resume content, `src/my_cv/templates/index.html` to update the shared layout and navigation, and `src/my_cv/static/style.css` to customize its appearance. Markdown is converted to HTML when rendered; raw HTML in section files is escaped.

## Signed PDF download

The download link produces a PDF containing all sections, with a watermark on every page and a cryptographic PDF signature. WeasyPrint requires its [native system dependencies](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

Set `MY_CV_CONFIG` to the path of a protected YAML file outside the repository. Without this variable, the application reads `config.yaml` in its working directory. The checked-in `config.yaml` is an empty example and does not contain credentials. Supply PEM content as YAML block scalars:

```yaml
certificate:
  public: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
  private: |
    -----BEGIN PRIVATE KEY-----
    ...
    -----END PRIVATE KEY-----
```

`public` must be an X.509 certificate, not a standalone public key; `private` must be the matching, unencrypted private key. Restrict access to the configuration file (for example, `chmod 600`) and never commit real credentials. `config.local.yaml` and `*.pem` are ignored by Git, but other secret-bearing files must also be kept out of the repository. The download returns HTTP 503 rather than an unsigned PDF if the configuration is missing, invalid, or the keys do not match. Signature trust depends on the certificate and the PDF viewer's trust settings; a self-signed certificate is not automatically trusted.

To run the tests, install `python -m pip install -e '.[test]'` and run `python -m unittest discover -s tests`.

## WSGI deployment

The WSGI callable is `application` in `my_cv.main` (`my_cv.main:application` in servers that accept `module:callable` notation). Configure your server's Python import path to include the project's `src` directory. The hosting server is responsible for providing the WSGI server; it is not pinned as a project dependency.
