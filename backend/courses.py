# course.py
from CEAB_Attributes import CEABAttributes

class Course:
    """Represents a university course and its CEAB accreditation details."""

    def __init__(self,
                 course_code: str,
                 num_credits: int,
                 area: int = None,
                 ceab: CEABAttributes = None,
                 kernel_course: bool = False,
                 technical_elective: bool = False,
                 free_elective: bool = False):

        self.course_code = course_code
        self.num_credits = num_credits  # Required
        self.area = area                # Optional (1–6)
        self.ceab = ceab if ceab is not None else CEABAttributes()
        self.kernel_course = kernel_course
        self.technical_elective = technical_elective
        self.free_elective = free_elective

    def __repr__(self):
        return (f"Course(code='{self.course_code}', area={self.area}, "
                f"num_credits={self.num_credits}, kernel={self.kernel_course}, "
                f"tech_elec={self.technical_elective}, free_elec={self.free_elective}, "
                f"ceab={self.ceab})")
