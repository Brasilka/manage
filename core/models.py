from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    HR = "hr", "HR"
    EMPLOYEE = "employee", "Employee"

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    position = models.CharField(max_length=100)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)

    def __str__(self):
        return f"{self.user.username} ({self.position})"

class TimeEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.user.username} — {self.started_at:%Y-%m-%d %H:%M} to {self.ended_at or '...'}"

class WorkShift(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    employees = models.ManyToManyField(Employee, blank=True)

    def __str__(self):
        return f"{self.date} ({self.start_time} - {self.end_time})"
