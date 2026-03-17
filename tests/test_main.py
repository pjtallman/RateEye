# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ensure the parent directory is in the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, format_num

client = TestClient(app)


def test_language_en():
    """Verify English strings are returned by default or explicitly."""
    response = client.get("/", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert response.status_code == 200
    assert "Yield Tracker" in response.text
    assert "File" in response.text
    # Verify the specific Edit menu items are present
    assert "Cut" in response.text
    assert "Copy" in response.text


def test_language_es():
    """Verify Spanish strings are returned when requested."""
    response = client.get("/", headers={"Accept-Language": "es-ES,es;q=0.9"})
    assert response.status_code == 200
    assert "Rastreador de Rendimiento" in response.text
    assert "Archivo" in response.text
    assert "Cortar" in response.text


def test_language_fallback():
    """Verify that an unknown language falls back to English."""
    response = client.get("/", headers={"Accept-Language": "fr-FR"})
    assert "Yield Tracker" in response.text


def test_numeric_localization():
    """Verify the Jinja2 filter swaps separators for Spanish."""
    val = 1234.56
    assert format_num(val, "en") == "1,234.56"
    assert format_num(val, "es") == "1.234,56"
