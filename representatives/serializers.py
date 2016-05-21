# coding: utf-8

from django.db import transaction
from rest_framework import serializers

import representatives.models as models


class CountrySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Country
        fields = ('name', 'code')


class ChamberSerializer(serializers.HyperlinkedModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = models.Chamber
        fields = (
            'name',
            'country',
            'abbreviation',
            'fingerprint',
            'url',
        )


class EmailSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Email
        fields = ('email', 'kind')


class WebsiteSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.WebSite
        fields = ('url', 'kind')

    def validate_url(self, value):
        # Don’t validate url, because it could break import of not proper
        # formed url
        return value


class PhoneSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Phone
        fields = ('number', 'kind')

    def validate_phone(self, value):
        return value


class AddressSerializer(serializers.HyperlinkedModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = models.Address
        fields = ('country', 'city', 'street',
                  'number', 'postcode', 'floor',
                  'office_number', 'kind',
                  )


class ContactField(serializers.Serializer):
    emails = EmailSerializer(many=True)
    phones = PhoneSerializer(many=True)
    websites = WebsiteSerializer(many=True)
    address = AddressSerializer(many=True)

    def get_attribute(self, obj):
        return {
            'emails': obj.email_set.all(),
            'websites': obj.website_set.all(),
            'phones': obj.phone_set.all(),
            'address': obj.address_set.all(),
        }


class ConstituencySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Constituency
        fields = ('id', 'name', 'fingerprint')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    chamber = ChamberSerializer()

    class Meta:
        model = models.Group
        fields = (
            'name',
            'abbreviation',
            'kind',
            'chamber',
            'url'
        )


class RepresentativeMandateSerializer(serializers.HyperlinkedModelSerializer):
    group = GroupSerializer()
    constituency = ConstituencySerializer()

    class Meta:
        depth = 1
        model = models.Mandate
        fields = (
            'id',
            'role',
            'begin_date',
            'end_date',
            'fingerprint',
            'url',
            'group',
            'constituency',
        )


class MandateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        depth = 1
        model = models.Mandate
        fields = RepresentativeMandateSerializer.Meta.fields + ('representative',)


class RepresentativeSerializer(RepresentativeMandateSerializer):
    class Meta:
        model = models.Representative
        fields = (
            'id',
            'slug',
            'remote_id',
            'full_name',
            'gender',
            'birth_place',
            'birth_date',
            'photo',
            'active',
            'fingerprint',
            'url',
        )


class RepresentativeDetailSerializer(RepresentativeSerializer):
    mandates = RepresentativeMandateSerializer(many=True)
    contact = ContactField()

    class Meta(RepresentativeSerializer.Meta):
        fields = RepresentativeSerializer.Meta.fields + (
            'mandates',
            'contact',
        )


class MandateDetailSerializer(RepresentativeMandateSerializer):
    representative = RepresentativeSerializer()

    class Meta(RepresentativeMandateSerializer.Meta):
        fields = RepresentativeMandateSerializer.Meta.fields + ('representative',)
