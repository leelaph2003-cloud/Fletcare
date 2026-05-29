from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from . import utils
from django.contrib.auth.models import User

# User type checking functions
def is_admin(user):
    return user.is_superuser

def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()

def is_mechanic(user):
    return user.groups.filter(name='MECHANIC').exists()

def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'vehicle/index.html')


#for showing signup/login button for customer
def customerclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'vehicle/customerclick.html')

#for showing signup/login button for mechanics
def mechanicsclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'vehicle/mechanicsclick.html')


#for showing signup/login button for ADMIN(by sumit)
def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return HttpResponseRedirect('adminlogin')


def customer_signup_view(request):
    userForm = forms.CustomerUserForm()
    customerForm = forms.CustomerForm()
    
    if request.method=='POST':
        userForm = forms.CustomerUserForm(request.POST)
        customerForm = forms.CustomerForm(request.POST, request.FILES)
        
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(user.password)
            user.save()
            
            customer = customerForm.save(commit=False)
            customer.user = user
            customer.save()
            
            # Add to CUSTOMER group
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
            
            # Initialize KNN location data for new customer
            try:
                from .utils import update_customer_location
                # Set default location (can be updated later)
                update_customer_location(customer.id, 0.0, 0.0)
            except Exception as e:
                print(f"KNN initialization error: {e}")
            
            messages.success(request, 'Account created successfully! Please login.')
            return HttpResponseRedirect('customerlogin')
        else:
            # Form validation failed, render with errors
            pass
    
    mydict = {'userForm': userForm, 'customerForm': customerForm}
    return render(request, 'vehicle/customersignup.html', context=mydict)


def mechanic_signup_view(request):
    userForm = forms.MechanicUserForm()
    mechanicForm = forms.MechanicForm()
    
    if request.method=='POST':
        userForm = forms.MechanicUserForm(request.POST)
        mechanicForm = forms.MechanicForm(request.POST, request.FILES)
        
        if userForm.is_valid() and mechanicForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(user.password)
            user.save()
            
            mechanic = mechanicForm.save(commit=False)
            mechanic.user = user
            mechanic.status = False  # Needs admin approval
            mechanic.save()
            
            my_mechanic_group = Group.objects.get_or_create(name='MECHANIC')
            my_mechanic_group[0].user_set.add(user)
            
            messages.success(request, 'Account created successfully! Please wait for admin approval.')
            return HttpResponseRedirect('mechaniclogin')
        else:
            # Form validation failed, render with errors
            pass
    
    mydict = {'userForm': userForm, 'mechanicForm': mechanicForm}
    return render(request, 'vehicle/mechanicsignup.html', context=mydict)


#for checking user customer, mechanic or admin(by sumit)
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()
def is_mechanic(user):
    return user.groups.filter(name='MECHANIC').exists()


def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-dashboard')
    elif is_mechanic(request.user):
        accountapproval=models.Mechanic.objects.all().filter(user_id=request.user.id,status=True)
        if accountapproval:
            return redirect('mechanic-dashboard')
        else:
            return render(request,'vehicle/mechanic_wait_for_approval.html')
    else:
        return redirect('admin-dashboard')



#============================================================================================
# ADMIN RELATED views start
#============================================================================================

@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    enquiry=models.Request.objects.all().order_by('-id')
    customers=[]
    for enq in enquiry:
        customer=models.Customer.objects.get(id=enq.customer_id)
        customers.append(customer)
    
    # Import utils for KNN functionality
    from .utils import get_location_stats, find_nearest_mechanics_for_admin
    
    # Get location tracking statistics
    location_stats = get_location_stats()
    
    # Get nearest mechanics for admin monitoring (using a default location - can be enhanced later)
    # For now, using coordinates near the center of a typical city
    default_admin_lat = 12.9716  # Example: Bangalore coordinates
    default_admin_lon = 77.5946
    nearest_mechanics = []
    
    try:
        nearest_mechanics = find_nearest_mechanics_for_admin(
            default_admin_lat, 
            default_admin_lon, 
            count=5, 
            max_distance=100.0
        )
    except Exception as e:
        # If KNN fails, just show empty list
        nearest_mechanics = []
    
    dict={
    'total_customer':models.Customer.objects.all().count(),
    'total_mechanic':models.Mechanic.objects.all().count(),
    'total_request':models.Request.objects.all().count(),
    'total_feedback':models.Feedback.objects.all().count(),
    'data':zip(customers,enquiry),
    'location_stats': location_stats,
    'nearest_mechanics': nearest_mechanics,
    }
    return render(request,'vehicle/admin_dashboard.html',context=dict)


@login_required(login_url='adminlogin')
def admin_customer_view(request):
    return render(request,'vehicle/admin_customer.html')

@login_required(login_url='adminlogin')
def admin_view_customer_view(request):
    customers=models.Customer.objects.all()
    return render(request,'vehicle/admin_view_customer.html',{'customers':customers})


