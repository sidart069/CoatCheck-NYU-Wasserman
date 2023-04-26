
from flask import Flask, render_template, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import date
from datetime import time
from datetime import timedelta
import os
import requests


# Initialize the Flask application
app = Flask(__name__)


app.config['SECRET_KEY'] = 'insert_key_here'
app.config['MAILGUN_API_KEY'] = 'insert_key_here'
app.config['MAILGUN_DOMAIN'] = 'insert_key_here'

# Set up the Google Sheets API credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('secret_client.json', scope)
client = gspread.authorize(creds)


# Define the index page
@app.route('/')
def index():
    return render_template('index.html')


# Define the Borrow Coat page
@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        email = request.form['email']
        if not email.endswith('@nyu.edu'):
            # If the email does not end with the domain "nyu.edu", return an error message
            return 'Invalid email domain. Please enter an email with the domain "@nyu.edu"'

        coat_number = request.form['coat_number']
        sheet = client.open('CoatDatabase').sheet1
        coat_entries = sheet.col_values(2)
        coat_row = None
        for i, entry in enumerate(coat_entries):
            if entry == str(coat_number):
                coat_row = i + 1  # add 1 to account for header row

        if coat_row is None:
            # If the coat number was not found, return an error message
            return 'Invalid coat number'

        allocated_flag= sheet.cell(int(coat_row), 3).value
        allocated_email = sheet.cell(int(coat_row), 1).value
        #print(allocated_flag)
        if allocated_flag=='Allocated':
        	return f'Invalid coat, sorry this coat is already taken by {allocated_email}, try another coat. :)'
        
        # Update the status, email, date, and return date columns for the borrowed coat
        today = datetime.today().strftime('%Y-%m-%d')
        update_values = [email, 'allocated', today]
        

        sheet.update_cell(coat_row, 1, email)
        sheet.update_cell(coat_row, 3, 'Allocated')
        sheet.update_cell(coat_row, 4, today)
        row = sheet.row_values(coat_row)
        total_users = int(row[5])
        sheet.update_cell(coat_row, 6, total_users + 1)

        message = f'The coat number {coat_number} has been allocated to {email}. Thankyou :)'
        response=requests.post('https://api.mailgun.net/v3/{}/messages'.format(app.config['MAILGUN_DOMAIN']),
                      auth=('api', app.config['MAILGUN_API_KEY']),
                      data={'from': 'nyu_wasstech@nyu.com',
                            'to': email,
                            'subject': 'Coat Allocation Confirmation',
                            'text': message})

        sheet_2= client.open('CoatDatabase').worksheet('Sheet2')
        sheet_2.append_row([email, coat_number,today])
        
        return render_template('borrow_success.html', coat_number=coat_number, email=email)
    return render_template('borrow.html')


# Define the Return Coat page

@app.route('/return', methods=['GET', 'POST'])
def return_coat():
    if request.method == 'POST':
        coat_number = request.form['coat_number']
        sheet = client.open('CoatDatabase').sheet1
        cell = sheet.find(coat_number)
        row = cell.row
        sheet.update_cell(row, 3, 'Available')
        sheet.update_cell(row, 1, 'NA')
        sheet.update_cell(row, 4, 'NA')
        message = f'Thank you for returning coat number {coat_number}.'
        '''
        requests.post('https://api.mailgun.net/v3/{}/messages'.format(app.config['MAILGUN_DOMAIN']),
                      auth=('api', app.config['MAILGUN_API_KEY']),
                      data={'from': 'nyu_wasstech@nyu.com',
                            'to': sheet.cell(row, 1).value,
                            'subject': 'Coat Return Confirmation',
                            'text': message})
        '''
        return render_template('return_success.html', coat_number=coat_number)
    return render_template('return.html')

# Run the Flask application


if __name__ == '__main__':
    app.run()
