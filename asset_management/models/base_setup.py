from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AmDepartment(models.Model):
    _name = 'am.department'
    _description = 'Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(required=True, tracking=True)
    complete_name = fields.Char(string='Full Name', compute='_compute_complete_name', store=True, recursive=True)
    parent_id = fields.Many2one('am.department', string='Parent Department', index=True, ondelete='restrict')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('am.department', 'parent_id', string='Child Departments')
    head_user_id = fields.Many2one('res.users', string='Department Head', tracking=True)
    member_ids = fields.One2many('am.employee', 'department_id', string='Members')
    active = fields.Boolean(default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for dept in self:
            if dept.parent_id:
                dept.complete_name = f'{dept.parent_id.complete_name} / {dept.name}'
            else:
                dept.complete_name = dept.name

    def action_archive(self):
        return self.write({'active': False})

    def action_unarchive(self):
        return self.write({'active': True})


class AmCategory(models.Model):
    _name = 'am.category'
    _description = 'Asset Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    # Category-specific fields (conditionally shown in views via Odoo 19 visibility)
    warranty_period_months = fields.Integer(string='Warranty Period (Months)', default=0,
        help='Default warranty period for assets in this category (used for Electronics)')
    default_condition = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Default Condition', default='new')
    active = fields.Boolean(default=True)
    asset_ids = fields.One2many('asset.asset', 'category_id', string='Assets')

    def action_archive(self):
        return self.write({'active': False})

    def action_unarchive(self):
        return self.write({'active': True})


class AmEmployee(models.Model):
    _name = 'am.employee'
    _description = 'Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    user_id = fields.Many2one('res.users', string='User Account', required=True, ondelete='restrict', tracking=True)
    email = fields.Char(related='user_id.login', string='Email', readonly=True)
    department_id = fields.Many2one('am.department', string='Department', tracking=True)
    role = fields.Selection([
        ('employee', 'Employee'),
        ('dept_head', 'Department Head'),
        ('asset_manager', 'Asset Manager'),
        ('admin', 'Admin'),
    ], string='Role', default='employee', required=True, tracking=True, readonly=True)
    job_title = fields.Char(string='Job Title')
    phone = fields.Char()
    image_128 = fields.Image(string='Photo', max_width=128, max_height=128)
    active = fields.Boolean(default=True)

    _unique_user_constraint = models.Constraint(
        'UNIQUE(user_id)',
        'Each user can only be linked to one employee record.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_user_groups()
        return records

    def action_promote_dept_head(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Admins can promote employees.'))
        self.write({'role': 'dept_head'})
        self._sync_user_groups()
        self.message_post(body=f'{self.name} promoted to Department Head')

    def action_promote_asset_manager(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Admins can promote employees.'))
        self.write({'role': 'asset_manager'})
        self._sync_user_groups()
        self.message_post(body=f'{self.name} promoted to Asset Manager')

    def action_promote_admin(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Admins can promote to Admin.'))
        self.write({'role': 'admin'})
        self._sync_user_groups()
        self.message_post(body=f'{self.name} promoted to Admin')

    def action_revoke_role(self):
        self.ensure_one()
        if not self.env.user.has_group('asset_management.group_admin'):
            raise ValidationError(_('Only Admins can revoke roles.'))
        if self.user_id == self.env.user:
            raise ValidationError(_('You cannot revoke your own admin role.'))
        self.write({'role': 'employee'})
        self._sync_user_groups()
        self.message_post(body=f'{self.name} role revoked to Employee')

    def _sync_user_groups(self):
        """Sync the role field to actual Odoo group membership on the linked user."""
        group_xmlids = {
            'employee': 'asset_management.group_employee',
            'dept_head': 'asset_management.group_dept_head',
            'asset_manager': 'asset_management.group_asset_manager',
            'admin': 'asset_management.group_admin',
        }
        all_groups = []
        for xmlid in group_xmlids.values():
            grp = self.env.ref(xmlid, raise_if_not_found=False)
            if grp:
                all_groups.append(grp)

        for emp in self:
            if not emp.user_id:
                continue
            target_xmlid = group_xmlids.get(emp.role, group_xmlids['employee'])
            target_group = self.env.ref(target_xmlid, raise_if_not_found=False)
            # Remove from all asset_management role groups
            for g in all_groups:
                if g in emp.user_id.group_ids:
                    emp.user_id.write({'group_ids': [(3, g.id)]})
            # Add to the target group
            if target_group and target_group not in emp.user_id.group_ids:
                emp.user_id.write({'group_ids': [(4, target_group.id)]})

    def action_archive(self):
        return self.write({'active': False})

    def action_unarchive(self):
        return self.write({'active': True})


class ResUsers(models.Model):
    _inherit = 'res.users'

    employee_ids = fields.One2many('am.employee', 'user_id', string='Employee Records')
    am_role = fields.Selection([
        ('employee', 'Employee'),
        ('dept_head', 'Department Head'),
        ('asset_manager', 'Asset Manager'),
        ('admin', 'Admin'),
    ], string='Asset Management Role', compute='_compute_am_role', store=True)

    @api.depends('employee_ids.role')
    def _compute_am_role(self):
        for user in self:
            emp = user.employee_ids[:1]
            user.am_role = emp.role if emp else 'employee'