@login_required(login_url='adminlogin')
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('admin-view-customer')


@login_required(login_url='adminlogin')
def update_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,request.FILES,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('admin-view-customer')
    return render(request,'vehicle/update_customer.html',context=mydict)


@login_required(login_url='adminlogin')
def admin_add_customer_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST,request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customer=customerForm.save(commit=False)
            customer.user=user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
        return HttpResponseRedirect('/admin-view-customer')
    return render(request,'vehicle/admin_add_customer.html',context=mydict)


@login_required(login_url='adminlogin')
def admin_view_customer_enquiry_view(request):
    enquiry=models.Request.objects.all().order_by('-id')
    customers=[]
    for enq in enquiry:
        customer=models.Customer.objects.get(id=enq.customer_id)
        customers.append(customer)
    return render(request,'vehicle/admin_view_customer_enquiry.html',{'data':zip(customers,enquiry)})


@login_required(login_url='adminlogin')
def admin_view_customer_invoice_view(request):
    enquiry=models.Request.objects.values('customer_id').annotate(Sum('cost'))
    print(enquiry)
    customers=[]
    for enq in enquiry:
        print(enq)
        customer=models.Customer.objects.get(id=enq['customer_id'])
        customers.append(customer)
    return render(request,'vehicle/admin_view_customer_invoice.html',{'data':zip(customers,enquiry)})

@login_required(login_url='adminlogin')
def admin_mechanic_view(request):
    return render(request,'vehicle/admin_mechanic.html')


@login_required(login_url='adminlogin')
def admin_approve_mechanic_view(request):
    mechanics=models.Mechanic.objects.all().filter(status=False)
    return render(request,'vehicle/admin_approve_mechanic.html',{'mechanics':mechanics})

@login_required(login_url='adminlogin')
def approve_mechanic_view(request,pk):
    mechanicSalary=forms.MechanicSalaryForm()
    if request.method=='POST':
        mechanicSalary=forms.MechanicSalaryForm(request.POST)
        if mechanicSalary.is_valid():
            mechanic=models.Mechanic.objects.get(id=pk)
            mechanic.salary=mechanicSalary.cleaned_data['salary']
            mechanic.status=True
            mechanic.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('/admin-approve-mechanic')
    return render(request,'vehicle/admin_approve_mechanic_details.html',{'mechanicSalary':mechanicSalary})


@login_required(login_url='adminlogin')
def delete_mechanic_view(request,pk):
    mechanic=models.Mechanic.objects.get(id=pk)
    user=models.User.objects.get(id=mechanic.user_id)
    user.delete()
    mechanic.delete()
    return redirect('admin-approve-mechanic')


@login_required(login_url='adminlogin')
def admin_add_mechanic_view(request):
    userForm=forms.MechanicUserForm()
    mechanicForm=forms.MechanicForm()
    mechanicSalary=forms.MechanicSalaryForm()
    mydict={'userForm':userForm,'mechanicForm':mechanicForm,'mechanicSalary':mechanicSalary}
    if request.method=='POST':
        userForm=forms.MechanicUserForm(request.POST)
        mechanicForm=forms.MechanicForm(request.POST,request.FILES)
        mechanicSalary=forms.MechanicSalaryForm(request.POST)
        if userForm.is_valid() and mechanicForm.is_valid() and mechanicSalary.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            mechanic=mechanicForm.save(commit=False)
            mechanic.user=user
            mechanic.status=True
            mechanic.salary=mechanicSalary.cleaned_data['salary']
            mechanic.save()
            my_mechanic_group = Group.objects.get_or_create(name='MECHANIC')
            my_mechanic_group[0].user_set.add(user)
            return HttpResponseRedirect('admin-view-mechanic')
        else:
            print('problem in form')
    return render(request,'vehicle/admin_add_mechanic.html',context=mydict)


@login_required(login_url='adminlogin')
def admin_view_mechanic_view(request):
    mechanics=models.Mechanic.objects.all()
    return render(request,'vehicle/admin_view_mechanic.html',{'mechanics':mechanics})


@login_required(login_url='adminlogin')
def delete_mechanic_view(request,pk):
    mechanic=models.Mechanic.objects.get(id=pk)
    user=models.User.objects.get(id=mechanic.user_id)
    user.delete()
    mechanic.delete()
    return redirect('admin-view-mechanic')


@login_required(login_url='adminlogin')
def update_mechanic_view(request,pk):
    mechanic=models.Mechanic.objects.get(id=pk)
    user=models.User.objects.get(id=mechanic.user_id)
    userForm=forms.MechanicUserForm(instance=user)
    mechanicForm=forms.MechanicForm(request.FILES,instance=mechanic)
    mydict={'userForm':userForm,'mechanicForm':mechanicForm}
    if request.method=='POST':
        userForm=forms.MechanicUserForm(request.POST,instance=user)
        mechanicForm=forms.MechanicForm(request.POST,request.FILES,instance=mechanic)
        if userForm.is_valid() and mechanicForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            mechanicForm.save()
            return redirect('admin-view-mechanic')
    return render(request,'vehicle/update_mechanic.html',context=mydict)

