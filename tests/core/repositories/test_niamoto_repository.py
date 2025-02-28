"""Test NiamotoRepository class."""

import pytest
from unittest import mock
from sqlalchemy import Column, Integer, String

from niamoto.core.repositories.niamoto_repository import NiamotoRepository
from niamoto.core.models import Base
from niamoto.common.exceptions import DatabaseError, ValidationError, DataTransformError


# Test Model
class MockTaxon(Base):
    """Mock taxon model for testing."""

    __tablename__ = "test_taxon"

    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    rank_name = Column(String)
    parent_id = Column(Integer)


@pytest.fixture
def mock_db():
    """Mock Database class."""
    with mock.patch("niamoto.core.repositories.niamoto_repository.Database") as mock_db:
        yield mock_db


@pytest.fixture
def mock_session():
    """Create a mock session."""
    session = mock.MagicMock()
    return session


@pytest.fixture
def repository(mock_db, mock_session):
    """Create a repository instance with mocked database."""
    mock_db.return_value.session = mock_session
    return NiamotoRepository("test.db")


def test_init_success(mock_db):
    """Test successful repository initialization."""
    repo = NiamotoRepository("test.db")
    assert repo.db == mock_db.return_value
    mock_db.assert_called_once_with("test.db")


def test_init_failure(mock_db):
    """Test repository initialization failure."""
    mock_db.side_effect = Exception("Database error")
    with pytest.raises(DatabaseError) as exc_info:
        NiamotoRepository("test.db")
    assert "Failed to initialize repository" in str(exc_info.value)


def test_get_entities_success(repository, mock_session):
    """Test successful entity retrieval."""
    # Setup mock
    expected_entities = [MockTaxon(id=1), MockTaxon(id=2)]
    mock_session.query.return_value.all.return_value = expected_entities

    # Execute
    entities = repository.get_entities(MockTaxon)

    # Verify
    assert entities == expected_entities
    mock_session.query.assert_called_once_with(MockTaxon)


def test_get_entities_with_order(repository, mock_session):
    """Test entity retrieval with ordering."""
    # Setup mock
    expected_entities = [MockTaxon(id=1), MockTaxon(id=2)]
    mock_query = mock_session.query.return_value
    mock_query.order_by.return_value.all.return_value = expected_entities

    # Execute
    order_by = MockTaxon.id
    entities = repository.get_entities(MockTaxon, order_by=order_by)

    # Verify
    assert entities == expected_entities
    mock_session.query.assert_called_once_with(MockTaxon)
    mock_query.order_by.assert_called_once_with(order_by)


def test_get_entities_invalid_class(repository):
    """Test entity retrieval with invalid entity class."""

    class InvalidClass:
        pass

    with pytest.raises(ValidationError) as exc_info:
        repository.get_entities(InvalidClass)
    assert "Invalid entity class" in str(exc_info.value)


def test_get_entities_database_error(repository, mock_session):
    """Test entity retrieval with database error."""
    mock_session.query.side_effect = Exception("Database error")

    with pytest.raises(DatabaseError) as exc_info:
        repository.get_entities(MockTaxon)
    assert "Failed to retrieve entities" in str(exc_info.value)


def test_build_taxonomy_tree_success():
    """Test successful taxonomy tree building."""
    # Create test data
    taxons = [
        MockTaxon(id=1, full_name="Family1", rank_name="Famille", parent_id=None),
        MockTaxon(id=2, full_name="Genus1", rank_name="Genus", parent_id=1),
        MockTaxon(id=3, full_name="Species1", rank_name="Species", parent_id=2),
    ]

    # Execute
    tree = NiamotoRepository.build_taxonomy_tree(taxons)

    # Verify
    assert len(tree) == 1  # One root node
    assert tree[0]["name"] == "Family1"
    assert len(tree[0]["children"]) == 1  # One genus
    assert tree[0]["children"][0]["name"] == "Genus1"
    assert len(tree[0]["children"][0]["children"]) == 1  # One species
    assert tree[0]["children"][0]["children"][0]["name"] == "Species1"


def test_build_taxonomy_tree_no_roots():
    """Test taxonomy tree building with no root nodes."""
    # Create test data with no root nodes (all have parents)
    taxons = [
        MockTaxon(id=1, full_name="Genus1", rank_name="Genus", parent_id=99),
        MockTaxon(id=2, full_name="Species1", rank_name="Species", parent_id=1),
    ]

    with pytest.raises(DataTransformError) as exc_info:
        NiamotoRepository.build_taxonomy_tree(taxons)
    assert "Failed to build taxonomy tree" in str(exc_info.value)


def test_build_taxonomy_tree_error():
    """Test taxonomy tree building with error."""
    with pytest.raises(DataTransformError) as exc_info:
        NiamotoRepository.build_taxonomy_tree(None)
    assert "Failed to build taxonomy tree" in str(exc_info.value)
    assert "Input taxons cannot be None" in str(exc_info.value.details["error"])


def test_close_session_success(repository, mock_db):
    """Test successful session closing."""
    repository.close_session()
    mock_db.return_value.close_db_session.assert_called_once()


def test_close_session_error(repository, mock_db):
    """Test session closing with error."""
    mock_db.return_value.close_db_session.side_effect = Exception("Session error")

    with pytest.raises(DatabaseError) as exc_info:
        repository.close_session()
    assert "Failed to close database session" in str(exc_info.value)


def test_context_manager(mock_db):
    """Test repository as context manager."""
    mock_session = mock.MagicMock()
    mock_db.return_value.session = mock_session

    with NiamotoRepository("test.db") as repo:
        assert repo.db == mock_db.return_value
        assert repo.session == mock_session

    # Verify session was closed
    mock_db.return_value.close_db_session.assert_called_once()
