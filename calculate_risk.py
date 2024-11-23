import pandas as pd
import numpy as np
from datetime import datetime
import re
import requests
import pandas as pd
from joblib import Parallel, delayed
import time


def clean_text(text):
    return re.sub(r'[^\w\s]', '', str(text)).lower().strip()


def extract_words(url):
    # Remove protocol (http:// or https://)
    url = re.sub(r'^https?://', '', url)

    # Remove www. if present
    url = re.sub(r'^www\.', '', url)

    # Replace common separators with spaces
    url = re.sub(r'[/\-_=.]', ' ', url)

    # Remove any remaining non-alphanumeric characters
    url = re.sub(r'[^a-zA-Z0-9\s]', '', url)

    # Convert to lowercase and split into words
    words = url.lower().split()

    return words


def calculate_economic_zone_score(economic_zone):
    economic_zone_scores = {
        'Dubai Department of Economic Development': 15,
        'Abu Dhabi Department for Economic Development': 15,
        'Head Office-Fujairah Municipality': 5,
        'Masdar': 5,
        'Sharjah Economic Development Department': 15,
        'ADAFZ': 10,
        'ADGM': 30,
        'Ajman Department of Economic Development': 15,
        'Ajman Media City Free Zone': 10,
        'DAFZA': 10,
        'DCCA': 10,
        'Department of Economic Development in Abu Dhabi': 15,
        'Department of Economic Development in Dubai': 15,
        'DHCC': 10,
        'Dibba Municipality': 5,
        'DIFC': 30,
        'DMCC': 10,
        'DSO': 10,
        'Dubai CommerCity': 10,
        'Dubai Department of Economy & Tourism': 10,
        'DWTC': 10,
        'Fujairah Free Zone': 10,
        'Hamriyah Free Zone Authority': 5,
        'Dubai South': 5,
        'Jafza': 10,
        'KIZAD': 10,
        'Meydan': 5,
        'Ras Al Khaimah Department of Economic Development': 15,
        'Ras Al Khaimah Economic Zone': 15,
        'Saif Free Zone': 10,
        'Sharjah Media City': 5,
        'Sharjah Publishing City Free Zone': 5,
        'Trakhees Dubai FZ': 10,
        'TRAKHEES-Department of Planning and Development': 10,
        'Umm Al Quwain Department of Economic Development': 15,
        'Umm Al Quwain Free Trade Zone': 5
    }
    return economic_zone_scores.get(economic_zone, 0)


def calculate_date_of_operations_score(est_date, expiry_date):
    if pd.isnull(est_date) or pd.isnull(expiry_date):
        return 0
    est_date = pd.to_datetime(est_date)
    expiry_date = pd.to_datetime(expiry_date)
    years_of_operation = (expiry_date - est_date).days / 365.25
    if years_of_operation > 3:
        return 15
    elif 1 <= years_of_operation <= 3:
        return 5
    return 0


def calculate_status_score(status):
    return 10 if status == 'Active' else -50


def calculate_legal_type_score(legal_type):
    legal_type_scores = {
        'Branch of a foreign establishment': 20,
        'Branch of Company Registered in other emirates': 5,
        'Civil Company': 20,
        'Companie Branches': 5,
        'Establishments': 5,
        'Limited Liability Company': 5,
        'Single Person Company': 0,
        'Branch of Company Registered in free zone': 20,
        'Branch of Foreign Company': 20,
        'Branch of Local Company': 5,
        'Company limited by shares': 5,
        'Cooperative societies': 5,
        'Free Zone Company': 5,
        'Free Zone Company Branch': 5,
        'Free Zone Corporate': 5,
        'Free Zone Establishment': 5,
        'GCC Company Branch': 5,
        'Limited Liability Company - Single Owner(LLC - SO)': 5,
        'Private Shareholding Company': 20,
        'Public Shareholding Company': 20
    }
    return legal_type_scores.get(legal_type, 0)


