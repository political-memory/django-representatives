# coding: utf-8

import gc
import fileinput
import json
import time
import os
import logging
import hashlib
from tempfile import gettempdir
from urllib import urlopen, urlretrieve

import django.dispatch
from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from django.db import transaction
from django.utils import timezone

import ijson
from datetime import datetime

from representatives.models import (Representative, Group,
                                    Constituency, Mandate,
                                    Address, Country, Phone,
                                    Email, WebSite)

_parse_date = lambda date: datetime.strptime(date, "%Y-%m-%dT00:%H:00").date()

logger = logging.getLogger(__name__)

class GenericImporter(object):
    """
    """
    def pre_import(self):
        self.import_start_datetime = timezone.now()

    def post_import(self):
        # Clean not touched models
        models = [Representative, Group, Constituency,
                  Mandate, Address, Phone, Email, WebSite]
        for model in models:
            model.objects.filter(updated__lt=self.import_start_datetime).delete()

    def touch_model(self, model, **data):
        '''
        This method create or look up a model with the given data
        it saves the given model if it exists, updating its
        updated field
        '''
        instance, created = model.objects.get_or_create(**data)

        if not created:
            if instance.updated < self.import_start_datetime:
                instance.save()     # Updates updated field

        return (instance, created)

    def do_import(self):
        '''
        This is the main import method, it should be overrided by
        custom importers
        '''
        pass

    def process(self):
        self.pre_import()
        self.do_import()
        self.post_import()


class FileImporter(GenericImporter):
    """
    """
    def pre_import(self):
        self.download_file()
        super(FileImporter, self).pre_import()

    def pre_download(self, destination):
        pass

    def post_download(self, destination, downloaded):
        pass

    def download_file(self):
        url_hash = hashlib.sha1(self.url).hexdigest()
        destination = os.path.join(settings.DATA_DIR, url_hash)
        etag_location = os.path.join(settings.DATA_DIR, url_hash + '.hash')
        self.pre_download(destination)

        request = urlopen(self.url)
        etag = False

        if self.check_etag and os.path.exists(etag_location):
            # Check etag cache
            request_etag = request.info()['ETag']
            with open(etag_location, 'r') as f:
                etag = (f.read() == request_etag)

        if self.check_etag and not etag:
            # Update etag cache
            with open(etag_location, 'w+') as f:
                logger.info('Writing file ETag {}'.format(etag_location))
                f.write(request.info()['ETag'])

        if not etag:
            # File must be downloaded
            logger.info('Download file {} to {}'.format(self.url, destination))
            if os.path.exists(destination):
                os.remove(destination)

            urlretrieve(self.url, destination)

        self.downloaded_file = destination
        self.post_download(destination, downloaded=(not etag))
        return self.download_file


