from ninja import Router
from typing import List
from django.contrib.auth.models import User
from .models import Employee
from pydantic import BaseModel
from ninja_jwt.authentication import JWTAuth
from .models import TimeEntry, Employee
from datetime import datetime
from django.utils.timezone import now
from ninja.errors import HttpError
from .models import WorkShift
from datetime import date, time
from .utils import require_hr_or_admin
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils.timezone import now
from .models import Employee, TimeEntry, WorkShift, Role


api = Router(auth=JWTAuth())

# ===== Схемы =====
class EmployeeOut(BaseModel):
    id: int
    username: str
    position: str
    hourly_rate: float
    role: str

    class Config:
        from_attributes = True

# ===== Эндпоинты =====

@api.get("/employees", response=List[EmployeeOut])
def list_employees(request):
    employees = Employee.objects.select_related("user").all()
    return [
        EmployeeOut(
            id=e.id,
            username=e.user.username,
            position=e.position,
            hourly_rate=float(e.hourly_rate),
            role=e.role,
        ) for e in employees
    ]

class TimeEntryOut(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None

    class Config:
        from_attributes = True

# Начать работу
@api.post("/time-entry/start", response=TimeEntryOut)
def start_time_entry(request):
    user = request.auth
    employee = Employee.objects.get(user=user)

    # Проверка: нельзя начать, если уже есть незакрытая запись
    if TimeEntry.objects.filter(employee=employee, ended_at__isnull=True).exists():
        raise HttpError(400, "Вы уже начали смену и не завершили её")

    entry = TimeEntry.objects.create(employee=employee)
    return entry

# Завершить работу
@api.post("/time-entry/stop", response=TimeEntryOut)
def stop_time_entry(request):
    user = request.auth
    employee = Employee.objects.get(user=user)

    try:
        entry = TimeEntry.objects.get(employee=employee, ended_at__isnull=True)
        entry.ended_at = now()
        entry.save()
        return entry
    except TimeEntry.DoesNotExist:
        raise HttpError(400, "Нет активной смены для завершения")

# Посмотреть свои записи
@api.get("/time-entry/my", response=List[TimeEntryOut])
def my_time_entries(request):
    user = request.auth
    employee = Employee.objects.get(user=user)
    return TimeEntry.objects.filter(employee=employee).order_by("-started_at")

class WorkShiftIn(BaseModel):
    date: date
    start_time: time
    end_time: time

class ShiftEmployeeOut(BaseModel):
    id: int
    username: str
    position: str

    class Config:
        from_attributes = True

class WorkShiftOut(BaseModel):
    id: int
    date: date
    start_time: time
    end_time: time
    employees: List[ShiftEmployeeOut]

    class Config:
        from_attributes = True

# Получить список смен
@api.get("/shifts", response=List[WorkShiftOut])
def list_shifts(request):
    shifts = WorkShift.objects.prefetch_related("employees__user").all()
    result = []
    for shift in shifts:
        result.append(
            WorkShiftOut(
                id=shift.id,
                date=shift.date,
                start_time=shift.start_time,
                end_time=shift.end_time,
                employees=[
                    ShiftEmployeeOut(
                        id=e.id,
                        username=e.user.username,
                        position=e.position,
                    ) for e in shift.employees.all()
                ]
            )
        )
    return result

# Создать смену (HR/админ)
@api.post("/shifts", response=WorkShiftOut)
def create_shift(request, data: WorkShiftIn):
    shift = WorkShift.objects.create(**data.dict())
    return WorkShiftOut(
        id=shift.id,
        date=shift.date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        employees=[],
    )


# Назначить сотрудников на смену
@api.patch("/shifts/{shift_id}/assign", response=WorkShiftOut)
def assign_employees(request, shift_id: int, employee_ids: List[int]):
    shift = WorkShift.objects.prefetch_related("employees__user").get(id=shift_id)
    shift.employees.set(Employee.objects.filter(id__in=employee_ids))
    shift.save()

    return WorkShiftOut(
        id=shift.id,
        date=shift.date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        employees=[
            ShiftEmployeeOut(
                id=e.id,
                username=e.user.username,
                position=e.position
            ) for e in shift.employees.all()
        ]
    )

@api.get("/employees/{employee_id}", response=EmployeeOut)
def get_employee(request, employee_id: int):
    require_hr_or_admin(request)
    employee = Employee.objects.select_related("user").get(id=employee_id)
    return EmployeeOut(
        id=employee.id,
        username=employee.user.username,
        position=employee.position,
        hourly_rate=float(employee.hourly_rate),
        role=employee.role,
    )

@api.delete("/employees/{employee_id}")
def delete_employee(request, employee_id: int):
    require_hr_or_admin(request)
    employee = Employee.objects.get(id=employee_id)
    employee.user.delete()  # удалим и юзера
    return {"success": True}

@api.get("/salary/me")
def get_my_salary(request):
    user = request.auth
    employee = Employee.objects.get(user=user)

    current_month = now().month
    entries = TimeEntry.objects.filter(
        employee=employee,
        started_at__month=current_month,
        ended_at__isnull=False
    ).annotate(
        duration=ExpressionWrapper(
            F('ended_at') - F('started_at'),
            output_field=DurationField()
        )
    )

    total_hours = sum([(e.duration.total_seconds() or 0) / 3600 for e in entries])
    salary = round(total_hours * float(employee.hourly_rate), 2)

    return {
        "employee": employee.user.username,
        "month": now().strftime("%B"),
        "worked_hours": round(total_hours, 2),
        "salary": salary
    }

@api.patch("/shifts/{shift_id}", response=WorkShiftOut)
def update_shift(request, shift_id: int, data: WorkShiftIn):
    require_hr_or_admin(request)
    shift = WorkShift.objects.get(id=shift_id)
    for field, value in data.dict().items():
        setattr(shift, field, value)
    shift.save()
    return WorkShiftOut(
        id=shift.id,
        date=shift.date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        employees=[
            ShiftEmployeeOut(
                id=e.id,
                username=e.user.username,
                position=e.position
            ) for e in shift.employees.all()
        ]
    )

@api.delete("/shifts/{shift_id}")
def delete_shift(request, shift_id: int):
    require_hr_or_admin(request)
    WorkShift.objects.get(id=shift_id).delete()
    return {"success": True}

class EmployeeCreateIn(BaseModel):
    username: str
    password: str
    position: str
    hourly_rate: float
    role: Role

@api.post("/employees_add", response=EmployeeOut)
def create_employee(request, data: EmployeeCreateIn):
    require_hr_or_admin(request)

    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Пользователь с таким логином уже существует")

    user = User.objects.create_user(username=data.username, password=data.password)
    employee = Employee.objects.create(
        user=user,
        position=data.position,
        hourly_rate=data.hourly_rate,
        role=data.role
    )
    return EmployeeOut(
        id=employee.id,
        username=user.username,
        position=employee.position,
        hourly_rate=float(employee.hourly_rate),
        role=employee.role
    )
