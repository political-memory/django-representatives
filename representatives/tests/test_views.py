from django import test

from responsediff.test import ResponseDiffTestMixin


from representatives.models import Representative
from representatives.views import RepresentativeViewMixin


class RepresentativeManagerTest(ResponseDiffTestMixin, test.TestCase):
    fixtures = ['representatives_test.json']

    def test_representatives_test(self):
        self.assertWebsiteSame('/api/')
