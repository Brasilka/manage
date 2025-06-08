from ninja.errors import HttpError
from .models import Employee, Role

def is_hr_or_admin(user):
    try:
        employee = Employee.objects.get(user=user)
        return employee.role in [Role.HR, Role.ADMIN]
    except Employee.DoesNotExist:
        return False

def require_hr_or_admin(request):
    if not is_hr_or_admin(request.auth):
        raise HttpError(403, "Доступ разрешён только HR или администратору")