def calculate_wps_score(wps_status):
    wps_status = str(wps_status).upper()
    if wps_status in ['PRIVATE', 'private', 'N', 'N/', 'N/A', 'NA', '']:
        return 10

    negative_patterns = [
        '*SALARY STAMENT,', '*STOP NEW WORK PERMIT - WPS', 'CANCEL COMPANY',
        '*COMPANY HAVING FINE,', '*TAWTEEN - NEW WP BLOCK,',
        '*STOPPED FOR EXPIRED LABOUR CARD FOR MORE THAN 6 MONTHS,',
        '*COMMUNICATION INFO REQUIRED,', '*HIGH RISK COMPANY,',
        '*TRANSACTION OF LABOUR CARD IS PENDING IN MOL,',
        '*WORKPERMIT UNDER CANCELLATION MORE THAN ONE MONTH,',
        '*WORKPERMIT UNDER CANCELLATION MORE THAN SIX MONTHS,',
        'NO ACTIVE OWNERS;', 'NO AUTHORIZED OWNER;', 'NO ACTIVE ESIGNATURE CARD;',
        'NO TRADES FOR THE COMPANY;', '*COMPANY BLOCKED FOR LABOUR CAMP REQUIREMENT,',
        '*COMPANY HAS FINE INSTALLMENTS,', '*STOPPED BY ADPF,',
        '*INSTALLMENT NOT PAID AT TIME,'
    ]

    for pattern in negative_patterns:
        if pattern in wps_status:
            return -10

    return 0


def calculate_visa_ratio_score(visa_approved, visa_cancelled, visa_requested, visa_used):
    visa_score = 0
    total_visas = visa_approved + visa_cancelled
    if total_visas > 0:
        cancellation_ratio = visa_cancelled / total_visas
        unused_ratio = (visa_approved - visa_used) / visa_approved if visa_approved > 0 else 0
        request_approval_ratio = visa_requested / visa_approved if visa_approved > 0 else float('inf')

        if cancellation_ratio > 0.3:
            visa_score -= 15
        if unused_ratio > 0.5:
            visa_score -= 10
        if request_approval_ratio > 2:
            visa_score -= 5

        if visa_approved > 50 and visa_used / visa_approved > 0.8:
            visa_score += 10

    return visa_score


def calculate_visa_number_score(visa_approved, visa_cancelled):
    visa_number = visa_approved + visa_cancelled
    if pd.isnull(visa_number):
        return 0  # NA case
    if visa_number > 50:
        return 20  # More than 50 Visas
    elif visa_number > 0:
        return 10  # Less than 50 Visas (but more than 0)
    else:
        return 0  # 0 Visas


def calculate_phone_score(phone_number):
    if pd.isnull(phone_number):
        return 0

    # Convert to string, handling potential float values
    phone_str = str(phone_number)

    # Remove any decimal point and following digits
    phone_str = phone_str.split('.')[0]

    # Strip any whitespace and remove any non-digit characters
    phone_str = ''.join(filter(str.isdigit, phone_str.strip()))

    if not phone_str:
        return 0

    # Check for UAE cell phone numbers
    if phone_str.startswith('9715') or (phone_str.startswith('05') and len(phone_str) == 10):
        return 5  # UAE cell phone

    # Check for other UAE numbers (assumed to be landlines)
    if phone_str.startswith('971') or phone_str.startswith('0'):
        return 20  # UAE landline

    return 5  # Other international number


def calculate_website_score(website):
    if pd.isnull(website) or str(website).strip() == '':
        return 0
    return 10


def calculate_email_score(email):
    if pd.isnull(email) or str(email).strip() == '':
        return -10  # Penalize if email is not found

    email = str(email).lower().strip()

    # List of common public email domains
    public_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']

    # Check if the email uses a public domain
    if any(email.endswith('@' + domain) for domain in public_domains):
        return -5  # Penalize if email is from a public domain

    # Check if it's a valid email format and not a public domain
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) and not any(
            email.endswith('@' + domain) for domain in public_domains):
        return 5  # Reward if it's a valid email with a company domain

    return 0  # Neutral score for any other case


def calculate_branch_score(is_branch):
    return 5 if is_branch.lower() == 'yes' else 0


