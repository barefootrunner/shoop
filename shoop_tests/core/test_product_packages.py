# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2015, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

import pytest
from shoop.core.models import OrderLineType, AnonymousContact, ProductMode
from shoop.core.order_creator import OrderCreator
from shoop.core.order_creator.source import SourceLine
from shoop.core.pricing import TaxlessPrice
from shoop.testing.factories import create_product, get_default_shop, get_default_supplier, get_initial_order_status
from shoop_tests.utils.basketish_order_source import BasketishOrderSource
import six


@pytest.mark.django_db
def test_package():
    shop = get_default_shop()
    supplier = get_default_supplier()
    package_product = create_product("PackageParent", shop=shop, supplier=supplier)
    assert not package_product.get_package_child_to_quantity_map()
    children = [create_product("PackageChild-%d" % x, shop=shop, supplier=supplier) for x in range(4)]
    package_def = {child: 1 + i for (i, child) in enumerate(children)}
    package_product.make_package(package_def)
    assert package_product.is_package_parent()
    package_product.save()
    sp = package_product.get_shop_instance(shop)
    assert not list(sp.get_orderability_errors(supplier=supplier, quantity=1, customer=AnonymousContact()))

    with pytest.raises(ValueError):  # Test re-packaging fails
        package_product.make_package(package_def)

    # Check that OrderCreator can deal with packages

    source = BasketishOrderSource()
    source.lines.append(SourceLine(
        type=OrderLineType.PRODUCT,
        product=package_product,
        supplier=get_default_supplier(),
        quantity=10,
        unit_price=TaxlessPrice(10),
    ))

    source.shop = get_default_shop()
    source.status = get_initial_order_status()
    creator = OrderCreator(request=None)
    order = creator.create_order(source)
    pids_to_quantities = order.get_product_ids_and_quantities()
    for child, quantity in six.iteritems(package_def):
        assert pids_to_quantities[child.pk] == 10 * quantity
