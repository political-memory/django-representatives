# coding: utf-8

# This file is part of compotista.
#
# compotista is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version.
#
# compotista is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU General Affero Public
# License along with Foobar.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2013 Laurent Peuch <cortex@worlddomination.be>
# Copyright (C) 2015 Arnaud Fabre <af@laquadrature.net>

from __future__ import absolute_import

from django.core.management.base import BaseCommand
from import_parltrack_representatives.parltrack_importer import ParltrackImporter

from celery import shared_task

@shared_task
def do_import():
    importer = ParltrackImporter()
    importer.process()


class Command(BaseCommand):
    help = "Update the eurodeputies data by pulling it from parltrack"

    def add_arguments(self, parser):
        parser.add_argument('--celery', action='store_true', default=False)

    # @transaction.atomic
    def handle(self, *args, **options):
        if options['celery']:
            do_import.delay()
        else:
            do_import()