def calculate_risk_score(row):
    scores = {}
    weights = {
        'Economic Zone': 0.15,
        'Date of Operations': 0.30,
        'Status': 0.10,
        'Legal Type': 0.10,
        'WPS': 0.05,
        'Visa Number': 0.30,
        'Visa Ratio': 0.30,
        'Phone': 0.10,
        'Website': 0.10,
        'Email': 0.10,  # New weight for email
        'Branch': 0.10  # New weight for branch factor
    }

    scores['Economic Zone_raw'] = calculate_economic_zone_score(row.get('economic_department', ''))
    scores['Economic Zone'] = scores['Economic Zone_raw'] * weights['Economic Zone']

    scores['Date of Operations_raw'] = calculate_date_of_operations_score(row.get('est_date'), row.get('expiry_date'))
    scores['Date of Operations'] = scores['Date of Operations_raw'] * weights['Date of Operations']

    scores['Status_raw'] = calculate_status_score(row.get('status', ''))
    scores['Status'] = scores['Status_raw'] * weights['Status']

    scores['Legal Type_raw'] = calculate_legal_type_score(row.get('legal_type', ''))
    scores['Legal Type'] = scores['Legal Type_raw'] * weights['Legal Type']

    scores['WPS_raw'] = calculate_wps_score(row.get('wps', ''))
    scores['WPS'] = scores['WPS_raw'] * weights['WPS']

    # Visa score calculations
    visa_approved = row.get('visa_approved', 0)
    visa_cancelled = row.get('visa_cancelled', 0)
    visa_requested = row.get('visa_requested', 0)
    visa_used = row.get('visa_used', 0)

    scores['Visa Ratio_raw'] = calculate_visa_ratio_score(visa_approved, visa_cancelled, visa_requested, visa_used)
    scores['Visa Ratio'] = scores['Visa Ratio_raw'] * weights['Visa Ratio']

    scores['Visa Number_raw'] = calculate_visa_number_score(visa_approved, visa_cancelled)
    scores['Visa Number'] = scores['Visa Number_raw'] * weights['Visa Number']

    # Branch score calculation
    scores['Branch_raw'] = calculate_branch_score(row.get('is_branch', False))
    scores['Branch'] = scores['Branch_raw'] * weights['Branch']

    # Phone score calculation
    phone_no = row.get('phone_no')
    mobile_no = row.get('mobile_no')

    if pd.notnull(phone_no) and str(phone_no).strip():
        phone_number = phone_no
    elif pd.notnull(mobile_no) and str(mobile_no).strip():
        phone_number = mobile_no
    else:
        phone_number = ''

    scores['Phone_raw'] = calculate_phone_score(phone_number)
    scores['Phone'] = scores['Phone_raw'] * weights['Phone']

    scores['Website_raw'] = calculate_website_score(row.get('website', ''))
    scores['Website'] = scores['Website_raw'] * weights['Website']

    scores['Email_raw'] = calculate_email_score(row.get('email', ''))
    scores['Email'] = scores['Email_raw'] * weights['Email']

    scores['Total_raw'] = sum(scores[k + '_raw'] for k in weights.keys())
    scores['Total_weight_adjusted'] = sum(scores[k] for k in weights.keys())

    return scores


# Load the Excel file
df_org = pd.read_excel('./data/appro-companies.xlsx', engine='openpyxl')
df_extended = pd.read_csv('./data/3k_extended.csv')

df = pd.concat([df_org, df_extended], ignore_index=True)
df.reset_index(drop= True, inplace=True)

# Print column names and first few rows
print("Column names:")
print(df.columns.tolist())
print("\nFirst few rows:")
print(df.head())

# Define a batch size
batch_size = int(round((len(df) / 8 + 1), 0))  # For example, to create 8 batches
print(batch_size)

all_risk_scores = []
start_time_apply = time.time()
# Process in batches
for i in range(0, len(df), batch_size):
    batch = df.iloc[i:i + batch_size]
    risk_scores_batch = Parallel(n_jobs=-1)(delayed(calculate_risk_score)(row) for _, row in batch.iterrows())
    # Append the results of the current batch to the overall results list
    all_risk_scores.extend(risk_scores_batch)

end_time_apply = time.time()
# Calculate execution times
parallel_time = end_time_apply - start_time_apply

print(f"Parallel execution time: {parallel_time:.4f} seconds")

risk_scores = pd.Series(all_risk_scores)

# Convert the list of dictionaries to a DataFrame
risk_score_df = pd.DataFrame(risk_scores.tolist())

# Concatenate the original DataFrame with the risk score DataFrame
df_with_scores = pd.concat([df, risk_score_df], axis=1)

# Sort companies by total risk score (highest to lowest)
df_sorted = df_with_scores.sort_values('Total_weight_adjusted', ascending=False)

# Save results to a new Excel file
df_sorted.to_excel('./data/company_risk_scores.xlsx', index=False, engine='openpyxl')

print("Risk scores calculated and saved to 'company_risk_scores.xlsx'")
