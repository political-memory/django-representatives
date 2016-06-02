from dbdiff.test import DbdiffTestMixin

from representatives import models


class ImportTestMixin(DbdiffTestMixin):
    dbdiff_models = [
        models.Representative,
        models.Email,
        models.WebSite,
        models.Address,
        models.Phone,
        models.Chamber,
        models.Group,
        models.Constituency,
        models.Mandate,
    ]

    dbdiff_exclude = {
        '*': (
            'created',
            'updated',
            'fingerprint'
        )
    }

    dbdiff_reset_sequences = True
    dbdiff_fixtures = ['country_initial_data.json']
