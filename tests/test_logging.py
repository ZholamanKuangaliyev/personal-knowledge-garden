import logging

from garden.core.logging import get_logger, setup_logging


class TestSetupLogging:
    def test_verbose_sets_debug(self):
        setup_logging(verbose=True)
        logger = logging.getLogger("garden")
        assert logger.level == logging.DEBUG

    def test_default_sets_warning(self):
        setup_logging(verbose=False)
        logger = logging.getLogger("garden")
        assert logger.level == logging.WARNING

    def test_no_duplicate_handlers(self):
        logger = logging.getLogger("garden")
        logger.handlers.clear()
        setup_logging()
        setup_logging()
        assert len(logger.handlers) == 1


class TestGetLogger:
    def test_returns_namespaced_logger(self):
        log = get_logger("router")
        assert log.name == "garden.router"

    def test_inherits_parent_level(self):
        setup_logging(verbose=True)
        log = get_logger("test_child")
        assert log.getEffectiveLevel() == logging.DEBUG
