# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2015, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from jsonfield.fields import JSONField

from shoop.core.fields import InternalIdentifierField
from shoop.notify.base import Event
from shoop.notify.enums import StepNext


@python_2_unicode_compatible
class Script(models.Model):
    event_identifier = models.CharField(max_length=64, blank=False, db_index=True)
    identifier = InternalIdentifierField()
    created_on = models.DateTimeField(auto_now_add=True, editable=False)
    name = models.CharField(max_length=64)
    enabled = models.BooleanField(default=False, db_index=True)
    _step_data = JSONField(default=[], db_column="step_data")

    def get_steps(self):
        """
        :rtype Iterable[Step]
        """
        if getattr(self, "_steps", None) is None:
            from shoop.notify.script import Step
            self._steps = [Step.unserialize(data) for data in self._step_data]
        return self._steps

    def set_steps(self, steps):
        self._step_data = [step.serialize() for step in steps]
        self._steps = steps

    def get_serialized_steps(self):
        return [step.serialize() for step in self.get_steps()]

    def set_serialized_steps(self, serialized_data):
        self._steps = None
        self._step_data = serialized_data
        # Poor man's validation
        for step in self.get_steps():
            pass

    @property
    def event_class(self):
        return Event.class_for_identifier(self.event_identifier)

    def __str__(self):
        return self.name

    def execute(self, context):
        """
        Execute the script in the given context.

        :param context: Script context
        :type context: shoop.notify.script.Context
        """
        for step in self.get_steps():
            if step.execute(context) == StepNext.STOP:
                break
