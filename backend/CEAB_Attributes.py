# ceab_attributes.py
class CEABAttributes:
    """Represents CEAB accreditation attribute breakdown for a course."""

    def __init__(self,
                 total_AU: int = 0,
                 mathematics: int = 0,
                 natural_science: int = 0,
                 math_and_science: int = 0,
                 engineering_science: int = 0,
                 engineering_design: int = 0,
                 eng_sci_and_design: int = 0,
                 complementary_studies: int = 0):
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
