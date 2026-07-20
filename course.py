"""Shared course data model used by the scraper and market simulator."""

from dataclasses import asdict, dataclass


@dataclass
class Course:
    name: str
    department: str
    level: int
    capacity: int
    credits: float
    prerequisites: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Course":
        return cls(**data)

    def __repr__(self) -> str:
        prereq = f" | Prereqs: {self.prerequisites[:30]}..." if self.prerequisites else ""
        return (
            f"{self.name} (Dept: {self.department}, Level: {self.level}, "
            f"Cap: {self.capacity}, {self.credits}cr{prereq})"
        )
