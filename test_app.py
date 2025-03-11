def test_app_import():
    """Test that the app module can be imported."""
    import app
    assert app is not None

def test_hello_world():
    """Test that the hello_world route returns the index.html template."""
    import app
    with app.app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'Hello, World!' in response.data 