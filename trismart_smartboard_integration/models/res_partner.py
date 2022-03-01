from odoo import api, fields, models, tools
from ..utils.endpoint import SmartBoardAPIURL
from ..utils.extractor import Extractor


class Partner(models.Model):
    _inherit = "res.partner"

    # Add technical fields
    sb_lead_id = fields.Integer('Smartboard Lead ID')
    sync_status = fields.Selection([('1', 'Pending'), ('2', 'Done'), ('3', 'Error')])
    x_api_key = fields.Char('X API Key')

    def fetch_smartboard_project(self):
        self.ensure_one()
        smartboard_request = self.env['smartboard.request']
        data = {'id': self.sb_lead_id}
        response_data = smartboard_request.api_request(SmartBoardAPIURL.READ_LEAD_URL, data, self)
        image_response_data = smartboard_request.api_request(SmartBoardAPIURL.READ_IMAGE_URL, data, self)
        document_response_data = smartboard_request.api_request(SmartBoardAPIURL.READ_DOCUMENT_URL, data, self)
        response_data.update(image_response_data)
        response_data.update(document_response_data)
        return response_data

    @api.model
    def _cron_fetch_project_smartboard(self):
        """
        Fetch information from SmartBoard to update Lead, Project, Customer Info for Pending Partner
        :return:
        """
        pending_partners = self.search([('sync_status', '=', '1')])
        extractor = Extractor()
        for partner in pending_partners:
            sb_lead_id = partner.sb_lead_id
            response_data = partner.fetch_smartboard_project()
            x_api_key = partner.x_api_key
            if not x_api_key:
                continue
            extracted_data = extractor.extract_data(response_data)
            try:
                for model, data in extracted_data.items():
                    model_record = self.env[model].search([('sb_lead_id', '=', sb_lead_id)])
                    ready_data = self.env['smartboard.processor'].parse_data(model, data)
                    model_record.update(ready_data)
            except Exception as e:
                raise ValueError(e)
            else:
                return True
