# coding: utf-8

# This file is part of django-parltrack-meps.
#
# django-parltrack-meps is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version.
#
# django-parltrack-meps is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU General Affero Public
# License along with Foobar.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2013  Laurent Peuch <cortex@worlddomination.be>

import os
import ijson
import urllib

from tempfile import gettempdir

from os.path import join
from datetime import datetime


# from guess_language import guessLanguage
# from lxml import etree
from django.template.defaultfilters import slugify

from django.core.management.base import BaseCommand
# from django.db.models import Count
from django.db import transaction

from representatives.models import Representative, Group, Constituency, Mandate, Address, Country, Phone, Email, WebSite

# from import_parltrack.models import Country

JSON_DUMP_ARCHIVE_LOCALIZATION = join(gettempdir(), "ep_meps_current.json.xz")
JSON_DUMP_ARCHIVE_LOCALIZATION_TAG = join(gettempdir(), "ep_meps_current.hash")
JSON_DUMP_LOCALIZATION = join(gettempdir(), "ep_meps_current.json")
PARLTRACK_URL = 'http://parltrack.euwiki.org/dumps/ep_meps_current.json.xz'
CURRENT_TERM = 8
_parse_date = lambda date: datetime.strptime(date, "%Y-%m-%dT00:%H:00")


def download_file():
    if os.system("which unxz > /dev/null") != 0:
        raise Exception("unxz binary missing, please install xz")

    if os.path.exists(JSON_DUMP_ARCHIVE_LOCALIZATION_TAG):
        with open(JSON_DUMP_ARCHIVE_LOCALIZATION_TAG, 'r') as f:
            etag = f.read()
    else:
        etag = False
    
    request = urllib.urlopen(PARLTRACK_URL)
    request_etag = request.info()['ETag']

    if not etag or not etag == request_etag:
        print "clean old downloaded files"
        
        if os.path.exists(JSON_DUMP_ARCHIVE_LOCALIZATION):
            os.remove(JSON_DUMP_ARCHIVE_LOCALIZATION)
            
        if os.path.exists(JSON_DUMP_LOCALIZATION):
            os.remove(JSON_DUMP_LOCALIZATION)

        urllib.urlretrieve(PARLTRACK_URL, JSON_DUMP_ARCHIVE_LOCALIZATION)

        with open(JSON_DUMP_ARCHIVE_LOCALIZATION_TAG, 'w+') as f:
            f.write(request_etag)

        print "unxz dump"
        os.system("unxz %s" % JSON_DUMP_ARCHIVE_LOCALIZATION)


class Command(BaseCommand):
    help = "Update the eurodeputies data by pulling it from parltrack"

    def handle(self, *args, **options):
        download_file()

        print "load json"
        meps = ijson.items(open(JSON_DUMP_LOCALIZATION), 'item')
        # print "Set all current active mep to unactive before importing"
        with transaction.atomic():
            # MEP.objects.filter(active=True).update(active=False)
            # a = 0
            for mep_json in meps:
                # TODO only active ?
                # print(mep_json.get("active"))
                
                manage_mep(mep_json)
                """
                if not mep_json.get("active"):
                    continue
                a += 1
                print a, "-", mep_json["Name"]["full"].encode("Utf-8")
                in_db_mep = MEP.objects.filter(ep_id=int(mep_json["UserID"]))
                if in_db_mep:
                    mep = in_db_mep[0]
                    mep.active = mep_json['active']
                    manage_mep(mep, mep_json)
                else:
                    mep = create_mep(mep_json)
            clean()
        print
                """

def manage_mep(mep_json):
    remote_id = mep_json['UserID']
    representative, created = Representative.objects.get_or_create(remote_id=remote_id)
    # Save representative attributes
    change_representative_details(representative, mep_json)
    # Add Mandates
    add_mandates(representative, mep_json)
    # Add Contacts
    add_contacts(representative, mep_json)
    

    representative.save()


