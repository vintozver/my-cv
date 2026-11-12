from flask import Flask, abort, redirect, render_template, url_for


SECTION_TITLES = {
    "profile": "Profile",
    "experience": "Experience",
    "projects": "Selected projects",
    "skills": "Technical skills",
    "education": "Education",
    "credentials": "Certifications",
    "interests": "Interests",
}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return redirect(url_for("section_page", section="profile"))

    @app.get("/<section>")
    def section_page(section: str):
        if section not in SECTION_TITLES:
            abort(404)
        return render_template(
            "index.html",
            active_section=section,
            section_title=SECTION_TITLES[section],
        )

    return app


application = create_app()
