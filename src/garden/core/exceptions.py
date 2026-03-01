class GardenError(Exception):
    """Base exception for the garden."""


class IngestionError(GardenError):
    """Error during document ingestion."""


class UnsupportedFileType(IngestionError):
    """File type not supported."""


class OllamaConnectionError(GardenError):
    """Cannot connect to Ollama."""


class EmptyDocumentError(IngestionError):
    """Document has no content."""


class RetrievalError(GardenError):
    """Error during document retrieval."""


class ConceptExtractionError(GardenError):
    """Error extracting concepts."""


class CardGenerationError(GardenError):
    """Error generating flashcards."""
