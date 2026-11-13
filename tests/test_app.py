import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import yaml
from asn1crypto import x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pypdf import PdfReader
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

from my_cv.main import SECTION_TITLES, create_app


class ResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test signer")])
        now = datetime.now(timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, content_commitment=True,
                    key_encipherment=False, data_encipherment=False,
                    key_agreement=False, key_cert_sign=True, crl_sign=True,
                    encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )
        cls.public_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
        cls.public_key_pem = certificate.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        cls.private_pem = key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        cls.cert_asn1 = asn1_x509.Certificate.load(
            certificate.public_bytes(serialization.Encoding.DER)
        )

    def setUp(self):
        self.client = create_app().test_client()

    def test_sections_and_markdown_rendering(self):
        self.assertEqual(self.client.get("/").location, "/profile")
        for section in SECTION_TITLES:
            with self.subTest(section=section):
                response = self.client.get(f"/{section}")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'href="/resume.pdf"', response.data)
                self.assertIn(b"<h1>", response.data)
        projects = self.client.get("/projects")
        for technology_url in (
            b"https://ollama.com/",
            b"https://huggingface.co/",
            b"https://huggingface.co/docs/transformers/index",
            b"https://github.com/features/copilot",
            b"/projects/pi-registrar",
        ):
            self.assertIn(technology_url, projects.data)
        for project_id, title in (
            ("pi-registrar", b"pi_registrar"),
            ("skydive-toledo-manifest", b"Skydive Toledo manifest system"),
            (
                "skydive-toledo-winds-temperatures",
                b"Winds and temperatures aloft display for Skydive Toledo",
            ),
        ):
            with self.subTest(project_id=project_id):
                detail = self.client.get(f"/projects/{project_id}")
                self.assertEqual(detail.status_code, 200)
                self.assertIn(title, detail.data)
        registrar_detail = self.client.get("/projects/pi-registrar")
        for project_detail in (
            b"https://github.com/vintozver/pi_registrar/",
            b"certificate identities",
            b"SQLite",
            b"dnspython",
            b"systemd",
        ):
            self.assertIn(project_detail, registrar_detail.data)
        education = self.client.get("/education")
        self.assertIn(
            b'<a href="https://www.bsuir.by/en/academic-department-of-software-for-information-technologies">Faculty of Computer Systems and Networks</a>',
            education.data,
        )
        self.assertIn(b"<strong>Belarusian State University of Informatics and Radioelectronics</strong>", education.data)
        interests = self.client.get("/interests")
        self.assertIn(b'href="/home-improvement"', interests.data)
        self.assertNotIn(b"porcelain tile", interests.data)
        home_improvement = self.client.get("/home-improvement")
        self.assertEqual(home_improvement.status_code, 200)
        self.assertIn(b"porcelain tile", home_improvement.data)
        self.assertIn(b"I choose quality", home_improvement.data)
        self.assertIn(b"over quantity", home_improvement.data)
        for index in range(1, 4):
            thumbnail_url = f"/static/home-improvement-{index}-thumb.jpg".encode()
            original_url = f"/static/home-improvement-{index}.jpg".encode()
            self.assertIn(
                b'<a href="' + original_url + b'"><img src="' + thumbnail_url,
                home_improvement.data,
            )
            for image_url in (thumbnail_url, original_url):
                image_response = self.client.get(image_url.decode())
                try:
                    self.assertEqual(image_response.status_code, 200)
                    self.assertEqual(image_response.mimetype, "image/jpeg")
                finally:
                    image_response.close()
        manifest_detail = self.client.get("/projects/skydive-toledo-manifest")
        self.assertIn(b'<img src="https://manifest.skydivetoledo.com/"', manifest_detail.data)
        self.assertEqual(self.client.get("/projects/missing").status_code, 404)
        self.assertEqual(self.client.get("/missing").status_code, 404)

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "profile.md").write_text(
                "# Title\n\n**Bold**\n\n<script>alert(1)</script>", encoding="utf-8"
            )
            with patch("my_cv.main.SECTION_DIR", Path(directory)):
                response = self.client.get("/profile")
        self.assertIn(b"<strong>Bold</strong>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertNotIn(b"<script>", response.data)

    def test_download_is_signed_and_watermarked_on_every_page(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory, "config.yaml")
            config.write_text(yaml.safe_dump({"certificate": {
                "public": self.public_pem, "private": self.private_pem,
            }}), encoding="utf-8")
            with patch.dict(os.environ, {"MY_CV_CONFIG": str(config)}):
                key_response = self.client.get("/.well-known/pki/pub")
                response = self.client.get("/resume.pdf")

        self.assertEqual(key_response.status_code, 200)
        self.assertEqual(key_response.data, self.public_key_pem)
        self.assertEqual(key_response.mimetype, "text/plain")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        pdf = PdfReader(BytesIO(response.data))
        self.assertGreater(len(pdf.pages), 1)
        pages = [page.extract_text() for page in pdf.pages]
        for page in pages:
            self.assertIn("Vitaly Greck · Resume", page)
        self.assertIn("Generated:", pages[0])
        self.assertIn("Signature and certificate details", pages[0])
        self.assertIn("PDF signature and certificate details", pages[-1])
        self.assertIn("signer", pages[-1])
        self.assertIn("SHA-256 fingerprint", pages[-1])
        self.assertIn("https://www.vitaly-greck.us/.well-known/pki/pub", pages[-1])
        self.assertIn("pdfsig", pages[-1])
        self.assertNotIn("PDF signature and certificate details", pages[-2])
        text = "\n".join(pages)
        for heading in (
            "Engineering thoughtful, dependable software", "Professional experience",
            "Personal statement", "Projects", "Local AI experiments and online resume",
            "Skydive Toledo manifest system",
            "Winds and temperatures aloft display for Skydive Toledo",
            "Ollama", "Hugging Face", "multimodal models", "GitHub Copilot",
            "human review", "digitally signed", "Technical skills", "Education",
            "Certifications & awards", "Interests", "More commercial and independent projects",
        ):
            self.assertIn(heading, text)
        self.assertNotIn("Raspberry Pi 4 Model B", text)
        self.assertNotIn("two-step rollout", text)
        self.assertNotIn("porcelain tile", text)
        self.assertNotIn("I choose quality", text)
        project_links = [
            annotation.get_object()["/A"].get("/URI")
            for page in pdf.pages
            for annotation in page.get("/Annots", [])
            if annotation.get_object().get("/A", {}).get("/URI")
        ]
        self.assertIn("http://localhost/projects/skydive-toledo-manifest", project_links)
        self.assertIn("http://localhost/projects/skydive-toledo-winds-temperatures", project_links)

        reader = PdfFileReader(BytesIO(response.data))
        self.assertEqual(len(reader.embedded_signatures), 1)
        status = validate_pdf_signature(
            reader.embedded_signatures[0],
            signer_validation_context=ValidationContext(trust_roots=[self.cert_asn1]),
        )
        self.assertTrue(status.intact)
        self.assertTrue(status.valid)
        self.assertTrue(status.trusted)

    def test_missing_and_invalid_signing_configuration_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory, "config.yaml")
            with patch.dict(os.environ, {"MY_CV_CONFIG": str(config)}):
                self.assertEqual(self.client.get("/resume.pdf").status_code, 503)
                self.assertEqual(self.client.get("/.well-known/pki/pub").status_code, 503)
                config.write_text("certificate: []", encoding="utf-8")
                self.assertEqual(self.client.get("/resume.pdf").status_code, 503)
                other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                other_pem = other_key.private_bytes(
                    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                ).decode()
                config.write_text(yaml.safe_dump({"certificate": {
                    "public": self.public_pem, "private": other_pem,
                }}), encoding="utf-8")
                response = self.client.get("/resume.pdf")
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(other_pem.encode(), response.data)


if __name__ == "__main__":
    unittest.main()
