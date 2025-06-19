import os
from setuptools import setup, find_packages

setup(
    name="videoist_flask",
    version="1.0.0",
    description="A Flask-based video processing application",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Flask==3.1.1",
        "Flask-Bootstrap==3.3.7.1",
        "Flask-Login==0.6.3",
        "Flask-Mail==0.10.0",
        "Flask-Migrate==4.1.0",
        "Flask-SQLAlchemy==3.1.1",
        "Flask-WTF==1.2.2",
        "Jinja2==3.1.6",
        "Werkzeug==3.1.3",
        "WTForms==3.2.1",
        "python-dotenv==1.1.0",
        "SQLAlchemy==2.0.41",
        "alembic==1.16.1",
        "email_validator==2.2.0",
        "requests==2.32.4",
        "openai==1.86.0",
        "opencv-python==4.11.0.86",
        "pydub==0.25.1",
        "edge-tts==7.0.2",
        "pysrt==1.1.2",
    ],
    entry_points={
        "console_scripts": [
            "videoist=app:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)