# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2015, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

import babel
from babel.numbers import format_currency
from django.conf import settings
from django.utils import translation
from django.utils.lru_cache import lru_cache

from shoop.utils.numbers import parse_decimal_string


@lru_cache()
def get_babel_locale(locale_string):
    """
    Parse a Django-format (dash-separated) locale string
    and return a Babel locale.

    This function is decorated with lru_cache, so executions
    should be cheap even if `babel.Locale.parse()` most definitely
    is not.

    :param locale_string: A locale string ("en-US", "fi-FI", "fi")
    :type locale_string: str
    :return: Babel Locale
    :rtype: babel.Locale
    """
    return babel.Locale.parse(locale_string, "-")


def get_current_babel_locale():
    """
    Get a Babel locale based on the thread's locale context.

    :return: Babel Locale
    :rtype: babel.Locale
    """
    return get_babel_locale(locale_string=translation.get_language())


def format_home_currency(value, locale=None):
    value = parse_decimal_string(value)
    return format_currency(value, currency=settings.SHOOP_HOME_CURRENCY, locale=locale or get_current_babel_locale())


def get_language_name(language_code):
    return get_current_babel_locale().languages.get(language_code, language_code)
