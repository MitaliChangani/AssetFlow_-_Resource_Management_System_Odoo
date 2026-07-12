# Asset Management System - Odoo 19 CE

Full-featured asset lifecycle management module for Odoo 19 Community Edition.

---

## Table of Contents

1. [Module Overview](#module-overview)
2. [Installation](#installation)
3. [User Roles & Access Rights](#user-roles--access-rights)
4. [Features](#features)
5. [Models & Fields](#models--fields)
6. [Workflows](#workflows)
7. [Menu Structure](#menu-structure)
8. [Dashboard](#dashboard)
9. [Testing Guide](#testing-guide)
10. [Database Seed Data](#database-seed-data)

---

## Module Overview

| Detail | Value |
|---|---|
| Module Name | `asset_management` |
| Version | 19.0.1.0.0 |
| Depends | `mail`, `resource` |
| License | LGPL-3 |
| Category | Inventory/Inventory |

---

## Installation

1. Place the `asset_management` folder in your Odoo addons path
2. Update the module list: **Settings > Activate the developer mode > Update Apps List**
3. Search for **Asset Management** and click **Install**

---

## User Roles & Access Rights

### Role Hierarchy

```
Asset Admin (group_admin)
├── implies: group_dept_head
├── implies: group_asset_manager
└── implies: group_employee

Asset Manager (group_asset_manager)
└── implies: group_employee

Department Head (group_dept_head)
└── implies: group_employee

Employee (group_employee)
└── base level
```

### Access Matrix

| Feature | Employee | Dept Head | Asset Manager | Asset Admin |
|---|---|---|---|---|
| **Dashboard** | View (own dept) | View (own dept) | View (all) | View (all) |
| **Assets** | Read only | Read + Write | Full CRUD | Full CRUD |
| **Asset Create** | No | No | Yes | Yes |
| **Asset Delete** | No | No | No | Yes |
| **Allocations** | Create + Read | Create + Read | Full CRUD | Full CRUD |
| **Transfers** | Create + Read | Create + Read | Full CRUD | Full CRUD |
| **Bookings** | Create + Read | Create + Read | Full CRUD | Full CRUD |
| **Maintenance** | Create + Read | Create + Read | Full CRUD | Full CRUD |
| **Audit** | No access | No access | Full CRUD | Full CRUD |
| **Reports** | View all | View all | View all | View all |
| **Organization Setup** | No access | No access | No access | Admin only |
| **Employee Directory** | No access | No access | Full access | Full access |
| **Activity Log** | No access | No access | No access | Admin only |
| **Promote Users** | No | No | No | Yes |
| **Revoke Roles** | No | No | No | Yes (others only) |

---

## Features

### 1. Asset Management

- Register assets with categories, serial numbers, QR codes
- Track asset lifecycle: Available → Allocated → Maintenance → Disposed
- Asset condition tracking: New, Good, Fair, Poor
- Asset location tracking
- Department-wise asset assignment
- Current holder tracking
- Acquisition date and cost tracking
- Bookable flag for resource booking

### 2. Asset Categories

- Categorize assets (Laptops, Desktops, Monitors, etc.)
- Default warranty period per category
- Default condition setting
- Asset count per category

### 3. Allocations

- Allocate assets to employees
- Expected return date tracking
- Return condition recording (Good/Fair/Poor)
- Overdue detection
- Active/Overdue/All tab filtering

### 4. Transfers

- Request asset transfers between employees
- Transfer workflow: Requested → Approved → Completed
- Rejection support
- Reason tracking

### 5. Resource Booking

- Book assets for specific time periods
- Upcoming/Ongoing/Completed status
- Purpose tracking
- Conflict prevention (same asset, overlapping dates)

### 6. Maintenance Requests

- Raise maintenance requests for assets
- Priority levels: Low, Medium, High
- Workflow: Pending → Approved → Assigned → In Progress → Completed
- Rejection support
- Technician assignment

### 7. Audit Cycles

- Create audit cycles (Q1, Q2, Q3 audits)
- Department-level or company-wide scope
- Audit lines per asset
- Results: Verified, Missing, Damaged, Discrepancy
- Summary statistics

### 8. Dashboard

- Real-time KPI cards
- Available asset count
- Allocated asset count
- Maintenance today count
- Active bookings count
- Pending transfers count
- Upcoming returns (next 7 days)
- Overdue returns count
- Quick action buttons

### 9. Reports

- Asset Report
- Allocation Report
- Maintenance Report
- Booking Report

### 10. Activity Log

- Track all activities across models
- Filter by model type
- Search and group capabilities

---

## Models & Fields

### am.department

| Field | Type | Description |
|---|---|---|
| name | Char | Department name |
| complete_name | Char | Full hierarchical name (recursive) |
| parent_id | Many2one | Parent department |
| parent_path | Char | Materialized path for tree queries |
| child_ids | One2many | Child departments |
| head_user_id | Many2one | Department head (res.users) |
| member_ids | One2many | Department members (am.employee) |
| active | Boolean | Active flag |

### am.category

| Field | Type | Description |
|---|---|---|
| name | Char | Category name |
| description | Text | Description |
| warranty_period_months | Integer | Default warranty in months |
| default_condition | Selection | Default asset condition |
| active | Boolean | Active flag |
| asset_ids | One2many | Assets in this category |

### am.employee

| Field | Type | Description |
|---|---|---|
| name | Char | Employee name |
| user_id | Many2one | Linked user account (required) |
| email | Char | Email (from user) |
| department_id | Many2one | Department |
| role | Selection | employee/dept_head/asset_manager/admin |
| job_title | Char | Job title |
| phone | Char | Phone number |
| image_128 | Image | Photo |
| active | Boolean | Active flag |

### asset.asset

| Field | Type | Description |
|---|---|---|
| name | Char | Asset name |
| asset_tag | Char | Unique asset tag |
| serial_number | Char | Serial number |
| condition | Selection | new/good/fair/poor |
| location | Char | Physical location |
| qr_code | Char | QR code value |
| state | Selection | available/allocated/maintenance/disposed |
| acquisition_date | Date | Purchase date |
| acquisition_cost | Float | Purchase cost |
| category_id | Many2one | Asset category |
| department_id | Many2one | Department |
| current_holder_id | Many2one | Current holder (am.employee) |
| active_allocation_id | Many2one | Active allocation |
| is_bookable | Boolean | Available for booking |

### asset.allocation

| Field | Type | Description |
|---|---|---|
| name | Char | Allocation reference |
| asset_id | Many2one | Allocated asset (required) |
| employee_id | Many2one | Allocated to (required) |
| department_id | Many2one | Department |
| state | Selection | allocated/returned/overdue/cancelled |
| allocated_date | Date | Allocation date |
| expected_return_date | Date | Expected return |
| actual_return_date | Date | Actual return |
| return_condition | Selection | good/fair/poor |
| return_condition_notes | Text | Return notes |
| is_overdue | Boolean | Overdue flag |

### asset.transfer

| Field | Type | Description |
|---|---|---|
| name | Char | Transfer reference |
| asset_id | Many2one | Asset to transfer (required) |
| current_holder_id | Many2one | Current holder |
| requested_by | Many2one | Requested by user (required) |
| requested_to | Many2one | Requested to employee (required) |
| state | Selection | requested/approved/completed/rejected |
| reason | Text | Transfer reason |

### resource.booking

| Field | Type | Description |
|---|---|---|
| name | Char | Booking reference |
| asset_id | Many2one | Booked asset (required) |
| booked_by | Many2one | Booked by user (required) |
| state | Selection | upcoming/ongoing/completed/cancelled |
| purpose | Char | Booking purpose |
| start_datetime | Datetime | Start date and time |
| stop_datetime | Datetime | Stop date and time |

### am.maintenance.request

| Field | Type | Description |
|---|---|---|
| name | Char | Request reference |
| asset_id | Many2one | Asset (required) |
| requested_by | Many2one | Requested by user (required) |
| approved_by | Many2one | Approved by user |
| technician_id | Many2one | Assigned technician |
| employee_id | Many2one | Employee |
| state | Selection | pending/approved/assigned/in_progress/completed/rejected |
| priority | Selection | low/medium/high |
| description | Text | Issue description |

### asset.audit.cycle

| Field | Type | Description |
|---|---|---|
| name | Char | Cycle name |
| reference | Char | Reference code |
| scope_type | Selection | company/department |
| location | Char | Location |
| state | Selection | draft/in_progress/completed |
| date_start | Date | Start date |
| date_end | Date | End date |
| department_id | Many2one | Department (if department scope) |
| total_lines | Integer | Total audit lines |
| verified_count | Integer | Verified count |
| missing_count | Integer | Missing count |
| damaged_count | Integer | Damaged count |
| discrepancy_count | Integer | Discrepancy count |

### asset.audit.line

| Field | Type | Description |
|---|---|---|
| cycle_id | Many2one | Audit cycle (required) |
| asset_id | Many2one | Asset (required) |
| auditor_id | Many2one | Auditor (res.users) |
| asset_tag | Char | Asset tag |
| asset_state | Char | Asset state |
| cycle_state | Selection | pending/verified/missing/damaged/discrepancy |
| result | Selection | verified/missing/damaged/discrepancy |
| notes | Text | Audit notes |

---

## Workflows

### Asset Lifecycle

```
Asset Created (state: available)
    │
    ├── Allocate ──────────→ Allocated (state: allocated)
    │                            │
    │                            ├── Return ──────→ Available (state: available)
    │                            │                    │
    │                            │                    └── If maintenance pending → Maintenance
    │                            │
    │                            └── Transfer Requested
    │
    ├── Maintenance Request → Maintenance (state: maintenance)
    │                            │
    │                            └── Completed ──→ Available (state: available)
    │
    └── Dispose ────────────→ Disposed (state: disposed)
```

### Transfer Workflow

```
Transfer Created (state: requested)
    │
    ├── Approve ────→ Approved (state: approved)
    │                    │
    │                    └── Complete ──→ Completed (state: completed)
    │                                      └── Asset holder changes
    │
    └── Reject ─────→ Rejected (state: rejected)
```

### Maintenance Workflow

```
Request Created (state: pending)
    │
    ├── Approve ────→ Approved (state: approved)
    │                    │
    │                    └── Assign ──→ Assigned (state: assigned)
    │                                    │
    │                                    └── Start ──→ In Progress (state: in_progress)
    │                                                    │
    │                                                    └── Complete ──→ Completed (state: completed)
    │                                                                      └── Asset → Available
    │
    └── Reject ─────→ Rejected (state: rejected)
```

### Booking Workflow

```
Booking Created (state: upcoming)
    │
    ├── Start ──────→ Ongoing (state: ongoing)
    │                    │
    │                    └── Complete ──→ Completed (state: completed)
    │
    └── Cancel ─────→ Cancelled (state: cancelled)
```

---

## Menu Structure

```
Asset Management (menu_am_root)
├── Dashboard (menu_am_dashboard)
│
├── Assets (menu_am_assets)
│   ├── All Assets (asset_action)
│   ├── Available (asset_action_available)
│   └── Categories (am_category_action)
│
├── Allocations (menu_am_allocations)
│   ├── All Allocations (allocation_action)
│   ├── Active (allocation_action_active)
│   └── Overdue (allocation_action_overdue)
│
├── Transfers (menu_am_transfers)
│   ├── All Transfers (transfer_action)
│   └── Pending (transfer_action_pending)
│
├── Resource Booking (menu_am_bookings)
│   ├── All Bookings (booking_action)
│   └── Upcoming (booking_action_upcoming)
│
├── Maintenance (menu_am_maintenance)
│   ├── All Requests (maintenance_action)
│   └── Pending (maintenance_action_pending)
│
├── Audit (menu_am_audit) [Manager/Admin only]
│   ├── Audit Cycles (audit_cycle_action)
│   └── Audit Lines (audit_line_action)
│
├── Reports (menu_am_reports)
│   ├── Asset Report
│   ├── Allocation Report
│   ├── Maintenance Report
│   └── Booking Report
│
├── Organization Setup (menu_am_setup) [Admin only]
│   ├── Departments (am_department_action)
│   ├── Asset Categories (am_category_action)
│   └── Employee Directory (am_employee_action)
│
└── Activity Log (menu_am_logs) [Admin only]
```

---

## Dashboard

### KPI Cards

| KPI | Description | Filter |
|---|---|---|
| Available | Assets with state=available | By user scope |
| Allocated | Assets with state=allocated | By user scope |
| In Maintenance | Assets with state=maintenance | All |
| Active Bookings | Bookings with state=upcoming/ongoing | By user scope |
| Pending Transfers | Transfers with state=requested | By user scope |
| Upcoming Returns | Allocations returning in next 7 days | By user scope |
| Overdue Returns | Allocations past return date | By user scope |

### Quick Actions

- Register Asset (dialog)
- Book Resource (dialog)
- Raise Maintenance (dialog)
- Request Transfer (dialog)

### User Scope Logic

```
Admin/Manager → scope: 'all' (see everything)
Dept Head → scope: 'department' (see own department)
Employee → scope: 'own' (see own records only)
No employee record → scope: 'own' (see own records only)
```

---

## Testing Guide

### Test Users

| Login | Password | Role | Department | Job Title |
|---|---|---|---|---|
| employee1 | admin | Employee | Software Dev | Software Developer |
| depthead1 | admin | Dept Head | Software Dev | Team Lead |
| manager1 | admin | Asset Manager | Engineering | Engineering Manager |
| admin1 | admin | Asset Admin | Management | Operations Head |
| admin | admin | Asset Admin | Management | CEO |

### Test Checklist

#### Dashboard
- [ ] All KPI cards visible
- [ ] Numbers match expected data
- [ ] Quick action buttons work
- [ ] Cards navigate to correct list views

#### Assets
- [ ] All Assets shows all assets
- [ ] Available tab shows only available assets
- [ ] Categories list shows all categories
- [ ] Employee can only read assets
- [ ] Dept Head can read + write assets
- [ ] Manager can create + edit assets
- [ ] Admin can create + edit + delete assets

#### Allocations
- [ ] All Allocations shows all
- [ ] Active tab shows allocated only
- [ ] Overdue tab shows overdue only
- [ ] Create allocation works
- [ ] Return allocation works
- [ ] Return condition wizard works

#### Transfers
- [ ] All Transfers shows all
- [ ] Pending tab shows requested only
- [ ] Create transfer works
- [ ] Approve transfer works
- [ ] Complete transfer works
- [ ] Reject transfer works

#### Resource Booking
- [ ] All Bookings shows all
- [ ] Upcoming tab shows upcoming only
- [ ] Create booking works
- [ ] Start booking works
- [ ] Complete booking works
- [ ] Cancel booking works

#### Maintenance
- [ ] All Requests shows all
- [ ] Pending tab shows pending only
- [ ] Create request works
- [ ] Approve request works
- [ ] Assign technician works
- [ ] Mark in progress works
- [ ] Complete request works
- [ ] Reject request works

#### Audit (Manager/Admin only)
- [ ] Employee cannot see Audit menu
- [ ] Manager can see Audit menu
- [ ] Create audit cycle works
- [ ] Create audit lines works
- [ ] Verify/Mark damaged works

#### Organization Setup (Admin only)
- [ ] Only admin sees this menu
- [ ] Departments CRUD works
- [ ] Employee Directory CRUD works
- [ ] Promote buttons work
- [ ] Revoke Role button works
- [ ] Admin cannot revoke own role

#### Activity Log (Admin only)
- [ ] Only admin sees this menu
- [ ] All activities visible
- [ ] Filter by model works
- [ ] Search works

---

## Database Seed Data

### Departments (9 records)

```
Management
├── HR
└── Finance

Engineering
├── Software Dev (Head: depthead1)
└── Hardware

Operations
├── Logistics
└── Warehouse
```

### Categories (8 records)

| Category | Warranty | Condition |
|---|---|---|
| Laptops | 24 months | new |
| Desktops | 36 months | new |
| Monitors | 24 months | new |
| Printers | 12 months | new |
| Furniture | 60 months | new |
| Networking | 36 months | new |
| Vehicles | 60 months | new |
| Tools | 12 months | new |

### Assets (20 records)

| Tag | Name | Category | State | Dept |
|---|---|---|---|---|
| LAP-001 | Dell Latitude 5540 | Laptops | available | Software Dev |
| LAP-002 | HP EliteBook 860 | Laptops | allocated | Software Dev |
| LAP-003 | Lenovo ThinkPad X1 | Laptops | allocated | Management |
| LAP-004 | MacBook Pro 14 | Laptops | available | Software Dev |
| DES-001 | Dell OptiPlex 7090 | Desktops | allocated | Hardware |
| DES-002 | HP ProDesk 400 | Desktops | available | Hardware |
| MON-001 | Dell 27 4K Monitor | Monitors | allocated | Software Dev |
| MON-002 | LG UltraWide 34 | Monitors | allocated | Management |
| MON-003 | Samsung 24 FHD | Monitors | available | Operations |
| PRT-001 | HP LaserJet Pro M404 | Printers | available | Logistics |
| PRT-002 | Canon imageRUNNER | Printers | maintenance | Warehouse |
| FRN-001 | Ergonomic Desk | Furniture | allocated | Software Dev |
| FRN-002 | Executive Chair | Furniture | allocated | Management |
| FRN-003 | Filing Cabinet | Furniture | available | HR |
| NET-001 | Cisco Router | Networking | allocated | Engineering |
| NET-002 | Ubiquiti Switch 48P | Networking | available | Engineering |
| VEH-001 | Toyota Innova | Vehicles | available | Operations |
| VEH-002 | Maruti Ertiga | Vehicles | allocated | Operations |
| TL-001 | Crimping Tool Set | Tools | available | Hardware |
| TL-002 | Digital Multimeter | Tools | allocated | Hardware |

### Allocations (10 records)

| Asset | Employee | Department | Expected Return |
|---|---|---|---|
| HP EliteBook 860 | Test Employee | Software Dev | 2025-09-01 |
| Lenovo ThinkPad X1 | Test Admin | Management | 2025-08-15 |
| Dell 27 Monitor | Test Employee | Software Dev | 2025-09-01 |
| LG UltraWide 34 | Test Admin | Management | 2025-08-20 |
| Dell OptiPlex 7090 | Test Dept Head | Hardware | 2025-07-10 |
| Ergonomic Desk | Test Employee | Software Dev | 2025-12-01 |
| Executive Chair | Test Admin | Management | 2025-11-01 |
| Cisco Router | Test Manager | Engineering | 2026-05-01 |
| Maruti Ertiga | Test Admin | Operations | 2025-06-01 |
| Digital Multimeter | Test Dept Head | Hardware | 2025-07-15 |

### Transfers (5 records)

| Asset | Reason | State |
|---|---|---|
| Dell Latitude 5540 | Need laptop for HR onboarding | requested |
| Canon imageRUNNER | Warehouse needs better printing | approved |
| Samsung 24 FHD | Logistics needs extra monitor | completed |
| Filing Cabinet | Finance needs more storage | requested |
| Crimping Tool Set | Need tools for network setup | requested |

### Bookings (8 records)

| Asset | Purpose | State |
|---|---|---|
| Toyota Innova | Client visit to Mumbai | upcoming |
| Toyota Innova | Airport pickup | upcoming |
| Dell Latitude 5540 | New employee training | upcoming |
| MacBook Pro 14 | UI/UX design sprint | ongoing |
| HP LaserJet Pro M404 | Monthly report printing | upcoming |
| Crimping Tool Set | New floor network cabling | completed |
| Maruti Ertiga | Engineering team outing | completed |
| Samsung 24 FHD | Product demo at client | upcoming |

### Maintenance Requests (7 records)

| Asset | Priority | State |
|---|---|---|
| Canon imageRUNNER | high | in_progress |
| HP EliteBook 860 | medium | approved |
| Dell 27 Monitor | low | pending |
| Executive Chair | medium | pending |
| Toyota Innova | high | approved |
| Maruti Ertiga | high | assigned |
| Cisco Router | medium | completed |

### Audit Cycles (3 records)

| Name | Scope | State | Total Lines |
|---|---|---|---|
| Q1 2025 IT Audit | Department (Engineering) | completed | 6 |
| Q2 2025 IT Audit | Department (Software Dev) | completed | 5 |
| Q3 2025 IT Audit | Company (All Offices) | in_progress | 20 |

---

## File Structure

```
asset_management/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── base_setup.py          # am.department, am.category, am.employee, res.users
│   ├── asset.py               # asset.asset
│   ├── allocation.py          # asset.allocation
│   ├── transfer.py            # asset.transfer
│   ├── booking.py             # resource.booking
│   ├── maintenance.py         # am.maintenance.request
│   ├── audit.py               # asset.audit.cycle, asset.audit.line
│   └── dashboard.py           # am.dashboard (abstract)
├── views/
│   ├── base_setup_views.xml   # Department, Category, Employee views
│   ├── asset_views.xml        # Asset views
│   ├── allocation_views.xml   # Allocation views
│   ├── transfer_views.xml     # Transfer views
│   ├── booking_views.xml      # Booking views
│   ├── maintenance_views.xml  # Maintenance views
│   ├── audit_views.xml        # Audit views
│   ├── report_views.xml       # Report views
│   ├── dashboard.xml          # Dashboard client action
│   ├── log_views.xml          # Activity log views
│   └── menus.xml              # Menu definitions
├── security/
│   ├── security.xml           # Group definitions
│   ├── ir.model.access.csv    # Access control lists
│   └── record_rules.xml       # Record rules
├── static/
│   ├── src/
│   │   ├── js/
│   │   │   ├── dashboard.js   # Dashboard OWL component
│   │   │   └── kanban_widget.js
│   │   ├── xml/
│   │   │   └── dashboard.xml  # Dashboard template
│   │   └── css/
│   │       └── dashboard.css  # Dashboard styles
│   └── description/
│       └── icon.png           # Module icon
└── wizard/
    ├── __init__.py
    ├── return_condition.py    # Return condition wizard
    └── return_condition_views.xml
```

---

## Notes

- `groups_id` renamed to `group_ids` in Odoo 19
- `_sql_constraints` replaced by `models.Constraint` in Odoo 19
- Abstract models (`am.dashboard`) need `@api.model` for RPC calls
- JS `orm.call` passes args directly for `@api.model` methods
- Employee auto-syncs groups on create and role change
- Admin cannot revoke own role (self-lockout protection)
- Dashboard gracefully handles AccessError for unauthorized users
