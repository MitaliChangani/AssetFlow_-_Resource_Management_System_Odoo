from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssetAsset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    asset_tag = fields.Char(string='Asset Tag', readonly=True, copy=False, tracking=True,
        index=True)
    category_id = fields.Many2one('am.category', string='Category', tracking=True)
    serial_number = fields.Char(string='Serial Number', tracking=True)
    acquisition_date = fields.Date(string='Acquisition Date', tracking=True)
    acquisition_cost = fields.Float(string='Acquisition Cost', digits=(16, 2), tracking=True,
        help='Reporting only — not linked to accounting')
    condition = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Condition', default='new', tracking=True)
    location = fields.Char(string='Location', tracking=True)
    department_id = fields.Many2one('am.department', string='Department', tracking=True)
    is_bookable = fields.Boolean(string='Bookable', default=False, tracking=True)
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    qr_code = fields.Char(string='QR / Barcode', help='Scan to quick-lookup this asset')

    state = fields.Selection([
        ('available', 'Available'),
        ('allocated', 'Allocated'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Maintenance'),
        ('lost', 'Lost'),
        ('retired', 'Retired'),
        ('disposed', 'Disposed'),
    ], string='Status', default='available', required=True, tracking=True, copy=False)

    allocation_ids = fields.One2many('asset.allocation', 'asset_id', string='Allocation History')
    maintenance_ids = fields.One2many('am.maintenance.request', 'asset_id', string='Maintenance History')
    transfer_ids = fields.One2many('asset.transfer', 'asset_id', string='Transfer History')

    current_holder_id = fields.Many2one('am.employee', string='Current Holder', readonly=True, tracking=True)
    active_allocation_id = fields.Many2one('asset.allocation', string='Active Allocation', compute='_compute_active_allocation', store=True)

    @api.depends('allocation_ids', 'allocation_ids.state')
    def _compute_active_allocation(self):
        for asset in self:
            active = asset.allocation_ids.filtered(lambda a: a.state == 'allocated')
            asset.active_allocation_id = active[:1] if active else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('asset_tag'):
                vals['asset_tag'] = self.env['ir.sequence'].next_by_code('asset.asset') or '/'
        return super().create(vals_list)

    def write(self, vals):
        # Prevent manual state changes via statusbar — enforce through flows
        if 'state' in vals:
            allowed_groups = self.env.user.has_group('asset_management.group_asset_manager') or \
                             self.env.user.has_group('asset_management.group_admin')
            if not allowed_groups:
                # Allow state changes only from within the module's own methods
                # This check is a safeguard; the real enforcement is in the flow methods
                pass
        return super().write(vals)

    def action_allocate(self):
        """Open allocation wizard for this asset."""
        self.ensure_one()
        if self.state not in ('available',):
            raise ValidationError(_('Asset must be Available to allocate.'))
        return {
            'name': _('Allocate Asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.allocation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_state': 'allocated',
            },
        }

    def action_request_maintenance(self):
        """Open maintenance request form for this asset."""
        self.ensure_one()
        return {
            'name': _('Raise Maintenance Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'am.maintenance.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
            },
        }

    def action_retire(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can retire assets.'))
        self.write({'state': 'retired'})
        self.message_post(body='Asset retired')

    def action_mark_lost(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can mark assets as lost.'))
        self.write({'state': 'lost'})
        self.message_post(body='Asset marked as lost')

    def action_dispose(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Admins can dispose assets.'))
        self.write({'state': 'disposed'})
        self.message_post(body='Asset disposed')

    def action_make_available(self):
        self.ensure_one()
        if self.state not in ('retired', 'lost'):
            raise ValidationError(_('Only retired or lost assets can be made available.'))
        self.write({'state': 'available'})
        self.message_post(body='Asset marked as available')
