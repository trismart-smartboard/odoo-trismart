from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.endpoint import SmartBoardAPIURL
from ..utils.exceptions import HTTPError
import requests
from ..utils.extractor import Extractor
import json


class SmartBoardRequest(models.TransientModel):
    _name = 'smartboard.request'
    _description = 'SmartBoard Request'

    prod_environment = fields.Boolean('Is Production Environment?', default=False)
    endpoint = fields.Char('SmartBoard Endpoint')

    def get_endpoint(self):
        if not self.endpoint:
            return SmartBoardAPIURL.SMARTBOARD_URL_ENDPOINT if self.prod_environment else SmartBoardAPIURL.SMART_BOARD_SANDBOX_URL_ENDPOINT
        else:
            return self.endpoint

    def smartboard_api_request(self, url, payload):
        """
        Calling SmartBoard API
        :param url:
        :param payload:
        :return:
        """
        smart_board_endpoint = self.get_endpoint()
        record_id = payload.get('data', False) and payload['data'].get('id', False)
        api_endpoint = smart_board_endpoint + url + str(record_id)
        headers = {
            'x-api-key': payload['x-api-key'],
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.get(api_endpoint, headers=headers)

        # Check the response data
        if response.status_code not in SmartBoardAPIURL.OK_CODES:
            message = "received HTTP {0}: {1} when sending to {2}: {3}".format(
                response.status_code, response.text, api_endpoint, payload
            )
            return HTTPError(message)

        # Try to parse the response data
        try:
            extractor = Extractor()
            data = extractor.extract_response_json(response)
            return data
        except Exception as e:
            return e

    @api.model
    def api_request(self, endpoint, data, partner):
        """
        Send Request to SmartBoard
        Authenticate if the sessionId is expired
        :param endpoint: SmartBoard endpoint
        :param data: data in the body of request
        :param partner: current partner calling the SmartBoard API
        :return: response_data
        """
        x_api_key = partner.x_api_key
        if not x_api_key:
            raise UserError(_(f'Missing x_api_key for partner {partner.name}'))
        payload = {
            "x-api-key": x_api_key,
            "data": data
        }

        # Call the API
        response_data = self.smartboard_api_request(endpoint, payload)

        if isinstance(response_data, Exception):
            raise UserError(_(response_data))

        return response_data
