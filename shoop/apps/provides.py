# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2015, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
"""
This module contains the API to deal with the Provides system.

The Provides system is Shoop's mechanism for discovering and
loading components, both first-party and third-party.

.. seealso:: See :doc:`/provides` for further information about the Provides system.

"""

from __future__ import unicode_literals

from collections import OrderedDict, defaultdict
from contextlib import contextmanager

import six
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shoop.apps import AppConfig
from shoop.utils.importing import load

_provide_specs = defaultdict(list)
_loaded_provides = defaultdict(OrderedDict)
_identifier_to_spec = defaultdict(OrderedDict)
_identifier_to_object = defaultdict(OrderedDict)


def _uncache(category):
    _loaded_provides.pop(category, None)
    _identifier_to_spec.pop(category, None)
    _identifier_to_object.pop(category, None)


def clear_provides_cache():
    _provide_specs.clear()
    _loaded_provides.clear()
    _identifier_to_spec.clear()
    _identifier_to_object.clear()


def _get_provide_specs_from_apps(category):
    """
    Load provide spec strings from installed `shoop.apps.AppConfig`s.

    This function takes care to order the spec list to match the order
    the apps were enabled in `INSTALLED_APPS` to avoid nondeterministic
    failures that caused by different values of `PYTHONHASHSEED`
    (and the resulting change of dict iteration order).

    :param category: Provide category name
    :type category: str
    :return: List of spec strings.
    :rtype: list[str]
    """
    if category not in _provide_specs:  # (Re)load required?
        provide_list = []
        for app_config in apps.get_app_configs():
            if not isinstance(app_config, AppConfig):
                # No need to look at non-Shoop AppConfigen.
                continue
            spec_list = app_config.provides.get(category, ())
            for spec in spec_list:  # Insert in order without duplicates...
                if spec not in provide_list:
                    provide_list.append(spec)
        _provide_specs[category] = provide_list
    return _provide_specs[category]


def _load_provide_objects(category):
    provide_specs = _get_provide_specs_from_apps(category)
    loaded_provides = _loaded_provides[category]
    if set(provide_specs) != set(loaded_provides.keys()):  # Changes occurred, reload provides
        _uncache(category)
        explanation = "Loading provides %s" % category
        loaded_provides = OrderedDict()
        for spec in provide_specs:
            loaded_provides[spec] = load(spec, explanation)
        _loaded_provides[category] = loaded_provides
    return _loaded_provides.get(category, {})


def _load_identifier_maps(category):
    provides = _load_provide_objects(category)
    if category not in _identifier_to_spec:  # Either not loaded or `_uncache`d
        identifier_to_spec = OrderedDict()
        identifier_to_object = OrderedDict()

        for spec, object in six.iteritems(provides):
            identifier = getattr(object, "identifier", None)
            if identifier:
                identifier_to_spec[identifier] = spec
                identifier_to_object[identifier] = object

        _identifier_to_spec[category] = identifier_to_spec
        _identifier_to_object[category] = identifier_to_object


def get_provide_specs_and_objects(category):
    """
    Get a mapping of provide specs ("x.y.z:Q") to their loaded objects (<class Q>).

    :param category: Category to load objects for
    :type category: str
    :return: Dict of spec -> object
    :rtype: dict[str, object]
    """
    return _load_provide_objects(category).copy()


def get_provide_objects(category):
    """
    Get an iterable of provide objects for the given category.

    :param category: Category to load objects for
    :type category: str
    :return: Iterable of objects
    :rtype: Iterable[object]
    """
    return six.itervalues(_load_provide_objects(category))


def get_identifier_to_spec_map(category):
    _load_identifier_maps(category)
    return _identifier_to_spec[category].copy()


def get_identifier_to_object_map(category):
    _load_identifier_maps(category)
    return _identifier_to_object[category].copy()


@contextmanager
def override_provides(category, spec_list):
    """
    Context manager to override `provides` for a given category.

    Useful for testing.

    :param category: Category name.
    :type category: str
    :param spec_list: List of specs.
    :type spec_list: list[str]
    """
    old_provides = _provide_specs[category]
    _uncache(category)
    _provide_specs[category] = spec_list
    try:
        yield
    finally:
        _uncache(category)
        _provide_specs[category] = old_provides


def load_module(setting_name, provide_category):
    """
    Load a module from a module setting.

    The value of the setting must be a module identifier for the given provide category.

    :param setting_name: The setting name for the identifier
    :type setting_name: str
    :param provide_category: The provide category for the identifier lookup (e.g. `tax_module`)
    :type provide_category: str
    :return: An object.
    :rtype: object
    """
    setting_value = getattr(settings, setting_name, None)
    if not setting_value:
        raise ImproperlyConfigured("The setting `%s` MUST be set." % setting_name)

    object = get_identifier_to_object_map(provide_category).get(setting_value)
    if not object:
        raise ImproperlyConfigured(
            "Setting %s refers to a provide with identifier %r, but "
            "it isn't one of the known identifiers in the %s category: %r" % (
                setting_name, setting_value, provide_category,
                sorted(get_identifier_to_object_map(provide_category).keys())
            )
        )

    return object
