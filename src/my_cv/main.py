import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import yaml
from asn1crypto import keys, x509
from cryptography import x509 as crypto_x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from flask import Flask, Response, abort, redirect, render_template, send_file, url_for
from markdown_it import MarkdownIt
from markupsafe import Markup
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore
from weasyprint import CSS, HTML


SECTION_TITLES = {
    "profile": "Profile",
    "personal-statement": "Personal statement",
    "experience": "Experience",
    "projects": "Selected projects",
    "skills": "Technical skills",
    "education": "Education",
    "credentials": "Certifications",
    "interests": "Interests",
}

PROJECT_DETAILS = {
    "skydive-toledo-manifest": (
        "Skydive Toledo manifest system",
        "skydive-toledo-manifest.md",
    ),
    "skydive-toledo-winds-temperatures": (
        "Winds and temperatures aloft display for Skydive Toledo",
        "skydive-toledo-winds-temperatures.md",
    ),
}

SECTION_DIR = Path(__file__).parent / "templates" / "sections"
STYLE_PATH = Path(__file__).parent / "static" / "style.css"
MARKDOWN = MarkdownIt("commonmark", {"html": False})


def render_markdown(source: str) -> Markup:
    return Markup(MARKDOWN.render(source))


def render_section(section: str) -> Markup:
    source = (SECTION_DIR / f"{section}.md").read_text(encoding="utf-8")
    return render_markdown(source)


def load_certificate(config_path: str) -> crypto_x509.Certificate:
    try:
        with open(config_path, encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
        public_pem = config["certificate"]["public"].encode("utf-8")
        return crypto_x509.load_pem_x509_certificate(public_pem)
    except (OSError, yaml.YAMLError, KeyError, TypeError, AttributeError,
            ValueError, UnsupportedAlgorithm) as exc:
        raise ValueError("Invalid PDF signing configuration") from exc


def load_signer(config_path: str) -> tuple[signers.SimpleSigner, crypto_x509.Certificate]:
    try:
        cert = load_certificate(config_path)
        with open(config_path, encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
        private_pem = config["certificate"]["private"].encode("utf-8")
        key = serialization.load_pem_private_key(private_pem, password=None)
        public_key = cert.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        key_public = key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if public_key != key_public:
            raise ValueError("Certificate and private key do not match")
        cert_der = cert.public_bytes(serialization.Encoding.DER)
        key_der = key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        return (
            signers.SimpleSigner(
                signing_cert=x509.Certificate.load(cert_der),
                signing_key=keys.PrivateKeyInfo.load(key_der),
                cert_registry=SimpleCertificateStore(),
            ),
            cert,
        )
    except (OSError, yaml.YAMLError, KeyError, TypeError, AttributeError,
            ValueError, UnsupportedAlgorithm) as exc:
        raise ValueError("Invalid PDF signing configuration") from exc


def reject_pdf_url(url: str):
    raise ValueError("External resources are not allowed in PDF rendering")


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return redirect(url_for("section_page", section="profile"))

    @app.get("/.well-known/pki/pub")
    def public_key():
        config_path = os.environ.get("MY_CV_CONFIG", "config.yaml")
        try:
            cert = load_certificate(config_path)
        except ValueError:
            app.logger.error("PDF signing certificate is missing or invalid")
            abort(503, description="PDF signing is not configured.")
        public_key_pem = cert.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return Response(public_key_pem, mimetype="text/plain")

    @app.get("/<section>")
    def section_page(section: str):
        if section not in SECTION_TITLES:
            abort(404)
        return render_template(
            "index.html",
            active_section=section,
            section_title=SECTION_TITLES[section],
            section_content=render_section(section),
            sections=SECTION_TITLES,
        )

    @app.get("/projects/<project_id>")
    def project_page(project_id: str):
        project = PROJECT_DETAILS.get(project_id)
        if project is None:
            abort(404)
        title, filename = project
        source = (SECTION_DIR / filename).read_text(encoding="utf-8")
        return render_template(
            "index.html",
            active_section="projects",
            section_title=title,
            section_content=render_markdown(source),
            sections=SECTION_TITLES,
        )

    @app.get("/resume.pdf")
    def download_pdf():
        config_path = os.environ.get("MY_CV_CONFIG", "config.yaml")
        try:
            signer, cert = load_signer(config_path)
        except ValueError:
            app.logger.error("PDF signing configuration is missing or invalid")
            abort(503, description="PDF signing is not configured.")

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cert_details = {
            "subject": cert.subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "serial_number": format(cert.serial_number, "X"),
            "not_before": cert.not_valid_before_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "not_after": cert.not_valid_after_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "sha256_fingerprint": cert.fingerprint(hashes.SHA256()).hex(),
        }
        html = render_template(
            "resume_pdf.html",
            sections=[(section, render_section(section)) for section in SECTION_TITLES],
            generated_at=generated_at,
            cert_details=cert_details,
        )
        pdf = HTML(string=html, url_fetcher=reject_pdf_url).write_pdf(
            stylesheets=[CSS(string=STYLE_PATH.read_text(encoding="utf-8"))]
        )
        signed = signers.sign_pdf(
            IncrementalPdfFileWriter(BytesIO(pdf)),
            signers.PdfSignatureMetadata(field_name="ResumeSignature"),
            signer=signer,
        )
        signed.seek(0)
        response = send_file(
            signed, mimetype="application/pdf", as_attachment=True,
            download_name="vitaly-greck-resume.pdf",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


application = create_app()
