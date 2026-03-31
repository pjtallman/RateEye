import pytest
# Note: Testing browser-based TS classes in pytest is usually done with Playwright or similar.
# Since I'm in a CLI, I'll verify the backend logic for bulk creation instead.

def test_bulk_create_endpoint(client, test_admin, db):
    from database import init_db, Security
    init_db(db)
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    # Test bulk create with multiple symbols
    # Note: this will hit the live active endpoint (Yahoo Scraper)
    symbols = ["AAPL", "MSFT"]
    resp = client.post("/admin/securities/bulk_create", json={"symbols": symbols})
    assert resp.status_code == 200
    data = resp.json()
    assert "AAPL" in data["added"]
    assert "MSFT" in data["added"]
    
    # Verify they exist in DB
    secs = db.query(Security).filter(Security.symbol.in_(symbols)).all()
    assert len(secs) == 2

def test_bulk_create_duplicates(client, test_admin, db):
    from database import init_db, Security
    init_db(db)
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    # Add one first
    client.post("/admin/securities/bulk_create", json={"symbols": ["VOO"]})
    
    # Try bulk with duplicate
    resp = client.post("/admin/securities/bulk_create", json={"symbols": ["VOO", "GOOG"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "VOO already exists" in data["errors"][0]
    assert "GOOG" in data["added"]