class ParltrackImporter(FileImporter):
    url = 'http://parltrack.euwiki.org/dumps/ep_meps_current.json.xz'
    check_etag = True
    representative_pre_save = django.dispatch.Signal(
        providing_args=['representative', 'data'])
    representative_post_save = django.dispatch.Signal(
        providing_args=['representative', 'data'])

    def parse_date(self, date):
        return _parse_date(date)

    def __init__(self):
        self.cache = {}

    def _travis(self):
        """ Avoid being killed after 10 minutes without output """
        if not os.environ.get('TRAVIS', False):
            return

        now = time.time()
        last_output = getattr(self, '_travis_last_output', None)

        if last_output is None or now - last_output >= 530:
            print('Do not kill me !')
            self._travis_last_output = now

    def post_download(self, destination, downloaded):
        '''
        Uncompress xz file
        '''
        if not downloaded:
            return
        os.rename(destination, destination + '.xz')
        if os.system("which unxz > /dev/null") != 0:
            raise Exception(
                "unxz binary missing, please install xz")

        logger.info('unxz {}'.format(destination + '.xz'))
        os.system('unxz {}'.format(destination + '.xz'))

    def do_import(self):
        '''
        Main import method
        '''
        logger.info('start processing representatives')
        i = 2
        with open(self.downloaded_file, 'r') as json_data_file:
            for mep in ijson.items(json_data_file, 'item'):
                logger.info(u'Processing representative #%s: %s',
                        mep['UserID'], mep['Name']['full'])

                self.mep_cache = dict(staff=[], constituencies=[],
                        committees=[], groups=[], delegations=[])
                self.manage_mep(mep)
                i += 1

                self._travis()
        print i

    @transaction.atomic
    def manage_mep(self, mep_json):
        '''
        Import a mep as a representative from the json dict fetched from
        parltrack
        '''
        remote_id = mep_json['UserID']

        if not remote_id:
            logger.warning('Skipping MEP without UID %s %s',
                    mep_json['Name']['full'], mep_json['UserID'])
            return

        try:
            representative = Representative.objects.get(remote_id=remote_id)
        except Representative.DoesNotExist:
            representative = Representative(remote_id=remote_id)

        # Save representative attributes
        self.save_representative_details(representative, mep_json)
        self.representative_pre_save.send(sender=self,
                representative=representative, data=mep_json)

        representative.save()

        self.add_mandates(representative, mep_json)

        self.add_contacts(representative, mep_json)

        self.representative_post_save.send(sender=self,
                representative=representative, data=mep_json)

        return representative

    def save_representative_details(self, representative, mep_json):
        representative.active = mep_json['active']

        if mep_json.get("Birth"):
            representative.birth_date = _parse_date(mep_json["Birth"]["date"])
            if "place" in mep_json["Birth"]:
                representative.birth_place = mep_json["Birth"]["place"]

        representative.first_name = mep_json["Name"]["sur"]
        representative.last_name = mep_json["Name"]["family"]
        representative.full_name = mep_json["Name"]["full"]

        representative.photo = mep_json["Photo"]

        fix_last_name_with_prefix = {
            "Esther de LANGE": "de LANGE",
            "Patricia van der KAMMEN": "van der KAMMEN",
            "Judith A. MERKIES": "MERKIES",
            "Heinz K. BECKER": "BECKER",
            "Cornelis de JONG": "de JONG",
            "Peter van DALEN": "van DALEN",
            "Sophia in 't VELD": "in 't VELD",
            "Marielle de SARNEZ": "de SARNEZ",
            "Anne E. JENSEN": "JENSEN",
            "Wim van de CAMP": "van de CAMP",
            "Lambert van NISTELROOIJ": "van NISTELROOIJ",
            "Johannes Cornelis van BAALEN": "van BAALEN",
            "Ioannis A. TSOUKALAS": "TSOUKALAS",
            "Pilar del CASTILLO VERA": "del CASTILLO VERA",
            "Luis de GRANDES PASCUAL": "de GRANDES PASCUAL",
            "Philippe de VILLIERS": "de VILLIERS",
            "Daniël van der STOEP": "van der STOEP",
            "William (The Earl of) DARTMOUTH": "(The Earl of) Dartmouth",
            "Bairbre de BRÚN": u'de Br\xfan',
            "Karl von WOGAU": u'von WOGAU',
            "Ieke van den BURG": u'van den BURG',
            "Manuel António dos SANTOS": u'dos SANTOS',
            "Paul van BUITENEN": u'van BUITENEN',
            "Elly de GROEN-KOUWENHOVEN": u'de GROEN-KOUWENHOVEN',
            "Margrietus van den BERG": u'van den BERG',
            u'Dani\xebl van der STOEP': u'van der STOEP',
            "Alexander Graf LAMBSDORFF": u'Graf LAMBSDORFF',
            u'Bairbre de BR\xdaN': u'de BR\xdaN',
            'Luigi de MAGISTRIS': 'de MAGISTRIS',
        }

        if fix_last_name_with_prefix.get(representative.full_name):
            representative.last_name = fix_last_name_with_prefix[representative.full_name]
        elif representative.last_name == "J.A.J. STASSEN":
            representative.last_name_with_prefix = "STASSEN"

        gender_convertion_dict = {
            u"F": 1,
            u"M": 2
        }
        if 'Gender' in mep_json:
            representative.gender = gender_convertion_dict.get(mep_json['Gender'], 0)
        else:
            representative.gender = 0

        representative.cv = "\n".join([cv_title for cv_title in mep_json.get("CV", [])])

        representative.slug = slugify(
            representative.full_name if representative.full_name
            else representative.first_name + " " + representative.last_name
        )


    def add_mandates(self, representative, mep_json):
        def get_or_create_mandate(mandate_data, representative, group,
                constituency):

            if mandate_data.get("start"):
                begin_date = _parse_date(mandate_data.get("start"))
            if mandate_data.get("end"):
                end_date = _parse_date(mandate_data.get("end"))

            role = mandate_data['role'] if 'role' in mandate_data else ''
            mandate, _ = Mandate.objects.get_or_create(
                representative=representative,
                group=group,
                constituency=constituency,
                role=role,
                begin_date=begin_date,
                end_date=end_date
            )

            if _:
                logger.info('Created mandate %s with %s', mandate.pk,
                        mandate_data)
            return mandate

        # Committee
        for mandate_data in mep_json.get('Committees', []):
            if mandate_data.get("committee_id"):
                group, _ = self.touch_model(model=Group,
                    abbreviation=mandate_data['committee_id'],
                    kind='committee',
                    name=mandate_data['Organization']
                )

                constituency, _ = self.touch_model(Constituency,
                    name='European Parliament'
                )

                self.mep_cache['committees'].append(
                    get_or_create_mandate(mandate_data, representative,
                        group, constituency)
                )

        # Delegations
        for mandate_data in mep_json.get('Delegations', []):
            group, _ = self.touch_model(model=Group,
                kind='delegation',
                name=mandate_data['Organization']
            )

            constituency, _ = Constituency.objects.get_or_create(
                name='European Parliament'
            )

            self.mep_cache['delegations'].append(
                get_or_create_mandate(mandate_data, representative, group,
                    constituency)
            )

        # Group
        convert = {"S&D": "SD", "NA": "NI", "ID": "IND/DEM", "PPE": "EPP", "Verts/ALE": "Greens/EFA"}
        for mandate_data in mep_json.get('Groups', []):
            if not mandate_data.get('groupid'):
                continue

            if type(mandate_data.get('groupid')) is list:
                abbreviation = mandate_data.get('groupid')[0]
            else:
                abbreviation = mandate_data.get('groupid')

            abbreviation = convert.get(abbreviation, abbreviation)
            group, _ = self.touch_model(model=Group,
                abbreviation=abbreviation,
                kind='group',
                name=mandate_data['Organization']
            )

            constituency, _ = self.touch_model(model=Constituency,
                name='European Parliament'
            )

            self.mep_cache['groups'].append(
                get_or_create_mandate(mandate_data, representative, group,
                    constituency)
            )

        # Countries
        for mandate_data in mep_json.get('Constituencies', []):
            if not mandate_data:
                continue

            _country = Country.objects.get(name=mandate_data['country'])

            group, _ = self.touch_model(model=Group,
                abbreviation=_country.code,
                kind='country',
                name=_country.name
            )

            local_party = mandate_data['party'] if mandate_data['party'] and mandate_data['party'] != '-' else 'unknown'
            constituency, _ = self.touch_model(model=Constituency,
                name=local_party
            )

            self.mep_cache['constituencies'].append(
                get_or_create_mandate(mandate_data, representative, group,
                    constituency)
            )

        # Organisations
        for mandate_data in mep_json.get('Staff', []):

            group, _ = self.touch_model(model=Group,
                abbreviation='',
                kind='organization',
                name=mandate_data['Organization']
            )

            constituency, _ = self.touch_model(model=Constituency,
                name='European Parliament'
            )

            self.mep_cache['staff'].append(
                get_or_create_mandate(mandate_data, representative, group,
                    constituency)
            )

    def add_contacts(self, representative, mep_json):
        # Addresses
        if mep_json.get('Addresses', None):
            address = mep_json.get('Addresses')

            belgium = Country.objects.get(name="Belgium")
            france = Country.objects.get(name="France")

            for city in address:
                if city in ['Brussels', 'Strasbourg']:
                    if city == 'Brussels':
                        country = belgium
                        street = u"rue Wiertz / Wiertzstraat"
                        number = '60'
                        postcode = '1047'
                        name = "Brussels European Parliament"
                    elif city == 'Strasbourg':
                        country = france
                        street = u"avenue du Pr\xe9sident Robert Schuman - CS 91024"
                        number = '1'
                        postcode = '67070'
                        name = "Strasbourg European Parliament"


                        address_model, _ = self.touch_model(model=Address,
                            representative=representative,
                            country=country,
                            city=city,
                            floor=address[city]['Address']['Office'][:3],
                            office_number=address[city]['Address']['Office'][3:],
                            street=street,
                            number=number,
                            postcode=postcode,
                            kind='official',
                            name=name
                        )

                        self.touch_model(model=Phone,
                            representative=representative,
                            address=address_model,
                            kind='office phone',
                            number=address[city].get('Phone', '')
                        )

        # Emails
        if mep_json.get('Mail', None):
            mails = mep_json.get('Mail')
            if type(mails) is not list:
                mails = list(mails)

            for mail in mails:
                self.touch_model(model=Email,
                    representative=representative,
                    kind='official' if '@europarl.europa.eu' in mail else 'other',
                    email=mail
                )
        # WebSite
        websites = mep_json.get('Homepage', [])
        for url in websites:
            self.touch_model(model=WebSite,
                url=url,
                representative=representative
            )

        if mep_json.get('Twitter', None):
            self.touch_model(model=WebSite,
                representative=representative,
                kind='twitter',
                url=mep_json.get('Twitter')[0]
            )

        if mep_json.get('Facebook', None):

            self.touch_model(model=WebSite,
                representative=representative,
                kind='facebook',
                url=mep_json.get('Facebook')[0]
            )


class Command(BaseCommand):
    help = "Update the eurodeputies data by pulling it from parltrack"

    def add_arguments(self, parser):
        parser.add_argument('--celery', action='store_true', default=False)

    def handle(self, *args, **options):
        importer = ParltrackImporter()
        importer.process()


def main():
    import django
    django.setup()

    importer = ParltrackImporter()
    GenericImporter.pre_import(importer)

    i = 0
    for line in fileinput.input():
        # Fix first line
        line = line.lstrip('[')
        # Fix last line
        line = line.rstrip(']')
        # Skip inter-line
        if line.strip() == ',':
            continue

        mep = json.loads(line)

        logger.info(u'Processing representative #%s: %s',
                mep['UserID'], mep['Name']['full'])

        importer.mep_cache = dict(staff=[], constituencies=[],
                committees=[], groups=[], delegations=[])
        importer.manage_mep(mep)

        i += 1
        if i > 100:
            gc.collect()
            i = 0
    importer.post_import()
