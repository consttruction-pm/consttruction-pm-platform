# Construction PM Platform
# Professional User Guide & Help System
## Draft Version 1.0

Status: Review Draft - Not Final Approval

---

# 1. Product Introduction

Construction PM Platform is a professional project management and construction control platform.

Core goals:
- Enterprise project planning
- Schedule management
- Resource and cost control
- Reporting and dashboards
- Universal Multi Language support

The product follows Primavera P6 capability coverage as a baseline. The official Oracle P6 documentation includes workspace basics, resources, roles, WBS, activity management, calendars, scheduling, baselines, layouts, tracking, reports and related project controls.

---

# 2. Permanent Product Rules

## Primavera Coverage Rule

The product must not be less than the latest Oracle Primavera reference in:

- Menus
- Submenus
- Fields
- Options
- Calculations
- Charts
- Reports
- Workflows

Additional features are allowed. Removing reference capabilities is not allowed.

## Universal Multi Language Rule

All modules support:

- Multiple languages
- RTL languages
- LTR languages
- Mixed direction text
- Unicode fonts
- Persian and Arabic shaping

---

# 3. Main Menu Help

## Project Management

Functions:
- New Project
- Open Project
- Project Information
- Project Settings
- Templates
- Import
- Export
- Backup
- Restore

## Enterprise Data

Functions:
- EPS
- OBS
- Codes
- User Defined Fields
- Dictionaries

## Planning

Functions:
- WBS
- Activities
- Relationships
- Activity Steps
- Notes
- Documents

## Scheduling

Functions:
- Schedule Run
- Calendar Calculation
- Forward Pass
- Backward Pass
- Float Calculation
- Critical Path

---

# 4. Activity Help

Activity fields:

- Activity ID
- Activity Name
- Activity Type
- Status
- Calendar
- Duration
- Start Date
- Finish Date
- Constraints
- Float
- Codes
- Notes
- Resources
- Costs

---

# 5. Scheduling Engine Reference

Inputs:

- Activities
- Relationships
- Calendars
- Constraints
- Data Date

Outputs:

- Early Start
- Early Finish
- Late Start
- Late Finish
- Total Float
- Critical Activities

Relationship Types:

FS - Finish to Start
SS - Start to Start
FF - Finish to Finish
SF - Start to Finish

---

# 6. Calendar Engine

Calendar support:

- Global Calendars
- Project Calendars
- Resource Calendars
- Holidays
- Exceptions
- Working Hours
- Jalali and Gregorian dates

---

# 7. Resource Management

Resource types:

- Labor
- Equipment
- Material
- Cost Resource

Features:

- Resource Dictionary
- Resource Assignment
- Availability
- Rates
- Resource Calendar

---

# 8. Cost and Earned Value

Formulas:

CV = EV - AC

SV = EV - PV

CPI = EV / AC

SPI = EV / PV

---

# 9. Layout and View System

Features:

- Add Columns
- Remove Columns
- Formula Columns
- Filters
- Grouping
- Sorting
- Saved Layouts

---

# 10. Charts and Reports

Supported visualization:

- Gantt Chart
- Network Diagram
- Resource Histogram
- Resource Usage Profile
- Cost Curve
- S Curve
- Progress Charts
- Variance Charts
- Dashboards

---

# 11. Administration

Features:

- Users
- Roles
- Permissions
- Security
- Audit Trail
- Language Management

---

# 12. Help Article Standard

Every help page must contain:

1. Overview
2. Purpose
3. Fields
4. Options
5. Procedure
6. Examples
7. Related Topics

---

# 13. Release Compliance Check

Before every release:

[ ] Primavera coverage review
[ ] Formula validation
[ ] Multi language test
[ ] RTL/LTR test
[ ] Font rendering test
[ ] Export test
[ ] Regression test

---

End of Draft
