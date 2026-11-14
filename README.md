# my-cv

A small Python CV website built with Flask and Jinja2. Flask exposes a WSGI application so it can be served by a WSGI-compatible web server.

## Run locally

Install the project, then start Flask's development server:

```sh
python -m pip install .
PYTHONPATH=src python -m flask --app my_cv.main run
```

Open <http://127.0.0.1:5000/>. Each resume section renders on its own page, with shared navigation between `/profile`, `/experience`, `/projects`, `/skills`, `/education`, `/credentials`, and `/interests`. The home page redirects to `/profile`. Edit the Markdown files in `src/my_cv/templates/sections/` to update resume content, `src/my_cv/templates/index.html` to update the shared layout and navigation, and `src/my_cv/static/style.css` to customize its appearance. Markdown is converted to HTML when rendered; raw HTML in section files is escaped.

## ATS-friendly PDF download

Use **Download ATS-friendly PDF** (`/resume-ats.pdf`) for employer application
portals. This unsigned, text-based PDF uses a single column, standard headings,
plain bullet lists, and visible website, LinkedIn, and GitHub URLs. It includes
the professional summary, technical skills, experience, projects, education, and
certifications, without the personal statement, interests, watermark, generation
timestamp, or signature-details appendix. It does not require signing credentials;
WeasyPrint's native system dependencies are still required.

The website and both PDF exports share the same Markdown content. Keep job titles,
employers, dates, and accomplishments accurate. For a specific opening, prioritize
relevant skills and achievements using the job description's terminology only
where it reflects actual experience; do not invent qualifications or metrics.
Check the exported PDF's extracted text and the portal's parsed fields before
submitting. ATS behavior varies, so this format does not guarantee a ranking or
successful parsing by every employer's system.

## Signed PDF download

The **Download signed PDF** link (`/resume.pdf`) produces a PDF containing all sections, with a watermark on every page and a cryptographic PDF signature. It records the UTC generation time and ends with a separate signature-details page, linked from the first page. The signature page lists the signing certificate details and explains how to validate the signature with standard PDF tools. WeasyPrint requires its [native system dependencies](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

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

The matching public key is served as PEM at <https://www.vitaly-greck.us/.well-known/pki/pub> so recipients can compare it with the key embedded in the signing certificate.

To run the tests, install `python -m pip install -e '.[test]'` and run `python -m unittest discover -s tests`.

## WSGI deployment

The WSGI callable is `application` in `my_cv.main` (`my_cv.main:application` in servers that accept `module:callable` notation). Configure your server's Python import path to include the project's `src` directory. The hosting server is responsible for providing the WSGI server; it is not pinned as a project dependency.
