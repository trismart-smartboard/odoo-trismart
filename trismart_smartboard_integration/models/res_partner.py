from odoo import api, fields, models, tools

class Partner(models.Model):
    _inherit = "res.partner"

    sb_lead_id = fields.Integer('Smartboard Lead ID', readonly=True)
    sync_status = fields.Selection([
        ('1', 'Needs Update'), ('2', 'Updated')])

