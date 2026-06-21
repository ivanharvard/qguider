import qguider
import pytest
from datetime import date
from pathlib import Path
from qguider.semester import Semester, Season

def test_qguider_args():
    qgdr = qguider.QGuider(creds=".env")

    assert qgdr._creds == ".env"
    assert qgdr._outpath == Path("qguider_data")


@pytest.fixture
def query():
    return qguider.QGuider(creds=".env").query()

def test_qguider_semesters(query):
    cal = Semester.for_school().latest(as_of=date(2021, 3, 1))
    query.semesters(cal.range(back=1))

    assert query._semesters == [
        Semester(season=Season.spring, year=2021),
        Semester(season=Season.fall, year=2020),
    ]

def test_qguider_schools(query):
    query.schools("FAS", "GSE")

    assert query._schools == [qguider.models.School.FAS, qguider.models.School.GSE]

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
