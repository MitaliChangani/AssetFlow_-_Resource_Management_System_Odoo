from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date


class AssetAllocation(models.Model):
    _name = 'asset.allocation'
    _description = 'Asset Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='/')
    asset_id = fields.Many2one('asset.asset', string='Asset', required=True, tracking=True)
    employee_id = fields.Many2one('am.employee', string='Allocated To', required=True, tracking=True)
    department_id = fields.Many2one('am.department', string='Department',
        related='employee_id.department_id', store=True)
    allocated_date = fields.Date(string='Allocation Date', default=fields.Date.context_today, tracking=True)
    expected_return_date = fields.Date(string='Expected Return Date', tracking=True)
    actual_return_date = fields.Date(string='Actual Return Date', tracking=True)
    return_condition_notes = fields.Text(string='Return Condition Notes')
    return_condition = fields.Selection([
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('damaged', 'Damaged'),
    ], string='Return Condition')

    state = fields.Selection([
        ('allocated', 'Allocated'),
        ('returned', 'Returned'),
    ], string='Status', default='allocated', required=True, tracking=True, copy=False)

    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True)
    asset_tag = fields.Char(related='asset_id.asset_tag', store=True)

    @api.depends('state', 'expected_return_date', 'actual_return_date')
    def _compute_is_overdue(self):
        today = date.today()
        for alloc in self:
            alloc.is_overdue = (
                alloc.state == 'allocated' and
                alloc.expected_return_date and
                alloc.expected_return_date < today and
                not alloc.actual_return_date
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.allocation') or '/'

            # Skip conflict check if called internally (e.g., transfer approval)
            if self.env.context.get('_skip_allocation_check'):
                continue

            asset = self.env['asset.asset'].browse(vals.get('asset_id'))
            if asset:
                # Conflict check: block if asset already has an active allocation
                if asset.state == 'allocated':
                    holder = asset.current_holder_id
                    holder_name = holder.name if holder else 'another user'
                    raise ValidationError(_(
                        'Cannot allocate asset "%(asset)s": it is currently held by %(holder)s.\n'
                        'Please request a transfer instead.',
                        asset=asset.name,
                        holder=holder_name,
                    ))
                if asset.state not in ('available',):
                    raise ValidationError(_(
                        'Asset "%(asset)s" is not available for allocation (current state: %(state)s).',
                        asset=asset.name,
                        state=asset.state,
                    ))
        allocations = super().create(vals_list)
        for alloc in allocations:
            # Update asset state and holder
            alloc.asset_id.write({
                'state': 'allocated',
                'current_holder_id': alloc.employee_id.id,
            })
            alloc.message_post(body=f'Asset allocated to {alloc.employee_id.name}')
        return allocations

    def action_return(self):
        """Open return dialog."""
        self.ensure_one()
        if self.state != 'allocated':
            raise ValidationError(_('Only active allocations can be returned.'))
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin') and \
           self.employee_id.user_id != self.env.user:
            raise ValidationError(_('You can only return your own allocations.'))
        return {
            'name': _('Return Asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'wiz.return.condition',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_allocation_id': self.id,
            },
        }

    def action_confirm_return(self, condition='good', notes=''):
        """Called by the return wizard to confirm return."""
        self.ensure_one()
        self.write({
            'state': 'returned',
            'actual_return_date': date.today(),
            'return_condition': condition,
            'return_condition_notes': notes,
        })
        # Determine next state for asset
        open_maintenance = self.env['am.maintenance.request'].search([
            ('asset_id', '=', self.asset_id.id),
            ('state', 'in', ('pending', 'approved', 'assigned', 'in_progress')),
        ], limit=1)
        if open_maintenance:
            self.asset_id.write({'state': 'maintenance'})
        else:
            self.asset_id.write({
                'state': 'available',
                'current_holder_id': False,
            })
        self.message_post(body=f'Asset returned by {self.employee_id.name}. Condition: {condition}')

    def _cron_mark_overdue(self):
        """Scheduled action: send notifications for newly-overdue allocations."""
        today = date.today()
        overdue = self.search([
            ('state', '=', 'allocated'),
            ('expected_return_date', '<', today),
            ('actual_return_date', '=', False),
        ])
        for alloc in overdue:
            recent_messages = alloc.message_ids.filtered(
                lambda m: 'overdue' in (m.body or '').lower() and
                m.date.date() == today
            )
            if not recent_messages:
                alloc.message_post(
                    body=f'⚠️ Allocation is OVERDUE. Expected return: {alloc.expected_return_date}',
                    subtype_xmlid='mail.mt_note',
                )
                if alloc.employee_id.user_id:
                    alloc.activity_schedule(
                        activity_type_id=self.env.ref('asset_management.mail_activity_data_overdue_return').id,
                        user_id=alloc.employee_id.user_id.id,
                        summary=f'Overdue return: {alloc.asset_id.name}',
                        note=f'Asset {alloc.asset_id.asset_tag} was due on {alloc.expected_return_date}. Please return it as soon as possible.',
                    )
