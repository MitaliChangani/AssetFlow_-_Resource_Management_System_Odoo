from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AmMaintenanceRequest(models.Model):
    # Renamed from 'maintenance.request' to avoid collision with Odoo core's
    # maintenance module model of the same name.
    _name = 'am.maintenance.request'
    _description = 'Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='/')
    asset_id = fields.Many2one('asset.asset', string='Asset', required=True, tracking=True)
    description = fields.Text(string='Description', required=True, tracking=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Priority', default='medium', required=True, tracking=True)
    photo = fields.Image(string='Photo', max_width=1024, max_height=1024)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], string='Status', default='pending', required=True, tracking=True, copy=False)

    requested_by = fields.Many2one('res.users', string='Requested By',
        default=lambda self: self.env.user, required=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    technician_id = fields.Many2one('am.employee', string='Assigned Technician', tracking=True)
    employee_id = fields.Many2one('am.employee', string='Requested By (Employee)',
        compute='_compute_employee_id', store=True)

    asset_tag = fields.Char(related='asset_id.asset_tag', store=True)

    @api.depends('requested_by')
    def _compute_employee_id(self):
        for req in self:
            emp = self.env['am.employee'].search([('user_id', '=', req.requested_by.id)], limit=1)
            req.employee_id = emp

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('am.maintenance.request') or '/'
        requests = super().create(vals_list)
        for r in requests:
            r.message_post(body=f'Maintenance request created by {r.requested_by.name}')
        return requests

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can approve maintenance requests.'))
        if self.state != 'pending':
            raise ValidationError(_('Only pending requests can be approved.'))
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
        })
        self.asset_id.write({'state': 'maintenance'})
        self.message_post(body=f'Maintenance approved by {self.env.user.name}')
        self.asset_id.message_post(body=f'Maintenance approved for this asset by {self.env.user.name}')

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can reject maintenance requests.'))
        if self.state != 'pending':
            raise ValidationError(_('Only pending requests can be rejected.'))
        self.write({'state': 'rejected'})
        self.message_post(body=f'Maintenance rejected by {self.env.user.name}')

    def action_assign_technician(self, technician_id):
        """Assign a technician. Called from the form."""
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can assign technicians.'))
        self.write({
            'state': 'assigned',
            'technician_id': technician_id,
        })
        tech_name = self.env['am.employee'].browse(technician_id).name
        self.message_post(body=f'Technician assigned: {tech_name}')

    def action_start_work(self):
        self.ensure_one()
        if self.state != 'assigned':
            raise ValidationError(_('Only assigned requests can be started.'))
        if self.technician_id.user_id != self.env.user and \
           not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only the assigned technician or managers can start work.'))
        self.write({'state': 'in_progress'})
        self.message_post(body='Maintenance work started')

    def action_resolve(self):
        self.ensure_one()
        if self.state not in ('assigned', 'in_progress'):
            raise ValidationError(_('Only assigned or in-progress requests can be resolved.'))
        if self.technician_id.user_id != self.env.user and \
           not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only the assigned technician or managers can resolve.'))
        self.write({'state': 'resolved'})
        self.message_post(body='Maintenance request resolved')

        # Auto-transition asset back to available (unless other open requests exist)
        open_requests = self.search([
            ('asset_id', '=', self.asset_id.id),
            ('state', 'in', ('pending', 'approved', 'assigned', 'in_progress')),
            ('id', '!=', self.id),
        ])
        if not open_requests:
            active_alloc = self.env['asset.allocation'].search([
                ('asset_id', '=', self.asset_id.id),
                ('state', '=', 'allocated'),
            ], limit=1)
            if active_alloc:
                self.asset_id.write({'state': 'allocated'})
            else:
                self.asset_id.write({'state': 'available'})
        self.asset_id.message_post(body='Maintenance resolved for this asset')
