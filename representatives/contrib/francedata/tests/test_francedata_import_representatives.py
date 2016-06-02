import os

from representatives.tests.utils import ImportTestMixin

from django import test

from representatives.contrib.francedata import import_representatives


class FrancedataImportTest(ImportTestMixin, test.TestCase):
    dbdiff_expected = os.path.join(
        'representatives',
        'contrib',
        'francedata',
        'tests',
        'representatives_expected.json',
    )

    def dbdiff_test(self):
        fixture = os.path.join(
            os.path.dirname(__file__),
            'representatives_fixture.json'
        )

        with open(fixture, 'r') as f:
            import_representatives.main(f)
