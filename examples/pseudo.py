import qguider
from qguider import ALL

from pathlib import Path

# ex 1: download qguides for the specified years
qgdr = qguider.QGuider(creds=".env")

results = (
    qgdr.query()
        .semesters("Fall 2020", "Fall 2021", "Spring 2022") # or as a list
        .classes("COMPSCI 50", "COMPSCI 51") # or as a list
        .departments(ALL) # or as a list, redundant in this example
        .outdir(Path("data/"))
        .execute()
)

# ex 2: parse qguides in memory
results = results.parse()

# ex 3: dump parsed qguides to disk
results.json_dump(Path("data/parsed/"))

# ex 4: load parsed qguides from disk
results = qgdr.json_load(Path("data/parsed/"))

# ex 5: access results
for qguide in results:
    print(qguide.semester, qguide.course, qguide.instructor, qguide.reasons_for_taking.elective)

for qguide in results:
    for comment in qguide.comments:
        print(comment)

# ex 6: concatenate results
summary = (
    results
    .filter(lambda qguide: qguide.course == "COMPSCI 50")
    .aggregate({
        "comments":           qguider.agg.append(lambda q: q.comments),
        "reasons_for_taking": qguider.agg.sum(lambda q: q.reasons_for_taking.elective),
        "course_ratings":     qguider.agg.mean(lambda q: q.course_ratings.overall)
    })
)

