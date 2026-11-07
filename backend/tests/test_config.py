from app.config import Settings


def test_database_url_normalized_for_sqlalchemy():
    assert Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+psycopg2://u:p@h/db"
    assert Settings(database_url="postgresql://u:p@h/db?sslmode=require").database_url == "postgresql+psycopg2://u:p@h/db?sslmode=require"
    assert Settings(database_url="postgresql+psycopg2://u:p@h/db").database_url == "postgresql+psycopg2://u:p@h/db"
    assert Settings(database_url="sqlite://").database_url == "sqlite://"