@login_required(login_url='adminlogin')
def admin_view_mechanic_salary_view(request):
    mechanics=models.Mechanic.objects.all()
    return render(request,'vehicle/admin_view_mechanic_salary.html',{'mechanics':mechanics})

@login_required(login_url='adminlogin')
def update_salary_view(request,pk):
    mechanicSalary=forms.MechanicSalaryForm()
    if request.method=='POST':
        mechanicSalary=forms.MechanicSalaryForm(request.POST)
        if mechanicSalary.is_valid():
            mechanic=models.Mechanic.objects.get(id=pk)
            mechanic.salary=mechanicSalary.cleaned_data['salary']
            mechanic.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('/admin-view-mechanic-salary')
    return render(request,'vehicle/admin_approve_mechanic_details.html',{'mechanicSalary':mechanicSalary})


@login_required(login_url='adminlogin')
def admin_request_view(request):
    return render(request,'vehicle/admin_request.html')

@login_required(login_url='adminlogin')
def admin_view_request_view(request):
    enquiry=models.Request.objects.all().order_by('-id')
    customers=[]
    for enq in enquiry:
        customer=models.Customer.objects.get(id=enq.customer_id)
        customers.append(customer)
    return render(request,'vehicle/admin_view_request.html',{'data':zip(customers,enquiry)})


@login_required(login_url='adminlogin')
def change_status_view(request,pk):
    adminenquiry=forms.AdminApproveRequestForm()
    if request.method=='POST':
        adminenquiry=forms.AdminApproveRequestForm(request.POST)
        if adminenquiry.is_valid():
            enquiry_x=models.Request.objects.get(id=pk)
            enquiry_x.mechanic=adminenquiry.cleaned_data['mechanic']
            enquiry_x.cost=adminenquiry.cleaned_data['cost']
            enquiry_x.status=adminenquiry.cleaned_data['status']
            enquiry_x.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('/admin-view-request')
    return render(request,'vehicle/admin_approve_request_details.html',{'adminenquiry':adminenquiry})


@login_required(login_url='adminlogin')
def admin_delete_request_view(request,pk):
    requests=models.Request.objects.get(id=pk)
    requests.delete()
    return redirect('admin-view-request')



@login_required(login_url='adminlogin')
def admin_add_request_view(request):
    enquiry=forms.RequestForm()
    adminenquiry=forms.AdminRequestForm()
    mydict={'enquiry':enquiry,'adminenquiry':adminenquiry}
    if request.method=='POST':
        enquiry=forms.RequestForm(request.POST)
        adminenquiry=forms.AdminRequestForm(request.POST)
        if enquiry.is_valid() and adminenquiry.is_valid():
            enquiry_x=enquiry.save(commit=False)
            enquiry_x.customer=adminenquiry.cleaned_data['customer']
            enquiry_x.mechanic=adminenquiry.cleaned_data['mechanic']
            enquiry_x.cost=adminenquiry.cleaned_data['cost']
            enquiry_x.status='Approved'
            enquiry_x.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('admin-view-request')
    return render(request,'vehicle/admin_add_request.html',context=mydict)

@login_required(login_url='adminlogin')
def admin_approve_request_view(request):
    enquiry=models.Request.objects.all().filter(status='Pending')
    return render(request,'vehicle/admin_approve_request.html',{'enquiry':enquiry})

@login_required(login_url='adminlogin')
def approve_request_view(request,pk):
    adminenquiry=forms.AdminApproveRequestForm()
    if request.method=='POST':
        adminenquiry=forms.AdminApproveRequestForm(request.POST)
        if adminenquiry.is_valid():
            enquiry_x=models.Request.objects.get(id=pk)
            enquiry_x.mechanic=adminenquiry.cleaned_data['mechanic']
            enquiry_x.cost=adminenquiry.cleaned_data['cost']
            enquiry_x.status=adminenquiry.cleaned_data['status']
            enquiry_x.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('/admin-approve-request')
    return render(request,'vehicle/admin_approve_request_details.html',{'adminenquiry':adminenquiry})




@login_required(login_url='adminlogin')
def admin_view_service_cost_view(request):
    enquiry=models.Request.objects.all().order_by('-id')
    customers=[]
    for enq in enquiry:
        customer=models.Customer.objects.get(id=enq.customer_id)
        customers.append(customer)
    print(customers)
    return render(request,'vehicle/admin_view_service_cost.html',{'data':zip(customers,enquiry)})


