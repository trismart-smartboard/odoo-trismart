from odoo import api, fields, _


def write_off(inv, form, is_apply):
    description = (form.reason or inv.name) + _(" %s") % str(fields.Datetime.now())

    refund = inv.create_refund(form.write_off_amount, form.currency_id,
                               form.account_id,
                               form.date, description, inv.journal_id.id)

    # Put the reason in the chatter
    subject = 'Write Off An Account'
    body = description
    refund.message_post(body=body, subject=subject)

    if is_apply:
        internal_type = 'payable' if inv.move_type == 'in_invoice' else 'receivable'
        refund.action_post()
        (refund.line_ids | inv.line_ids).filtered(
            lambda r: r.account_id.internal_type == internal_type).reconcile()

    return refund
