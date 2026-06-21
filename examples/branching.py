import qguider
from qguider.semester import Semester

def avg_overall(qset):
    means = [
        q.course_feedback.overall.course_mean
        for q in qset
        if q.course_feedback and q.course_feedback.overall.course_mean is not None
    ]
    return sum(means) / len(means) if means else None

qgdr = qguider.QGuider(creds=".env")

base = qgdr.query().semesters(Semester.latest())

subjects = ["COMPSCI", "MATH", "AFRAMER"]

for subject in subjects:
    results = base.subjects(subject).download().parse()  
    print(f"{subject} avg overall: {avg_overall(results):.2f}")
