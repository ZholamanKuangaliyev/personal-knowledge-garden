"""Tests for embedding model migration."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner


class TestMigrateEmbeddings:
    @patch("garden.ingestion.embedder.get_embeddings")
    @patch("garden.store.vector_store.get_vector_store")
    def test_no_migration_needed(self, mock_get_store, mock_get_emb):
        from garden.cli.migrate_embeddings import migrate_embeddings

        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_model": "nomic-embed-text"}
        mock_store = MagicMock()
        mock_store._collection = mock_collection
        mock_get_store.return_value = mock_store

        runner = CliRunner()
        result = runner.invoke(migrate_embeddings)
        assert result.exit_code == 0
        assert "No migration needed" in result.output

    @patch("garden.ingestion.embedder.get_embeddings")
    @patch("garden.store.vector_store.get_vector_store")
    def test_migrates_chunks(self, mock_get_store, mock_get_emb):
        from garden.cli.migrate_embeddings import migrate_embeddings

        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_model": "old-model"}
        mock_collection.get.return_value = {
            "ids": ["c1", "c2"],
            "documents": ["text1", "text2"],
            "metadatas": [{"source": "a.md"}, {"source": "b.md"}],
        }
        mock_store = MagicMock()
        mock_store._collection = mock_collection
        mock_get_store.return_value = mock_store

        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_get_emb.return_value = mock_embedder

        runner = CliRunner()
        result = runner.invoke(migrate_embeddings)
        assert result.exit_code == 0
        assert "Migration complete" in result.output
        mock_collection.delete.assert_called_once_with(ids=["c1", "c2"])
        mock_collection.add.assert_called_once()
        mock_collection.modify.assert_called()

    @patch("garden.ingestion.embedder.get_embeddings")
    @patch("garden.store.vector_store.get_vector_store")
    def test_empty_collection(self, mock_get_store, mock_get_emb):
        from garden.cli.migrate_embeddings import migrate_embeddings

        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_model": "old-model"}
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }
        mock_store = MagicMock()
        mock_store._collection = mock_collection
        mock_get_store.return_value = mock_store

        runner = CliRunner()
        result = runner.invoke(migrate_embeddings)
        assert result.exit_code == 0
        assert "No chunks to migrate" in result.output


class TestEmbeddingModelMismatch:
    @patch("garden.store.vector_store.get_vector_store")
    def test_detects_mismatch(self, mock_get_store):
        from garden.store.vector_store import check_embedding_model_mismatch

        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_model": "old-model"}
        mock_store = MagicMock()
        mock_store._collection = mock_collection
        mock_get_store.return_value = mock_store

        with patch("garden.store.vector_store.settings") as mock_settings:
            mock_settings.embedding_model = "new-model"
            warning = check_embedding_model_mismatch()
            assert warning is not None
            assert "mismatch" in warning

    @patch("garden.store.vector_store.get_vector_store")
    def test_no_mismatch(self, mock_get_store):
        from garden.store.vector_store import check_embedding_model_mismatch

        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_model": "nomic-embed-text"}
        mock_store = MagicMock()
        mock_store._collection = mock_collection
        mock_get_store.return_value = mock_store

        with patch("garden.store.vector_store.settings") as mock_settings:
            mock_settings.embedding_model = "nomic-embed-text"
            warning = check_embedding_model_mismatch()
            assert warning is None
