from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('index.html')


@app.route("/about", methods=['POST'])
def about():
    return render_template('www.intellipaat.com')


@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['employee_id']
    employee_name = request.form['employee_name']
    contact = request.form['contact']
    email = request.form['email']
    position = request.form['position']
    payscale = request.form['payscale']
    hiredDate = request.form['hiredDate']
    emp_image_file = request.files['image']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, employee_name, contact, email, position,payscale,hiredDate))
        db_conn.commit()
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp_id_" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

#get employee
@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    if request.method == 'POST':
        emp_id = request.form['query_employee_id']

        # Fetch employee data from the database
        select_sql = "SELECT * FROM employee WHERE employee_id = %s"
        cursor = db_conn.cursor()
        cursor.execute(select_sql, (emp_id))
        employee = cursor.fetchone()
        cursor.close()

        if employee:
            emp_id, employee_name, contact, email, position,payscale,hiredDate = employee
            emp_image_file_name_in_s3 = "emp_id_{0}_image_file".format(emp_id)

            # Download image URL from S3
            s3 = boto3.client('s3')
            bucket_location = s3.get_bucket_location(Bucket=custombucket)
            s3_location = bucket_location['LocationConstraint']
            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location
            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

            return render_template('GetEmpOutput.html', name=employee_name, contact=contact, email = email, position = position, payscale=payscale, hiredDate=hiredDate, image_url = object_url)
        else:
            return "Employee not found"

    return render_template('GetEmpInput.html')

##delete employee
@app.route("/deleteemp", methods=['GET', 'POST'])
def DeleteEmp():
    if request.method == 'POST':
        emp_id = request.form['delete_employee_id']

        # Delete employee record from the database
        delete_sql = "DELETE FROM employee WHERE employee_id = %s"
        cursor = db_conn.cursor()
        cursor.execute(delete_sql, (emp_id,))
        db_conn.commit()

        deleted_rows = cursor.rowcount
        cursor.close()

        # Delete employee image from S3
        if deleted_rows > 0:
            emp_image_file_name_in_s3 = "emp_id_{0}_image_file".format(emp_id)
            s3 = boto3.client('s3')

            try:
                s3.delete_object(Bucket=custombucket, Key=emp_image_file_name_in_s3)
                return "Employee and their image have been successfully deleted."
            except Exception as e:
                return f"Employee deleted, but there was an issue deleting the image: {str(e)}"
        else:
            return "Employee not found or already deleted."

    return render_template('DeleteEmpInput.html')

#updateemployee
@app.route("/updateemp", methods=['GET', 'POST'])
def UpdateEmp():
    if request.method == 'POST':
        emp_id = request.form['update_employee_id']
        employee_name = request.form['update_employee_name']
        contact = request.form['update_payroll']
        email = request.form['email']
        position = request.form['position']
        payscale = request.form['payscale']
        emp_image_file = request.files['emp_image_file']

        # Update employee record in the database
        update_sql = """UPDATE employee SET employee_name = %s, contact = %s,
                        email = %s, position = %s,payscale = %s WHERE emp_id = %s"""
        cursor = db_conn.cursor()
        cursor.execute(update_sql, (employee_name, contact, email, position, payscale,emp_id))
        db_conn.commit()

        updated_rows = cursor.rowcount
        cursor.close()
        
        if updated_rows > 0:
            # Update employee image in S3
            emp_image_file_name_in_s3 = "emp_id_{0}_image_file".format(emp_id)
            s3 = boto3.client('s3')

            try:
                if emp_image_file.filename != "":
                    # Delete existing image file
                    s3.delete_object(Bucket=custombucket, Key=emp_image_file_name_in_s3)
                    # Upload new image file
                    s3.upload_fileobj(emp_image_file, custombucket, emp_image_file_name_in_s3)
                return "Employee information and image have been successfully updated."
            except Exception as e:
                return f"Employee information updated, but there was an issue updating the image: {str(e)}"
        else:
            return "Employee not found or no changes made."

    return render_template('UpdateEmpInput.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

