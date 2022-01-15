from odoo import api, fields, models, tools

class Project(models.Model):
    _inherit = "project.project"

    sb_lead_id = fields.Integer(string='Smartboard Lead ID', readonly=True)

    def create_project_from_template(self, sb_lead_id=None):
        if sb_lead_id:
            new_project = self.copy(
                default={"name": 'SBLead-' + str(sb_lead_id), 'sb_lead_id': sb_lead_id, "active": True, "alias_name": False}
            )
            if new_project.subtask_project_id != new_project:
                new_project.subtask_project_id = new_project.id

            # SINCE THE END DATE DOESN'T COPY OVER ON TASKS
            # (Even when changed to copy=true), POPULATE END DATES ON THE TASK
            for new_task_record in new_project.task_ids:
                for old_task_record in self.task_ids:
                    if new_task_record.name == old_task_record.name:
                        new_task_record.date_end = old_task_record.date_end

            # OPEN THE NEWLY CREATED PROJECT FORM
            return {
                "view_type": "form",
                "view_mode": "form",
                "res_model": "project.project",
                "target": "current",
                "res_id": new_project.id,
                "type": "ir.actions.act_window",
            }
        else:
            return super(Project, self).create_project_from_template()

