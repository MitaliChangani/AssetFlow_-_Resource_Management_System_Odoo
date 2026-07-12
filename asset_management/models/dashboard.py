from odoo import models, fields, api
from odoo.exceptions import AccessError
from datetime import date, timedelta


class AmDashboard(models.AbstractModel):
    _name = 'am.dashboard'
    _description = 'Asset Management Dashboard'

    def _get_user_scope(self):
        """Determine what records the current user can see based on their role."""
        user = self.env.user
        if user.has_group('asset_management.group_admin') or \
           user.has_group('asset_management.group_asset_manager'):
            return 'all'

        try:
            employee = self.env['am.employee'].search([('user_id', '=', user.id)], limit=1)
        except AccessError:
            return 'own'

        if not employee:
            return 'own'

        if user.has_group('asset_management.group_dept_head'):
            return 'department'

        return 'own'

    def _get_employee(self):
        try:
            return self.env['am.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        except AccessError:
            return self.env['am.employee']

    def _get_asset_domain(self):
        scope = self._get_user_scope()
        domain = [('state', '!=', 'disposed')]
        if scope == 'own':
            employee = self._get_employee()
            if employee:
                domain.append(('department_id', '=', employee.department_id.id))
            else:
                domain.append(('id', '=', False))
        elif scope == 'department':
            employee = self._get_employee()
            if employee and employee.department_id:
                domain.append(('department_id', '=', employee.department_id.id))
        return domain

    def _get_allocation_domain(self):
        scope = self._get_user_scope()
        domain = [('state', '=', 'allocated')]
        if scope == 'own':
            domain.append(('employee_id.user_id', '=', self.env.user.id))
        elif scope == 'department':
            employee = self._get_employee()
            if employee and employee.department_id:
                domain.append(('employee_id.department_id', '=', employee.department_id.id))
        return domain

    def _get_booking_domain(self):
        scope = self._get_user_scope()
        domain = [('state', 'in', ('upcoming', 'ongoing'))]
        if scope == 'own':
            domain.append(('booked_by', '=', self.env.user.id))
        elif scope == 'department':
            employee = self._get_employee()
            if employee and employee.department_id:
                domain.append(('booked_by', 'in', employee.department_id.member_ids.mapped('user_id').ids))
        return domain

    def _get_maintenance_domain(self):
        scope = self._get_user_scope()
        domain = [('state', 'in', ('pending', 'approved', 'assigned', 'in_progress'))]
        if scope == 'own':
            domain.append(('requested_by', '=', self.env.user.id))
        elif scope == 'department':
            employee = self._get_employee()
            if employee and employee.department_id:
                domain.append(('employee_id.department_id', '=', employee.department_id.id))
        return domain

    def _get_transfer_domain(self):
        scope = self._get_user_scope()
        domain = [('state', '=', 'requested')]
        if scope == 'own':
            domain.append(('requested_by', '=', self.env.user.id))
        elif scope == 'department':
            employee = self._get_employee()
            if employee and employee.department_id:
                domain.append(('current_holder_id.department_id', '=', employee.department_id.id))
        return domain

    @api.model
    def get_kpis(self):
        zero = {
            'available_count': 0,
            'allocated_count': 0,
            'maintenance_today': 0,
            'active_bookings': 0,
            'pending_transfers': 0,
            'upcoming_returns': 0,
            'overdue_returns': 0,
        }

        try:
            Asset = self.env['asset.asset']
            Allocation = self.env['asset.allocation']
            Booking = self.env['resource.booking']
            Transfer = self.env['asset.transfer']

            asset_domain = self._get_asset_domain()
            all_assets = Asset.search(asset_domain)

            available_count = len(all_assets.filtered(lambda a: a.state == 'available'))
            allocated_count = len(all_assets.filtered(lambda a: a.state == 'allocated'))
            maintenance_today = Asset.search_count([('state', '=', 'maintenance')])

            booking_domain = self._get_booking_domain()
            active_bookings = Booking.search_count(booking_domain)

            transfer_domain = self._get_transfer_domain()
            pending_transfers = Transfer.search_count(transfer_domain)

            today = date.today()
            week_end = today + timedelta(days=7)
            upcoming_domain = self._get_allocation_domain() + [
                ('expected_return_date', '>=', today),
                ('expected_return_date', '<=', week_end),
            ]
            upcoming_returns = Allocation.search_count(upcoming_domain)

            overdue_domain = self._get_allocation_domain() + [
                ('state', '=', 'allocated'),
                ('expected_return_date', '<', today),
            ]
            overdue_returns = Allocation.search_count(overdue_domain)

            return {
                'available_count': available_count,
                'allocated_count': allocated_count,
                'maintenance_today': maintenance_today,
                'active_bookings': active_bookings,
                'pending_transfers': pending_transfers,
                'upcoming_returns': upcoming_returns,
                'overdue_returns': overdue_returns,
            }
        except AccessError:
            return zero