def change_representative_details(representative, mep_json):
    representative.active = mep_json['active']

    if mep_json.get("Birth"):
        representative.birth_date = _parse_date(mep_json["Birth"]["date"])
        if "place" in mep_json["Birth"]:
            representative.birth_place = mep_json["Birth"]["place"]

    representative.first_name = mep_json["Name"]["sur"]
    representative.last_name = mep_json["Name"]["family"]
    representative.full_name = "%s %s" % (mep_json["Name"]["sur"], mep_json["Name"]["family"])

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

    # mep.swaped_name = "%s %s" % (mep.last_name, mep.first_name)
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


def create_mandate(mandate_data, representative, group, constituency):
    if mandate_data.get("start"):
        begin_date = _parse_date(mandate_data.get("start"))
    if mandate_data.get("end"):
        end_date = _parse_date(mandate_data.get("end"))
    
    role = mandate_data['role'] if 'role' in mandate_data else None
    Mandate.objects.create(
        representative=representative,
        group=group,
        constituency=constituency,
        role=role,
        begin_date=begin_date,
        end_date=end_date
    )


def add_mandates(representative, mep_json):
    # Committee
    for mandate_data in mep_json.get('Committees', []):
        if mandate_data.get("committee_id"):
            group, cr = Group.objects.get_or_create(
                abbreviation=mandate_data['committee_id'],
                kind='committee',
                name=mandate_data['Organization']
            )

            constituency, cr = Constituency.objects.get_or_create(
                name='European Parliament'
            )

            create_mandate(mandate_data, representative, group, constituency)

    # Delegations 
    for mandate_data in mep_json.get('Delegations', []):
        group, cr = Group.objects.get_or_create(
            kind='delegation',
            name=mandate_data['Organization']
        )

        constituency, cr = Constituency.objects.get_or_create(
            name='European Parliament'
        )

        create_mandate(mandate_data, representative, group, constituency)

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
        group, cr = Group.objects.get_or_create(
            abbreviation=abbreviation,
            kind='group',
            name=mandate_data['Organization']
        )

        constituency, cr = Constituency.objects.get_or_create(
            name='European Parliament'
        )

        create_mandate(mandate_data, representative, group, constituency)

    # Countries
    for mandate_data in mep_json.get('Constituencies', []):
        if not mandate_data:
            continue

        _country = Country.objects.get(name=mandate_data['country'])

        group, cr = Group.objects.get_or_create(
            abbreviation=_country.code,
            kind='country',
            name=_country.name
        )
        
        local_party = mandate_data['party'] if mandate_data['party'] and mandate_data['party'] != '-' else 'unknown'
        constituency, cr = Constituency.objects.get_or_create(
            name=local_party
        )
        
        create_mandate(mandate_data, representative, group, constituency)
        
    # Organisations
    for mandate_data in mep_json.get('Staff', []):

        group, cr = Group.objects.get_or_create(
            abbreviation=None,
            kind='organization',
            name=mandate_data['Organization']
        )

        constituency, cr = Constituency.objects.get_or_create(
            name='European Parliament'
        )
        
        create_mandate(mandate_data, representative, group, constituency)
    

def add_contacts(representative, mep_json):
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
                

                    address_model = Address.objects.create(
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
                    
                    Phone.objects.create(
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
            Email.objects.get_or_create(
                representative=representative,
                kind='official' if '@europarl.europa.eu' in mail else 'other',
                email=mail
            )
    # WebSite
    websites = mep_json.get('Homepage', [])
    for url in websites:
        WebSite.objects.create(
            url=url,
            representative=representative
        )

    if mep_json.get('Twitter', None):
        WebSite.objects.create(
            representative=representative,
            kind='twitter',
            url= mep_json.get('Twitter')[0]
        )

    if mep_json.get('Facebook', None):
        WebSite.objects.create(
            representative=representative,
            kind='facebook',
            url= mep_json.get('Facebook')[0]
        )

