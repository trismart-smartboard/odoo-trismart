from odoo import models, fields, api, _, Command


class SmartBoardProcessor(models.TransientModel):
    _name = 'smartboard.processor'
    _description = 'SmartBoard Processor'

    def parse_data(self, model, data):
        """
        :param model:
        :param data:
        :return:
        """
        ready_values = {}
        model = self.env['ir.model'].search([('model', '=', model)])
        for field_name, value in data.items():
            parsed_value = value
            field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', field_name)])
            field_type = field.ttype
            if not field_type:
                continue
            parse_method = f"parse_{field_type}_data"
            if hasattr(self, parse_method):
                try:
                    parsed_value = getattr(self, parse_method)(value, field)
                except Exception as e:
                    print(e)
            ready_values.update({field_name: parsed_value})
        return ready_values

    def parse_datetime_data(self, value, field=None):
        """

        :param value:
        :param field:
        :return:
        """
        return fields.Datetime.from_string(value)

    def parse_many2one_data(self, value, field):
        """

        :param value:
        :param field:
        :return:
        """
        related_model = field.relation
        if related_model == 'res.country.state':
            record = self.env[related_model].search([('code', '=', value)])
            return (record and record[0].id) or None
        if value['id'] is None:
            return
        record = self.env[related_model].search([('sb_id', '=', int(value['id']))])
        if not record:
            record = self.env[related_model].create({'sb_id': int(value['id']), 'name': value['name']})
        return record.id

    def parse_one2many_data(self, value, field):
        """

        :param value:
        :param field:
        :return:
        """
        related_model = field.relation
        records = []
        for val in value:
            new_record = self.env[related_model].create(val)
            records.append(Command.link(new_record.id))
        return records

    def parse_float_data(self, value, field):
        return (value and float(value)) or 0.0

    def parse_integer_data(self, value, field):
        return (value and int(value)) or 0