@login_required(login_url='adminlogin')
def update_cost_view(request,pk):
    updateCostForm=forms.UpdateCostForm()
    if request.method=='POST':
        updateCostForm=forms.UpdateCostForm(request.POST)
        if updateCostForm.is_valid():
            enquiry_x=models.Request.objects.get(id=pk)
            enquiry_x.cost=updateCostForm.cleaned_data['cost']
            enquiry_x.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('/admin-view-service-cost')
    return render(request,'vehicle/update_cost.html',{'updateCostForm':updateCostForm})



@login_required(login_url='adminlogin')
def admin_mechanic_attendance_view(request):
    return render(request,'vehicle/admin_mechanic_attendance.html')


@login_required(login_url='adminlogin')
def admin_take_attendance_view(request):
    mechanics=models.Mechanic.objects.all().filter(status=True)
    aform=forms.AttendanceForm()
    if request.method=='POST':
        form=forms.AttendanceForm(request.POST)
        if form.is_valid():
            Attendances=request.POST.getlist('present_status')
            date=form.cleaned_data['date']
            for i in range(len(Attendances)):
                AttendanceModel=models.Attendance()
                
                AttendanceModel.date=date
                AttendanceModel.present_status=Attendances[i]
                print(mechanics[i].id)
                print(int(mechanics[i].id))
                mechanic=models.Mechanic.objects.get(id=int(mechanics[i].id))
                AttendanceModel.mechanic=mechanic
                AttendanceModel.save()
            return redirect('admin-view-attendance')
        else:
            print('form invalid')
    return render(request,'vehicle/admin_take_attendance.html',{'mechanics':mechanics,'aform':aform})

@login_required(login_url='adminlogin')
def admin_view_attendance_view(request):
    form=forms.AskDateForm()
    if request.method=='POST':
        form=forms.AskDateForm(request.POST)
        if form.is_valid():
            date=form.cleaned_data['date']
            attendancedata=models.Attendance.objects.all().filter(date=date)
            mechanicdata=models.Mechanic.objects.all().filter(status=True)
            mylist=zip(attendancedata,mechanicdata)
            return render(request,'vehicle/admin_view_attendance_page.html',{'mylist':mylist,'date':date})
        else:
            print('form invalid')
    return render(request,'vehicle/admin_view_attendance_ask_date.html',{'form':form})

@login_required(login_url='adminlogin')
def admin_report_view(request):
    reports=models.Request.objects.all().filter(Q(status="Repairing Done") | Q(status="Released"))
    dict={
        'reports':reports,
    }
    return render(request,'vehicle/admin_report.html',context=dict)


@login_required(login_url='adminlogin')
def admin_feedback_view(request):
    feedback=models.Feedback.objects.all().order_by('-id')
    return render(request,'vehicle/admin_feedback.html',{'feedback':feedback})

#============================================================================================
# ADMIN RELATED views END
#============================================================================================


#============================================================================================
# CUSTOMER RELATED views start
#============================================================================================

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_dashboard_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    work_in_progress=models.Request.objects.all().filter(customer_id=customer.id,status='Repairing').count()
    work_completed=models.Request.objects.all().filter(customer_id=customer.id).filter(Q(status="Repairing Done") | Q(status="Released")).count()
    new_request_made=models.Request.objects.all().filter(customer_id=customer.id).filter(Q(status="Pending") | Q(status="Approved")).count()
    bill=models.Request.objects.all().filter(customer_id=customer.id).filter(Q(status="Repairing Done") | Q(status="Released")).aggregate(Sum('cost'))
    print(bill)
    
    # Import utils for KNN functionality
    from .utils import find_nearest_mechanics
    
    # Get nearest mechanics if customer has location data
    nearest_mechanics = []
    if customer.current_latitude and customer.current_longitude:
        try:
            nearest_mechanics = find_nearest_mechanics(
                float(customer.current_latitude), 
                float(customer.current_longitude), 
                count=5, 
                max_distance=50.0
            )
        except Exception as e:
            # If KNN fails, just show empty list
            nearest_mechanics = []
    
    dict={
    'work_in_progress':work_in_progress,
    'work_completed':work_completed,
    'new_request_made':new_request_made,
    'bill':bill['cost__sum'],
    'customer':customer,
    'nearest_mechanics': nearest_mechanics,
    }
    return render(request,'vehicle/customer_dashboard.html',context=dict)


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_request_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'vehicle/customer_request.html',{'customer':customer})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_view_request_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    enquiries=models.Request.objects.all().filter(customer_id=customer.id , status="Pending")
    return render(request,'vehicle/customer_view_request.html',{'customer':customer,'enquiries':enquiries})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_delete_request_view(request,pk):
    customer=models.Customer.objects.get(user_id=request.user.id)
    enquiry=models.Request.objects.get(id=pk)
    enquiry.delete()
    return redirect('customer-view-request')

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_view_approved_request_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    enquiries=models.Request.objects.all().filter(customer_id=customer.id).exclude(status='Pending')
    return render(request,'vehicle/customer_view_approved_request.html',{'customer':customer,'enquiries':enquiries})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_view_approved_request_invoice_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    enquiries=models.Request.objects.all().filter(customer_id=customer.id).exclude(status='Pending')
    return render(request,'vehicle/customer_view_approved_request_invoice.html',{'customer':customer,'enquiries':enquiries})



