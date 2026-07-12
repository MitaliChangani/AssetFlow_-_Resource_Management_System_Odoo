from odoo import fields, models, _


class WizReturnCondition(models.TransientModel):
    _name = 'wiz.return.condition'
    _description = 'Return Condition Wizard'

    allocation_id = fields.Many2one('asset.allocation', string='Allocation', required=True)
    condition = fields.Selection([
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('damaged', 'Damaged'),
    ], string='Condition', required=True, default='good')
    notes = fields.Text(string='Condition Notes')

    def action_confirm(self):
        self.ensure_one()
        self.allocation_id.action_confirm_return(
            condition=self.condition,
            notes=self.notes,
        )
        return {'type': 'ir.actions.act_window_close'}
