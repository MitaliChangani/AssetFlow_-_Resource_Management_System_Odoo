from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssetAuditCycle(models.Model):
    _name = 'asset.audit.cycle'
    _description = 'Asset Audit Cycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', readonly=True, copy=False, default='/')
    scope_type = fields.Selection([
        ('department', 'Department'),
        ('location', 'Location'),
    ], string='Scope Type', default='department', required=True)
    department_id = fields.Many2one('am.department', string='Department',
        help='Audit scope: all assets in this department')
    location = fields.Char(string='Location',
        help='Audit scope: all assets at this location')
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    auditor_ids = fields.Many2many('res.users', string='Auditors', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('asset.audit.line', 'cycle_id', string='Audit Lines')
    total_lines = fields.Integer(compute='_compute_line_stats', store=True)
    verified_count = fields.Integer(compute='_compute_line_stats', store=True)
    missing_count = fields.Integer(compute='_compute_line_stats', store=True)
    damaged_count = fields.Integer(compute='_compute_line_stats', store=True)
    discrepancy_count = fields.Integer(compute='_compute_line_stats', store=True)
    line_ids_completed = fields.Boolean(compute='_compute_lines_completed', store=True)

    @api.depends('line_ids.result')
    def _compute_line_stats(self):
        for cycle in self:
            lines = cycle.line_ids
            cycle.total_lines = len(lines)
            cycle.verified_count = len(lines.filtered(lambda l: l.result == 'verified'))
            cycle.missing_count = len(lines.filtered(lambda l: l.result == 'missing'))
            cycle.damaged_count = len(lines.filtered(lambda l: l.result == 'damaged'))
            cycle.discrepancy_count = len(lines.filtered(lambda l: l.result in ('missing', 'damaged')))

    @api.depends('line_ids', 'line_ids.result')
    def _compute_lines_completed(self):
        for cycle in self:
            pending = cycle.line_ids.filtered(lambda l: not l.result)
            cycle.line_ids_completed = len(pending) == 0 and len(cycle.line_ids) > 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', '/') == '/':
                vals['reference'] = self.env['ir.sequence'].next_by_code('asset.audit.cycle') or '/'
        return super().create(vals_list)

    def action_start(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can start audit cycles.'))
        if self.state != 'draft':
            raise ValidationError(_('Only draft cycles can be started.'))

        # Auto-generate audit lines for in-scope assets
        Asset = self.env['asset.asset']
        domain = [('state', '!=', 'disposed')]
        if self.scope_type == 'department' and self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        elif self.scope_type == 'location' and self.location:
            domain.append(('location', 'ilike', self.location))

        assets = Asset.search(domain)
        if not assets:
            raise ValidationError(_('No assets found in the specified scope.'))

        lines = []
        for asset in assets:
            lines.append({
                'cycle_id': self.id,
                'asset_id': asset.id,
            })
        self.env['asset.audit.line'].create(lines)
        self.write({'state': 'in_progress'})
        self.message_post(body=f'Audit cycle started. {len(assets)} assets to audit.')

    def action_close(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_asset_manager') and \
           not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Asset Managers or Admins can close audit cycles.'))
        if self.state != 'in_progress':
            raise ValidationError(_('Only in-progress cycles can be closed.'))

        # Check all lines have results
        pending = self.line_ids.filtered(lambda l: not l.result)
        if pending:
            raise ValidationError(_(
                'Cannot close: %(count)d line(s) still need results.',
                count=len(pending),
            ))

        self.write({'state': 'closed'})

        # Auto-generate discrepancy report via chatter
        discrepancies = self.line_ids.filtered(lambda l: l.result in ('missing', 'damaged'))
        if discrepancies:
            report_lines = []
            for line in discrepancies:
                report_lines.append(
                    f'• {line.asset_id.asset_tag} - {line.asset_id.name}: '
                    f'{line.result.upper()} {line.notes or ""}'
                )
            report_body = '<br/>'.join(report_lines)
            self.message_post(
                body=f'<strong>Audit Discrepancy Report:</strong><br/>{report_body}',
                subtype_xmlid='mail.mt_comment',
            )

        # Bulk-update missing assets to lost
        missing_lines = self.line_ids.filtered(lambda l: l.result == 'missing')
        for line in missing_lines:
            line.asset_id.write({'state': 'lost'})
            line.asset_id.message_post(
                body=f'Asset marked as LOST during audit cycle "{self.name}" by auditor {line.auditor_id.name}'
            )

        self.message_post(body='Audit cycle closed.')


class AssetAuditLine(models.Model):
    _name = 'asset.audit.line'
    _description = 'Asset Audit Line'
    _order = 'cycle_id, asset_id'

    cycle_id = fields.Many2one('asset.audit.cycle', string='Audit Cycle', required=True, ondelete='cascade')
    asset_id = fields.Many2one('asset.asset', string='Asset', required=True)
    result = fields.Selection([
        ('verified', 'Verified'),
        ('missing', 'Missing'),
        ('damaged', 'Damaged'),
    ], string='Result')
    notes = fields.Text(string='Notes')
    auditor_id = fields.Many2one('res.users', string='Auditor',
        default=lambda self: self.env.user)

    asset_tag = fields.Char(related='asset_id.asset_tag', store=True)
    asset_state = fields.Selection(related='asset_id.state', store=True)
    cycle_state = fields.Selection(related='cycle_id.state', store=True)

    def action_verify(self):
        self.ensure_one()
        if self.cycle_id.state != 'in_progress':
            raise ValidationError(_('Audit cycle must be in progress.'))
        self.write({'result': 'verified'})
        self.cycle_id.message_post(body=f'{self.asset_id.asset_tag} verified by {self.auditor_id.name}')

    def action_missing(self):
        self.ensure_one()
        if self.cycle_id.state != 'in_progress':
            raise ValidationError(_('Audit cycle must be in progress.'))
        self.write({'result': 'missing'})
        self.cycle_id.message_post(body=f'{self.asset_id.asset_tag} marked as MISSING')

    def action_damaged(self):
        self.ensure_one()
        if self.cycle_id.state != 'in_progress':
            raise ValidationError(_('Audit cycle must be in progress.'))
        self.write({'result': 'damaged'})
        self.cycle_id.message_post(body=f'{self.asset_id.asset_tag} marked as DAMAGED')
