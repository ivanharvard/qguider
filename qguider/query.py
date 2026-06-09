import logging
from pathlib import Path
from types import NoneType

from .models import Semester, School
from .downloader import Downloader

logger = logging.getLogger(__name__)

class Query:
    def __init__(self, creds: str | Path, outpath: str | Path = Path("qguider_data")):
        self._outpath = outpath
        self._creds = creds

        self._schools = [School.FAS]
        self._semesters = []
        self._subjects = []
        self._departments = []
        self._classes = []
        self._instructor_last_name = None
        self._search_term = None

    def semesters(self, *args):
        sems = self._unpack(*args)
        self._semesters = [self._coerce(sem, Semester) for sem in sems]

        return self

    def schools(self, *_args):
        logging.warning("Only FAS is currently supported. Ignoring schools argument.")
        self._schools = [School.FAS]

        return self
    
    def subjects(self, *args):
        sbjcts = self._unpack(*args)
        self._subjects = [self._coerce(sbjct, str) for sbjct in sbjcts]

        return self
    
    def departments(self, *args):
        dprtmnts = self._unpack(*args)
        self._departments = [self._coerce(dprtmnt, str) for dprtmnt in dprtmnts]

        return self

    def instructor_last_name(self, instructor_last_name: str):
        self._instructor_last_name = instructor_last_name
        return self
    
    def search(self, search_term: str):
        """
        Search for courses or instructors. 
        """
        self._search_term = search_term
        return self
    
    def download(self) -> None:
        downloader = Downloader(self)
        return downloader.download()

    def run(self):
        return self.download().parse()

    def outpath(self, path: str | Path | NoneType):
        self._outpath = path
        return self

    def _unpack(self, *args):
        """
        Unpacks arguments, i.e., foo("a", "b", "c") and foo(["a", "b", "c"]).
        """
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            return args[0]
        return args
    
    def _coerce(self, value, target_type):
        try:
            if isinstance(value, target_type):
                return value

            from_string = getattr(target_type, "from_string", None)

            if from_string and isinstance(value, str):
                return from_string(value)

            return target_type(value)
        except Exception as e:
            raise ValueError(f"Could not coerce {value} to {target_type}") from e