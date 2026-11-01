from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Company, Document, ExpenseReport, LeaveBalance, LeaveRequest, Notification, Payslip, PayslipLine,
    ProfileChangeRequest, User,
)


@admin.register(User)
class SilahUserAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'last_name', 'role', 'job_title', 'department', 'is_active']
    list_filter = ['role', 'is_active', 'department']
    fieldsets = UserAdmin.fieldsets + (
        ('Dossier salarié', {'fields': (
            'company', 'role', 'manager', 'employee_number', 'job_title', 'department', 'contract_type',
            'hire_date', 'birth_date', 'social_security_number', 'phone', 'address', 'city', 'postal_code',
            'emergency_contact', 'bank_name', 'iban', 'base_salary')}),
    )


class PayslipLineInline(admin.TabularInline):
    model = PayslipLine
    extra = 0


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ['employee', 'year', 'month', 'status', 'gross_salary', 'net_salary']
    list_filter = ['status', 'year', 'month']
    inlines = [PayslipLineInline]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days', 'status']
    list_filter = ['status', 'leave_type']


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'category', 'amount', 'status']
    list_filter = ['status', 'category']


admin.site.register([Company, Document, LeaveBalance, ProfileChangeRequest, Notification])
