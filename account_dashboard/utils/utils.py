import base64
import odoo
import dateutil
import re
from pytz import timezone
from odoo.tools.safe_eval import wrap_module
from odoo.tools import formatLang

mods = ['parser', 'relativedelta', 'rrule', 'tz']
for mod in mods:
    __import__('dateutil.%s' % mod)


def format_currency(self, value):
    currency = self.env.company.currency_id
    return_value = formatLang(self.env, currency.round(value) + 0.0, currency_obj=currency)
    return return_value


def format_percentage(number):
    precision = 2
    str_num_formatted = "{:.{}f}".format(number, precision) + '%'
    return str_num_formatted


def get_eval_context(self, model_name, user_id=None, company_id=None):
    """ Prepare the context used when evaluating python code, like the
    python formulas or code server actions.
    :param user_id:
    :param self:
    :param model_name:
    :param action: the current server action
    :type action: browse record
    :returns: dict -- evaluation context given to (safe_)safe_eval """
    if user_id:
        user = self.env['res.users'].search([('id', '=', user_id)])
    else:
        user_id = self._uid
        user = self.env.user

    eval_context = {
        'uid': user_id,
        'user': user,
        'time': wrap_module(__import__('time'), ['time', 'strptime', 'strftime']),
        'datetime': wrap_module(__import__('datetime'), ['date', 'datetime', 'time', 'timedelta',
                                                         'timezone', 'tzinfo', 'MAXYEAR', 'MINYEAR']),
        'dateutil': wrap_module(dateutil, {
            mod: getattr(dateutil, mod).__all__ for mod in mods}),
        'timezone': timezone,
        'b64encode': base64.b64encode,
        'b64decode': base64.b64decode,
    }
    model = self.env[model_name]
    if company_id:
        model._context.update({'company_id': company_id})
    record = None
    records = None
    if self._context.get('active_model') == model_name and self._context.get('active_id'):
        record = model.browse(self._context['active_id'])
    if self._context.get('active_model') == model_name and self._context.get('active_ids'):
        records = model.browse(self._context['active_ids'])
    if self._context.get('onchange_self'):
        record = self._context['onchange_self']
    eval_context.update({
        # orm
        'env': self.env,
        'model': model,
        # Exceptions
        'Warning': odoo.exceptions.Warning,
        # record
        'record': record,
        'records': records,
    })
    return eval_context


def format_human_readable_amount(amount, suffix=''):
    for unit in ['', 'K', 'M', 'G']:
        if abs(amount) < 1000.0:
            return "%3.2f%s%s" % (amount, unit, suffix)
        amount /= 1000.0
    return "%.2f%s%s" % (amount, 'T', suffix)


def format_currency_amount(amount, currency_id, no_break_space=False):
    pre = post = u''
    if currency_id.position == 'before':
        pre = u'{symbol}%s'.format(symbol=currency_id.symbol or '') % \
              (u'\N{NO-BREAK SPACE}' if no_break_space else '',)
    else:
        post = u'%s{symbol}'.format(symbol=currency_id.symbol or '') % \
               (u'\N{NO-BREAK SPACE}' if no_break_space else '',)
    return u'{pre}{0}{post}'.format(amount, pre=pre, post=post)


def get_short_currency_amount(value, currency_id):
    converted_amount = format_human_readable_amount(value)
    short_title = format_currency_amount(converted_amount, currency_id)
    return short_title


def get_list_companies_child(cur_coms):
    list_com_id = cur_coms.ids
    for com in cur_coms:
        for child in com.child_ids:
            list_com_id += get_list_companies_child(child)
    return list_com_id


def reverse_formatLang(self, string):
    currency_symbol = self.env['res.currency'].search([('active', '=', True)]).mapped('symbol')
    active_language = self.env['res.lang'].search([('active', '=', True)])
    thousand_separator = active_language.thousands_sep
    decimal_separator = active_language.decimal_point
    symbols_to_replace = {thousand_separator: '', decimal_separator: '.', ' ': ''}
    currency_symbol_to_replace = {symbol: '' for symbol in currency_symbol}
    symbols_to_replace.update(currency_symbol_to_replace)
    for symbol, replace_value in symbols_to_replace.items():
        string = string.replace(symbol, replace_value)
    return float(string)
