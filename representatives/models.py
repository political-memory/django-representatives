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
# License along with django-representatives.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2013 Laurent Peuch <cortex@worlddomination.be>
# Copyright (C) 2015 Arnaud Fabre <af@laquadrature.net>

import hashlib
from datetime import datetime

from django.db import models
from django.utils.functional import cached_property
from django.utils.encoding import smart_str

from memopol_utils.mixins import HashableModel, TimeStampedModel


class Country(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=2)

    @property
    def fingerprint(self):
        fingerprint = hashlib.sha1()
        fingerprint.update(smart_str(self.name))
        fingerprint.update(smart_str(self.code))
        return fingerprint.hexdigest()

    def __unicode__(self):
        return u'{} [{}]'.format(self.name, self.code)


class Representative(HashableModel, TimeStampedModel):
    """
    Base model for representatives
    """

    slug = models.SlugField(max_length=100)
    remote_id = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255)
    GENDER = (
        (0, "N/A"),
        (1, "F"),
        (2, "M"),
    )
    gender = models.SmallIntegerField(choices=GENDER, default=0)
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    cv = models.TextField(blank=True, null=True)
    photo = models.CharField(max_length=512, null=True)
    active =  models.BooleanField(default=False)
    
    hashable_fields = ['remote_id']

    def __unicode__(self):
        return u'{} ({})'.format(self.full_name.decode('utf-8'), self.remote_id)

    def gender_as_str(self):
        genders = {0: 'N/A', 1: 'F', 2: 'M'}
        return genders[self.gender]


# Contact related models
class Contact(TimeStampedModel):
    representative = models.ForeignKey(Representative)

    class Meta:
        abstract = True


class Email(Contact):
    email = models.EmailField()
    kind = models.CharField(max_length=255, blank=True, null=True)


class WebSite(Contact):
    url = models.CharField(max_length=2048, blank=True, null=True)
    kind = models.CharField(max_length=255, blank=True, null=True)


class Address(Contact):
    country = models.ForeignKey(Country)
    city = models.CharField(max_length=255, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    number = models.CharField(max_length=255, blank=True, null=True)
    postcode = models.CharField(max_length=255, blank=True, null=True)
    floor = models.CharField(max_length=255, blank=True, null=True)
    office_number = models.CharField(max_length=255, blank=True, null=True)
    kind = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)  # TODO Find standard for storage in charfield

    '''
    hashable_fields = ['country', 'city', 'street', 'number',
                       'postcode', 'floor', 'office_number',
                       'kind', 'name', 'location', 'representative']
    '''

class Phone(Contact):
    number = models.CharField(max_length=255, blank=True, null=True)
    kind = models.CharField(max_length=255, blank=True, null=True)
    address = models.ForeignKey(Address, null=True, related_name='phones')
    

class Group(TimeStampedModel):
    """
    An entity represented by a representative through a mandate
    """
    name = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=10, blank=True, null=True)
    kind = models.CharField(max_length=255, blank=True, null=True)

    @cached_property
    def fingerprint(self):
        fingerprint = hashlib.sha1()
        fingerprint.update(smart_str(self.name))
        fingerprint.update(smart_str(self.abbreviation))
        fingerprint.update(smart_str(self.kind))
        return fingerprint.hexdigest()
        
    @cached_property
    def active(self):
        return self.mandates.filter(end_date__gte=datetime.now()).exists()

    def __unicode__(self):
        return unicode(self.name)


class Constituency(TimeStampedModel):
    """
    An authority for which a representative has a mandate
    """
    name = models.CharField(max_length=255)

    @cached_property
    def fingerprint(self):
        fingerprint = hashlib.sha1()
        fingerprint.update(smart_str(self.name))
        return fingerprint.hexdigest()

    @cached_property
    def active(self):
        return self.mandates.filter(end_date__gte=datetime.now()).exists()

    def __unicode__(self):
        return unicode(self.name)


class Mandate(HashableModel, TimeStampedModel):
    group = models.ForeignKey(Group, null=True, related_name='mandates')
    constituency = models.ForeignKey(Constituency, null=True, related_name='mandates')
    representative = models.ForeignKey(Representative, related_name='mandates')
    role = models.CharField(
        max_length=25,
        blank=True,
        default='',
        help_text="Eg.: president of a political group at the European Parliament"
    )
    begin_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    link = models.URLField()

    hashable_fields = ['group', 'constituency', 'role',
                       'begin_date', 'end_date', 'representative']

    @property
    def active(self):
        return self.end_date >= datetime.now().date()

    def __unicode__(self):
        return u'Mandate : {representative},{role} {group} for {constituency}'.format(
            representative=self.representative,
            role=(u' {} of'.format(self.role) if self.role else u''),
            constituency=self.constituency,
            group=self.group
        )