@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_add_request_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    enquiry=forms.RequestForm()
    if request.method=='POST':
        enquiry=forms.RequestForm(request.POST)
        if enquiry.is_valid():
            customer=models.Customer.objects.get(user_id=request.user.id)
            enquiry_x=enquiry.save(commit=False)
            enquiry_x.customer=customer
            enquiry_x.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect('customer-dashboard')
    return render(request,'vehicle/customer_add_request.html',{'enquiry':enquiry,'customer':customer})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'vehicle/customer_profile.html',{'customer':customer})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_customer_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm,'customer':customer}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return HttpResponseRedirect('customer-profile')
    return render(request,'vehicle/edit_customer_profile.html',context=mydict)


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_invoice_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    enquiries=models.Request.objects.all().filter(customer_id=customer.id).exclude(status='Pending')
    return render(request,'vehicle/customer_invoice.html',{'customer':customer,'enquiries':enquiries})

@user_passes_test(is_customer)
def customer_invoice_pdf_view(request, request_id):
    """
    Generate and download PDF invoice for a specific service request
    """
    print(f"🔍 PDF view called for request_id: {request_id}")  # Debug print
    
    try:
        # First check if the request exists and belongs to the customer
        customer = models.Customer.objects.get(user_id=request.user.id)
        print(f"🔍 Customer found: {customer.user.username}")  # Debug print
        
        service_request = models.Request.objects.get(id=request_id, customer_id=customer.id)
        print(f"🔍 Service request found: {service_request.problem_description[:50]}...")  # Debug print
        
        # Import the invoice utility
        from .invoice_utils import generate_invoice_pdf
        print("🔍 Invoice utility imported successfully")  # Debug print
        
        # Generate PDF
        print("🔍 Starting PDF generation...")  # Debug print
        pdf_buffer = generate_invoice_pdf(request_id)
        
        if not pdf_buffer:
            print("❌ PDF generation returned None")  # Debug print
            messages.error(request, 'Failed to generate PDF invoice. Please try again.')
            return redirect('customer-invoice')
        
        print(f"🔍 PDF generated successfully, size: {len(pdf_buffer.getvalue())} bytes")  # Debug print
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{request_id:06d}.pdf"'
        
        print("🔍 PDF response created, returning...")  # Debug print
        return response
        
    except models.Request.DoesNotExist:
        print(f"❌ Request {request_id} not found")  # Debug print
        messages.error(request, 'Service request not found.')
        return redirect('customer-invoice')
    except models.Customer.DoesNotExist:
        print(f"❌ Customer not found for user {request.user.id}")  # Debug print
        messages.error(request, 'Customer profile not found.')
        return redirect('customer-invoice')
    except ImportError as e:
        print(f"❌ Import error: {e}")  # Debug print
        messages.error(request, f'PDF generation module not found: {str(e)}')
        return redirect('customer-invoice')
    except Exception as e:
        print(f"❌ PDF Generation Error: {str(e)}")  # Debug print
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('customer-invoice')

@user_passes_test(is_customer)
def customer_invoice_email_view(request, request_id):
    """
    Generate PDF invoice and send via email to custom recipient
    """
    try:
        # Get the custom email address from query parameters
        recipient_email = request.GET.get('email')
        
        if not recipient_email:
            messages.error(request, 'No email address provided.')
            return redirect('customer-invoice')
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(recipient_email)
        except ValidationError:
            messages.error(request, 'Invalid email address format.')
            return redirect('customer-invoice')
        
        print(f"🔍 Attempting to send invoice {request_id} to {recipient_email}")
        
        # Import the invoice utility
        from .invoice_utils import generate_and_send_invoice_custom_email
        
        # Generate and send invoice to custom email
        success, message = generate_and_send_invoice_custom_email(request_id, recipient_email)
        
        if success:
            messages.success(request, f'✅ Invoice has been sent to {recipient_email} successfully!')
            print(f"✅ Invoice {request_id} sent successfully to {recipient_email}")
        else:
            messages.error(request, f'❌ Failed to send invoice: {message}')
            print(f"❌ Invoice {request_id} failed to send: {message}")
            
            # Add helpful guidance for common issues
            if "App Password" in message or "authentication" in message.lower():
                messages.warning(request, '💡 Email authentication failed. Please check your Gmail App Password in settings.py.')
            
    except Exception as e:
        error_msg = f'Error sending invoice: {str(e)}'
        messages.error(request, error_msg)
        print(f"❌ Invoice email error: {error_msg}")
    
    return redirect('customer-invoice')

