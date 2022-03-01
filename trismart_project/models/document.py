from odoo import models, fields, api, _


class DocumentSubType(models.Model):
    _name = 'documents.subtype'

    document_type = fields.Selection([('image', 'Image'), ('document', 'Document')], string='Document Type')
    name = fields.Char('Document Subtype')


class Document(models.Model):
    _inherit = 'documents.document'

    created = fields.Datetime('Created')
    user_email = fields.Char('Email To')
    document_subtype = fields.Many2one('documents.subtype', domain="[('document_type','=','document')]")
    image_subtype = fields.Many2one('documents.subtype', domain="[('document_type','=','image')]")
    project_id = fields.Many2one('project.project', string='Project for this Document')
    sb_lead_id = fields.Integer('SmartBoard Lead Id', related='project_id.sb_lead_id')
