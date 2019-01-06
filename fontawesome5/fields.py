from __future__ import absolute_import

from django.db import models
from django.utils.translation import ugettext as _

from .app_settings import get_icon_class, get_prefix
from .forms import IconFormField
from .shims import shims

prefix = get_prefix()
Icon = get_icon_class()


class IconField(models.Field):
    description = _('A fontawesome icon field')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 60
        kwargs['blank'] = True
        super(IconField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        if not ',' in value:
            value = shims.get(value, 'None,None')
        values = value.split(',')
        return Icon(style_prefix=values[0], prefix=prefix, icon=values[1])

    def to_python(self, value):
        if not value or value == 'None':
            return None

        if isinstance(value, Icon):
            return value
        if not ',' in value:
            value = shims.get(value, 'None,None')
        values = value.split(',')
        return Icon(style_prefix=values[0], prefix=prefix, icon=values[1])

    def get_prep_value(self, value):
        return str(value)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': IconFormField,
        }

        defaults.update(kwargs)
        return super(IconField, self).formfield(**defaults)