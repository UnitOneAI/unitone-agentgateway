"""Base generator class and registry for PII generators."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from faker import Faker


class GeneratorRegistry:
    """Registry for auto-discovering and managing generators."""

    def __init__(self):
        self._generators: dict[str, "BaseGenerator"] = {}
        self._type_to_generator: dict[str, "BaseGenerator"] = {}

    def register(self, generator: "BaseGenerator") -> None:
        """Register a generator instance."""
        self._generators[generator.category] = generator
        for pii_type in generator.supported_types:
            self._type_to_generator[pii_type] = generator

    def get_by_category(self, category: str) -> "BaseGenerator | None":
        """Get generator by category name."""
        return self._generators.get(category)

    def get_by_type(self, pii_type: str) -> "BaseGenerator | None":
        """Get generator that handles a specific PII type."""
        return self._type_to_generator.get(pii_type)

    def list_categories(self) -> list[str]:
        """List all registered categories."""
        return list(self._generators.keys())

    def list_types(self) -> dict[str, list[str]]:
        """List all types organized by category."""
        return {
            category: gen.supported_types
            for category, gen in self._generators.items()
        }

    def generate(self, pii_type: str) -> dict[str, Any]:
        """Generate data for a specific PII type."""
        generator = self.get_by_type(pii_type)
        if not generator:
            raise ValueError(f"Unknown PII type: {pii_type}")
        return generator.generate(pii_type)


# Global registry instance
generator_registry = GeneratorRegistry()


class BaseGenerator(ABC):
    """Abstract base class for PII generators."""

    category: ClassVar[str]
    supported_types: ClassVar[list[str]]

    def __init__(self, faker_instance: Faker | None = None):
        self.faker = faker_instance or Faker()

    def __init_subclass__(cls, **kwargs):
        """Auto-register subclasses."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "category") and hasattr(cls, "supported_types"):
            instance = cls()
            generator_registry.register(instance)

    @abstractmethod
    def generate(self, pii_type: str) -> dict[str, Any]:
        """Generate PII data of the specified type.

        Args:
            pii_type: The type of PII to generate.

        Returns:
            Dictionary containing the generated PII data.
        """
        pass

    def generate_bulk(self, pii_type: str, count: int) -> list[dict[str, Any]]:
        """Generate multiple PII records.

        Args:
            pii_type: The type of PII to generate.
            count: Number of records to generate.

        Returns:
            List of dictionaries containing generated PII data.
        """
        return [self.generate(pii_type) for _ in range(count)]