@user_passes_test(is_customer)
def customer_invoice_bulk_email_view(request):
    """
    Send invoices for all completed service requests via email
    """
    try:
        from .invoice_utils import generate_and_send_invoice
        
        customer = models.Customer.objects.get(user_id=request.user.id)
        completed_requests = models.Request.objects.filter(
            customer_id=customer.id
        ).exclude(status='Pending')
        
        if not completed_requests.exists():
            messages.warning(request, 'No completed service requests found.')
            return redirect('customer-invoice')
        
        success_count = 0
        failed_count = 0
        error_messages = []
        
        for service_request in completed_requests:
            try:
                success, message = generate_and_send_invoice(service_request.id)
                if success:
                    success_count += 1
                    print(f"✅ Invoice {service_request.id} sent successfully")
                else:
                    failed_count += 1
                    error_messages.append(f"Request #{service_request.id}: {message}")
                    print(f"❌ Invoice {service_request.id} failed: {message}")
            except Exception as e:
                failed_count += 1
                error_msg = f"Request #{service_request.id}: {str(e)}"
                error_messages.append(error_msg)
                print(f"❌ Invoice {service_request.id} error: {error_msg}")
        
        # Show detailed results
        if success_count > 0:
            messages.success(request, f'Successfully sent {success_count} invoice(s) to your email!')
        
        if failed_count > 0:
            # Show the first few error messages to help with debugging
            if len(error_messages) <= 3:
                for error in error_messages:
                    messages.error(request, error)
            else:
                messages.error(request, f'Failed to send {failed_count} invoice(s). First error: {error_messages[0]}')
                messages.error(request, f'Check the console for more details or fix your email configuration.')
            
            # Add helpful guidance
            messages.warning(request, '💡 To fix email issues: Check your Gmail App Password in settings.py. You need 2-Factor Authentication enabled and an App Password generated.')
            
    except Exception as e:
        messages.error(request, f'Error sending bulk invoices: {str(e)}')
        print(f"❌ Bulk email error: {str(e)}")
    
    return redirect('customer-invoice')


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_feedback_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    feedback=forms.FeedbackForm()
    if request.method=='POST':
        feedback=forms.FeedbackForm(request.POST)
        if feedback.is_valid():
            feedback.save()
        else:
            print("form is invalid")
        return render(request,'vehicle/feedback_sent_by_customer.html',{'customer':customer})
    return render(request,'vehicle/customer_feedback.html',{'feedback':feedback,'customer':customer})
#============================================================================================
# CUSTOMER RELATED views END
#============================================================================================






#============================================================================================
# MECHANIC RELATED views start
#============================================================================================


@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_dashboard_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    work_in_progress=models.Request.objects.all().filter(mechanic_id=mechanic.id,status='Repairing').count()
    work_completed=models.Request.objects.all().filter(mechanic_id=mechanic.id).filter(Q(status="Repairing Done") | Q(status="Released")).count()
    new_request_made=models.Request.objects.all().filter(mechanic_id=mechanic.id).filter(Q(status="Pending") | Q(status="Approved")).count()
    salary=models.Mechanic.objects.get(user_id=request.user.id).salary
    dict={
    'work_in_progress':work_in_progress,
    'work_completed':work_completed,
    'new_request_made':new_request_made,
    'salary':salary,
    'mechanic':mechanic,
    }
    
    # Import utils for KNN functionality
    from .utils import get_mechanic_service_area_stats, find_nearest_customers
    
    # Get service area statistics
    try:
        service_area_stats = get_mechanic_service_area_stats(mechanic.id)
    except Exception as e:
        service_area_stats = {
            'total_customers_nearby': 0,
            'customers_within_10km': 0,
            'customers_within_25km': 0,
            'customers_within_50km': 0,
            'average_distance': 0,
            'service_area_coverage': 'Not available'
        }
    
    # Get nearby customers if mechanic has location data
    nearby_customers = []
    if mechanic.current_latitude and mechanic.current_longitude:
        try:
            nearby_customers = find_nearest_customers(
                float(mechanic.current_latitude), 
                float(mechanic.current_longitude), 
                count=5, 
                max_distance=50.0
            )
        except Exception as e:
            nearby_customers = []
    
    dict.update({
        'service_area_stats': service_area_stats,
        'nearby_customers': nearby_customers,
    })
    
    return render(request,'vehicle/mechanic_dashboard.html',context=dict)

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_work_assigned_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    works=models.Request.objects.all().filter(mechanic_id=mechanic.id)
    return render(request,'vehicle/mechanic_work_assigned.html',{'works':works,'mechanic':mechanic})


