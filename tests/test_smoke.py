from app import create_app

def test_home_redirect():
    app = create_app()
    client = app.test_client()
    r = client.get("/")
    assert r.status_code in (301, 302)
