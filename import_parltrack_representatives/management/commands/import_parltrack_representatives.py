from __future__ import absolute_import

from django.core.management.base import BaseCommand
from import_parltrack_representatives.parltrack_importer import ParltrackImporter

class Command(BaseCommand):
    help = "Update the eurodeputies data by pulling it from parltrack"

    # @transaction.atomic
    def handle(self, *args, **options):
        importer = ParltrackImporter()
        importer.process()