@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_update_status_view(request,pk):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    updateStatus=forms.MechanicUpdateStatusForm()
    if request.method=='POST':
        updateStatus=forms.MechanicUpdateStatusForm(request.POST)
        if updateStatus.is_valid():
            enquiry_x=models.Request.objects.get(id=pk)
            old_status = enquiry_x.status
            enquiry_x.status=updateStatus.cleaned_data['status']
            enquiry_x.save()
            
            # Auto-generate and send invoice when service is completed
            if updateStatus.cleaned_data['status'] in ['Repairing Done', 'Released'] and old_status not in ['Repairing Done', 'Released']:
                try:
                    from .invoice_utils import generate_and_send_invoice
                    success, message = generate_and_send_invoice(pk)
                    if success:
                        messages.success(request, f'Service status updated to {updateStatus.cleaned_data["status"]}. Invoice has been automatically sent to customer.')
                    else:
                        messages.warning(request, f'Service status updated to {updateStatus.cleaned_data["status"]}. Invoice generation failed: {message}')
                except Exception as e:
                    messages.warning(request, f'Service status updated to {updateStatus.cleaned_data["status"]}. Invoice generation failed: {str(e)}')
            else:
                messages.success(request, f'Service status updated to {updateStatus.cleaned_data["status"]}')
        else:
            print("form is invalid")
        return HttpResponseRedirect('/mechanic-work-assigned')
    return render(request,'vehicle/mechanic_update_status.html',{'updateStatus':updateStatus,'mechanic':mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_attendance_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    attendaces=models.Attendance.objects.all().filter(mechanic=mechanic)
    return render(request,'vehicle/mechanic_view_attendance.html',{'attendaces':attendaces,'mechanic':mechanic})





@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_feedback_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    feedback=forms.FeedbackForm()
    if request.method=='POST':
        feedback=forms.FeedbackForm(request.POST)
        if feedback.is_valid():
            feedback.save()
        else:
            print("form is invalid")
        return render(request,'vehicle/feedback_sent.html',{'mechanic':mechanic})
    return render(request,'vehicle/mechanic_feedback.html',{'feedback':feedback,'mechanic':mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_salary_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    workdone=models.Request.objects.all().filter(mechanic_id=mechanic.id).filter(Q(status="Repairing Done") | Q(status="Released"))
    return render(request,'vehicle/mechanic_salary.html',{'workdone':workdone,'mechanic':mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_profile_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    return render(request,'vehicle/mechanic_profile.html',{'mechanic':mechanic})

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def edit_mechanic_profile_view(request):
    mechanic=models.Mechanic.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=mechanic.user_id)
    userForm=forms.MechanicUserForm(instance=user)
    mechanicForm=forms.MechanicForm(request.FILES,instance=mechanic)
    mydict={'userForm':userForm,'mechanicForm':mechanicForm,'mechanic':mechanic}
    if request.method=='POST':
        userForm=forms.MechanicUserForm(request.POST,instance=user)
        mechanicForm=forms.MechanicForm(request.POST,request.FILES,instance=mechanic)
        if userForm.is_valid() and mechanicForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            mechanicForm.save()
            return redirect('mechanic-profile')
    return render(request,'vehicle/edit_mechanic_profile.html',context=mydict)






#============================================================================================
# MECHANIC RELATED views start
#============================================================================================




# for aboutus and contact
def aboutus_view(request):
    return render(request,'vehicle/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message,settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'vehicle/contactussuccess.html')
    return render(request, 'vehicle/contactus.html', {'form':sub})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('/')

def customer_login_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/afterlogin')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return HttpResponseRedirect('/afterlogin')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'vehicle/customerlogin.html')

def mechanic_login_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/afterlogin')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return HttpResponseRedirect('/afterlogin')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'vehicle/mechaniclogin.html')

def admin_login_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/afterlogin')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return HttpResponseRedirect('/afterlogin')
        else:
            messages.error(request, 'Invalid username or password or insufficient privileges.')
    
    return render(request, 'vehicle/adminlogin.html')

# Location and KNN related views
@csrf_exempt
@require_http_methods(["POST"])
def update_customer_location_view(request):
    """Update customer's current location"""
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not all([customer_id, latitude, longitude]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        success = utils.update_customer_location(customer_id, float(latitude), float(longitude))
        return JsonResponse({'success': success})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def update_mechanic_location_view(request):
    """Update mechanic's current location"""
    try:
        data = json.loads(request.body)
        mechanic_id = data.get('mechanic_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not all([mechanic_id, latitude, longitude]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        success = utils.update_mechanic_location(mechanic_id, float(latitude), float(longitude))
        return JsonResponse({'success': success})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def find_nearest_mechanics_view(request):
    """Find nearest 4 mechanics for customer using KNN"""
    try:
        customer = models.Customer.objects.get(user=request.user)
        
        if not customer.current_latitude or not customer.current_longitude:
            # If no location data, show all available mechanics with a message
            all_mechanics = models.Mechanic.objects.filter(status=True).select_related('user')
            context = {
                'nearest_mechanics': [],
                'all_mechanics': all_mechanics,
                'location_enabled': False,
                'customer_location': None,
                'message': 'Location services not enabled. Showing all available mechanics.'
            }
            return render(request, 'vehicle/find_nearest_mechanics.html', context)
        
        # Find nearest mechanics using KNN
        nearest_mechanics = utils.find_nearest_mechanics(
            float(customer.current_latitude),
            float(customer.current_longitude),
            count=4
        )
        
        context = {
            'nearest_mechanics': nearest_mechanics,
            'all_mechanics': [],
            'location_enabled': True,
            'customer_location': {
                'latitude': customer.current_latitude,
                'longitude': customer.current_longitude
            },
            'message': f'Found {len(nearest_mechanics)} nearest mechanics within 50km'
        }
        
        return render(request, 'vehicle/find_nearest_mechanics.html', context)
        
    except models.Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer-dashboard')
    except Exception as e:
        messages.error(request, f'Error finding mechanics: {str(e)}')
        return redirect('customer-dashboard')

@login_required(login_url='mechaniclogin')
@user_passes_test(is_mechanic)
def mechanic_location_tracking_view(request):
    """Mechanic's location tracking and nearby customers"""
    try:
        mechanic = models.Mechanic.objects.get(user=request.user)
        
        if not mechanic.current_latitude or not mechanic.current_longitude:
            # If no location data, show basic info with location setup instructions
            context = {
                'mechanic': mechanic,
                'nearby_customers': [],
                'current_location': None,
                'location_enabled': False,
                'message': 'Location services not enabled. Enable location tracking to see nearby customers.'
            }
            return render(request, 'vehicle/mechanic_location_tracking.html', context)
        
        # Find nearby customers
        nearby_customers = utils.find_nearest_customers(
            float(mechanic.current_latitude),
            float(mechanic.current_longitude),
            count=10
        )
        
        context = {
            'mechanic': mechanic,
            'nearby_customers': nearby_customers,
            'current_location': {
                'latitude': mechanic.current_latitude,
                'longitude': mechanic.current_longitude
            },
            'location_enabled': True,
            'message': f'Found {len(nearby_customers)} customers within 50km'
        }
        
        return render(request, 'vehicle/mechanic_location_tracking.html', context)
        
    except models.Mechanic.DoesNotExist:
        messages.error(request, 'Mechanic profile not found.')
        return redirect('mechanic-dashboard')
    except Exception as e:
        messages.error(request, f'Error tracking location: {str(e)}')
        return redirect('mechanic-dashboard')

@user_passes_test(is_admin)
def admin_location_tracking_view(request):
    if request.method == 'POST':
        if 'update_customer' in request.POST:
            customer_id = request.POST.get('customer_id')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            
            try:
                customer = models.Customer.objects.get(id=customer_id)
                customer.current_latitude = float(latitude)
                customer.current_longitude = float(longitude)
                customer.save()
                messages.success(request, f'Location updated for {customer.get_name()}')
            except Exception as e:
                messages.error(request, f'Error updating location: {str(e)}')
                
        elif 'update_mechanic' in request.POST:
            mechanic_id = request.POST.get('mechanic_id')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            
            try:
                mechanic = models.Mechanic.objects.get(id=mechanic_id)
                mechanic.current_latitude = float(latitude)
                mechanic.current_longitude = float(longitude)
                mechanic.save()
                messages.success(request, f'Location updated for {mechanic.get_name()}')
            except Exception as e:
                messages.error(request, f'Error updating location: {str(e)}')
                
        elif 'find_mechanics' in request.POST:
            customer_lat = float(request.POST.get('customer_lat'))
            customer_lon = float(request.POST.get('customer_lon'))
            radius = int(request.POST.get('radius', 50))
            
            # Find nearest mechanics using KNN
            try:
                from .utils import get_nearest_mechanics
                nearest_mechanics = get_nearest_mechanics(customer_lat, customer_lon, radius)
                request.session['nearest_mechanics'] = nearest_mechanics
                messages.success(request, f'Found {len(nearest_mechanics)} mechanics within {radius}km')
            except Exception as e:
                messages.error(request, f'Error finding mechanics: {str(e)}')
                nearest_mechanics = []
    
    # Get all customers and mechanics
    customers = models.Customer.objects.all()
    mechanics = models.Mechanic.objects.all()
    
    # Calculate location statistics
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
    
    # Get nearest mechanics from session if available
    nearest_mechanics = request.session.get('nearest_mechanics', [])
    
    context = {
        'customers': customers,
        'mechanics': mechanics,
        'location_stats': location_stats,
        'nearest_mechanics': nearest_mechanics,
    }
    
    return render(request, 'vehicle/admin_location_tracking.html', context)
