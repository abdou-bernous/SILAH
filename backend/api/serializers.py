from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    Company, Payslip, PayslipLine, Document, LeaveBalance, LeaveRequest,
    ExpenseReport, ProfileChangeRequest, Notification, LeaveType,
)

User = get_user_model()

# Fields an employee may change themselves, straight away.
SELF_EDITABLE_FIELDS = ['phone', 'emergency_contact']
# Fields that go through an HR-validated change request.
REQUESTABLE_FIELDS = ['first_name', 'last_name', 'address', 'city', 'postal_code',
                      'bank_name', 'iban', 'social_security_number', 'birth_date']


def validate_upload(file):
    if file and file.size > settings.MAX_UPLOAD_SIZE:
        raise serializers.ValidationError('Fichier trop volumineux (10 Mo maximum).')
    return file


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'legal_form', 'address', 'city', 'nif', 'nis', 'rc',
                  'cnas_number', 'weekend_days', 'annual_leave_days']


class UserLiteSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'first_name', 'last_name', 'job_title', 'department']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ProfileSerializer(serializers.ModelSerializer):
    """The signed-in user's own profile. Only SELF_EDITABLE_FIELDS are writable."""
    full_name = serializers.SerializerMethodField()
    manager = UserLiteSerializer(read_only=True)
    company = CompanySerializer(read_only=True)
    is_hr = serializers.BooleanField(read_only=True)
    team_size = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role', 'is_hr',
                  'employee_number', 'job_title', 'department', 'contract_type', 'hire_date',
                  'birth_date', 'social_security_number', 'phone', 'address', 'city', 'postal_code',
                  'emergency_contact', 'bank_name', 'iban', 'manager', 'company', 'team_size']
        read_only_fields = [f for f in fields if f not in SELF_EDITABLE_FIELDS]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_team_size(self, obj):
        return obj.team.filter(is_active=True).count()


class EmployeeSerializer(serializers.ModelSerializer):
    """HR view of an employee — everything is editable."""
    full_name = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'full_name', 'role',
                  'is_active', 'employee_number', 'job_title', 'department', 'contract_type', 'hire_date',
                  'birth_date', 'social_security_number', 'phone', 'address', 'city', 'postal_code',
                  'emergency_contact', 'bank_name', 'iban', 'base_salary', 'manager', 'manager_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_manager_name(self, obj):
        return str(obj.manager) if obj.manager else None

    def validate_manager(self, value):
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError('Un salarié ne peut pas être son propre manager.')
        return value

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'Mot de passe initial requis.'})
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Mot de passe actuel incorrect.')
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context['request'].user)
        return value


class PayslipLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipLine
        fields = ['code', 'label', 'kind', 'base', 'rate', 'employee_amount', 'employer_amount']


class PayslipListSerializer(serializers.ModelSerializer):
    employee = UserLiteSerializer(read_only=True)

    class Meta:
        model = Payslip
        fields = ['id', 'employee', 'year', 'month', 'status', 'gross_salary', 'net_salary',
                  'employer_cost', 'published_at', 'viewed_at']


class PayslipDetailSerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    lines = PayslipLineSerializer(many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = ['id', 'employee', 'company', 'year', 'month', 'status', 'job_title', 'department',
                  'worked_days', 'unpaid_days', 'gross_salary', 'social_contributions', 'taxable_salary',
                  'income_tax', 'net_salary', 'employer_contributions', 'employer_cost', 'lines',
                  'created_at', 'published_at', 'viewed_at']

    def get_employee(self, obj):
        e = obj.employee
        return {
            'id': e.id, 'full_name': e.get_full_name() or e.username, 'employee_number': e.employee_number,
            'social_security_number': e.social_security_number, 'hire_date': e.hire_date,
            'contract_type': e.get_contract_type_display(), 'address': e.address, 'city': e.city,
            'iban': e.iban, 'bank_name': e.bank_name,
        }

    def get_company(self, obj):
        c = obj.employee.company
        return CompanySerializer(c).data if c else None


class BonusInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=150)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    contributory = serializers.BooleanField(default=True)
    taxable = serializers.BooleanField(default=True)


class PayrollRunSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    employees = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), many=True, required=False)
    bonuses = BonusInputSerializer(many=True, required=False)
    publish = serializers.BooleanField(default=False)


class DocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'employee', 'employee_name', 'category', 'category_label', 'title', 'description',
                  'file', 'file_name', 'file_size', 'created_at', 'viewed_at']
        read_only_fields = ['created_at', 'viewed_at']
        # Files are confidential: never expose a public media URL, they are
        # downloaded through the authenticated /download/ action instead.
        extra_kwargs = {'file': {'write_only': True}}

    def get_employee_name(self, obj):
        return str(obj.employee) if obj.employee else None

    def get_file_name(self, obj):
        return obj.file.name.rsplit('/', 1)[-1] if obj.file else None

    def get_file_size(self, obj):
        try:
            return obj.file.size
        except (OSError, ValueError):
            return None

    def validate_file(self, value):
        return validate_upload(value)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['id', 'employee', 'leave_type', 'year', 'allotted', 'carried_over']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee = UserLiteSerializer(read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    leave_type_label = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'employee', 'leave_type', 'leave_type_label', 'start_date', 'end_date', 'start_half',
                  'end_half', 'days', 'reason', 'attachment', 'has_attachment', 'status', 'status_label', 'reviewer_name',
                  'review_comment', 'reviewed_at', 'created_at']
        read_only_fields = ['days', 'status', 'review_comment', 'reviewed_at', 'created_at']
        extra_kwargs = {'attachment': {'write_only': True}}

    has_attachment = serializers.SerializerMethodField()

    def get_has_attachment(self, obj):
        return bool(obj.attachment)

    def get_reviewer_name(self, obj):
        return str(obj.reviewer) if obj.reviewer else None

    def validate_attachment(self, value):
        return validate_upload(value)

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'La date de fin doit suivre la date de début.'})
        return attrs


class ExpenseSerializer(serializers.ModelSerializer):
    employee = UserLiteSerializer(read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ExpenseReport
        fields = ['id', 'employee', 'date', 'category', 'category_label', 'amount', 'description', 'receipt',
                  'has_receipt', 'status', 'status_label', 'reviewer_name', 'review_comment', 'reviewed_at', 'created_at']
        read_only_fields = ['status', 'review_comment', 'reviewed_at', 'created_at']
        extra_kwargs = {'receipt': {'write_only': True}}

    has_receipt = serializers.SerializerMethodField()

    def get_has_receipt(self, obj):
        return bool(obj.receipt)

    def get_reviewer_name(self, obj):
        return str(obj.reviewer) if obj.reviewer else None

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Le montant doit être positif.')
        return value

    def validate_receipt(self, value):
        return validate_upload(value)


class ProfileChangeRequestSerializer(serializers.ModelSerializer):
    employee = UserLiteSerializer(read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    current_values = serializers.SerializerMethodField()

    class Meta:
        model = ProfileChangeRequest
        fields = ['id', 'employee', 'changes', 'current_values', 'comment', 'status', 'status_label',
                  'review_comment', 'reviewed_at', 'created_at']
        read_only_fields = ['status', 'review_comment', 'reviewed_at', 'created_at']

    def get_current_values(self, obj):
        return {k: str(getattr(obj.employee, k) or '') for k in obj.changes if k in REQUESTABLE_FIELDS}

    def validate_changes(self, value):
        if not isinstance(value, dict) or not value:
            raise serializers.ValidationError('Indiquez au moins une modification.')
        unknown = set(value) - set(REQUESTABLE_FIELDS)
        if unknown:
            raise serializers.ValidationError(f"Champs non modifiables : {', '.join(sorted(unknown))}")
        return {k: str(v).strip() for k, v in value.items()}


class ReviewSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'link', 'read', 'created_at']


LEAVE_TYPE_CHOICES = [{'value': v, 'label': l} for v, l in LeaveType.choices]
