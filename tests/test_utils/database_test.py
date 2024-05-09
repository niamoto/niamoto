import unittest
from sqlalchemy.orm import scoped_session
from niamoto.common.database import Database
from niamoto.core.models import Base


class DatabaseTest(unittest.TestCase):
    """
    The DatabaseTest class provides test cases for the Database class.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup method for the test cases. It is automatically called before each test case.
        """
        cls.db_path = "tests/test_data/data/db/test.db"
        cls.database = Database(cls.db_path)
        cls.engine = cls.database.engine
        cls.session_factory = scoped_session(cls.database.session_factory)

        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        """
        Teardown method for the test cases. It is automatically called after each test case.
        """
        Base.metadata.drop_all(cls.engine)
        cls.session_factory.remove()
        cls.database.close_db_session()

    def setUp(self):
        """
        Setup method for each test.
        """
        self.transaction = self.database.begin_transaction()
        self.session = self.session_factory()

    def tearDown(self):
        """
        Teardown method for each test.
        """
        # Roll back the transaction after each test to restore the initial state of the database
        self.database.rollback_transaction()
        self.session.close()

    def commit(self):
        """
        Commit the changes made to the database during a test.
        """
        self.session.commit()
        self.database.commit_transaction()

    def rollback(self):
        """
        Roll back the changes made to the database during a test.
        """
        self.session.rollback()
        self.database.rollback_transaction()
