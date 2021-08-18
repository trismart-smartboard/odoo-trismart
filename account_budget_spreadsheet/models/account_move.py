from odoo import models, fields, api
import datetime
import uuid
import re
from odoo.exceptions import UserError
from odoo.tools import OrderedSet

regex_field_agg = re.compile(r'(\w+)(?::(\w+)(?:\((\w+)\))?)?')
# valid SQL aggregation functions
VALID_AGGREGATE_FUNCTIONS = {
    'array_agg', 'count', 'count_distinct',
    'bool_and', 'bool_or', 'max', 'min', 'avg', 'sum',
}


class AccountMove(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        result = super()._read_group_raw(domain, fields, groupby, offset, limit, orderby, lazy)
        if 'budget_spreadsheet' in self._context:
            user_id_type = \
                list(filter(lambda x: 'account_id.user_type_id' in x or 'account_id.user_type_id.type' in x,
                            domain))[0]
            analytic_account_domain = list(filter(lambda x: 'analytic_account_id' in x, domain))
            user_id_domain = [user_id_type[-1]] if type(user_id_type[-1]) in [str, int] else user_id_type[-1]
            accounts = self.env['account.account'].search([('user_type_id', 'in', user_id_domain)])
            if len(analytic_account_domain) or len(result) == 0:
                for account in accounts:
                    account_name = account.name
                    new_result = {'__count': 1, 'balance': 0.0,
                                  'account_id': (account.id, str(account.code) + " " + account_name),
                                  groupby[1]: "",
                                  '__domain': ['&', '&', '&', ('account_id', '=', account.id),
                                               ('display_type', 'not in', ['line_section', 'line_note']), '&',
                                               ('move_id.state', '!=', 'cancel'),
                                               ('move_id.state', '=', 'posted'), '&',
                                               ('account_id.user_type_id', '=', account.id)
                                               ]}
                    if len(analytic_account_domain):
                        new_result['__domain'] = new_result['__domain'] + analytic_account_domain[0]
                    result.append(new_result)
            else:
                if len(result):
                    first_result = result[0]
                    domain = first_result['__domain']
                    for account in accounts:
                        account_name = account.name
                        domain[2] = ('account_id', '=', account.id)
                        new_domain = domain
                        result.append({'__count': 1, 'balance': 0.0,
                                       'account_id': (account.id, str(account.code) + " " + account_name),
                                       groupby[1]: "",
                                       '__domain': new_domain})
        return result
