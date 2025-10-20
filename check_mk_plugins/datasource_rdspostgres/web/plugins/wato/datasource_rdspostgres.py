#!/usr/bin/env python3
# -*- mode: Python; encoding: utf-8; indent-offset: 4; autowrap: nil -*-

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    TextAscii,
    PasswordSpec,
)

from cmk.gui.plugins.wato.utils import (
    # IndividualOrStoredPassword,
    # RulespecGroup,
    # monitoring_macro_help,
    # rulespec_group_registry,
    rulespec_registry,
    HostRulespec,
)

# from cmk.gui.plugins.wato.datasource_programs import (
#     RulespecGroupDatasourcePrograms,
# )

from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourcePrograms


def _valuespec_special_agents_rdspostgres():
    return Dictionary(
        elements=[
            ("username", TextAscii(title=_("Username"), allow_empty=False)),
            ("password", PasswordSpec(title=_("Password"), allow_empty=False))
        ],
        optional_keys=False,
        title=_("RDS credentials"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:rdspostgres",
        valuespec=_valuespec_special_agents_rdspostgres,
    ))
