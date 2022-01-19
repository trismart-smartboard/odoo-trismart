from odoo import api, fields, models, tools

class Partner(models.Model):
    _inherit = "res.partner"

    # Add technical fields
    sb_lead_id = fields.Integer('Smartboard Lead ID', readonly=True)
    sync_status = fields.Selection([('1', 'Pending'), ('2', 'Done'), ('3', 'Error')])
    x_api_key = fields.Char('X API Key', readonly=True)

