from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssetTransfer(models.Model):
    _name = 'asset.transfer'
    _description = 'Asset Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='/')
    asset_id = fields.Many2one('asset.asset', string='Asset', required=True, tracking=True)
    current_holder_id = fields.Many2one('am.employee', string='Current Holder',
        related='asset_id.current_holder_id', store=True)
    requested_by = fields.Many2one('res.users', string='Requested By',
        default=lambda self: self.env.user, required=True, tracking=True)
    requested_to = fields.Many2one('am.employee', string='Transfer To', required=True, tracking=True)
    reason = fields.Text(string='Reason for Transfer')
    state = fields.Selection([
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], string='Status', default='requested', required=True, tracking=True, copy=False)

    asset_tag = fields.Char(related='asset_id.asset_tag', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.transfer') or '/'
        transfers = super().create(vals_list)
        for t in transfers:
            t.message_post(body=f'Transfer requested by {t.requested_by.name} to {t.requested_to.name}')
        return transfers

    def _check_can_approve(self):
        """Only Asset Manager or the relevant Department Head can approve."""
        self.ensure_one()
        user = self.env.user
        is_asset_manager = user.has_group('asset_management.group_asset_manager')
        is_dept_head = (
            self.current_holder_id and
            self.current_holder_id.department_id and
            self.current_holder_id.department_id.head_user_id == user
        )
        is_admin = user.has_group('asset_management.group_admin')
        if not (is_asset_manager or is_dept_head or is_admin):
            raise ValidationError(_('Only Asset Managers, the relevant Department Head, or Admins can approve transfers.'))

    def action_approve(self):
        for t in self:
            t._check_can_approve()
            if t.state != 'requested':
                raise ValidationError(_('Only requested transfers can be approved.'))

            Asset = self.env['asset.asset']
            Allocation = self.env['asset.allocation']

            # Close the old allocation
            old_allocation = t.asset_id.allocation_ids.filtered(
                lambda a: a.state == 'allocated'
            )[:1]
            if old_allocation:
                old_allocation.write({
                    'state': 'returned',
                    'actual_return_date': fields.Date.context_today(self),
                    'return_condition_notes': 'Transferred to another employee',
                })

            # Update asset state to available BEFORE creating new allocation
            # (avoids the conflict check in Allocation.create)
            t.asset_id.with_context(_skip_allocation_check=True).write({
                'state': 'available',
                'current_holder_id': False,
            })

            # Create new allocation for the new holder
            new_alloc = Allocation.create({
                'asset_id': t.asset_id.id,
                'employee_id': t.requested_to.id,
                'allocated_date': fields.Date.context_today(self),
                'expected_return_date': old_allocation.expected_return_date if old_allocation else False,
            })

            t.write({'state': 'completed'})
            t.message_post(body=f'Transfer approved and completed. Asset now held by {t.requested_to.name}')
            t.asset_id.message_post(body=f'Asset transferred to {t.requested_to.name}')

    def action_reject(self):
        for t in self:
            t._check_can_approve()
            if t.state != 'requested':
                raise ValidationError(_('Only requested transfers can be rejected.'))
            t.write({'state': 'rejected'})
            t.message_post(body=f'Transfer rejected by {self.env.user.name}')
