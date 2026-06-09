import qguider
import pytest
from pathlib import Path

def test_qguider_args():
    qgdr = qguider.QGuider(creds=".env")

    assert qgdr._creds == ".env"
    assert qgdr._outpath == Path("qguider_data")


@pytest.fixture
def query():
    return qguider.QGuider(creds=".env").query()

def test_qguider_semesters(query):
    query.semesters("Fall 2020", "Spring 2021")

    assert query._semesters == [
        qguider.models.Semester(season="Fall", year=2020),
        qguider.models.Semester(season="Spring", year=2021),
    ]

def test_qguider_schools(query):
    query.schools("FAS", "SEAS")

    assert query._schools == [qguider.models.School.FAS]

def test_qguider_subjects(query):
    query.subjects("COMPSCI", "MATH")

    assert query._subjects == ["COMPSCI", "MATH"]

def test_qguider_departments(query):
    query.departments("COMPSCI", "MATH")

    assert query._departments == ["COMPSCI", "MATH"]

def test_qguider_instructor_last_name(query):
    query.instructor_last_name("Smith")

    assert query._instructor_last_name == "Smith"

def test_qguider_search(query):
    query.search("machine learning")

    assert query._search_term == "machine learning"
