# backend/types/ceab_attributes.py
class CEABAttributes:
    """Represents CEAB accreditation attribute breakdown for a course."""

    def __init__(self,
                 total_AU: float = 0.0,
                 mathematics: float = 0.0,
                 natural_science: float = 0.0,
                 math_and_science: float = 0.0,
                 engineering_science: float = 0.0,
                 engineering_design: float = 0.0,
                 eng_sci_and_design: float = 0.0,
                 complementary_studies: float = 0.0):
        self.total_AU = total_AU
        self.mathematics = mathematics
        self.natural_science = natural_science
        self.math_and_science = math_and_science
        self.engineering_science = engineering_science
        self.engineering_design = engineering_design
        self.eng_sci_and_design = eng_sci_and_design
        self.complementary_studies = complementary_studies

    def __repr__(self):
        return (f"CEABAttributes(TotalAU={self.total_AU}, Math={self.mathematics}, "
                f"NatSci={self.natural_science}, EngSci={self.engineering_science}, "
                f"EngDesign={self.engineering_design}, CompStudies={self.complementary_studies})")
