from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class ResourceBooking(models.Model):
    _name = 'resource.booking'
    _description = 'Resource Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='/')
    asset_id = fields.Many2one('asset.asset', string='Resource', required=True,
        domain=[('is_bookable', '=', True)], tracking=True)
    booked_by = fields.Many2one('res.users', string='Booked By',
        default=lambda self: self.env.user, required=True, tracking=True)
    start_datetime = fields.Datetime(string='Start', required=True, tracking=True)
    stop_datetime = fields.Datetime(string='End', required=True, tracking=True)
    purpose = fields.Char(string='Purpose')
    state = fields.Selection([
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='upcoming', required=True, tracking=True, copy=False)

    asset_tag = fields.Char(related='asset_id.asset_tag', store=True)

    @api.constrains('asset_id', 'start_datetime', 'stop_datetime', 'state')
    def _check_overlap(self):
        for booking in self:
            if booking.state == 'cancelled':
                continue
            if not booking.start_datetime or not booking.stop_datetime:
                continue
            if booking.start_datetime >= booking.stop_datetime:
                raise ValidationError(_('End time must be after start time.'))
            # Find overlapping bookings for the same resource
            domain = [
                ('asset_id', '=', booking.asset_id.id),
                ('state', 'in', ('upcoming', 'ongoing')),
                ('id', '!=', booking.id),
                ('start_datetime', '<', booking.stop_datetime),
                ('stop_datetime', '>', booking.start_datetime),
            ]
            conflict = self.search(domain, limit=1)
            if conflict:
                raise ValidationError(_(
                    'Booking overlaps with an existing booking for "%(asset)s":\n'
                    '%(conflict_start)s → %(conflict_end)s (by %(user)s)',
                    asset=booking.asset_id.name,
                    conflict_start=conflict.start_datetime,
                    conflict_end=conflict.stop_datetime,
                    user=conflict.booked_by.name,
                ))

    @api.depends('asset_id', 'start_datetime', 'stop_datetime')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.asset_id.name} ({rec.start_datetime} - {rec.stop_datetime})'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('resource.booking') or '/'
        bookings = super().create(vals_list)
        for b in bookings:
            b.message_post(body=f'Booking confirmed by {b.booked_by.name}')
        return bookings

    def action_cancel(self):
        self.ensure_one()
        if self.state not in ('upcoming',):
            raise ValidationError(_('Only upcoming bookings can be cancelled.'))
        if self.booked_by != self.env.user and not self.env.user.has_group('asset_management.group_asset_manager'):
            raise ValidationError(_('You can only cancel your own bookings.'))
        self.write({'state': 'cancelled'})
        self.message_post(body='Booking cancelled')

    def action_reschedule(self):
        """Open form to modify booking times."""
        self.ensure_one()
        if self.state not in ('upcoming',):
            raise ValidationError(_('Only upcoming bookings can be rescheduled.'))
        return {
            'name': _('Reschedule Booking'),
            'type': 'ir.actions.act_window',
            'res_model': 'resource.booking',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    @api.model
    def _cron_update_booking_states(self):
        """Scheduled action: update booking states based on current time."""
        now = fields.Datetime.now()
        # upcoming → ongoing
        upcoming = self.search([
            ('state', '=', 'upcoming'),
            ('start_datetime', '<=', now),
            ('stop_datetime', '>', now),
        ])
        for b in upcoming:
            b.write({'state': 'ongoing'})
            b.message_post(body='Booking is now ongoing')

        # ongoing → completed
        ongoing = self.search([
            ('state', '=', 'ongoing'),
            ('stop_datetime', '<=', now),
        ])
        for b in ongoing:
            b.write({'state': 'completed'})
            b.message_post(body='Booking completed')

        # upcoming → completed (if start and end both in the past, missed by cron)
        missed = self.search([
            ('state', '=', 'upcoming'),
            ('stop_datetime', '<=', now),
        ])
        for b in missed:
            b.write({'state': 'completed'})

    @api.model
    def _cron_send_reminders(self):
        """Send reminders 30 minutes before booking starts."""
        now = fields.Datetime.now()
        reminder_window = now + timedelta(minutes=30)
        upcoming = self.search([
            ('state', '=', 'upcoming'),
            ('start_datetime', '>', now),
            ('start_datetime', '<=', reminder_window),
        ])
        for b in upcoming:
            # Check if reminder was already sent
            recent = b.message_ids.filtered(
                lambda m: 'reminder' in (m.body or '').lower() and
                (now - m.date).total_seconds() < 3600
            )
            if not recent:
                b.message_post(
                    body=f'🔔 Reminder: Booking starts at {b.start_datetime}',
                    subtype_xmlid='mail.mt_comment',
                )
                b.activity_schedule(
                    activity_type_id=self.env.ref('asset_management.mail_activity_data_booking_reminder').id,
                    user_id=b.booked_by.id,
                    summary=f'Booking reminder: {b.asset_id.name}',
                    note=f'Your booking starts at {b.start_datetime}',
                )
