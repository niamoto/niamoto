import unittest
from sqlalchemy.orm import scoped_session
from niamoto.common.database import Database
from niamoto.core.models import Base


class DatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = "tests/test_data/data/db/test.db"
        cls.database = Database(cls.db_path)
        cls.engine = cls.database.engine
        cls.session_factory = scoped_session(cls.database.session_factory)

        # Créer les tables dans la base de données de test
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        # Nettoyer la base de données après tous les tests
        Base.metadata.drop_all(cls.engine)
        cls.session_factory.remove()
        cls.database.close_db_session()

    def setUp(self):
        self.transaction = self.database.begin_transaction()
        self.session = self.session_factory()

    def tearDown(self):
        # Annuler la transaction après chaque test pour rétablir l'état initial de la base de données
        self.database.rollback_transaction()
        self.session.close()

    def commit(self):
        # Valider les modifications apportées à la base de données pendant un test
        self.session.commit()
        self.database.commit_transaction()

    def rollback(self):
        # Annuler les modifications apportées à la base de données pendant un test
        self.session.rollback()
        self.database.rollback_transaction()
