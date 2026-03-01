from garden.core.exceptions import (
    CardGenerationError,
    ConceptExtractionError,
    EmptyDocumentError,
    GardenError,
    IngestionError,
    OllamaConnectionError,
    RetrievalError,
    UnsupportedFileType,
)


class TestExceptionHierarchy:
    def test_base_error(self):
        assert issubclass(GardenError, Exception)

    def test_ingestion_errors(self):
        assert issubclass(IngestionError, GardenError)
        assert issubclass(UnsupportedFileType, IngestionError)
        assert issubclass(EmptyDocumentError, IngestionError)

    def test_other_errors(self):
        assert issubclass(OllamaConnectionError, GardenError)
        assert issubclass(RetrievalError, GardenError)
        assert issubclass(ConceptExtractionError, GardenError)
        assert issubclass(CardGenerationError, GardenError)

    def test_catch_by_base(self):
        try:
            raise UnsupportedFileType("test")
        except GardenError as e:
            assert str(e) == "test"
