from django.shortcuts import render, redirect
from . import forms, models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login, update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from . import utils
from django.contrib.auth.models import User


# --- User type helpers ---
def is_admin(user):
    return user.is_superuser

def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()

def is_mechanic(user):
    return user.groups.filter(name='MECHANIC').exists()


# --- Public views ---
def home_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    return render(request, 'vehicle/index.html')

def customerclick_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    return render(request, 'vehicle/customerclick.html')

def mechanicsclick_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    return render(request, 'vehicle/mechanicsclick.html')

def adminclick_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    return redirect('adminlogin')


# --- Auth views ---
def customer_login_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('afterlogin')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'vehicle/customerlogin.html')

def mechanic_login_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('afterlogin')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'vehicle/mechaniclogin.html')

def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('afterlogin')
        else:
            messages.error(request, 'Invalid credentials or insufficient privileges.')
    return render(request, 'vehicle/adminlogin.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('/')

def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-dashboard')
    elif is_mechanic(request.user):
        approved = models.Mechanic.objects.filter(user_id=request.user.id, status=True).exists()
        if approved:
            return redirect('mechanic-dashboard')
        else:
            return render(request, 'vehicle/mechanic_wait_for_approval.html')
    else:
        return redirect('admin-dashboard')


# --- Signup views ---
def customer_signup_view(request):
    userForm = forms.CustomerUserForm()
    customerForm = forms.CustomerForm()
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST)
        customerForm = forms.CustomerForm(request.POST, request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            customer = customerForm.save(commit=False)
            customer.user = user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
            try:
                utils.update_customer_location(customer.id, 0.0, 0.0)
            except Exception as e:
                print(f"KNN initialization error: {e}")
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('customerlogin')
    return render(request, 'vehicle/customersignup.html', {'userForm': userForm, 'customerForm': customerForm})


def mechanic_signup_view(request):
    userForm = forms.MechanicUserForm()
    mechanicForm = forms.MechanicForm()
    if request.method == 'POST':
        userForm = forms.MechanicUserForm(request.POST)
        mechanicForm = forms.MechanicForm(request.POST, request.FILES)
        if userForm.is_valid() and mechanicForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            mechanic = mechanicForm.save(commit=False)
            mechanic.user = user
            mechanic.status = False
            mechanic.save()
            my_mechanic_group = Group.objects.get_or_create(name='MECHANIC')
            my_mechanic_group[0].user_set.add(user)
            messages.success(request, 'Account created! Please wait for admin approval.')
            return redirect('mechaniclogin')
    return render(request, 'vehicle/mechanicsignup.html', {'userForm': userForm, 'mechanicForm': mechanicForm})


# =============================================================================
# ADMIN VIEWS
# =============================================================================

@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    enquiry = models.Request.objects.all().order_by('-id').select_related('customer__user')
    customers = [models.Customer.objects.get(id=enq.customer_id) for enq in enquiry]

    from .utils import get_location_stats, find_nearest_mechanics_for_admin
    location_stats = get_location_stats()
    nearest_mechanics = []
    try:
        nearest_mechanics = find_nearest_mechanics_for_admin(12.9716, 77.5946, count=5, max_distance=100.0)
    except Exception:
        pass

    context = {
        'total_customer': models.Customer.objects.count(),
        'total_mechanic': models.Mechanic.objects.count(),
        'total_request': models.Request.objects.count(),
        'total_feedback': models.Feedback.objects.count(),
        'data': zip(customers, enquiry),
        'location_stats': location_stats,
        'nearest_mechanics': nearest_mechanics,
    }
    return render(request, 'vehicle/admin_dashboard.html', context=context)


@login_required(login_url='adminlogin')
def admin_customer_view(request):
    return render(request, 'vehicle/admin_customer.html')

@login_required(login_url='adminlogin')
def admin_view_customer_view(request):
    customers = models.Customer.objects.all()
    return render(request, 'vehicle/admin_view_customer.html', {'customers': customers})

@login_required(login_url='adminlogin')
def delete_customer_view(request, pk):
    customer = models.Customer.objects.get(id=pk)
    user = models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('admin-view-customer')

@login_required(login_url='adminlogin')
def update_customer_view(request, pk):
    customer = models.Customer.objects.get(id=pk)
    user = models.User.objects.get(id=customer.user_id)
    userForm = forms.CustomerUserForm(instance=user)
    customerForm = forms.CustomerForm(instance=customer)
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST, instance=user)
        customerForm = forms.CustomerForm(request.POST, request.FILES, instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save(commit=False)
            # FIX: only hash if a new password was typed
            new_password = userForm.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
            user.save()
            customerForm.save()
            return redirect('admin-view-customer')
    return render(request, 'vehicle/update_customer.html', {'userForm': userForm, 'customerForm': customerForm})

@login_required(login_url='adminlogin')
def admin_add_customer_view(request):
    userForm = forms.CustomerUserForm()
    customerForm = forms.CustomerForm()
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST)
        customerForm = forms.CustomerForm(request.POST, request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            customer = customerForm.save(commit=False)
            customer.user = user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
            return redirect('admin-view-customer')
    return render(request, 'vehicle/admin_add_customer.html', {'userForm': userForm, 'customerForm': customerForm})

@login_required(login_url='adminlogin')
def admin_view_customer_enquiry_view(request):
    enquiry = models.Request.objects.all().order_by('-id')
    customers = [models.Customer.objects.get(id=enq.customer_id) for enq in enquiry]
    return render(request, 'vehicle/admin_view_customer_enquiry.html', {'data': zip(customers, enquiry)})

@login_required(login_url='adminlogin')
def admin_view_customer_invoice_view(request):
    enquiry = models.Request.objects.values('customer_id').annotate(Sum('cost'))
    customers = [models.Customer.objects.get(id=enq['customer_id']) for enq in enquiry]
    return render(request, 'vehicle/admin_view_customer_invoice.html', {'data': zip(customers, enquiry)})

@login_required(login_url='adminlogin')
def admin_mechanic_view(request):
    return render(request, 'vehicle/admin_mechanic.html')

@login_required(login_url='adminlogin')
def admin_approve_mechanic_view(request):
    mechanics = models.Mechanic.objects.filter(status=False)
    return render(request, 'vehicle/admin_approve_mechanic.html', {'mechanics': mechanics})

@login_required(login_url='adminlogin')
def approve_mechanic_view(request, pk):
    mechanicSalary = forms.MechanicSalaryForm()
    if request.method == 'POST':
        mechanicSalary = forms.MechanicSalaryForm(request.POST)
        if mechanicSalary.is_valid():
            mechanic = models.Mechanic.objects.get(id=pk)
            mechanic.salary = mechanicSalary.cleaned_data['salary']
            mechanic.status = True
            mechanic.save()
        return redirect('admin-approve-mechanic')
    return render(request, 'vehicle/admin_approve_mechanic_details.html', {'mechanicSalary': mechanicSalary})

@login_required(login_url='adminlogin')
def admin_add_mechanic_view(request):
    userForm = forms.MechanicUserForm()
    mechanicForm = forms.MechanicForm()
    mechanicSalary = forms.MechanicSalaryForm()
    if request.method == 'POST':
        userForm = forms.MechanicUserForm(request.POST)
        mechanicForm = forms.MechanicForm(request.POST, request.FILES)
        mechanicSalary = forms.MechanicSalaryForm(request.POST)
        if userForm.is_valid() and mechanicForm.is_valid() and mechanicSalary.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            mechanic = mechanicForm.save(commit=False)
            mechanic.user = user
            mechanic.status = True
            mechanic.salary = mechanicSalary.cleaned_data['salary']
            mechanic.save()
            my_mechanic_group = Group.objects.get_or_create(name='MECHANIC')
            my_mechanic_group[0].user_set.add(user)
            return redirect('admin-view-mechanic')
    return render(request, 'vehicle/admin_add_mechanic.html', {'userForm': userForm, 'mechanicForm': mechanicForm, 'mechanicSalary': mechanicSalary})

@login_required(login_url='adminlogin')
def admin_view_mechanic_view(request):
    mechanics = models.Mechanic.objects.all()
    return render(request, 'vehicle/admin_view_mechanic.html', {'mechanics': mechanics})

@login_required(login_url='adminlogin')
def delete_mechanic_view(request, pk):
    mechanic = models.Mechanic.objects.get(id=pk)
    user = models.User.objects.get(id=mechanic.user_id)
    user.delete()
    mechanic.delete()
    return redirect('admin-view-mechanic')

@login_required(login_url='adminlogin')
def update_mechanic_view(request, pk):
    mechanic = models.Mechanic.objects.get(id=pk)
    user = models.User.objects.get(id=mechanic.user_id)
    userForm = forms.MechanicUserForm(instance=user)
    mechanicForm = forms.MechanicForm(instance=mechanic)
    if request.method == 'POST':
        userForm = forms.MechanicUserForm(request.POST, instance=user)
        mechanicForm = forms.MechanicForm(request.POST, request.FILES, instance=mechanic)
        if userForm.is_valid() and mechanicForm.is_valid():
            user = userForm.save(commit=False)
            # FIX: only hash if a new password was typed
            new_password = userForm.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
            user.save()
            mechanicForm.save()
            return redirect('admin-view-mechanic')
    return render(request, 'vehicle/update_mechanic.html', {'userForm': userForm, 'mechanicForm': mechanicForm})

@login_required(login_url='adminlogin')
def admin_view_mechanic_salary_view(request):
    mechanics = models.Mechanic.objects.all()
    return render(request, 'vehicle/admin_view_mechanic_salary.html', {'mechanics': mechanics})

@login_required(login_url='adminlogin')
def update_salary_view(request, pk):
    mechanicSalary = forms.MechanicSalaryForm()
    if request.method == 'POST':
        mechanicSalary = forms.MechanicSalaryForm(request.POST)
        if mechanicSalary.is_valid():
            mechanic = models.Mechanic.objects.get(id=pk)
            mechanic.salary = mechanicSalary.cleaned_data['salary']
            mechanic.save()
        return redirect('admin-view-mechanic-salary')
    return render(request, 'vehicle/admin_approve_mechanic_details.html', {'mechanicSalary': mechanicSalary})

@login_required(login_url='adminlogin')
def admin_request_view(request):
    return render(request, 'vehicle/admin_request.html')

@login_required(login_url='adminlogin')
def admin_view_request_view(request):
    enquiry = models.Request.objects.all().order_by('-id')
    customers = [models.Customer.objects.get(id=enq.customer_id) for enq in enquiry]
    return render(request, 'vehicle/admin_view_request.html', {'data': zip(customers, enquiry)})

@login_required(login_url='adminlogin')
def change_status_view(request, pk):
    adminenquiry = forms.AdminApproveRequestForm()
    if request.method == 'POST':
        adminenquiry = forms.AdminApproveRequestForm(request.POST)
        if adminenquiry.is_valid():
            enquiry_x = models.Request.objects.get(id=pk)
            enquiry_x.mechanic = adminenquiry.cleaned_data['mechanic']
            enquiry_x.cost = adminenquiry.cleaned_data['cost']
            enquiry_x.status = adminenquiry.cleaned_data['status']
            enquiry_x.save()
        return redirect('admin-view-request')
    return render(request, 'vehicle/admin_approve_request_details.html', {'adminenquiry': adminenquiry})

@login_required(login_url='adminlogin')
def admin_delete_request_view(request, pk):
    models.Request.objects.get(id=pk).delete()
    return redirect('admin-view-request')

@login_required(login_url='adminlogin')
def admin_add_request_view(request):
    enquiry = forms.RequestForm()
    adminenquiry = forms.AdminRequestForm()
    if request.method == 'POST':
        enquiry = forms.RequestForm(request.POST)
        adminenquiry = forms.AdminRequestForm(request.POST)
        if enquiry.is_valid() and adminenquiry.is_valid():
            enquiry_x = enquiry.save(commit=False)
            enquiry_x.customer = adminenquiry.cleaned_data['customer']
            enquiry_x.mechanic = adminenquiry.cleaned_data['mechanic']
            enquiry_x.cost = adminenquiry.cleaned_data['cost']
            enquiry_x.status = 'Approved'
            enquiry_x.save()
            return redirect('admin-view-request')
    return render(request, 'vehicle/admin_add_request.html', {'enquiry': enquiry, 'adminenquiry': adminenquiry})

@login_required(login_url='adminlogin')
def admin_approve_request_view(request):
    enquiry = models.Request.objects.filter(status='Pending')
    return render(request, 'vehicle/admin_approve_request.html', {'enquiry': enquiry})

@login_required(login_url='adminlogin')
def approve_request_view(request, pk):
    adminenquiry = forms.AdminApproveRequestForm()
    if request.method == 'POST':
        adminenquiry = forms.AdminApproveRequestForm(request.POST)
        if adminenquiry.is_valid():
            enquiry_x = models.Request.objects.get(id=pk)
            enquiry_x.mechanic = adminenquiry.cleaned_data['mechanic']
            enquiry_x.cost = adminenquiry.cleaned_data['cost']
            enquiry_x.status = adminenquiry.cleaned_data['status']
            enquiry_x.save()
        return redirect('admin-approve-request')
    return render(request, 'vehicle/admin_approve_request_details.html', {'adminenquiry': adminenquiry})

@login_required(login_url='adminlogin')
def admin_view_service_cost_view(request):
    enquiry = models.Request.objects.all().order_by('-id')
    customers = [models.Customer.objects.get(id=enq.customer_id) for enq in enquiry]
    return render(request, 'vehicle/admin_view_service_cost.html', {'data': zip(customers, enquiry)})

@login_required(login_url='adminlogin')
def update_cost_view(request, pk):
    updateCostForm = forms.UpdateCostForm()
    if request.method == 'POST':
        updateCostForm = forms.UpdateCostForm(request.POST)
        if updateCostForm.is_valid():
            enquiry_x = models.Request.objects.get(id=pk)
            enquiry_x.cost = updateCostForm.cleaned_data['cost']
            enquiry_x.save()
        return redirect('admin-view-service-cost')
    return render(request, 'vehicle/update_cost.html', {'updateCostForm': updateCostForm})

@login_required(login_url='adminlogin')
def admin_mechanic_attendance_view(request):
    return render(request, 'vehicle/admin_mechanic_attendance.html')

@login_required(login_url='adminlogin')
def admin_take_attendance_view(request):
    mechanics = models.Mechanic.objects.filter(status=True)
    aform = forms.AttendanceForm()
    if request.method == 'POST':
        form = forms.AttendanceForm(request.POST)
        if form.is_valid():
            Attendances = request.POST.getlist('present_status')
            date = form.cleaned_data['date']
            for i, mechanic in enumerate(mechanics):
                att = models.Attendance()
                att.date = date
                att.present_status = Attendances[i]
                att.mechanic = mechanic
                att.save()
            return redirect('admin-view-attendance')
    return render(request, 'vehicle/admin_take_attendance.html', {'mechanics': mechanics, 'aform': aform})

@login_required(login_url='adminlogin')
def admin_view_attendance_view(request):
    form = forms.AskDateForm()
    if request.method == 'POST':
        form = forms.AskDateForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            attendancedata = models.Attendance.objects.filter(date=date)
            mechanicdata = models.Mechanic.objects.filter(status=True)
            mylist = zip(attendancedata, mechanicdata)
            return render(request, 'vehicle/admin_view_attendance_page.html', {'mylist': mylist, 'date': date})
    return render(request, 'vehicle/admin_view_attendance_ask_date.html', {'form': form})

@login_required(login_url='adminlogin')
def admin_report_view(request):
    reports = models.Request.objects.filter(Q(status="Repairing Done") | Q(status="Released"))
    return render(request, 'vehicle/admin_report.html', {'reports': reports})

@login_required(login_url='adminlogin')
def admin_feedback_view(request):
    feedback = models.Feedback.objects.all().order_by('-id')
    return render(request, 'vehicle/admin_feedback.html', {'feedback': feedback})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_profile_view(request):
    user = request.user
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                messages.error(request, 'Username already taken.')
                return render(request, 'vehicle/admin_profile.html', {'admin_user': user})
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        if password:
            user.set_password(password)
        user.save()
        if password:
            login(request, user)
            messages.success(request, 'Profile updated. Password changed.')
        else:
            messages.success(request, 'Profile updated successfully!')
        return redirect('admin-profile')
    return render(request, 'vehicle/admin_profile.html', {'admin_user': user})


# =============================================================================
# CUSTOMER VIEWS
# =============================================================================

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_dashboard_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    work_in_progress = models.Request.objects.filter(customer_id=customer.id, status='Repairing').count()
    work_completed = models.Request.objects.filter(customer_id=customer.id).filter(Q(status="Repairing Done") | Q(status="Released")).count()
    new_request_made = models.Request.objects.filter(customer_id=customer.id).filter(Q(status="Pending") | Q(status="Approved")).count()
    bill = models.Request.objects.filter(customer_id=customer.id).filter(Q(status="Repairing Done") | Q(status="Released")).aggregate(Sum('cost'))

    nearest_mechanics = []
    if customer.current_latitude and customer.current_longitude:
        try:
            nearest_mechanics = utils.find_nearest_mechanics(float(customer.current_latitude), float(customer.current_longitude), count=5, max_distance=50.0)
        except Exception:
            pass

    context = {
        'work_in_progress': work_in_progress,
        'work_completed': work_completed,
        'new_request_made': new_request_made,
        'bill': bill['cost__sum'],
        'customer': customer,
        'nearest_mechanics': nearest_mechanics,
    }
    return render(request, 'vehicle/customer_dashboard.html', context=context)

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_request_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    return render(request, 'vehicle/customer_request.html', {'customer': customer})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_view_request_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    enquiries = models.Request.objects.filter(customer_id=customer.id, status="Pending")
    return render(request, 'vehicle/customer_view_request.html', {'customer': customer, 'enquiries': enquiries})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_delete_request_view(request, pk):
    models.Request.objects.get(id=pk).delete()
    return redirect('customer-view-request')

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_view_approved_request_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    enquiries = models.Request.objects.filter(customer_id=customer.id).exclude(status='Pending')
    return render(request, 'vehicle/customer_view_approved_request.html', {'customer': customer, 'enquiries': enquiries})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_view_approved_request_invoice_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    enquiries = models.Request.objects.filter(customer_id=customer.id).exclude(status='Pending')
    return render(request, 'vehicle/customer_view_approved_request_invoice.html', {'customer': customer, 'enquiries': enquiries})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_add_request_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    enquiry = forms.RequestForm()
    if request.method == 'POST':
        enquiry = forms.RequestForm(request.POST)
        if enquiry.is_valid():
            enquiry_x = enquiry.save(commit=False)
            enquiry_x.customer = customer
            enquiry_x.save()
            messages.success(request, 'Service request submitted successfully!')
            return redirect('customer-dashboard')
        # FIX: only redirect on success, fall through to show errors if invalid
    return render(request, 'vehicle/customer_add_request.html', {'enquiry': enquiry, 'customer': customer})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_profile_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    return render(request, 'vehicle/customer_profile.html', {'customer': customer})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_customer_profile_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    user = models.User.objects.get(id=customer.user_id)
    userForm = forms.CustomerUserForm(instance=user)
    customerForm = forms.CustomerForm(instance=customer)
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST, instance=user)
        customerForm = forms.CustomerForm(request.POST, request.FILES, instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save(commit=False)
            # FIX: only hash if new password was typed
            new_password = userForm.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
            user.save()
            customerForm.save()
            # FIX: keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Profile updated successfully!')
            return redirect('customer-profile')
    return render(request, 'vehicle/edit_customer_profile.html', {'userForm': userForm, 'customerForm': customerForm, 'customer': customer})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_invoice_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    enquiries = models.Request.objects.filter(customer_id=customer.id).exclude(status='Pending')
    return render(request, 'vehicle/customer_invoice.html', {'customer': customer, 'enquiries': enquiries})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_invoice_pdf_view(request, request_id):
    try:
        customer = models.Customer.objects.get(user_id=request.user.id)
        models.Request.objects.get(id=request_id, customer_id=customer.id)
        from .invoice_utils import generate_invoice_pdf
        pdf_buffer = generate_invoice_pdf(request_id)
        if not pdf_buffer:
            messages.error(request, 'Failed to generate PDF invoice.')
            return redirect('customer-invoice')
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{request_id:06d}.pdf"'
        return response
    except models.Request.DoesNotExist:
        messages.error(request, 'Service request not found.')
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
    return redirect('customer-invoice')

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_invoice_email_view(request, request_id):
    try:
        recipient_email = request.GET.get('email')
        if not recipient_email:
            messages.error(request, 'No email address provided.')
            return redirect('customer-invoice')
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(recipient_email)
        except ValidationError:
            messages.error(request, 'Invalid email address format.')
            return redirect('customer-invoice')
        from .invoice_utils import generate_and_send_invoice_custom_email
        success, message = generate_and_send_invoice_custom_email(request_id, recipient_email)
        if success:
            messages.success(request, f'Invoice sent to {recipient_email} successfully!')
        else:
            messages.error(request, f'Failed to send invoice: {message}')
    except Exception as e:
        messages.error(request, f'Error sending invoice: {str(e)}')
    return redirect('customer-invoice')

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_invoice_bulk_email_view(request):
    try:
        from .invoice_utils import generate_and_send_invoice
        customer = models.Customer.objects.get(user_id=request.user.id)
        completed_requests = models.Request.objects.filter(customer_id=customer.id).exclude(status='Pending')
        if not completed_requests.exists():
            messages.warning(request, 'No completed service requests found.')
            return redirect('customer-invoice')
        success_count = 0
        failed_count = 0
        for service_request in completed_requests:
            try:
                success, _ = generate_and_send_invoice(service_request.id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
        if success_count > 0:
            messages.success(request, f'Successfully sent {success_count} invoice(s)!')
        if failed_count > 0:
            messages.error(request, f'Failed to send {failed_count} invoice(s). Check email settings.')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    return redirect('customer-invoice')

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_feedback_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    feedback = forms.FeedbackForm()
    if request.method == 'POST':
        feedback = forms.FeedbackForm(request.POST)
        if feedback.is_valid():
            feedback.save()
            return render(request, 'vehicle/feedback_sent_by_customer.html', {'customer': customer})
    return render(request, 'vehicle/customer_feedback.html', {'feedback': feedback, 'customer': customer})


# =============================================================================
# MECHANIC VIEWS
# =============================================================================

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_dashboard_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    work_in_progress = models.Request.objects.filter(mechanic_id=mechanic.id, status='Repairing').count()
    work_completed = models.Request.objects.filter(mechanic_id=mechanic.id).filter(Q(status="Repairing Done") | Q(status="Released")).count()
    new_request_made = models.Request.objects.filter(mechanic_id=mechanic.id).filter(Q(status="Pending") | Q(status="Approved")).count()
    salary = models.Mechanic.objects.get(user_id=request.user.id).salary

    service_area_stats = {
        'total_customers_nearby': 0, 'customers_within_10km': 0,
        'customers_within_25km': 0, 'customers_within_50km': 0,
        'average_distance': 0, 'service_area_coverage': 'Not available'
    }
    try:
        from .utils import get_mechanic_service_area_stats
        service_area_stats = get_mechanic_service_area_stats(mechanic.id)
    except Exception:
        pass

    nearby_customers = []
    if mechanic.current_latitude and mechanic.current_longitude:
        try:
            nearby_customers = utils.find_nearest_customers(float(mechanic.current_latitude), float(mechanic.current_longitude), count=5, max_distance=50.0)
        except Exception:
            pass

    context = {
        'work_in_progress': work_in_progress,
        'work_completed': work_completed,
        'new_request_made': new_request_made,
        'salary': salary,
        'mechanic': mechanic,
        'service_area_stats': service_area_stats,
        'nearby_customers': nearby_customers,
    }
    return render(request, 'vehicle/mechanic_dashboard.html', context=context)

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_work_assigned_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    works = models.Request.objects.filter(mechanic_id=mechanic.id)
    return render(request, 'vehicle/mechanic_work_assigned.html', {'works': works, 'mechanic': mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_update_status_view(request, pk):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    updateStatus = forms.MechanicUpdateStatusForm()
    if request.method == 'POST':
        updateStatus = forms.MechanicUpdateStatusForm(request.POST)
        if updateStatus.is_valid():
            enquiry_x = models.Request.objects.get(id=pk)
            old_status = enquiry_x.status
            enquiry_x.status = updateStatus.cleaned_data['status']
            enquiry_x.save()
            if updateStatus.cleaned_data['status'] in ['Repairing Done', 'Released'] and old_status not in ['Repairing Done', 'Released']:
                try:
                    from .invoice_utils import generate_and_send_invoice
                    success, message = generate_and_send_invoice(pk)
                    if success:
                        messages.success(request, f'Status updated. Invoice sent to customer.')
                    else:
                        messages.warning(request, f'Status updated. Invoice failed: {message}')
                except Exception as e:
                    messages.warning(request, f'Status updated. Invoice error: {str(e)}')
            else:
                messages.success(request, f'Status updated to {updateStatus.cleaned_data["status"]}')
        return redirect('mechanic-work-assigned')
    return render(request, 'vehicle/mechanic_update_status.html', {'updateStatus': updateStatus, 'mechanic': mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_attendance_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    attendaces = models.Attendance.objects.filter(mechanic=mechanic)
    return render(request, 'vehicle/mechanic_view_attendance.html', {'attendaces': attendaces, 'mechanic': mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_feedback_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    feedback = forms.FeedbackForm()
    if request.method == 'POST':
        feedback = forms.FeedbackForm(request.POST)
        if feedback.is_valid():
            feedback.save()
            return render(request, 'vehicle/feedback_sent.html', {'mechanic': mechanic})
    return render(request, 'vehicle/mechanic_feedback.html', {'feedback': feedback, 'mechanic': mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_salary_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    workdone = models.Request.objects.filter(mechanic_id=mechanic.id).filter(Q(status="Repairing Done") | Q(status="Released"))
    return render(request, 'vehicle/mechanic_salary.html', {'workdone': workdone, 'mechanic': mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_profile_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    return render(request, 'vehicle/mechanic_profile.html', {'mechanic': mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def edit_mechanic_profile_view(request):
    mechanic = models.Mechanic.objects.get(user_id=request.user.id)
    user = models.User.objects.get(id=mechanic.user_id)
    userForm = forms.MechanicUserForm(instance=user)
    mechanicForm = forms.MechanicForm(instance=mechanic)
    if request.method == 'POST':
        userForm = forms.MechanicUserForm(request.POST, instance=user)
        mechanicForm = forms.MechanicForm(request.POST, request.FILES, instance=mechanic)
        if userForm.is_valid() and mechanicForm.is_valid():
            user = userForm.save(commit=False)
            # FIX: only hash if new password was typed
            new_password = userForm.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
            user.save()
            mechanicForm.save()
            # FIX: keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Profile updated successfully!')
            return redirect('mechanic-profile')
    return render(request, 'vehicle/edit_mechanic_profile.html', {'userForm': userForm, 'mechanicForm': mechanicForm, 'mechanic': mechanic})


# =============================================================================
# LOCATION / KNN VIEWS
# =============================================================================

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def find_nearest_mechanics_view(request):
    try:
        customer = models.Customer.objects.get(user=request.user)
        if not customer.current_latitude or not customer.current_longitude:
            all_mechanics = models.Mechanic.objects.filter(status=True).select_related('user')
            return render(request, 'vehicle/find_nearest_mechanics.html', {
                'nearest_mechanics': [], 'all_mechanics': all_mechanics,
                'location_enabled': False, 'customer_location': None,
                'message': 'Location not enabled. Showing all available mechanics.'
            })
        nearest_mechanics = utils.find_nearest_mechanics(float(customer.current_latitude), float(customer.current_longitude), count=4)
        return render(request, 'vehicle/find_nearest_mechanics.html', {
            'nearest_mechanics': nearest_mechanics, 'all_mechanics': [],
            'location_enabled': True,
            'customer_location': {'latitude': customer.current_latitude, 'longitude': customer.current_longitude},
            'message': f'Found {len(nearest_mechanics)} nearest mechanics within 50km'
        })
    except models.Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer-dashboard')
    except Exception as e:
        messages.error(request, f'Error finding mechanics: {str(e)}')
        return redirect('customer-dashboard')

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_location_tracking_view(request):
    try:
        mechanic = models.Mechanic.objects.get(user=request.user)
        if not mechanic.current_latitude or not mechanic.current_longitude:
            return render(request, 'vehicle/mechanic_location_tracking.html', {
                'mechanic': mechanic, 'nearby_customers': [], 'current_location': None,
                'location_enabled': False, 'message': 'Enable location tracking to see nearby customers.'
            })
        nearby_customers = utils.find_nearest_customers(float(mechanic.current_latitude), float(mechanic.current_longitude), count=10)
        return render(request, 'vehicle/mechanic_location_tracking.html', {
            'mechanic': mechanic, 'nearby_customers': nearby_customers,
            'current_location': {'latitude': mechanic.current_latitude, 'longitude': mechanic.current_longitude},
            'location_enabled': True, 'message': f'Found {len(nearby_customers)} customers within 50km'
        })
    except models.Mechanic.DoesNotExist:
        messages.error(request, 'Mechanic profile not found.')
        return redirect('mechanic-dashboard')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('mechanic-dashboard')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_location_tracking_view(request):
    if request.method == 'POST':
        if 'update_customer' in request.POST:
            try:
                customer = models.Customer.objects.get(id=request.POST.get('customer_id'))
                customer.current_latitude = float(request.POST.get('latitude'))
                customer.current_longitude = float(request.POST.get('longitude'))
                customer.save()
                messages.success(request, f'Location updated for {customer.get_name}')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        elif 'update_mechanic' in request.POST:
            try:
                mechanic = models.Mechanic.objects.get(id=request.POST.get('mechanic_id'))
                mechanic.current_latitude = float(request.POST.get('latitude'))
                mechanic.current_longitude = float(request.POST.get('longitude'))
                mechanic.save()
                messages.success(request, f'Location updated for {mechanic.get_name}')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        elif 'find_mechanics' in request.POST:
            try:
                customer_lat = float(request.POST.get('customer_lat'))
                customer_lon = float(request.POST.get('customer_lon'))
                radius = int(request.POST.get('radius', 50))
                results = utils.get_nearest_mechanics(customer_lat, customer_lon, radius)
                # FIX: convert tuples to JSON-serializable dicts for session storage
                request.session['nearest_mechanics'] = [
                    {
                        'mechanic_id': m.id,
                        'name': m.get_name,
                        'mobile': m.mobile,
                        'skill': m.skill,
                        'distance_km': round(d, 2),
                    }
                    for m, d in results
                ]
                messages.success(request, f'Found {len(results)} mechanics within {radius}km')
            except Exception as e:
                messages.error(request, f'Error finding mechanics: {str(e)}')

    customers = models.Customer.objects.all()
    mechanics = models.Mechanic.objects.all()
    tracked_customers = customers.filter(current_latitude__isnull=False, current_longitude__isnull=False).count()
    tracked_mechanics = mechanics.filter(current_latitude__isnull=False, current_longitude__isnull=False).count()
    location_stats = {
        'total_customers': customers.count(),
        'total_mechanics': mechanics.count(),
        'tracked_customers': tracked_customers,
        'tracked_mechanics': tracked_mechanics,
        'tracking_coverage_customers': (tracked_customers / max(customers.count(), 1)) * 100,
        'tracking_coverage_mechanics': (tracked_mechanics / max(mechanics.count(), 1)) * 100,
    }
    return render(request, 'vehicle/admin_location_tracking.html', {
        'customers': customers,
        'mechanics': mechanics,
        'location_stats': location_stats,
        'nearest_mechanics': request.session.get('nearest_mechanics', []),
    })

# FIX: Added @login_required to location update API endpoints
@login_required(login_url='customerlogin')
@csrf_exempt
@require_http_methods(["POST"])
def update_customer_location_view(request):
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if not all([customer_id, latitude is not None, longitude is not None]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        success = utils.update_customer_location(customer_id, float(latitude), float(longitude))
        return JsonResponse({'success': success})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='mechaniclogin')
@csrf_exempt
@require_http_methods(["POST"])
def update_mechanic_location_view(request):
    try:
        data = json.loads(request.body)
        mechanic_id = data.get('mechanic_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if not all([mechanic_id, latitude is not None, longitude is not None]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        success = utils.update_mechanic_location(mechanic_id, float(latitude), float(longitude))
        return JsonResponse({'success': success})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# MISC VIEWS
# =============================================================================

def aboutus_view(request):
    return render(request, 'vehicle/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name = sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name) + ' || ' + str(email), message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently=False)
            return render(request, 'vehicle/contactussuccess.html')
    return render(request, 'vehicle/contactus.html', {'form': sub})